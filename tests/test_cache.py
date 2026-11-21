import os
import time
import pytest
from app.services.cache import SQLiteCacheManager

@pytest.fixture
def temp_cache(tmp_path):
    db_file = tmp_path / "test_cache.db"
    manager = SQLiteCacheManager(db_path=str(db_file))
    return manager

def test_cache_set_and_get(temp_cache):
    content_hash = "abc123hash"
    sample_response = {"brand": "TestBrand", "status": "success"}

    temp_cache.set(
        content_hash=content_hash,
        url="https://testsite.com",
        response_dict=sample_response,
        provider="mock",
        model="mock-v1",
        input_tokens=100,
        output_tokens=200,
        estimated_cost_usd=0.0001,
        ttl_seconds=10
    )

    cached = temp_cache.get(content_hash)
    assert cached is not None
    assert cached["brand"] == "TestBrand"

    # Verify hit counter incremented
    stats = temp_cache.get_stats()
    assert stats["total_hits"] == 1

def test_cache_ttl_expiration(temp_cache):
    content_hash = "expiring_hash"
    temp_cache.set(
        content_hash=content_hash,
        url="https://expiresite.com",
        response_dict={"data": "old"},
        provider="mock",
        model="mock-v1",
        ttl_seconds=1  # 1 second TTL
    )

    # Immediately should exist
    assert temp_cache.get(content_hash) is not None

    # Sleep 1.1 seconds to expire
    time.sleep(1.1)

    # Now should be None (expired)
    assert temp_cache.get(content_hash) is None

def test_cache_history_recording(temp_cache):
    temp_cache.record_history(
        url="https://auditsite.com",
        content_hash="audithash1",
        provider="mock",
        model="mock-v1",
        execution_time_ms=120.5,
        estimated_cost_usd=0.00005
    )

    history = temp_cache.get_history(limit=5)
    assert len(history) == 1
    assert history[0]["url"] == "https://auditsite.com"
    assert history[0]["provider"] == "mock"
