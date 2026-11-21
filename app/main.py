import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import (
    LinkAnalysisRequest,
    LinkAnalysisResponse,
    HealthCheckResponse,
    HistoryItem,
    CrawlSummary,
    Telemetry,
    CompetitorVsBrandAnalysis,
    Top5TargetSearchQueries,
    SEOImprovements,
    Top5Services,
    TargetAudience,
)
from app.services.crawler import WebsiteCrawler
from app.services.cache import cache_manager
from app.services.llm.factory import llm_factory
from app.services.ssrf import validate_url_security
from app.utils.logger import logger

settings = get_settings()
crawler = WebsiteCrawler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Dxora Website Link Analysis API on {settings.HOST}:{settings.PORT}")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Primary LLM: {settings.PRIMARY_LLM_PROVIDER}")
    yield
    logger.info("Shutting down Dxora Website Link Analysis API.")

app = FastAPI(
    title="Dxora AI-Powered Website Link Analysis API",
    description=(
        "Production-grade FastAPI service that extracts, cleans, and analyzes websites "
        "using LLMs (Gemini, OpenAI, Claude) across 5 core dimensions: Competitor Analysis, "
        "Top 5 Search Queries, SEO Improvements, Top 5 Services, and Target Audience."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for cleaner error JSON
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"error": "HTTP_ERROR", "message": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=detail)

@app.get("/", tags=["General"])
async def root():
    """Service landing page and navigation."""
    return {
        "service": "Dxora AI-Powered Website Link Analysis API",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "history": "/history",
        "cache_stats": "/cache/stats",
        "endpoints": {
            "analyze_website": "POST /link-analysis"
        }
    }

@app.get("/health", response_model=HealthCheckResponse, tags=["Monitoring"])
async def health_check():
    """Health check endpoint providing uptime and configuration state."""
    return HealthCheckResponse(
        status="ok",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        cache_enabled=settings.CACHE_ENABLED,
        llm_primary_provider=settings.PRIMARY_LLM_PROVIDER,
        llm_fallback_provider=settings.FALLBACK_LLM_PROVIDER,
        uptime_status="healthy",
    )

@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Analyze a Website URL",
    description=(
        "Crawls the specified website with SSRF security protection, extracts structured content, "
        "and runs comprehensive AI analysis returning 5 structured sections with token & cost tracking."
    ),
)
async def analyze_link(request: LinkAnalysisRequest):
    start_time = time.perf_counter()
    url = request.url.strip()

    # 1. SSRF and URL validation
    is_safe, error_msg = validate_url_security(url)
    if not is_safe:
        logger.warning(f"Rejected unsafe URL: {url} -> {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SSRF_SECURITY_VIOLATION", "message": error_msg, "url": url}
        )

    # 2. Extract and clean website content
    logger.info(f"Initiating crawling & extraction for: {url}")
    crawl_data = await crawler.crawl(url)

    # 3. Check Cache
    cached_payload = cache_manager.get(crawl_data.content_hash)
    if cached_payload:
        logger.info(f"Returning cached analysis for content hash {crawl_data.content_hash[:10]}...")
        # Mark cached flag and current request latency
        cached_payload["telemetry"]["cached"] = True
        cached_payload["telemetry"]["execution_time_ms"] = round((time.perf_counter() - start_time) * 1000.0, 2)
        return LinkAnalysisResponse(**cached_payload)

    # 4. LLM Analysis
    logger.info(f"Running LLM analysis for content hash {crawl_data.content_hash[:10]}...")
    try:
        llm_result = await llm_factory.execute_analysis(crawl_data)
    except Exception as e:
        logger.error(f"LLM analysis execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "LLM_ANALYSIS_FAILED", "message": f"AI analysis failed: {str(e)}", "url": url}
        )

    # 5. Validate output strictly against Pydantic section models
    try:
        competitor_analysis = CompetitorVsBrandAnalysis(**llm_result.data["competitor_analysis"])
        target_search_queries = Top5TargetSearchQueries(**llm_result.data["target_search_queries"])
        seo_improvements = SEOImprovements(**llm_result.data["seo_improvements"])
        top_services = Top5Services(**llm_result.data["top_services"])
        target_audience = TargetAudience(**llm_result.data["target_audience"])
    except Exception as validation_err:
        logger.error(f"Pydantic schema validation error on LLM response: {validation_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "SCHEMA_VALIDATION_ERROR",
                "message": f"LLM output failed strict schema validation: {str(validation_err)}",
                "url": url
            }
        )

    total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
    iso_timestamp = datetime.now(timezone.utc).isoformat()

    telemetry = Telemetry(
        provider=llm_result.provider,
        model=llm_result.model,
        is_mock=llm_result.is_mock,
        cached=False,
        execution_time_ms=total_latency_ms,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        estimated_cost_usd=llm_result.estimated_cost_usd,
        content_hash=crawl_data.content_hash,
        timestamp=iso_timestamp,
    )

    crawl_summary = CrawlSummary(
        title=crawl_data.title,
        meta_description=crawl_data.meta_description,
        pages_crawled=crawl_data.pages_crawled,
        total_characters_extracted=crawl_data.total_characters,
        internal_links_discovered=crawl_data.internal_links,
        has_schema_org=bool(crawl_data.schema_org),
        has_open_graph=bool(crawl_data.open_graph),
    )

    response = LinkAnalysisResponse(
        url=url,
        telemetry=telemetry,
        crawl_summary=crawl_summary,
        competitor_analysis=competitor_analysis,
        target_search_queries=target_search_queries,
        seo_improvements=seo_improvements,
        top_services=top_services,
        target_audience=target_audience,
    )

    # 6. Save to SQLite cache and audit history
    cache_manager.set(
        content_hash=crawl_data.content_hash,
        url=url,
        response_dict=response.model_dump(),
        provider=llm_result.provider,
        model=llm_result.model,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        estimated_cost_usd=llm_result.estimated_cost_usd,
    )
    cache_manager.record_history(
        url=url,
        content_hash=crawl_data.content_hash,
        provider=llm_result.provider,
        model=llm_result.model,
        execution_time_ms=total_latency_ms,
        estimated_cost_usd=llm_result.estimated_cost_usd,
    )

    return response

@app.get("/history", response_model=List[HistoryItem], tags=["Monitoring"])
async def get_analysis_history(limit: int = 20):
    """Retrieve recent website analyses history."""
    return cache_manager.get_history(limit=limit)

@app.get("/cache/stats", tags=["Monitoring"])
async def get_cache_statistics():
    """Retrieve SQLite cache performance, hit rates, and cost/token savings."""
    return cache_manager.get_stats()
