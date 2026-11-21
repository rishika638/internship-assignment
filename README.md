# Dxora Technologies - AI-Powered Website Link Analysis API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-24%20Passed%20(100%25)-success.svg)]()
[![Code%20Style](https://img.shields.io/badge/Code%20Style-Ruff%20%2F%20Black-000000.svg)](https://github.com/astral-sh/ruff)

A high-performance, enterprise-grade REST API that accepts a website URL, executes safe and authenticated web crawling with **rigorous SSRF defense**, extracts structured semantic information (HTML, OpenGraph, Schema.org JSON-LD, multi-page cues), and performs multi-dimensional AI intelligence analysis using **Google Gemini, OpenAI, Anthropic Claude**, or a zero-dependency **Mock Engine**.

---

## 1. System Architecture

The service is engineered with strict separation of concerns, defensive security barriers, SQLite content-hash caching, and multi-provider LLM fallbacks.

```mermaid
flowchart TD
    Client(["HTTP Client / Swagger UI / Webhook"])
    
    subgraph FastAPI_Service["FastAPI Application (Port 4000)"]
        Router["API Router (/link-analysis, /health, /history, /cache/stats)"]
        
        subgraph Security_Layer["Security & Validation Layer"]
            SSRFValidator["SSRF Guard & DNS Resolver<br/>(RFC 1918, Link-Local 169.254, IPv6)"]
            RedirectHook["Safe Redirect Interceptor<br/>(Re-validates each redirect hop)"]
        end
        
        subgraph Extraction_Engine["Website Extraction Engine"]
            HTTPXEngine["Async HTTPX Client<br/>(Timeout & Size Controls)"]
            SoupCleaner["BeautifulSoup Sanitizer<br/>(Decomposes scripts, styles, iframes)"]
            MetadataExtractor["Metadata & JSON-LD Extractor<br/>(OpenGraph, Headings, Subpages)"]
            Hasher["SHA-256 Content Fingerprinter"]
        end
        
        subgraph Optimization_Layer["Cost Optimization & Caching"]
            SQLiteCache[("SQLite Cache (data/cache.db)<br/>TTL Expiration & History Audit")]
        end
        
        subgraph AI_Intelligence["Multi-Provider LLM Intelligence Layer"]
            Factory{"LLM Provider Factory"}
            Gemini["Gemini 2.5 Flash<br/>(Primary, 503 Backoff + Jitter)"]
            OpenAI["OpenAI GPT-4o-mini<br/>(Secondary)"]
            Claude["Claude 3.5 Haiku / Sonnet<br/>(Analytical Nuance)"]
            MockEngine["Deterministic Mock Engine<br/>(Zero-Key Evaluation Mode)"]
        end
        
        subgraph Schema_Validation["Pydantic Strict Validation"]
            SchemaV["Enforce 5 Mandatory Analysis Sections"]
        end
    end

    Client -->|"POST /link-analysis"| Router
    Router --> SSRFValidator
    SSRFValidator -->|"Validated Public Host"| HTTPXEngine
    HTTPXEngine <-->|"Fetch HTML + Safe Redirects"| RemoteWeb["Public Target Website"]
    HTTPXEngine --> RedirectHook --> SoupCleaner
    SoupCleaner --> MetadataExtractor --> Hasher
    Hasher -->|"Lookup Content Hash"| SQLiteCache
    
    SQLiteCache -->|"Cache HIT (0ms, $0.00)"| Router
    SQLiteCache -->|"Cache MISS"| Factory
    
    Factory --> Gemini
    Factory --> OpenAI
    Factory --> Claude
    Factory --> MockEngine
    
    Gemini -.->|"Transient 503 / Failover"| MockEngine
    
    Gemini --> SchemaV
    OpenAI --> SchemaV
    Claude --> SchemaV
    MockEngine --> SchemaV
    
    SchemaV -->|"Save Analysis & Telemetry"| SQLiteCache
    SchemaV -->|"Return Structured JSON"| Router
    Router --> Client
```

---

## 2. Five Mandatory Analysis Sections

The API enforces complete Pydantic models for every analytical dimension:

| Section | Key Outputs | Distinguishing Verified vs Inferred |
| :--- | :--- | :--- |
| **A. Competitor vs Brand Analysis** | Brand overview, category, products/services, minimum 3 competitors, strengths, weaknesses, market gaps, competitive advantages, positioning opportunities. | Features separate `verified_information` (site content) and `ai_generated_suggestions` (strategic hypotheses). |
| **B. Top 5 Target Search Queries** | Exactly 5 queries across **Google, Facebook, Instagram, LinkedIn, and X**, search intent, business relevance, target audience. | Never fabricates search volumes or rankings. Queries reflect organic buyer journeys. |
| **C. SEO Improvements** | Primary, secondary, long-tail, and business keywords, recommended SEO title (under 60 chars), meta description (under 160 chars), landing pages, industry pages, FAQs, blogs, location pages. | Contextualized to the scraped company's niche and actual keyword gaps. |
| **D. Top 5 Services** | Service name, description, target industry, customer persona, main benefit, explicit evidence excerpt. | Explicitly flags `is_explicitly_stated: true` (with source quote) vs `is_explicitly_stated: false` (AI inferred). |
| **E. Target Audience** | Primary and secondary audiences, industry segments, business types (B2B/B2C), customer profiles, geographic focus, needs, challenges, marketing segments. | Employs separate lists for `extracted_facts` vs `ai_inferences`. |

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.12+ (or 3.10+)
- `pip`

### Step 1: Clone and Set Up Environment
```bash
git clone <repository_url>
cd intern-assigment-project

# Create and activate virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` to configure your preferred LLM provider:
```ini
HOST=0.0.0.0
PORT=4000
ENVIRONMENT=development
PRIMARY_LLM_PROVIDER=gemini
FALLBACK_LLM_PROVIDER=mock

# Gemini (Primary recommended)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# OpenAI (Optional)
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini

# Anthropic Claude (Optional)
ANTHROPIC_API_KEY=your_claude_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Force mock mode if testing without any API credentials:
MOCK_MODE=false

# Cache settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=86400
```
> **Notice on Zero-Key Testing:** If `GEMINI_API_KEY` is omitted, the API automatically and gracefully falls back to the high-fidelity **Mock Engine**, transparently flagging `is_mock: true` in the telemetry without breaking the service.

### Step 3: Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```
- Interactive Swagger UI: [http://localhost:4000/docs](http://localhost:4000/docs)
- ReDoc Documentation: [http://localhost:4000/redoc](http://localhost:4000/redoc)
- Health Check: [http://localhost:4000/health](http://localhost:4000/health)

---

## 4. API Endpoints & Live Examples

### 1. `POST /link-analysis`
Analyzes a submitted website URL.

#### Request:
```bash
curl -X POST "http://localhost:4000/link-analysis" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

#### Verified Response (Excerpt):
```json
{
  "url": "https://example.com",
  "telemetry": {
    "provider": "mock",
    "model": "mock-engine-v1",
    "is_mock": true,
    "cached": false,
    "execution_time_ms": 578.39,
    "input_tokens": 100,
    "output_tokens": 950,
    "estimated_cost_usd": 0.0,
    "content_hash": "7a641c5b802675fabafae43e6442eccb4e57147bd9893b8b23e8d2b3467bd304",
    "timestamp": "2026-11-22T00:54:24.120000+00:00"
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
      "Verified Domain: example.com"
    ],
    "ai_generated_suggestions": [
      "Develop specialized comparison landing pages against key competitors"
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
      "service_landing_pages": ["/services/example-domain-core-plat", "/services/example-domain-integrat", "/services/example-domain-enterpr"],
      "industry_pages": ["/industries/saas", "/industries/financial-services", "/industries/healthcare-tech"],
      "faqs": [
        "How does Example Domain ensure security and uptime?",
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
    "recommended_marketing_segments": ["Enterprise Technology Buyers", "Cloud Engineering Leaders", "Founder-led Tech Scale-ups"],
    "extracted_facts": ["Website Title: Example Domain", "Total Characters Extracted: 296"],
    "ai_inferences": [
      "[MOCK INFERENCE] Target persona focuses on engineering excellence and cost predictability.",
      "[MOCK INFERENCE] Organization benefits from clear technical documentation and live demo endpoints."
    ]
  }
}
```

### 2. `GET /health`
Returns system operational state, version, and active provider configuration.
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "cache_enabled": true,
  "llm_primary_provider": "gemini",
  "llm_fallback_provider": "mock",
  "uptime_status": "healthy"
}
```

### 3. `GET /cache/stats`
Reports real-time SQLite cache hits, stored hashes, and cumulative token/cost savings:
```json
{
  "cache_enabled": true,
  "total_entries": 4,
  "total_hits": 9,
  "tokens_saved": 9700,
  "cost_saved_usd": 0.0,
  "ttl_seconds": 86400
}
```

### 4. `GET /history`
Returns chronological audit trails of recent analyses with timestamps and execution latencies.

---

## 5. Security & SSRF Protection Architecture

Web scraping APIs represent a prime vector for Server-Side Request Forgery (SSRF) and Cloud Metadata Exfiltration. This project implements **defense-in-depth protection** (`app/services/ssrf.py`):

1. **Strict Scheme Whitelisting:** Permitting only `http` and `https`. Schemes like `file://`, `ftp://`, `gopher://`, `data:` are blocked immediately.
2. **Userinfo Stripping:** Disallowing embedded credentials (`http://user:pass@evil.com`).
3. **Restricted Subnet Blocking:** Rejecting direct IP literals and DNS-resolved addresses belonging to:
   - Loopback: `127.0.0.0/8`, `::1`
   - Private Networks (RFC 1918): `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
   - Link-Local / Cloud Metadata: `169.254.0.0/16`, `fe80::/10` (blocks AWS/GCP/Azure `169.254.169.254` and `metadata.google.internal`)
   - Carrier Grade NAT: `100.64.0.0/10`
   - Multicast & Broadcast: `224.0.0.0/4`, `255.255.255.255`
   - IPv4-mapped IPv6: `::ffff:0:0/96`
4. **Step-by-Step Redirect Validation:** HTTPX `follow_redirects=False` is enforced. Every redirect hop (`301`, `302`, `303`, `307`, `308`) resolves its destination URL through the SSRF security validator before issuing the subsequent request, thwarting DNS rebinding and open redirect pivot exploits.
5. **Content & Timeout Limits:** Response body max size: 1MB. Timeout limit: 15 seconds.

---

## 6. LLM Multi-Provider Comparison & Economics (15 Marks)

Comprehensive research was conducted using official provider pricing pages and APIs. Detailed report located in `research/LLM_RESEARCH.md`.

### Provider Matrix

| Provider & Model | Context Window | Input Cost / 1M | Output Cost / 1M | Latency | Structured JSON | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemini 2.5 Flash** | **1,048,576** | **\$0.15** | **\$0.60** | **1.2s – 1.8s** | Native JSON Schema | **Primary Choice (Top value & context)** |
| **OpenAI GPT-4o-mini**| 128,000 | \$0.15 | \$0.60 | 1.4s – 2.2s | Native JSON Schema | Secondary / Fallback |
| **Claude 3.5 Haiku** | 200,000 | \$0.80 | \$4.00 | 1.1s – 1.7s | Tool / Strict System | High nuance, higher cost |
| **Claude 3.5 Sonnet**| 200,000 | \$3.00 | \$15.00 | 2.8s – 4.5s | Tool / Strict System | Premium enterprise auditing |

### Cost per 100 & 1,000 Analyses (Assuming 3,000 In / 1,200 Out Tokens)

| Model | Cost per Analysis | Cost per 100 | Cost per 1,000 |
| :--- | :--- | :--- | :--- |
| **Gemini 2.5 Flash** | **\$0.001170** | **\$0.1170** | **\$1.170** |
| **OpenAI GPT-4o-mini** | **\$0.001170** | **\$0.1170** | **\$1.170** |
| **Claude 3.5 Haiku** | **\$0.007200** | **\$0.7200** | **\$7.200** |
| **OpenAI GPT-4o** | **\$0.019500** | **\$1.9500** | **\$19.500** |
| **Claude 3.5 Sonnet** | **\$0.027000** | **\$2.7000** | **\$27.000** |

### Benchmark Tool
Run the included benchmark utility to evaluate active providers:
```bash
python research/benchmark.py
```

---

## 7. Testing & Verification

The test suite contains 24 automated unit and integration tests executing under pytest:

```bash
python -m pytest -v
```

### Actual Test Results:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.1, pytest-8.3.4, pluggy-1.6.0
collected 24 items

examples/test_live_api.py::test_live_link_analysis PASSED                [  4%]
tests/test_api.py::test_get_root PASSED                                  [  8%]
tests/test_api.py::test_get_health PASSED                                [ 12%]
tests/test_api.py::test_post_link_analysis_ssrf_block PASSED             [ 16%]
tests/test_api.py::test_post_link_analysis_success PASSED                [ 20%]
tests/test_api.py::test_post_link_analysis_cache_hit PASSED              [ 25%]
tests/test_api.py::test_get_history_and_cache_stats PASSED               [ 29%]
tests/test_cache.py::test_cache_set_and_get PASSED                       [ 33%]
tests/test_cache.py::test_cache_ttl_expiration PASSED                    [ 37%]
tests/test_cache.py::test_cache_history_recording PASSED                 [ 41%]
tests/test_crawler.py::test_clean_and_extract_html PASSED                [ 45%]
tests/test_crawler.py::test_crawler_handles_inaccessible_website PASSED  [ 50%]
tests/test_crawler.py::test_crawler_handles_timeout PASSED               [ 54%]
tests/test_crawler.py::test_crawler_blocks_unsafe_redirect PASSED        [ 58%]
tests/test_crawler.py::test_real_website_crawler_integration PASSED      [ 62%]
tests/test_llm.py::test_mock_llm_provider_all_five_sections PASSED       [ 66%]
tests/test_llm.py::test_llm_factory_fallback_on_missing_keys PASSED      [ 70%]
tests/test_llm.py::test_llm_factory_fallback_on_primary_failure PASSED   [ 75%]
tests/test_llm.py::test_gemini_retry_on_transient_error PASSED           [ 79%]
tests/test_ssrf.py::test_disallowed_ip_ranges PASSED                     [ 83%]
tests/test_ssrf.py::test_ssrf_rejects_localhost_and_internal PASSED      [ 87%]
tests/test_ssrf.py::test_ssrf_rejects_unsupported_schemes PASSED         [ 91%]
tests/test_ssrf.py::test_ssrf_rejects_embedded_credentials PASSED        [ 95%]
tests/test_ssrf.py::test_ssrf_allows_legitimate_domains PASSED           [100%]

============================= 24 passed in 21.48s =============================
```

---

## 8. Deployment

### A. Docker Deployment
```bash
# Build the Docker image
docker build -t dxora-link-analyzer .

# Run the container mapping port 4000
docker run -p 4000:4000 --env-file .env dxora-link-analyzer
```

### B. Render Deployment
The project contains a ready `render.yaml` blueprint with persistent disk mounting for SQLite cache:
1. Push repository to GitHub.
2. Link repository in Render dashboard as a **Blueprint**.
3. Render automatically picks up `render.yaml`, configures Python 3, runs `pip install -r requirements.txt`, mounts `/app/data` disk, and starts Uvicorn on port 4000.
4. Set `GEMINI_API_KEY` (or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) in the Render environment variables tab.

---

## 9. Project Structure

```text
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusion rules (keys, DBs, caches excluded)
├── Dockerfile                # Multi-stage production container build
├── render.yaml               # Render Infrastructure-as-Code deployment blueprint
├── requirements.txt          # Pinned production dependencies
├── README.md                 # Complete documentation & architecture guide
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application, routes, lifespan, middleware
│   ├── config.py             # Pydantic BaseSettings environment manager
│   ├── schemas.py            # Pydantic models for 5 mandatory sections & telemetry
│   ├── services/
│   │   ├── crawler.py        # HTTPX + BeautifulSoup extraction & deduplication
│   │   ├── ssrf.py           # SSRF protection, IP/DNS validator, redirect hooks
│   │   ├── cache.py          # SQLite persistent caching, TTL, savings tracking
│   │   └── llm/
│   │       ├── base.py       # Abstract BaseLLMProvider & LLMResult
│   │       ├── gemini_provider.py # Gemini 2.5 Flash, 503 retry + jitter
│   │       ├── openai_provider.py # OpenAI gpt-4o-mini structured JSON
│   │       ├── claude_provider.py # Anthropic Claude 3.5 Haiku/Sonnet
│   │       ├── mock_provider.py   # Deterministic zero-credential test provider
│   │       ├── factory.py    # Multi-provider factory & graceful fallback resolver
│   │       └── prompts.py    # Token-efficient structured JSON prompt templates
│   └── utils/
│       ├── logger.py         # Formatted structured logging
│       └── pricing.py        # Official LLM token pricing tables & cost calculator
├── research/
│   ├── LLM_RESEARCH.md       # Mandatory 15-mark research & comparative analysis
│   ├── benchmark.py          # Provider latency, token, and cost measurement tool
│   └── benchmark_results.json# Exported benchmark run telemetry
├── examples/
│   ├── request_example.json  # Sample request payload
│   ├── response_example.json # Verified live output with all 5 sections
│   └── test_live_api.py      # Automated live API execution script
└── tests/
    ├── test_api.py           # FastAPI endpoints, SSRF blocks, cache hits
    ├── test_cache.py         # SQLite cache TTL, hits, and audit recording
    ├── test_crawler.py       # HTML parsing, redirects, timeouts, live crawl
    ├── test_llm.py           # All 5 sections validation, fallback, 503 retry
    └── test_ssrf.py          # Loopback, private IP, link-local, scheme rejection
```

---

## 10. Known Limitations & Roadmap

1. **JavaScript-Heavy Single-Page Applications (SPAs):**  
   - Currently, HTML is parsed via `httpx` + `BeautifulSoup`. Sites rendered entirely client-side via React/Vue with empty initial HTML templates return minimal content.
   - *Roadmap:* Integrate a headless Chromium worker (Playwright) conditionally when initial HTML text length is under 200 characters.
2. **CAPTCHA & Cloudflare Bot Management:**  
   - Highly protected websites (e.g. Cloudflare Turnstile, PerimeterX) block automated scrapers with HTTP 403. The crawler handles this gracefully by returning a structured `HTTP 502 REMOTE_HTTP_ERROR` rather than crashing.
3. **Multi-Region Distributed Caching:**  
   - The current cache uses SQLite with write-ahead logging (WAL), optimal for single-node deployments. For horizontally scaled clusters across multiple regions, Redis or DynamoDB would replace SQLite.
