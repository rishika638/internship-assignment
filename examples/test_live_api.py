import httpx
import json
import time

def test_live_link_analysis():
    print("Testing live API POST /link-analysis...")
    url = "http://localhost:4000/link-analysis"
    payload = {"url": "https://example.com"}

    # Request 1: Fresh live crawl and analysis
    t0 = time.time()
    resp1 = httpx.post(url, json=payload, timeout=30.0)
    dur1 = time.time() - t0
    print(f"Request 1 Status: {resp1.status_code} in {dur1:.2f}s")
    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}: {resp1.text}"

    data1 = resp1.json()
    print("\n--- Telemetry ---")
    print(f"Provider: {data1['telemetry']['provider']} (model: {data1['telemetry']['model']})")
    print(f"Is Mock: {data1['telemetry']['is_mock']}")
    print(f"Cached: {data1['telemetry']['cached']}")
    print(f"Execution Time: {data1['telemetry']['execution_time_ms']} ms")
    print(f"Content Hash: {data1['telemetry']['content_hash']}")

    print("\n--- Section A: Competitor vs Brand Analysis ---")
    comp = data1["competitor_analysis"]
    print(f"Brand Name: {comp['brand_name']}")
    print(f"Category: {comp['category']}")
    print(f"Competitors count: {len(comp['competitors'])} (Names: {[c['name'] for c in comp['competitors']]})")
    print(f"Competitive Advantages: {len(comp['brand_competitive_advantages'])}")

    print("\n--- Section B: Top 5 Target Search Queries ---")
    queries = data1["target_search_queries"]["queries"]
    print(f"Queries count: {len(queries)}")
    for q in queries:
        print(f"  - [{q['search_intent']}] \"{q['query']}\" -> Platforms: {q['relevant_platforms']}")

    print("\n--- Section C: SEO Improvements ---")
    seo = data1["seo_improvements"]
    print(f"Recommended Title: {seo['recommended_title']}")
    print(f"Recommended Meta Description: {seo['recommended_meta_description']}")
    print(f"Primary Keywords: {seo['keywords']['primary_keywords']}")

    print("\n--- Section D: Top 5 Services ---")
    services = data1["top_services"]["services"]
    print(f"Services count: {len(services)}")
    for s in services:
        print(f"  - {s['service_name']} (Explicitly Stated: {s['is_explicitly_stated']})")

    print("\n--- Section E: Target Audience ---")
    aud = data1["target_audience"]
    print(f"Primary Audience: {aud['primary_audience']}")
    print(f"Industry Segments: {aud['industry_segments']}")
    print(f"Extracted Facts: {aud['extracted_facts']}")

    # Save to examples/response_example.json
    with open("examples/response_example.json", "w", encoding="utf-8") as f:
        json.dump(data1, f, indent=2)
    print("\nSuccessfully saved verified response to examples/response_example.json!")

    # Request 2: Verify caching works live!
    print("\nTesting Cache Hit (Request 2)...")
    t0 = time.time()
    resp2 = httpx.post(url, json=payload, timeout=10.0)
    dur2 = time.time() - t0
    data2 = resp2.json()
    print(f"Request 2 Status: {resp2.status_code} in {dur2:.3f}s")
    print(f"Cached flag: {data2['telemetry']['cached']}")
    assert data2['telemetry']['cached'] is True, "Expected Request 2 to be served from cache!"

    # Test audit history
    print("\nTesting GET /history...")
    hist_resp = httpx.get("http://localhost:4000/history")
    print(f"History Status: {hist_resp.status_code}, entries: {len(hist_resp.json())}")

    # Test cache stats
    print("\nTesting GET /cache/stats...")
    stats_resp = httpx.get("http://localhost:4000/cache/stats")
    print(f"Stats Status: {stats_resp.status_code}, stats: {stats_resp.json()}")

if __name__ == "__main__":
    test_live_link_analysis()
