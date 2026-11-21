import time
import re
from urllib.parse import urlparse
from typing import Dict, Any, List
from app.services.llm.base import BaseLLMProvider, LLMResult
from app.services.crawler import CleanedWebsiteContent

class MockLLMProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "mock-engine-v1"):
        self._model = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    async def analyze(self, content: CleanedWebsiteContent) -> LLMResult:
        start_time = time.perf_counter()

        # Extract brand cues from domain or title
        domain = urlparse(content.url).netloc.replace("www.", "")
        brand_candidate = content.title.split("|")[0].split("-")[0].strip() if content.title else domain.capitalize()
        if not brand_candidate:
            brand_candidate = domain.split(".")[0].capitalize()

        # Identify services cues from headings
        raw_headings = content.headings.get("h2", []) + content.headings.get("h1", [])
        identified_services: List[str] = []
        for h in raw_headings:
            if 3 < len(h) < 60 and not any(skip in h.lower() for skip in ("cookie", "privacy", "menu", "sign in", "login")):
                identified_services.append(h)
                if len(identified_services) >= 4:
                    break

        if not identified_services:
            identified_services = [
                f"{brand_candidate} Core Platform Services",
                f"{brand_candidate} Integration & Automation",
                f"{brand_candidate} Enterprise Operations"
            ]

        # Safely extract sample heading
        h1_list = content.headings.get("h1", [])
        h1_topic = h1_list[0][:30] if h1_list else "business automation"

        # Construct realistic structured JSON
        mock_data: Dict[str, Any] = {
            "competitor_analysis": {
                "brand_name": brand_candidate,
                "brand_overview": f"[MOCK ANALYSIS] {brand_candidate} operates on {domain}. Extracted title: '{content.title}'. Specializes in modern digital services.",
                "category": "Technology, Software & Digital Services",
                "products_and_services": identified_services,
                "competitors": [
                    {
                        "name": "Competitor Alpha",
                        "overview": "Leading market incumbent providing scaled software solutions.",
                        "strengths": ["Extensive enterprise distribution", "Broad feature portfolio"],
                        "weaknesses": ["Legacy codebase", "Higher implementation pricing"],
                        "market_gaps": ["Rapid lightweight deployments", "Bespoke developer experience"],
                        "source_url": "https://example.com/competitor-alpha",
                        "is_verified": False
                    },
                    {
                        "name": "Competitor Beta",
                        "overview": "Cloud-native challenger with high automation focus.",
                        "strengths": ["Modern user interface", "Competitive self-serve tier"],
                        "weaknesses": ["Limited international compliance support"],
                        "market_gaps": ["Tailored white-glove onboarding for mid-market"],
                        "source_url": "https://example.com/competitor-beta",
                        "is_verified": False
                    },
                    {
                        "name": "Competitor Gamma",
                        "overview": "Boutique specialized consulting and engineering vendor.",
                        "strengths": ["High technical depth", "Agile delivery cycles"],
                        "weaknesses": ["Smaller team capacity for global 24/7 SLAs"],
                        "market_gaps": ["Integrated SaaS tooling combined with advisory"],
                        "source_url": "https://example.com/competitor-gamma",
                        "is_verified": False
                    }
                ],
                "brand_competitive_advantages": [
                    f"Direct focused architecture tailored to {brand_candidate}'s target niche",
                    "Agile and transparent service delivery",
                    "High responsiveness and personalized customer support"
                ],
                "market_positioning_opportunities": [
                    "Position as the agile, high-performance alternative to legacy players",
                    "Target underserved mid-market organizations seeking modern AI and API workflows"
                ],
                "verified_information": [
                    f"Verified Title: {content.title or 'N/A'}",
                    f"Verified Domain: {domain}",
                    f"Verified Headings Count: {len(content.headings.get('h1', [])) + len(content.headings.get('h2', []))}"
                ],
                "ai_generated_suggestions": [
                    "[MOCK ENGINE NOTE] This is synthetic strategic data generated for local testing without active API credits.",
                    "Develop specialized comparison landing pages against key competitors"
                ]
            },
            "target_search_queries": {
                "queries": [
                    {
                        "query": f"best {domain.split('.')[0]} alternatives for modern engineering",
                        "relevant_platforms": ["Google", "LinkedIn", "X"],
                        "search_intent": "Commercial",
                        "business_relevance": f"Attracts high-intent prospects comparing solutions against {brand_candidate}.",
                        "target_audience": "Technical Decision Makers, Engineering Directors"
                    },
                    {
                        "query": f"how to implement {identified_services[0]} efficiently",
                        "relevant_platforms": ["Google", "LinkedIn"],
                        "search_intent": "Informational",
                        "business_relevance": "Builds thought leadership and captures early research funnel traffic.",
                        "target_audience": "Software Architects, Product Leads"
                    },
                    {
                        "query": f"{brand_candidate} customer case studies and pricing",
                        "relevant_platforms": ["Google", "Facebook"],
                        "search_intent": "Navigational",
                        "business_relevance": "Protects branded queries and accelerates inbound conversion.",
                        "target_audience": "Procurement Officers, CTOs"
                    },
                    {
                        "query": f"top enterprise tools for {h1_topic}",
                        "relevant_platforms": ["LinkedIn", "X", "Google"],
                        "search_intent": "Commercial",
                        "business_relevance": "Drives discoverability in category-defining technology evaluations.",
                        "target_audience": "Enterprise Operations Managers, CIOs"
                    },
                    {
                        "query": f"fast API integration with {brand_candidate} platform",
                        "relevant_platforms": ["Google", "Instagram"],
                        "search_intent": "Transactional",
                        "business_relevance": "Direct conversion path for developers seeking ready-to-use APIs.",
                        "target_audience": "Backend Engineers, Tech Founders"
                    }
                ]
            },
            "seo_improvements": {
                "keywords": {
                    "primary_keywords": [brand_candidate.lower(), f"{domain.split('.')[0]} platform", "cloud software engineering"],
                    "secondary_keywords": ["automated link analysis", "API integration", "enterprise software solutions"],
                    "long_tail_keywords": [f"how to choose the best {domain.split('.')[0]} solution for enterprise", "scalable python api architecture"],
                    "business_keywords": [brand_candidate, f"{brand_candidate} official website", f"{domain}"]
                },
                "recommended_title": f"{brand_candidate} | Modern AI & Digital Architecture Solutions"[:60],
                "recommended_meta_description": f"Empower your business with {brand_candidate}. Explore advanced solutions, reliable integration, and industry-leading performance on {domain}."[:160],
                "supporting_content_suggestions": {
                    "service_landing_pages": [f"/services/{s.lower().replace(' ', '-')[:25]}" for s in identified_services[:3]],
                    "industry_pages": ["/industries/saas", "/industries/financial-services", "/industries/healthcare-tech"],
                    "faqs": [
                        f"How does {brand_candidate} ensure security and uptime?",
                        "What is the expected timeline for API integration?",
                        "What support and SLA packages are available?"
                    ],
                    "blogs": [
                        "Top Trends in Modern Cloud Architecture for 2026",
                        "Why High-Performance APIs are Critical for Digital Scale",
                        "A Guide to SSRF Security and Web Scraping Best Practices"
                    ],
                    "location_pages": ["/regions/north-america", "/regions/europe"]
                },
                "technical_and_onpage_notes": [
                    "Implement JSON-LD Schema.org 'Organization' and 'WebSite' markup.",
                    "Ensure all image assets have descriptive alt attributes.",
                    "Enhance Core Web Vitals, specifically Cumulative Layout Shift (CLS)."
                ]
            },
            "top_services": {
                "services": [
                    {
                        "service_name": s[:50],
                        "description": f"Professional offering addressing {s} for modern digital operations.",
                        "target_industry": "Information Technology & Enterprise Services",
                        "target_customer": "Technical Leads & Business Executives",
                        "main_benefit": "Accelerates time-to-market while reducing operational overhead.",
                        "is_explicitly_stated": True if i == 0 else False,
                        "evidence_or_source": f"Observed in website headings on {domain}"
                    }
                    for i, s in enumerate(identified_services[:5])
                ]
            },
            "target_audience": {
                "primary_audience": "Technology leaders, Product Managers, and Backend Architects seeking scalable solutions.",
                "secondary_audience": "Growing SMBs and scale-ups requiring dependable digital transformation partner.",
                "industry_segments": ["SaaS & Cloud Platforms", "FinTech", "Professional Services", "E-Commerce"],
                "business_types": ["B2B Mid-Market", "Enterprise", "High-growth Startups"],
                "customer_profiles": ["CTO", "VP of Engineering", "Head of Digital Strategy", "Principal Architect"],
                "geographic_focus": "Global with high adoption in North America and Western Europe.",
                "customer_needs": [
                    "High reliability and low-latency digital operations",
                    "Seamless API connectivity and strict data compliance"
                ],
                "customer_challenges": [
                    "Vendor lock-in and excessive pricing from legacy providers",
                    "Shortage of internal senior engineering bandwidth"
                ],
                "customer_interests": ["FastAPI", "Cloud Scalability", "SSRF Defense", "LLM Integration"],
                "recommended_marketing_segments": [
                    "Enterprise Technology Buyers",
                    "Cloud Engineering Leaders",
                    "Founder-led Tech Scale-ups"
                ],
                "extracted_facts": [
                    f"Website Title: {content.title or 'N/A'}",
                    f"Total Characters Extracted: {content.total_characters}"
                ],
                "ai_inferences": [
                    "[MOCK INFERENCE] Target persona focuses on engineering excellence and cost predictability.",
                    "[MOCK INFERENCE] Organization benefits from clear technical documentation and live demo endpoints."
                ]
            }
        }

        latency = (time.perf_counter() - start_time) * 1000.0

        # Synthetic token simulation
        input_tokens = max(100, content.total_characters // 4)
        output_tokens = 950

        return LLMResult(
            data=mock_data,
            provider="mock",
            model=self._model,
            is_mock=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=0.0,
            latency_ms=round(latency, 2)
        )
