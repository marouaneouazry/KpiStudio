import time
from collections import OrderedDict
import requests
from typing import Optional, List, Dict, Any, Tuple

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings


class TTLCache:
    """
    Size-bounded, Time-To-Live (TTL) cache.
    Automatically evicts expired items and enforces a maximum capacity using LRU order.
    """
    def __init__(self, maxsize: int = 5000, ttl_seconds: float = 900.0):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if key not in self._cache:
            return default
        created_at, value = self._cache[key]
        if time.time() - created_at > self.ttl:
            del self._cache[key]
            return default
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            del self._cache[key]
        self._cache[key] = (time.time(), value)
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None and key not in self._cache:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        now = time.time()
        expired = [k for k, (t, _) in self._cache.items() if now - t > self.ttl]
        for k in expired:
            del self._cache[k]
        return len(self._cache)


_history_cache = TTLCache(maxsize=5000, ttl_seconds=900)

class MantisClient:
    """
    HTTP Client responsible for Mantis REST API communication.
    Encapsulates endpoint construction, authentication headers, timeouts, and response caching.
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, verify_ssl: Optional[bool] = None):
        self.base_url = base_url if base_url is not None else settings.MANTIS_BASE_URL
        self.token = token if token is not None else settings.MANTIS_API_TOKEN
        self.verify_ssl = verify_ssl if verify_ssl is not None else settings.MANTIS_VERIFY_SSL

    def fetch_ticket_history(self, ticket_id: Any, session: Optional[Any] = None) -> Optional[List[Dict[str, Any]]]:
        key = str(ticket_id)
        if key in _history_cache:
            return _history_cache[key]

        if not self.token or not self.base_url:
            return None

        url = f"{self.base_url}/api/rest/index.php/issues/{ticket_id}"
        headers = {"Authorization": self.token}
        http = session or requests

        try:
            resp = http.get(url, headers=headers, timeout=10, verify=self.verify_ssl)
            resp.raise_for_status()
            data = resp.json()
            issue = data.get("issues", [{}])[0]
            history = issue.get("history", [])
            _history_cache[key] = history
            return history
        except Exception as e:
            # Print non-sensitive error notice
            print(f"[Phase2] Erreur API pour le ticket {ticket_id}: {e}")
            return None

    def clear_cache(self):
        global _history_cache
        _history_cache.clear()

_default_client = MantisClient()

def get_ticket_history(ticket_id: Any, session: Optional[Any] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Global helper function delegating to MantisClient.
    Preserves exact backward compatibility with processor.py.
    """
    return _default_client.fetch_ticket_history(ticket_id, session=session)
