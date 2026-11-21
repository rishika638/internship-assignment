import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.crawler import CleanedWebsiteContent

client = TestClient(app)

MOCK_EXTRACTED_CONTENT = CleanedWebsiteContent(
    url="https://dxora.com",
    final_url="https://dxora.com",
    title="Dxora Technologies | Modern Software Engineering",
    meta_description="Enterprise AI and scalable backend solutions.",
    headings={
        "h1": ["Enterprise Software Solutions"],
        "h2": ["AI Integration", "Cloud Migration", "Full Stack Development"]
    },
    body_text="Dxora Technologies provides software engineering and modern AI development.",
    pages_crawled=1,
    content_hash="test_api_hash_45678",
    total_characters=600
)

def test_get_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Dxora AI-Powered Website Link Analysis API" in data["service"]
    assert data["documentation"] == "/docs"

def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["uptime_status"] == "healthy"

def test_post_link_analysis_ssrf_block():
    # Attempt SSRF via loopback
    response = client.post("/link-analysis", json={"url": "http://127.0.0.1:4000/admin"})
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "SSRF_SECURITY_VIOLATION"

    # Attempt SSRF via cloud metadata
    response = client.post("/link-analysis", json={"url": "http://169.254.169.254/latest/meta-data"})
    assert response.status_code == 400
    assert response.json()["error"] == "SSRF_SECURITY_VIOLATION"

@patch("app.main.crawler.crawl", new_callable=AsyncMock)
def test_post_link_analysis_success(mock_crawl):
    mock_crawl.return_value = MOCK_EXTRACTED_CONTENT

    payload = {"url": "https://dxora.com"}
    response = client.post("/link-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["url"] == "https://dxora.com"
    assert "telemetry" in data
    assert "crawl_summary" in data

    # Check 5 mandatory sections
    assert "competitor_analysis" in data
    assert len(data["competitor_analysis"]["competitors"]) >= 3
    assert data["competitor_analysis"]["brand_name"] != ""

    assert "target_search_queries" in data
    assert len(data["target_search_queries"]["queries"]) == 5

    assert "seo_improvements" in data
    assert "primary_keywords" in data["seo_improvements"]["keywords"]
    assert len(data["seo_improvements"]["recommended_title"]) <= 60

    assert "top_services" in data
    assert 1 <= len(data["top_services"]["services"]) <= 5

    assert "target_audience" in data
    assert data["target_audience"]["primary_audience"] != ""

@patch("app.main.crawler.crawl", new_callable=AsyncMock)
def test_post_link_analysis_cache_hit(mock_crawl):
    dynamic_hash = f"cache_hash_{uuid.uuid4().hex}"
    cache_test_content = CleanedWebsiteContent(
        url="https://example.com",
        final_url="https://example.com",
        title="Cache Test Example",
        meta_description="Testing cache hits and latency.",
        headings={"h1": ["Cache Test"], "h2": ["Subheading"]},
        body_text="Testing cache retention and subsequent hit verification.",
        pages_crawled=1,
        content_hash=dynamic_hash,
        total_characters=300
    )
    mock_crawl.return_value = cache_test_content

    payload = {"url": "https://example.com"}
    # First request - cache store
    resp1 = client.post("/link-analysis", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["telemetry"]["cached"] is False

    # Second request - cache HIT!
    resp2 = client.post("/link-analysis", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["telemetry"]["cached"] is True
    assert resp2.json()["telemetry"]["content_hash"] == dynamic_hash

def test_get_history_and_cache_stats():
    resp_history = client.get("/history")
    assert resp_history.status_code == 200
    assert isinstance(resp_history.json(), list)

    resp_stats = client.get("/cache/stats")
    assert resp_stats.status_code == 200
    assert "total_entries" in resp_stats.json()
