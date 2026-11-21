import pytest
from app.services.crawler import CleanedWebsiteContent
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.factory import LLMProviderFactory
from app.schemas import (
    CompetitorVsBrandAnalysis,
    Top5TargetSearchQueries,
    SEOImprovements,
    Top5Services,
    TargetAudience,
)

SAMPLE_CLEAN_CONTENT = CleanedWebsiteContent(
    url="https://dxora.com",
    final_url="https://dxora.com",
    title="Dxora Technologies | Next-Gen Software & AI",
    meta_description="Dxora delivers enterprise digital transformation.",
    headings={
        "h1": ["Enterprise Software Solutions"],
        "h2": ["Custom AI Models", "Cloud Migration", "Full Stack Engineering"]
    },
    body_text="Dxora Technologies provides high-performance AI integration and scalable software engineering.",
    pages_crawled=1,
    content_hash="test_content_hash_12345",
    total_characters=500
)

@pytest.mark.asyncio
async def test_mock_llm_provider_all_five_sections():
    provider = MockLLMProvider()
    result = await provider.analyze(SAMPLE_CLEAN_CONTENT)

    assert result.is_mock is True
    assert result.provider == "mock"
    assert result.latency_ms > 0

    data = result.data

    # Section A: Competitor vs Brand Analysis
    comp_analysis = CompetitorVsBrandAnalysis(**data["competitor_analysis"])
    assert len(comp_analysis.competitors) >= 3
    assert comp_analysis.brand_name != ""
    assert len(comp_analysis.verified_information) > 0
    assert len(comp_analysis.ai_generated_suggestions) > 0

    # Section B: Top 5 Target Search Queries
    queries = Top5TargetSearchQueries(**data["target_search_queries"])
    assert len(queries.queries) == 5
    for q in queries.queries:
        assert len(q.relevant_platforms) > 0
        assert q.search_intent in ("Informational", "Navigational", "Commercial", "Transactional")

    # Section C: SEO Improvements
    seo = SEOImprovements(**data["seo_improvements"])
    assert len(seo.keywords.primary_keywords) > 0
    assert len(seo.recommended_title) <= 60
    assert len(seo.recommended_meta_description) <= 160
    assert len(seo.supporting_content_suggestions.service_landing_pages) > 0

    # Section D: Top 5 Services
    services = Top5Services(**data["top_services"])
    assert 1 <= len(services.services) <= 5
    assert any(s.is_explicitly_stated for s in services.services)

    # Section E: Target Audience
    audience = TargetAudience(**data["target_audience"])
    assert audience.primary_audience != ""
    assert len(audience.industry_segments) > 0
    assert len(audience.customer_profiles) > 0
    assert len(audience.extracted_facts) > 0
    assert len(audience.ai_inferences) > 0

@pytest.mark.asyncio
async def test_llm_factory_fallback_on_missing_keys(monkeypatch):
    factory = LLMProviderFactory()
    # Force provider to Gemini with no key
    monkeypatch.setattr(factory.settings, "PRIMARY_LLM_PROVIDER", "gemini")
    monkeypatch.setattr(factory.settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(factory.settings, "FALLBACK_LLM_PROVIDER", "mock")

    provider = factory.get_provider()
    assert provider.provider_name == "mock"

    result = await factory.execute_analysis(SAMPLE_CLEAN_CONTENT)
    assert result.is_mock is True
    assert "competitor_analysis" in result.data

@pytest.mark.asyncio
async def test_llm_factory_fallback_on_primary_failure(monkeypatch):
    factory = LLMProviderFactory()
    monkeypatch.setattr(factory.settings, "PRIMARY_LLM_PROVIDER", "gemini")
    monkeypatch.setattr(factory.settings, "GEMINI_API_KEY", "fake_key_12345")
    monkeypatch.setattr(factory.settings, "FALLBACK_LLM_PROVIDER", "mock")

    # Mock primary provider analyze to raise exception
    class FailingProvider:
        provider_name = "gemini"
        model_name = "gemini-2.5-flash"
        async def analyze(self, content):
            raise RuntimeError("Gemini Quota Exceeded")

    monkeypatch.setattr(factory, "get_provider", lambda name=None: FailingProvider() if name in (None, "gemini") else MockLLMProvider())

    result = await factory.execute_analysis(SAMPLE_CLEAN_CONTENT)
    assert result.is_mock is True
    assert any("SYSTEM FALLBACK NOTICE" in s for s in result.data["competitor_analysis"]["ai_generated_suggestions"])

@pytest.mark.asyncio
async def test_gemini_retry_on_transient_error(monkeypatch):
    from app.services.llm.gemini_provider import GeminiProvider
    from google.api_core.exceptions import ServiceUnavailable

    provider = GeminiProvider(api_key="mock_key", max_retries=2, base_delay=0.01)

    call_count = 0
    class MockSuccessResponse:
        text = """{
            "competitor_analysis": {"brand_name": "Test", "brand_overview": "O", "category": "C", "products_and_services": [], "competitors": [{"name": "C1", "overview": "O", "strengths": [], "weaknesses": [], "market_gaps": [], "is_verified": false}, {"name": "C2", "overview": "O", "strengths": [], "weaknesses": [], "market_gaps": [], "is_verified": false}, {"name": "C3", "overview": "O", "strengths": [], "weaknesses": [], "market_gaps": [], "is_verified": false}], "brand_competitive_advantages": [], "market_positioning_opportunities": [], "verified_information": [], "ai_generated_suggestions": []},
            "target_search_queries": {"queries": [{"query": "q1", "relevant_platforms": ["Google"], "search_intent": "Commercial", "business_relevance": "r", "target_audience": "a"}, {"query": "q2", "relevant_platforms": ["LinkedIn"], "search_intent": "Commercial", "business_relevance": "r", "target_audience": "a"}, {"query": "q3", "relevant_platforms": ["X"], "search_intent": "Informational", "business_relevance": "r", "target_audience": "a"}, {"query": "q4", "relevant_platforms": ["Facebook"], "search_intent": "Navigational", "business_relevance": "r", "target_audience": "a"}, {"query": "q5", "relevant_platforms": ["Instagram"], "search_intent": "Transactional", "business_relevance": "r", "target_audience": "a"}]},
            "seo_improvements": {"keywords": {"primary_keywords": ["k1"], "secondary_keywords": [], "long_tail_keywords": [], "business_keywords": []}, "recommended_title": "T", "recommended_meta_description": "M", "supporting_content_suggestions": {"service_landing_pages": [], "industry_pages": [], "faqs": [], "blogs": [], "location_pages": []}, "technical_and_onpage_notes": []},
            "top_services": {"services": [{"service_name": "S1", "description": "D", "target_industry": "I", "target_customer": "C", "main_benefit": "B", "is_explicitly_stated": true}]},
            "target_audience": {"primary_audience": "P", "secondary_audience": "S", "industry_segments": [], "business_types": [], "customer_profiles": [], "geographic_focus": "G", "customer_needs": [], "customer_challenges": [], "customer_interests": [], "recommended_marketing_segments": [], "extracted_facts": [], "ai_inferences": []}
        }"""
        usage_metadata = None

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ServiceUnavailable("503 Service Unavailable")
        return MockSuccessResponse()

    monkeypatch.setattr(provider.client_model, "generate_content_async", mock_generate)

    result = await provider.analyze(SAMPLE_CLEAN_CONTENT)
    assert call_count == 2
    assert result.provider == "gemini"
    assert result.data["competitor_analysis"]["brand_name"] == "Test"
