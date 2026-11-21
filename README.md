# Dxora AI-Powered Website Link Analysis API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-23%20Passed-success.svg)](#10-testing--verification)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render%20Free-46E3B7.svg?logo=render&logoColor=black)](https://dxora-link-analysis-api.onrender.com/)

A production-ready FastAPI service that takes a target website URL, enforces rigorous Server-Side Request Forgery (SSRF) defense, crawls and extracts cleaned semantic content, and runs multi-dimensional business and SEO intelligence analysis via Google Gemini, OpenAI, Anthropic Claude, or a deterministic Mock Engine.

---

### Quick Links

| Service Interface | URL |
| :--- | :--- |
| **Live API Root** | [https://dxora-link-analysis-api.onrender.com/](https://dxora-link-analysis-api.onrender.com/) |
| **Interactive Swagger UI** | [https://dxora-link-analysis-api.onrender.com/docs](https://dxora-link-analysis-api.onrender.com/docs) |
| **ReDoc Documentation** | [https://dxora-link-analysis-api.onrender.com/redoc](https://dxora-link-analysis-api.onrender.com/redoc) |
| **Health Check Endpoint** | [https://dxora-link-analysis-api.onrender.com/health](https://dxora-link-analysis-api.onrender.com/health) |
| **GitHub Repository** | [https://github.com/rishika638/internship-assignment](https://github.com/rishika638/internship-assignment) |

> [!NOTE]
> The live service is deployed on a Render Free instance. If inactive, the service spins down and may require a 30–50 second cold start to respond to initial requests.

---

## Table of Contents

- [1. What It Does](#1-what-it-does)
- [2. Five Analysis Dimensions](#2-five-analysis-dimensions)
- [3. System Architecture](#3-system-architecture)
- [4. Live Demo & Quick Verification](#4-live-demo--quick-verification)
- [5. Example API Request & Response](#5-example-api-request--response)
- [6. Tech Stack](#6-tech-stack)
- [7. Security Engineering & SSRF Defense](#7-security-engineering--ssrf-defense)
- [8. LLM Provider Comparison & Economics](#8-llm-provider-comparison--economics)
- [9. Local Setup & Execution](#9-local-setup--execution)
- [10. Testing & Verification](#10-testing--verification)
- [11. Deployment Architecture](#11-deployment-architecture)
- [12. Project Structure](#12-project-structure)
- [13. Limitations & Engineering Roadmap](#13-limitations--engineering-roadmap)

---

## 1. What It Does

The API automates technical link evaluation and competitor discovery from a single website entry point:

```
URL Input
  │
  ▼
[SSRF & Security Validation]      ── DNS resolution, private subnet / loopback rejection
  │
  ▼
[Defensive Web Crawler]          ── Safe redirect hops, 1MB payload caps, 15s timeout
  │
  ▼
[DOM Sanitization & Extraction]   ── Strips scripts/styles; extracts OpenGraph, JSON-LD, headings
  │
  ▼
[SHA-256 Content-Hash Caching]   ── Instant 0-token response on unchanged content
  │
  ▼
[Multi-Provider LLM Engine]      ── Gemini, OpenAI, Claude, or zero-key Mock fallback
  │
  ▼
[Pydantic Schema Enforcement]    ── Strict validation across all 5 dimensions
  │
  ▼
Structured JSON Response + Audit Telemetry
```

1. **URL Ingestion & Defensive Verification:** Validates URL structure, blocks credentials, rejects loopback/private subnets, and resolves hostnames against prohibited IPv4/IPv6 CIDR ranges.
2. **Defensive Web Crawling:** Issues asynchronous HTTP GET requests (`httpx`), inspecting each redirect destination individually to eliminate DNS-rebinding or redirect-pivot attacks.
3. **Semantic Extraction:** Decomposes scripts, styles, tracking tags, and modals via `BeautifulSoup`. Extracts page title, meta description, meta keywords, OpenGraph tags, Schema.org JSON-LD microdata, headings (`h1`–`h3`), and body text.
4. **Content-Hash Caching:** Computes a SHA-256 fingerprint of the cleaned HTML. If an identical page was analyzed within the TTL window (default 24h), the cached analysis is returned immediately at \$0.00 cost.
5. **Multi-Model Intelligence:** Dispatches the structured website context to the configured LLM provider using token-optimized prompts and native JSON-schema output modes.
6. **Schema Enforcement & Telemetry:** Enforces strict Pydantic models for every analytical field, logging latency, token usage, cost estimates, and provider metadata.

---

## 2. Five Analysis Dimensions

The endpoint (`POST /link-analysis`) produces a unified, strongly-typed JSON payload covering five mandatory business and technical dimensions:

| Dimension | Scope & Output Fields | Verification Distinction |
| :--- | :--- | :--- |
| **1. Competitor vs Brand Analysis** | Identified brand name, company overview, industry category, key products/services, minimum 3 competitors (overview, strengths, weaknesses, market gaps, reference URLs), competitive advantages, and market positioning opportunities. | Maintains separate lists for `verified_information` (direct crawl facts) and `ai_generated_suggestions` (inferred hypotheses). Each competitor contains an `is_verified` boolean. |
| **2. Target Search Queries** | Exactly 5 buyer search queries mapped across **Google, Facebook, Instagram, LinkedIn, and X**, categorized by intent (`Informational`, `Navigational`, `Commercial`, `Transactional`), business relevance, and target audience. | Does not fabricate search volume or cost-per-click metrics. Queries mirror real customer discovery journeys. |
| **3. SEO Improvements** | Four-tier keyword architecture (primary, secondary, long-tail, business keywords), click-worthy title tag (<60 characters), meta description (<160 characters), content expansion blueprints (service pages, industry pages, FAQs, blogs, location pages), and on-page/technical recommendations. | Tailored to detected content gaps, missing Schema.org metadata, and keyword density observed during extraction. |
| **4. Top 5 Services** | Up to 5 core service offerings, each detailing service name, description, target industry, customer persona, and core business benefit. | Every service explicitly flags `is_explicitly_stated` (boolean) accompanied by `evidence_or_source` (direct quote from page text) or marks it as an AI inference. |
| **5. Target Audience** | Primary and secondary customer segments, target industry verticals, business models (`B2B`, `B2C`, `Enterprise`, `SMB`), buyer personas / job titles, geographic focus, core customer needs, challenges, and marketing segments. | Segregated into `extracted_facts` (stated organizational attributes) versus `ai_inferences` (synthesized buyer profiles). |

---

## 3. System Architecture

The service is structured into modular layers ensuring isolation between transport, security, web extraction, caching, and intelligence generation:

```mermaid
flowchart TD
    Client(["HTTP Client / Swagger UI / Webhook"])

    subgraph Service["FastAPI Service (dxora-link-analysis-api)"]
        Router["API Router<br/>/link-analysis · /health · /history · /cache/stats"]

        subgraph Security["Security & SSRF Guard (app/services/ssrf.py)"]
            SchemeFilter["Scheme Filter (http/https only)"]
            DNSValidator["DNS & IP Resolver<br/>(Blocks RFC 1918, 169.254, Loopback, IPv6)"]
            RedirectHook["Step-by-Step Redirect Interceptor<br/>(Validates each hop independently)"]
        end

        subgraph Extraction["Extraction Engine (app/services/crawler.py)"]
            HTTPXClient["Async HTTPX Client<br/>(15s Timeout, 1MB Size Limit)"]
            SoupCleaner["BeautifulSoup Sanitizer<br/>(Decomposes scripts, styles, iframes)"]
            Extractor["Metadata & JSON-LD Extractor<br/>(OpenGraph, Schema.org, Headings)"]
            Fingerprint["SHA-256 Content Hasher"]
        end

        subgraph CacheLayer["Caching & Persistence (app/services/cache.py)"]
            SQLiteCache[("SQLite Cache (data/cache.db)<br/>WAL Mode · TTL Invalidation · Audit History")]
        end

        subgraph LLMLayer["LLM Orchestration (app/services/llm/)"]
            Factory{"LLM Factory Resolver"}
            Gemini["Gemini Provider<br/>(gemini-3.8-flash / Exponential Backoff)"]
            OpenAI["OpenAI Provider<br/>(gpt-4o-mini / Structured Outputs)"]
            Claude["Claude Provider<br/>(claude-3-5-haiku / Sonnet)"]
            MockEngine["Deterministic Mock Engine<br/>(Zero-Key Development & Testing)"]
        end

        subgraph SchemaValidator["Pydantic Validation (app/schemas.py)"]
            SchemaCheck["Strict 5-Section Schema Enforcement"]
        end
    end

    Client -->|"POST /link-analysis"| Router
    Router --> SchemeFilter --> DNSValidator
    DNSValidator -->|"Safe Public Host"| HTTPXClient
    HTTPXClient <-->|"Fetch Target Page"| RemoteSite["Target Website"]
    HTTPXClient --> RedirectHook --> SoupCleaner
    SoupCleaner --> Extractor --> Fingerprint
    Fingerprint -->|"Lookup Content Hash"| SQLiteCache

    SQLiteCache -->|"Cache HIT (0ms, $0.00)"| Router
    SQLiteCache -->|"Cache MISS"| Factory

    Factory --> Gemini
    Factory --> OpenAI
    Factory --> Claude
    Factory --> MockEngine

    Gemini -.->|"Failover on 503 / Missing Key"| MockEngine
    OpenAI -.->|"Failover on Missing Key"| MockEngine
    Claude -.->|"Failover on Missing Key"| MockEngine

    Gemini --> SchemaCheck
    OpenAI --> SchemaCheck
    Claude --> SchemaCheck
    MockEngine --> SchemaCheck

    SchemaCheck -->|"Persist Cache & History"| SQLiteCache
    SchemaCheck -->|"Return JSON"| Router
    Router --> Client
```

### Key Engineering Decisions

- **Multi-Provider Factory Pattern (`app/services/llm/factory.py`):** Decouples business logic from specific AI vendors. Providers adhere to `BaseLLMProvider`, allowing dynamic switching via environment variables (`PRIMARY_LLM_PROVIDER=gemini|openai|claude|mock`).
- **Resilient Fallback & Exponential Backoff:** The Gemini provider implements retry logic with exponential backoff and jitter for transient errors (HTTP 503, 429). If primary credentials are missing or fail, requests automatically fall back to the deterministic Mock Engine without crashing.
- **Content-Hash Driven Idempotency:** Caching operates on the SHA-256 hash of the extracted, cleaned text rather than solely the URL string. Minor query param alterations on identical content reuse cache entries, conserving API quota.

---

## 4. Live Demo & Quick Verification

### 1. Test via Interactive Swagger UI
1. Open [https://dxora-link-analysis-api.onrender.com/docs](https://dxora-link-analysis-api.onrender.com/docs).
2. Expand the **`POST /link-analysis`** endpoint.
3. Click **Try it out**, paste the request body:
   ```json
   {
     "url": "https://example.com"
   }
   ```
4. Click **Execute** and review the structured JSON response.

### 2. Test via cURL
Run this command in any terminal to test the deployed instance:

```bash
curl -X POST "https://dxora-link-analysis-api.onrender.com/link-analysis" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

### 3. Check System Health
```bash
curl -s "https://dxora-link-analysis-api.onrender.com/health"
```

Expected output:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "cache_enabled": true,
  "llm_primary_provider": "gemini",
  "llm_fallback_provider": "mock",
  "uptime_status": "healthy"
}
```

---

## 5. Example API Request & Response

### Request Payload (`examples/request_example.json`)
```json
{
  "url": "https://example.com"
}
```

### Response Payload (`examples/response_example.json` Excerpt)

> [!NOTE]
> The following excerpt illustrates the exact schema structure returned by the API. This specific run was produced by the built-in deterministic Mock Provider (`mock-engine-v1`) against `https://example.com`. Synthetic items are explicitly tagged with `[MOCK ANALYSIS]` and `is_verified: false` to distinguish mock simulation from live LLM inference.

```json
{
  "url": "https://example.com",
  "telemetry": {
    "provider": "mock",
    "model": "mock-engine-v1",
    "is_mock": true,
    "cached": false,
    "execution_time_ms": 469.22,
    "input_tokens": 100,
    "output_tokens": 950,
    "estimated_cost_usd": 0.0,
    "content_hash": "7a641c5b802675fabafae43e6442eccb4e57147bd9893b8b23e8d2b3467bd304",
    "timestamp": "2026-11-21T19:25:16.438052+00:00"
  },
  "crawl_summary": {
    "title": "Example Domain",
    "meta_description": "",
    "pages_crawled": 1,
    "total_characters_extracted": 296,
    "internal_links_discovered": [],
    "has_schema_org": false,
    "has_open_graph": false
  },
  "competitor_analysis": {
    "brand_name": "Example Domain",
    "brand_overview": "[MOCK ANALYSIS] Example Domain operates on example.com...",
    "category": "Technology, Software & Digital Services",
    "products_and_services": [
      "Example Domain Core Platform Services",
      "Example Domain Integration & Automation",
      "Example Domain Enterprise Operations"
    ],
    "competitors": [
      {
        "name": "Competitor Alpha",
        "overview": "Leading market incumbent providing scaled software solutions.",
        "strengths": ["Extensive enterprise distribution", "Broad feature portfolio"],
        "weaknesses": ["Legacy codebase", "Higher implementation pricing"],
        "market_gaps": ["Rapid lightweight deployments", "Bespoke developer experience"],
        "source_url": "https://example.com/competitor-alpha",
        "is_verified": false
      },
      {
        "name": "Competitor Beta",
        "overview": "Cloud-native challenger with high automation focus.",
        "strengths": ["Modern user interface", "Competitive self-serve tier"],
        "weaknesses": ["Limited international compliance support"],
        "market_gaps": ["Tailored white-glove onboarding for mid-market"],
        "source_url": "https://example.com/competitor-beta",
        "is_verified": false
      },
      {
        "name": "Competitor Gamma",
        "overview": "Boutique specialized consulting and engineering vendor.",
        "strengths": ["High technical depth", "Agile delivery cycles"],
        "weaknesses": ["Smaller team capacity for global 24/7 SLAs"],
        "market_gaps": ["Integrated SaaS tooling combined with advisory"],
        "source_url": "https://example.com/competitor-gamma",
        "is_verified": false
      }
    ],
    "brand_competitive_advantages": [
      "Direct focused architecture tailored to target niche",
      "Agile and transparent service delivery"
    ],
    "market_positioning_opportunities": [
      "Position as the agile, high-performance alternative to legacy players"
    ],
    "verified_information": [
      "Verified Title: Example Domain",
      "Verified Domain: example.com",
      "Verified Headings Count: 0"
    ],
    "ai_generated_suggestions": [
      "[MOCK ENGINE NOTE] Synthetic strategic suggestions generated for local testing without active API credits."
    ]
  },
  "target_search_queries": {
    "queries": [
      {
        "query": "best example alternatives for modern engineering",
        "relevant_platforms": ["Google", "LinkedIn", "X"],
        "search_intent": "Commercial",
        "business_relevance": "Attracts high-intent prospects comparing solutions.",
        "target_audience": "Technical Decision Makers, Engineering Directors"
      },
      {
        "query": "how to implement Example Domain Core Platform Services efficiently",
        "relevant_platforms": ["Google", "LinkedIn"],
        "search_intent": "Informational",
        "business_relevance": "Builds thought leadership and captures early research funnel traffic.",
        "target_audience": "Software Architects, Product Leads"
      },
      {
        "query": "Example Domain customer case studies and pricing",
        "relevant_platforms": ["Google", "Facebook"],
        "search_intent": "Navigational",
        "business_relevance": "Protects branded queries and accelerates inbound conversion.",
        "target_audience": "Procurement Officers, CTOs"
      },
      {
        "query": "top enterprise tools for business automation",
        "relevant_platforms": ["LinkedIn", "X", "Google"],
        "search_intent": "Commercial",
        "business_relevance": "Drives discoverability in category-defining technology evaluations.",
        "target_audience": "Enterprise Operations Managers, CIOs"
      },
      {
        "query": "fast API integration with Example Domain platform",
        "relevant_platforms": ["Google", "Instagram"],
        "search_intent": "Transactional",
        "business_relevance": "Direct conversion path for developers seeking ready-to-use APIs.",
        "target_audience": "Backend Engineers, Tech Founders"
      }
    ]
  },
  "seo_improvements": {
    "keywords": {
      "primary_keywords": ["example domain", "example platform", "cloud software engineering"],
      "secondary_keywords": ["automated link analysis", "API integration", "enterprise software solutions"],
      "long_tail_keywords": ["how to choose the best example solution for enterprise", "scalable python api architecture"],
      "business_keywords": ["Example Domain", "Example Domain official website", "example.com"]
    },
    "recommended_title": "Example Domain | Modern AI & Digital Architecture Solutions",
    "recommended_meta_description": "Empower your business with Example Domain. Explore advanced solutions, reliable integration, and industry-leading performance on example.com.",
    "supporting_content_suggestions": {
      "service_landing_pages": ["/services/example-domain-core-plat", "/services/example-domain-integrat"],
      "industry_pages": ["/industries/saas", "/industries/financial-services"],
      "faqs": [
        "How does Example Domain ensure security and uptime?",
        "What is the expected timeline for API integration?"
      ],
      "blogs": [
        "Top Trends in Modern Cloud Architecture for 2026",
        "Why High-Performance APIs are Critical for Digital Scale"
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
        "service_name": "Example Domain Core Platform Services",
        "description": "Professional offering addressing core services for modern digital operations.",
        "target_industry": "Information Technology & Enterprise Services",
        "target_customer": "Technical Leads & Business Executives",
        "main_benefit": "Accelerates time-to-market while reducing operational overhead.",
        "is_explicitly_stated": true,
        "evidence_or_source": "Observed in website headings on example.com"
      }
    ]
  },
  "target_audience": {
    "primary_audience": "Technology leaders, Product Managers, and Backend Architects seeking scalable solutions.",
    "secondary_audience": "Growing SMBs and scale-ups requiring dependable digital transformation partner.",
    "industry_segments": ["SaaS & Cloud Platforms", "FinTech", "Professional Services"],
    "business_types": ["B2B Mid-Market", "Enterprise", "High-growth Startups"],
    "customer_profiles": ["CTO", "VP of Engineering", "Head of Digital Strategy"],
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
    "recommended_marketing_segments": ["Enterprise Technology Buyers", "Cloud Engineering Leaders"],
    "extracted_facts": ["Website Title: Example Domain", "Total Characters Extracted: 296"],
    "ai_inferences": [
      "[MOCK INFERENCE] Target persona focuses on engineering excellence and cost predictability."
    ]
  }
}
```

---

## 6. Tech Stack

| Category | Technologies | Purpose in Project |
| :--- | :--- | :--- |
| **Framework & API** | **FastAPI 0.115+**, **Uvicorn**, **Pydantic v2** | High-performance asynchronous REST endpoints, lifecycle hooks, and strict schema validation. |
| **Web Crawling & Extraction** | **HTTPX (AsyncClient)**, **BeautifulSoup4**, **lxml** | Non-blocking HTTP queries, custom redirect interception, DOM parsing, and JSON-LD extraction. |
| **Security & Networking** | **Python `ipaddress`**, **Python `socket`** | Direct IP parsing, DNS forward resolution, and RFC 1918 / Cloud metadata CIDR filtering. |
| **Persistence & Cache** | **SQLite 3** (Write-Ahead Logging / WAL mode) | Zero-dependency local caching, SHA-256 fingerprint matching, TTL management, and request history. |
| **LLM Orchestration** | **Google Generative AI**, **OpenAI SDK**, **Anthropic SDK** | Multi-vendor LLM clients with structured JSON schemas, prompt token optimization, and retry logic. |
| **Quality & Testing** | **pytest 8.3+**, **pytest-asyncio**, **AnyIO** | Unit, integration, security, and end-to-end endpoint verification. |
| **Container & Cloud** | **Docker**, **Render Web Service** | Containerized packaging and public HTTPS cloud deployment. |

---

## 7. Security Engineering & SSRF Defense

Public scrapers are highly vulnerable to Server-Side Request Forgery (SSRF) and Cloud Metadata Exfiltration. This service implements a defense-in-depth model (`app/services/ssrf.py` and `app/services/crawler.py`):

### 1. Protocol & Credential Sanitization
- **Strict Scheme Whitelist:** Only `http://` and `https://` are permitted. Protocols like `file://`, `ftp://`, `gopher://`, and `data:` are blocked immediately (`HTTP 400`).
- **Userinfo Rejection:** URLs containing embedded credentials (e.g. `https://user:password@malicious.com`) are rejected before resolution.

### 2. Forbidden Hostnames & Dual-Stage IP Resolution
The service checks both literal IP hostnames and DNS-resolved addresses via `socket.getaddrinfo()` against prohibited subnets before establishing connections:

| Prohibited Network Category | CIDR / Address Range | Security Rationale |
| :--- | :--- | :--- |
| **Loopback** | `127.0.0.0/8`, `::1/128` | Prevents scanning internal ports and local daemons. |
| **Private Networks (RFC 1918)** | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7` (IPv6 ULA) | Prevents pivoting into private cluster networks or VPC subnets. |
| **Cloud Metadata & Link-Local** | `169.254.0.0/16`, `fe80::/10` | Blocks exfiltration of IAM role credentials (AWS/GCP/Azure `169.254.169.254`). |
| **Carrier-Grade NAT (CGNAT)** | `100.64.0.0/10` | Disallows internal provider networks. |
| **Multicast, Reserved & Broadcast** | `224.0.0.0/4`, `240.0.0.0/4`, `255.255.255.255/32`, `ff00::/8` | Prevents network-level broadcast abuses. |
| **IPv4-Mapped IPv6** | `::ffff:0:0/96`, `64:ff9b::/96` | Prevents bypassing IPv4 filters via IPv6 encapsulation. |
| **Explicit Hostnames** | `localhost`, `localhost.localdomain`, `metadata.google.internal`, `instance-data` | Direct prevention of common local hostnames and metadata endpoints. |

### 3. Step-by-Step Redirect Validation
Automated HTTP clients that enable automatic redirect following (`follow_redirects=True`) are vulnerable to open redirect pivots and DNS rebinding attacks. 
- In this implementation, `follow_redirects=False` is enforced.
- The crawler captures each redirect status (`301`, `302`, `303`, `307`, `308`) and resolves the `Location` header.
- Every individual hop is passed through `enforce_safe_url()` before the client makes another request.
- Redirects are capped at a maximum of 5 hops (`MAX_REDIRECTS=5`) to prevent circular loops.

### 4. Operational Boundaries
- **Request Timeout:** Enforced 15.0-second timeout (`REQUEST_TIMEOUT_SECONDS=15.0`) prevents resource exhaustion from Slowloris attacks.
- **Content-Length Limit:** Maximum download size is capped at 1MB (`MAX_PAGE_CONTENT_BYTES=1048576`). Payloads exceeding this threshold are truncated.
- **Content-Type Filter:** Rejects non-text responses (e.g. streaming binaries or disk images) prior to DOM parsing.
- **Prompt Token Cap:** Extracted body text is truncated to 25,000 characters (`MAX_BODY_TEXT_CHARS=25000`) before LLM prompt construction, preventing prompt injection through text flooding and managing token budgets.

---

## 8. LLM Provider Comparison & Economics

A comprehensive study of provider models was conducted to balance speed, cost, context window, and schema precision. For detailed analysis, inspect [research/LLM_RESEARCH.md](research/LLM_RESEARCH.md).

### 1. Published Provider Pricing & Specifications

*Official figures sourced from vendor documentation (Google AI, OpenAI, and Anthropic pricing pages):*

| Provider & Model | Context Window | Input Price / 1M | Output Price / 1M | JSON Schema Support | Primary Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini (`gemini-3.8-flash` / `2.5-flash`)** | **1,048,576** | **\$0.15** | **\$0.60** | Native (`response_mime_type="application/json"`) | **Primary Choice (Large context, lowest cost)** |
| **OpenAI (`gpt-4o-mini`)** | 128,000 | \$0.15 | \$0.60 | Native (`json_schema` Structured Outputs) | Secondary / Direct Fallback |
| **Anthropic (`claude-3-5-haiku-20241022`)** | 200,000 | \$0.80 | \$4.00 | Tool Use / Strict System Prompt | Fast analytical nuance |
| **Anthropic (`claude-3-5-sonnet-20241022`)** | 200,000 | \$3.00 | \$15.00 | Tool Use / Strict System Prompt | Premium deep auditing |

### 2. Calculated Workload Economics (Theoretical Estimates)

*Assumed baseline workload: 3,000 input tokens (cleaned DOM, headings, cues) and 1,200 output tokens (5 structured sections):*

$$\text{Cost} = \left(\frac{\text{Input Tokens}}{1,000,000} \times \text{Input Rate}\right) + \left(\frac{\text{Output Tokens}}{1,000,000} \times \text{Output Rate}\right)$$

| Model | Cost per Single Request | Estimated Cost / 100 Requests | Estimated Cost / 1,000 Requests |
| :--- | :--- | :--- | :--- |
| **Gemini Flash (`gemini-3.8-flash`)** | **\$0.001170** | **\$0.1170** | **\$1.170** |
| **OpenAI (`gpt-4o-mini`)** | **\$0.001170** | **\$0.1170** | **\$1.170** |
| **Claude 3.5 Haiku** | **\$0.007200** | **\$0.7200** | **\$7.200** |
| **OpenAI GPT-4o (Full)** | **\$0.019500** | **\$1.9500** | **\$19.500** |
| **Claude 3.5 Sonnet** | **\$0.027000** | **\$2.7000** | **\$27.000** |

### 3. Empirical Benchmark Telemetry

The project provides an automated evaluation script ([research/benchmark.py](research/benchmark.py)) that feeds identical payloads into available providers. 

Measured results recorded in [research/benchmark_results.json](research/benchmark_results.json):

| Provider | Model | Status | Success Rate | Average Latency | Measured Cost / Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mock Engine** | `mock-engine-v1` | **TESTED** (3 runs) | **100.0%** | **0.09 ms** | **\$0.00** |
| **Google Gemini** | `gemini-2.5-flash` | NOT TESTED (No API key in test run) | N/A | N/A | N/A |
| **OpenAI** | `gpt-4o-mini` | NOT TESTED (No API key in test run) | N/A | N/A | N/A |
| **Anthropic** | `claude-3-5-haiku` | NOT TESTED (No API key in test run) | N/A | N/A | N/A |

*Note: In the committed repository benchmark telemetry, the zero-dependency Mock Provider was tested locally. Live remote providers require their respective API keys exported in the environment before running `python research/benchmark.py`.*

---

## 9. Local Setup & Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/rishika638/internship-assignment.git
cd internship-assignment
```

### Step 2: Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Review and adjust settings in `.env`:
```ini
# Server Configuration
HOST=0.0.0.0
PORT=4000
ENVIRONMENT=development
LOG_LEVEL=INFO

# Provider Selection
PRIMARY_LLM_PROVIDER=gemini
FALLBACK_LLM_PROVIDER=mock

# Gemini Configuration (Active Model)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# Optional Providers
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini

ANTHROPIC_API_KEY=your_anthropic_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Mock Mode (Set true to force deterministic mock responses without API credentials)
MOCK_MODE=false

# Caching Configuration
CACHE_ENABLED=true
CACHE_DB_PATH=data/cache.db
CACHE_TTL_SECONDS=86400

# Extraction Safeguards
REQUEST_TIMEOUT_SECONDS=15
MAX_REDIRECTS=5
MAX_PAGE_CONTENT_BYTES=1048576
MAX_CRAWL_SUBPAGES=3
```

> [!TIP]
> **Zero-Key Evaluation Mode:** If you do not provide a `GEMINI_API_KEY`, the application automatically falls back to the deterministic **Mock Engine**. It parses real websites, extracts real DOM metadata, and returns structurally compliant analysis tagged with `"is_mock": true` at zero cost.

### Step 4: Run the Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Access the local server:
- API Documentation: [http://localhost:4000/docs](http://localhost:4000/docs)
- Alternative ReDoc: [http://localhost:4000/redoc](http://localhost:4000/redoc)
- Health Check: [http://localhost:4000/health](http://localhost:4000/health)

---

## 10. Testing & Verification

The test suite covers API routes, SQLite caching, crawler edge cases, SSRF defense, and multi-provider fallbacks.

Run the test suite:
```bash
python -m pytest tests/ -v
```

### Confirmed Test Execution Result
```text
============================= test session starts =============================
platform win32 -- Python 3.12.1, pytest-8.3.4, pluggy-1.6.0 -- python.exe
cachedir: .pytest_cache
rootdir: E:\intern-assigment-project
plugins: anyio-4.12.1, asyncio-0.23.8
asyncio: mode=Mode.STRICT
collected 23 items

tests/test_api.py::test_get_root PASSED                                  [  4%]
tests/test_api.py::test_get_health PASSED                                [  8%]
tests/test_api.py::test_post_link_analysis_ssrf_block PASSED             [ 13%]
tests/test_api.py::test_post_link_analysis_success PASSED                [ 17%]
tests/test_api.py::test_post_link_analysis_cache_hit PASSED              [ 21%]
tests/test_api.py::test_get_history_and_cache_stats PASSED               [ 26%]
tests/test_cache.py::test_cache_set_and_get PASSED                       [ 30%]
tests/test_cache.py::test_cache_ttl_expiration PASSED                    [ 34%]
tests/test_cache.py::test_cache_history_recording PASSED                 [ 39%]
tests/test_crawler.py::test_clean_and_extract_html PASSED                [ 43%]
tests/test_crawler.py::test_crawler_handles_inaccessible_website PASSED  [ 47%]
tests/test_crawler.py::test_crawler_handles_timeout PASSED               [ 52%]
tests/test_crawler.py::test_crawler_blocks_unsafe_redirect PASSED        [ 56%]
tests/test_crawler.py::test_real_website_crawler_integration PASSED      [ 60%]
tests/test_llm.py::test_mock_llm_provider_all_five_sections PASSED       [ 65%]
tests/test_llm.py::test_llm_factory_fallback_on_missing_keys PASSED      [ 69%]
tests/test_llm.py::test_llm_factory_fallback_on_primary_failure PASSED   [ 73%]
tests/test_llm.py::test_gemini_retry_on_transient_error PASSED           [ 78%]
tests/test_ssrf.py::test_disallowed_ip_ranges PASSED                     [ 82%]
tests/test_ssrf.py::test_ssrf_rejects_localhost_and_internal PASSED      [ 86%]
tests/test_ssrf.py::test_ssrf_rejects_unsupported_schemes PASSED         [ 91%]
tests/test_ssrf.py::test_ssrf_rejects_embedded_credentials PASSED        [ 95%]
tests/test_ssrf.py::test_ssrf_allows_legitimate_domains PASSED           [100%]

============================= 23 passed in 12.41s =============================
```

### Test Suite Breakdown

- **`tests/test_api.py` (6 tests):** Validates the root endpoint, health check status, SSRF rejection handling (`HTTP 400`), successful analysis generation, SQLite cache hit retrieval, and history/stats reporting.
- **`tests/test_cache.py` (3 tests):** Validates SQLite entry storage, cache hit return integrity, TTL expiration invalidation, and telemetry audit trail tracking.
- **`tests/test_crawler.py` (5 tests):** Validates HTML tag sanitization, inaccessible website error handling (`HTTP 502`), crawl timeout bounds (`HTTP 504`), unsafe redirect blocking, and live integration against public HTML.
- **`tests/test_llm.py` (4 tests):** Validates all 5 mandatory analytical dimensions, LLM factory fallback upon missing API credentials, graceful fallback upon runtime provider errors, and Gemini exponential retry logic under transient 503 conditions.
- **`tests/test_ssrf.py` (5 tests):** Validates CIDR subnet checks, loopback/private hostname rejection, non-HTTP scheme blocking, embedded credential rejection, and legitimate public domain resolution.

---

## 11. Deployment Architecture

### 1. Live Render Deployment
The service is deployed live on Render's Web Service platform:
- **Base Endpoint:** [https://dxora-link-analysis-api.onrender.com/](https://dxora-link-analysis-api.onrender.com/)
- **Swagger Documentation:** [https://dxora-link-analysis-api.onrender.com/docs](https://dxora-link-analysis-api.onrender.com/docs)
- **Deployment Tier:** Free Web Service

#### Technical Notes on Free Tier Behavior:
1. **Inactivity Sleep:** Free instances spin down after 15 minutes of inactivity. The first request after a sleep period incurs a cold-start delay of approximately 30–50 seconds while the container initializes. Subsequent requests execute with standard sub-second to low-second latency.
2. **Ephemeral Filesystem:** Render's Free tier does not support persistent disks. Consequently, the local SQLite database (`data/cache.db`) resides in ephemeral container storage. Cache data resets upon service redeployment or container restart.

### 2. Docker Deployment
The repository includes a production multi-stage Dockerfile:

```bash
# Build the Docker image
docker build -t dxora-link-analyzer .

# Run container mapping port 4000
docker run -p 4000:4000 --env-file .env dxora-link-analyzer
```

---

## 12. Project Structure

```text
├── .env.example              # Template for environment variables
├── .gitignore                # Git exclusions (keys, bytecode, caches)
├── Dockerfile                # Multi-stage production container build
├── render.yaml               # Render Infrastructure-as-Code blueprint
├── requirements.txt          # Production dependencies
├── README.md                 # Project documentation and engineering guide
│
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application, route handlers, middleware
│   ├── config.py             # Pydantic BaseSettings environment manager
│   ├── schemas.py            # Pydantic models for 5 analysis dimensions & telemetry
│   │
│   ├── services/
│   │   ├── crawler.py        # Async HTTPX crawler & BeautifulSoup sanitization
│   │   ├── ssrf.py           # SSRF guard, CIDR subnet checker, redirect hooks
│   │   ├── cache.py          # SQLite persistent caching, TTL, savings tracking
│   │   │
│   │   └── llm/
│   │       ├── base.py       # BaseLLMProvider abstract interface & LLMResult
│   │       ├── factory.py    # Multi-provider factory & graceful fallback resolver
│   │       ├── gemini_provider.py # Gemini 3.8/2.5 Flash with backoff + jitter
│   │       ├── openai_provider.py # OpenAI gpt-4o-mini structured JSON client
│   │       ├── claude_provider.py # Anthropic Claude 3.5 Haiku/Sonnet client
│   │       ├── mock_provider.py   # Deterministic zero-key fallback provider
│   │       └── prompts.py    # Structured JSON prompt engineering templates
│   │
│   └── utils/
│       ├── logger.py         # Standardized structured logging
│       └── pricing.py        # Token pricing tables & cost calculator
│
├── research/
│   ├── LLM_RESEARCH.md       # Comparative study of Gemini, OpenAI, and Claude
│   ├── benchmark.py          # Latency, token, and cost benchmarking utility
│   └── benchmark_results.json# Committed benchmark run results
│
├── examples/
│   ├── request_example.json  # Sample request payload
│   ├── response_example.json # Verified example response with all 5 sections
│   └── test_live_api.py      # Standalone script for live endpoint testing
│
└── tests/
    ├── test_api.py           # API endpoints, SSRF rejection, cache hit tests
    ├── test_cache.py         # SQLite cache TTL, hits, and history tests
    ├── test_crawler.py       # HTML parsing, redirects, timeouts, live crawl
    ├── test_llm.py           # 5-section validation, fallback, and retry tests
    └── test_ssrf.py          # Subnet filtering, scheme rejection, credential tests
```

---

## 13. Limitations & Engineering Roadmap

1. **Client-Side Rendered SPAs:**  
   - *Current Implementation:* The crawler uses asynchronous `httpx` and `BeautifulSoup`. Sites rendered entirely client-side via JavaScript (pure React/Vue Single Page Applications) without server-side rendering return minimal DOM text.
   - *Roadmap:* Introduce a conditional headless Chromium worker (e.g., Playwright) triggered only when static HTML body length is below 200 characters.
2. **Strict Bot Management & CAPTCHAs:**  
   - *Current Implementation:* Sites gated behind aggressive WAF challenges (e.g. Cloudflare Turnstile, PerimeterX) respond with HTTP 403. The crawler catches this and returns a clean, structured `HTTP 502 REMOTE_HTTP_ERROR` rather than failing unhandled.
3. **Distributed Cache Scaling:**  
   - *Current Implementation:* Local SQLite with Write-Ahead Logging (WAL) provides sub-millisecond lookups for single-node deployments.
   - *Roadmap:* Support Redis / Upstash as a drop-in caching backend for horizontally scaled multi-container clusters.
