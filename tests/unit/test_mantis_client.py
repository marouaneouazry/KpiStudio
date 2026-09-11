import pytest
from unittest.mock import MagicMock
from app.infrastructure.mantis.client import MantisClient

@pytest.fixture
def mock_history():
    return [
        {
            "created_at": "2026-01-05T09:00:00+00:00",
            "field": {"name": "status"},
            "new_value": {"label": "En cours"}
        },
        {
            "created_at": "2026-01-07T14:00:00+00:00",
            "field": {"name": "status"},
            "new_value": {"label": "A Clôturer"}
        }
    ]

def test_fetch_ticket_history_success(mock_history):
    client = MantisClient(base_url="http://mantis.test", token="test_token", verify_ssl=False)
    client.clear_cache()

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"issues": [{"history": mock_history}]}
    mock_resp.raise_for_status.return_value = None
    mock_session.get.return_value = mock_resp

    history = client.fetch_ticket_history(1001, session=mock_session)
    assert history == mock_history
    assert mock_session.get.call_count == 1

    # Second call should return cached history without calling HTTP again
    cached_history = client.fetch_ticket_history(1001, session=mock_session)
    assert cached_history == mock_history
    assert mock_session.get.call_count == 1  # Still 1 call due to caching

def test_fetch_ticket_history_api_failure():
    client = MantisClient(base_url="http://mantis.test", token="test_token", verify_ssl=False)
    client.clear_cache()

    mock_session = MagicMock()
    mock_session.get.side_effect = Exception("Connection refused")

    history = client.fetch_ticket_history(9999, session=mock_session)
    assert history is None

def test_fetch_ticket_history_missing_config():
    client = MantisClient(base_url="", token="", verify_ssl=False)
    history = client.fetch_ticket_history(1002)
    assert history is None

def test_ttl_cache_maxsize_eviction():
    from app.infrastructure.mantis.client import TTLCache
    cache = TTLCache(maxsize=3, ttl_seconds=60)
    cache["101"] = "data_101"
    cache["102"] = "data_102"
    cache["103"] = "data_103"
    assert len(cache) == 3

    # Add 4th item -> should evict 101 (oldest)
    cache["104"] = "data_104"
    assert len(cache) == 3
    assert "101" not in cache
    assert cache["102"] == "data_102"
    assert cache["104"] == "data_104"

def test_ttl_cache_ttl_expiration(monkeypatch):
    import time
    from app.infrastructure.mantis.client import TTLCache
    cache = TTLCache(maxsize=10, ttl_seconds=10)
    
    current_time = 1000.0
    monkeypatch.setattr(time, "time", lambda: current_time)

    cache["201"] = "val_201"
    assert "201" in cache

    # Advance time beyond 10s TTL
    current_time = 1015.0
    assert "201" not in cache
    assert cache.get("201") is None
