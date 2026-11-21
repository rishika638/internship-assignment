"""Benchmark Utility for LLM Providers (Gemini, OpenAI, Claude, Mock).
Measures actual latency, JSON validity rate, token usage, and calculates official pricing cost.
"""
import os
import sys
import json
import time
import asyncio
from typing import Dict, Any, List

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import get_settings
from app.services.crawler import CleanedWebsiteContent
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.claude_provider import ClaudeProvider
from app.schemas import (
    CompetitorVsBrandAnalysis,
    Top5TargetSearchQueries,
    SEOImprovements,
    Top5Services,
    TargetAudience,
)
from app.utils.pricing import calculate_llm_cost

SAMPLE_CONTENT = CleanedWebsiteContent(
    url="https://example-saas.com",
    final_url="https://example-saas.com",
    title="CloudFlow Technologies | Enterprise Workflow Automation Platform",
    meta_description="CloudFlow delivers intelligent enterprise workflow orchestration and real-time backend analytics.",
    meta_keywords=["workflow automation", "enterprise AI", "cloud integration", "ETL"],
    open_graph={"og:title": "CloudFlow Technologies", "og:description": "Next-gen enterprise workflow automation."},
    schema_org=[{"@context": "https://schema.org", "@type": "Organization", "name": "CloudFlow Technologies"}],
    headings={
        "h1": ["Next-Generation Enterprise Workflow Automation"],
        "h2": [
            "Seamless Cloud Integration",
            "Real-Time Data Pipeline Orchestration",
            "Enterprise Security & Role-Based Governance",
            "Developer-First REST & GraphQL APIs"
        ],
        "h3": ["High Availability Architecture", "Certified SOC-2 Compliance", "Pre-built SaaS Connectors"]
    },
    body_text=(
        "CloudFlow Technologies is an enterprise software platform that enables engineering and operations teams "
        "to design, execute, and monitor mission-critical workflows across multi-cloud environments. "
        "With native integrations for AWS, GCP, Azure, and modern SaaS ecosystems, CloudFlow eliminates repetitive manual tasks, "
        "accelerates data pipelines, and ensures robust compliance through automated audit logging. "
        "Our customers include fast-scaling fintechs, healthcare providers, and global retail enterprises requiring 99.99% uptime SLAs."
    ),
    pages_crawled=2,
    internal_links=["https://example-saas.com/features", "https://example-saas.com/pricing"],
    contact_cues={"emails": ["contact@cloudflow.io"], "phones": ["+1-800-555-0199"]},
    content_hash="benchmark_sample_hash_987654321",
    total_characters=890
)

async def test_provider(provider_instance, runs: int = 3) -> Dict[str, Any]:
    latencies = []
    valid_json_count = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    errors = []

    print(f"\nEvaluating Provider: {provider_instance.provider_name} [{provider_instance.model_name}]...")

    for i in range(runs):
        print(f"  Run {i + 1}/{runs}...", end=" ", flush=True)
        try:
            result = await provider_instance.analyze(SAMPLE_CONTENT)
            latencies.append(result.latency_ms)
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            total_cost += result.estimated_cost_usd

            # Validate schema
            CompetitorVsBrandAnalysis(**result.data["competitor_analysis"])
            Top5TargetSearchQueries(**result.data["target_search_queries"])
            SEOImprovements(**result.data["seo_improvements"])
            Top5Services(**result.data["top_services"])
            TargetAudience(**result.data["target_audience"])

            valid_json_count += 1
            print(f"SUCCESS ({result.latency_ms:.1f}ms, {result.input_tokens + result.output_tokens} tokens)")
        except Exception as e:
            errors.append(str(e))
            print(f"FAILED: {e}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    avg_input = total_input_tokens / len(latencies) if latencies else 0
    avg_output = total_output_tokens / len(latencies) if latencies else 0
    avg_cost = total_cost / len(latencies) if latencies else 0.0

    return {
        "status": "TESTED",
        "provider": provider_instance.provider_name,
        "model": provider_instance.model_name,
        "runs": runs,
        "success_rate_percent": (valid_json_count / runs) * 100.0,
        "avg_latency_ms": round(avg_latency, 2),
        "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
        "avg_input_tokens": int(avg_input),
        "avg_output_tokens": int(avg_output),
        "avg_cost_usd_per_analysis": round(avg_cost, 6),
        "cost_for_100_analyses_usd": round(avg_cost * 100, 4),
        "cost_for_1000_analyses_usd": round(avg_cost * 1000, 3),
        "errors": errors
    }

async def run_all_benchmarks(runs: int = 3):
    settings = get_settings()
    results = {}

    print("==========================================================================")
    print("      Dxora Technologies - LLM Multi-Provider Benchmark Suite             ")
    print("==========================================================================")

    # 1. Mock Engine Baseline
    mock_provider = MockLLMProvider("mock-engine-v1")
    results["mock"] = await test_provider(mock_provider, runs=runs)

    # 2. Gemini
    if settings.GEMINI_API_KEY:
        gemini_provider = GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        results["gemini"] = await test_provider(gemini_provider, runs=runs)
    else:
        results["gemini"] = {
            "status": "NOT TESTED",
            "provider": "gemini",
            "model": settings.GEMINI_MODEL,
            "reason": "GEMINI_API_KEY environment variable not configured."
        }
        print(f"\n[Gemini] Status: NOT TESTED (GEMINI_API_KEY not provided)")

    # 3. OpenAI
    if settings.OPENAI_API_KEY:
        openai_provider = OpenAIProvider(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
        results["openai"] = await test_provider(openai_provider, runs=runs)
    else:
        results["openai"] = {
            "status": "NOT TESTED",
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "reason": "OPENAI_API_KEY environment variable not configured."
        }
        print(f"\n[OpenAI] Status: NOT TESTED (OPENAI_API_KEY not provided)")

    # 4. Anthropic Claude
    if settings.ANTHROPIC_API_KEY:
        claude_provider = ClaudeProvider(settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_MODEL)
        results["claude"] = await test_provider(claude_provider, runs=runs)
    else:
        results["claude"] = {
            "status": "NOT TESTED",
            "provider": "claude",
            "model": settings.ANTHROPIC_MODEL,
            "reason": "ANTHROPIC_API_KEY environment variable not configured."
        }
        print(f"\n[Claude] Status: NOT TESTED (ANTHROPIC_API_KEY not provided)")

    # Save results to research/benchmark_results.json
    out_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n==========================================================================")
    print("                     BENCHMARK SUMMARY RESULTS                            ")
    print("==========================================================================")
    for p_key, data in results.items():
        if data["status"] == "TESTED":
            print(f"- {data['provider'].upper()} ({data['model']}):")
            print(f"    Avg Latency: {data['avg_latency_ms']} ms")
            print(f"    Schema Valid Rate: {data['success_rate_percent']}%")
            print(f"    Avg Tokens: {data['avg_input_tokens']} In / {data['avg_output_tokens']} Out")
            print(f"    Cost / Analysis: ${data['avg_cost_usd_per_analysis']:.6f} USD")
            print(f"    Cost / 1,000 Analyses: ${data['cost_for_1000_analyses_usd']:.3f} USD")
        else:
            print(f"- {p_key.upper()}: NOT TESTED ({data['reason']})")
    print(f"\nDetailed JSON saved to: {out_path}\n")

if __name__ == "__main__":
    asyncio.run(run_all_benchmarks(runs=3))
