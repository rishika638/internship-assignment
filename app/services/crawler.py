import re
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup, Comment
from fastapi import HTTPException, status

from app.config import get_settings
from app.services.ssrf import enforce_safe_url, validate_url_security
from app.utils.logger import logger

@dataclass
class CleanedWebsiteContent:
    url: str
    final_url: str
    title: str = ""
    meta_description: str = ""
    meta_keywords: List[str] = field(default_factory=list)
    open_graph: Dict[str, str] = field(default_factory=dict)
    schema_org: List[Dict[str, Any]] = field(default_factory=list)
    headings: Dict[str, List[str]] = field(default_factory=lambda: {"h1": [], "h2": [], "h3": []})
    body_text: str = ""
    services_cues: List[str] = field(default_factory=list)
    about_cues: List[str] = field(default_factory=list)
    contact_cues: Dict[str, Any] = field(default_factory=dict)
    pages_crawled: int = 1
    internal_links: List[str] = field(default_factory=list)
    content_hash: str = ""
    total_characters: int = 0

class WebsiteCrawler:
    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 DxoraLinkAnalyzer/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_with_safe_redirects(self, client: httpx.AsyncClient, start_url: str) -> httpx.Response:
        """
        Fetch URL while validating SSRF security on initial URL and every subsequent redirect location.
        """
        current_url = start_url
        max_redirects = self.settings.MAX_REDIRECTS

        for redirect_count in range(max_redirects + 1):
            enforce_safe_url(current_url)

            try:
                response = await client.get(
                    current_url,
                    headers=self.headers,
                    follow_redirects=False,
                    timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
                )
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail={"error": "FETCH_TIMEOUT", "message": f"Website timed out after {self.settings.REQUEST_TIMEOUT_SECONDS} seconds.", "url": current_url}
                )
            except httpx.ConnectError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"error": "CONNECTION_FAILED", "message": f"Failed to connect to website: {str(e)}", "url": current_url}
                )
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"error": "HTTP_FETCH_ERROR", "message": f"Error fetching website: {str(e)}", "url": current_url}
                )

            # Check response status
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={"error": "INVALID_REDIRECT", "message": "Redirect response missing Location header.", "url": current_url}
                    )
                # Resolve relative redirect URLs
                next_url = urljoin(str(response.url), location)
                logger.info(f"Redirecting from {current_url} -> {next_url}")
                current_url = next_url
                continue

            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"error": "REMOTE_HTTP_ERROR", "message": f"Target website returned HTTP {response.status_code}.", "url": current_url}
                )

            # Verify content-type is HTML or XML
            content_type = response.headers.get("content-type", "").lower()
            if not any(t in content_type for t in ("text/html", "application/xhtml+xml", "text/plain")):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": "UNSUPPORTED_CONTENT_TYPE", "message": f"Unsupported Content-Type: '{content_type}'. Expected HTML.", "url": current_url}
                )

            # Check content length limit
            content_len = len(response.content)
            if content_len > self.settings.MAX_PAGE_CONTENT_BYTES:
                logger.warning(f"Response size {content_len} bytes exceeds limit {self.settings.MAX_PAGE_CONTENT_BYTES} bytes. Truncating.")
                response._content = response.content[:self.settings.MAX_PAGE_CONTENT_BYTES]

            return response

        raise HTTPException(
            status_code=status.HTTP_508_LOOP_DETECTED,
            detail={"error": "TOO_MANY_REDIRECTS", "message": f"Exceeded maximum allowed redirects ({max_redirects}).", "url": start_url}
        )

    def clean_and_extract_html(self, html: str, base_url: str) -> Dict[str, Any]:
        """
        Parse HTML, strip irrelevant tags (scripts, styles, tracking, modals),
        extract metadata, OpenGraph, Schema.org, headings, cues, and cleaned body text.
        """
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract Schema.org JSON-LD before stripping scripts
        schema_org_data: List[Dict[str, Any]] = []
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string:
                try:
                    data = json.loads(script.string.strip())
                    if isinstance(data, list):
                        schema_org_data.extend(data[:3])
                    elif isinstance(data, dict):
                        schema_org_data.append(data)
                except Exception:
                    pass

        # 2. Extract OpenGraph & Meta
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        meta_desc = ""
        meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)}) or \
                        soup.find("meta", attrs={"property": "og:description"})
        if meta_desc_tag and meta_desc_tag.get("content"):
            meta_desc = meta_desc_tag["content"].strip()

        meta_keywords: List[str] = []
        keywords_tag = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
        if keywords_tag and keywords_tag.get("content"):
            meta_keywords = [k.strip() for k in keywords_tag["content"].split(",") if k.strip()]

        og_data: Dict[str, str] = {}
        for og_tag in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
            prop = og_tag.get("property", "").lower()
            val = og_tag.get("content", "")
            if prop and val:
                og_data[prop] = val.strip()

        # 3. Discover relevant internal navigation links
        parsed_base = urlparse(base_url)
        internal_links: Set[str] = set()
        cues_links: Dict[str, str] = {}

        for a in soup.find_all("a", href=True):
            raw_href = a["href"].strip()
            if not raw_href or raw_href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            abs_link = urljoin(base_url, raw_href)
            parsed_link = urlparse(abs_link)
            if parsed_link.netloc == parsed_base.netloc:
                clean_path = parsed_link.path.lower()
                internal_links.add(abs_link)
                if any(w in clean_path for w in ("about", "company", "who-we-are")) and "about" not in cues_links:
                    cues_links["about"] = abs_link
                elif any(w in clean_path for w in ("services", "solutions", "products", "offerings")) and "services" not in cues_links:
                    cues_links["services"] = abs_link
                elif any(w in clean_path for w in ("contact", "get-in-touch")) and "contact" not in cues_links:
                    cues_links["contact"] = abs_link

        # 4. Extract Headings
        headings: Dict[str, List[str]] = {"h1": [], "h2": [], "h3": []}
        for level in ("h1", "h2", "h3"):
            for h in soup.find_all(level):
                text = h.get_text(separator=" ", strip=True)
                if text and len(text) > 2 and text not in headings[level]:
                    headings[level].append(text)

        # 5. Extract contact cues (emails, phone numbers)
        emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)))[:5]
        phones = list(set(re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", html)))[:5]

        # 6. Remove unwanted tags
        unwanted_tags = [
            "script", "style", "noscript", "svg", "iframe", "canvas",
            "nav", "footer", "form", "select", "option", "header", "aside"
        ]
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 7. Extract main text blocks and deduplicate
        text_blocks: List[str] = []
        for elem in soup.find_all(["p", "article", "section", "li", "span", "div"]):
            block = elem.get_text(separator=" ", strip=True)
            # Filter noise and short snippets
            if len(block) > 40:
                # Deduplicate repeated phrases or blocks
                if not any(block in existing or existing in block for existing in text_blocks[-10:]):
                    text_blocks.append(block)

        raw_body_text = "\n\n".join(text_blocks)
        # Normalize whitespace
        cleaned_body = re.sub(r"\s+", " ", raw_body_text).strip()

        # Truncate cleanly if oversized for prompt token efficiency
        if len(cleaned_body) > self.settings.MAX_BODY_TEXT_CHARS:
            cleaned_body = cleaned_body[:self.settings.MAX_BODY_TEXT_CHARS] + "..."

        return {
            "title": title,
            "meta_description": meta_desc,
            "meta_keywords": meta_keywords,
            "open_graph": og_data,
            "schema_org": schema_org_data,
            "headings": headings,
            "body_text": cleaned_body,
            "internal_links": list(internal_links)[:20],
            "discovered_cues_links": cues_links,
            "contact_cues": {"emails": emails, "phones": phones},
        }

    async def crawl(self, url: str) -> CleanedWebsiteContent:
        """
        Execute full extraction pipeline:
        1. Fetch and clean landing page with SSRF security.
        2. Optionally fetch up to MAX_CRAWL_SUBPAGES (About, Services) to enrich analysis.
        3. Synthesize comprehensive content payload.
        """
        async with httpx.AsyncClient(verify=True) as client:
            # 1. Fetch Landing Page
            logger.info(f"Crawling root website: {url}")
            root_resp = await self.fetch_with_safe_redirects(client, url)
            final_url = str(root_resp.url)
            root_extracted = self.clean_and_extract_html(root_resp.text, final_url)

            if not root_extracted["body_text"] and not root_extracted["title"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": "EMPTY_WEBSITE_CONTENT", "message": "Website returned empty or non-extractable text content.", "url": url}
                )

            pages_crawled = 1
            combined_body_parts = [
                f"--- [PRIMARY PAGE: {final_url}] ---",
                f"Page Title: {root_extracted['title']}",
                f"Meta Description: {root_extracted['meta_description']}",
                f"Headings H1: {', '.join(root_extracted['headings']['h1'])}",
                f"Headings H2: {', '.join(root_extracted['headings']['h2'])}",
                f"Content Summary:\n{root_extracted['body_text']}"
            ]

            # 2. Enrich with up to MAX_CRAWL_SUBPAGES (e.g. /about, /services)
            cues_links = root_extracted["discovered_cues_links"]
            subpage_targets = [link for name, link in cues_links.items() if link != final_url]
            subpages_to_crawl = subpage_targets[:self.settings.MAX_CRAWL_SUBPAGES]

            for sub_url in subpages_to_crawl:
                try:
                    logger.info(f"Crawling enrichment subpage: {sub_url}")
                    sub_resp = await self.fetch_with_safe_redirects(client, sub_url)
                    sub_data = self.clean_and_extract_html(sub_resp.text, str(sub_resp.url))
                    if sub_data["body_text"]:
                        pages_crawled += 1
                        combined_body_parts.append(
                            f"\n--- [SUBPAGE: {sub_url}] ---\n"
                            f"Title: {sub_data['title']}\n"
                            f"Headings: {', '.join(sub_data['headings']['h1'] + sub_data['headings']['h2'])}\n"
                            f"{sub_data['body_text'][:3000]}"
                        )
                except Exception as e:
                    logger.warning(f"Skipping subpage {sub_url} due to extraction issue: {e}")

            full_body_combined = "\n\n".join(combined_body_parts)
            
            # 3. Create SHA-256 Content Hash for Caching & Deduplication
            content_hash = hashlib.sha256(full_body_combined.encode("utf-8")).hexdigest()

            return CleanedWebsiteContent(
                url=url,
                final_url=final_url,
                title=root_extracted["title"],
                meta_description=root_extracted["meta_description"],
                meta_keywords=root_extracted["meta_keywords"],
                open_graph=root_extracted["open_graph"],
                schema_org=root_extracted["schema_org"],
                headings=root_extracted["headings"],
                body_text=full_body_combined,
                pages_crawled=pages_crawled,
                internal_links=root_extracted["internal_links"],
                contact_cues=root_extracted["contact_cues"],
                content_hash=content_hash,
                total_characters=len(full_body_combined),
            )
