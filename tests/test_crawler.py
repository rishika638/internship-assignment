import pytest
import httpx
from fastapi import HTTPException
from app.services.crawler import WebsiteCrawler

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Acme Software | Enterprise Cloud AI</title>
    <meta name="description" content="Leading AI platform for enterprise developers.">
    <meta name="keywords" content="AI, Enterprise, Cloud, FastAPI">
    <meta property="og:title" content="Acme Software Platform">
    <meta property="og:description" content="Build apps faster with Acme.">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Acme Software",
        "url": "https://acme.example.com"
    }
    </script>
    <style>body { color: red; }</style>
    <script>alert("tracking code");</script>
</head>
<body>
    <header>Header content to drop</header>
    <nav><a href="/about">About Us</a><a href="/services">Our Services</a><a href="https://external.com">External</a></nav>
    <main>
        <h1>Welcome to Acme Software</h1>
        <h2>Scalable Cloud Intelligence</h2>
        <p>Acme Software provides state-of-the-art intelligent infrastructure for modern enterprises.</p>
        <p>Our distributed architecture ensures that high workloads execute with low latency and robust fault tolerance.</p>
        <h2>Enterprise Integrations</h2>
        <p>Connect with your existing data warehouses, Kubernetes clusters, and observability stacks effortlessly.</p>
    </main>
    <footer>Contact us at info@acme.example.com or +1 800-555-0199</footer>
</body>
</html>
"""

def test_clean_and_extract_html():
    crawler = WebsiteCrawler()
    extracted = crawler.clean_and_extract_html(SAMPLE_HTML, "https://acme.example.com")

    assert extracted["title"] == "Acme Software | Enterprise Cloud AI"
    assert "Leading AI platform" in extracted["meta_description"]
    assert "FastAPI" in extracted["meta_keywords"]
    assert extracted["open_graph"].get("og:title") == "Acme Software Platform"
    
    # Check Schema.org
    assert len(extracted["schema_org"]) == 1
    assert extracted["schema_org"][0]["name"] == "Acme Software"

    # Check Headings
    assert "Welcome to Acme Software" in extracted["headings"]["h1"]
    assert "Scalable Cloud Intelligence" in extracted["headings"]["h2"]

    # Verify script, style, header, footer stripped from main text
    assert "tracking code" not in extracted["body_text"]
    assert "color: red" not in extracted["body_text"]

    # Check contact cues
    assert "info@acme.example.com" in extracted["contact_cues"]["emails"]

    # Check discovered internal links
    assert "https://acme.example.com/about" in extracted["discovered_cues_links"]["about"]
    assert "https://acme.example.com/services" in extracted["discovered_cues_links"]["services"]

@pytest.mark.asyncio
async def test_crawler_handles_inaccessible_website(monkeypatch):
    crawler = WebsiteCrawler()

    # Mock validate_url_security to succeed so execution reaches network fetch
    monkeypatch.setattr("app.services.crawler.enforce_safe_url", lambda url: None)

    # Mock client.get to raise ConnectError
    async def mock_get(*args, **kwargs):
        raise httpx.ConnectError("Connection refused by peer", request=httpx.Request("GET", "https://example.com"))

    async with httpx.AsyncClient() as client:
        monkeypatch.setattr(client, "get", mock_get)
        with pytest.raises(HTTPException) as excinfo:
            await crawler.fetch_with_safe_redirects(client, "https://example.com")
        assert excinfo.value.status_code == 502
        assert "CONNECTION_FAILED" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_crawler_handles_timeout(monkeypatch):
    crawler = WebsiteCrawler()

    async def mock_timeout(*args, **kwargs):
        raise httpx.TimeoutException("Timed out waiting for response", request=httpx.Request("GET", "https://slow-site.com"))

    async with httpx.AsyncClient() as client:
        monkeypatch.setattr(client, "get", mock_timeout)
        with pytest.raises(HTTPException) as excinfo:
            await crawler.fetch_with_safe_redirects(client, "https://slow-site.com")
        assert excinfo.value.status_code == 504
        assert "FETCH_TIMEOUT" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_crawler_blocks_unsafe_redirect(monkeypatch):
    crawler = WebsiteCrawler()

    class MockRedirectResponse:
        status_code = 302
        headers = {"location": "http://169.254.169.254/latest/meta-data"}
        url = httpx.URL("https://legit-site.com")

    first_call = True
    async def mock_redirect(*args, **kwargs):
        nonlocal first_call
        if first_call:
            first_call = False
            return MockRedirectResponse()
        return None

    async with httpx.AsyncClient() as client:
        monkeypatch.setattr(client, "get", mock_redirect)
        # Should raise 400 bad request due to SSRF guard detecting link-local redirect
        with pytest.raises(HTTPException) as excinfo:
            await crawler.fetch_with_safe_redirects(client, "https://legit-site.com")
        assert excinfo.value.status_code == 400
        assert "SSRF_SECURITY_VIOLATION" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_real_website_crawler_integration():
    """Live integration test against the RFC 2606 reserved example.com domain."""
    crawler = WebsiteCrawler()
    content = await crawler.crawl("https://example.com")
    assert content.url == "https://example.com"
    assert "Example Domain" in content.title or "example" in content.body_text.lower()
    assert content.total_characters > 50
    assert len(content.content_hash) == 64  # SHA-256 length
