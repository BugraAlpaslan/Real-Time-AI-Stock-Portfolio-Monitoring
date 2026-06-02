import json
import time
import urllib.error
import urllib.request
from decimal import Decimal

from app.config import settings

_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL = 300  # 5 dakika


def _fetch_midas(ticker: str) -> float | None:
    url = f"{settings.midas_base_url}/quotes?symbols={ticker}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
        # Olası yanıt yapıları deneniyor
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data.get(ticker) or data.get("data", [None])[0] if "data" in data else data
        else:
            return None
        if item is None:
            return None
        for key in ("price", "last", "lastPrice", "close", "regularMarketPrice"):
            val = item.get(key) if isinstance(item, dict) else None
            if val is not None:
                return float(val)
    except Exception:
        pass
    return None


def _fetch_yahoo(ticker: str) -> float | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
        meta = data["chart"]["result"][0]["meta"]
        return float(meta.get("regularMarketPrice") or meta.get("previousClose"))
    except Exception:
        pass
    return None


def get_price(ticker: str) -> Decimal | None:
    now = time.monotonic()
    if ticker in _cache:
        price, ts = _cache[ticker]
        if now - ts < CACHE_TTL:
            return Decimal(str(price))

    price = _fetch_midas(ticker) or _fetch_yahoo(ticker)
    if price is not None:
        _cache[ticker] = (price, now)
        return Decimal(str(price))
    return None
