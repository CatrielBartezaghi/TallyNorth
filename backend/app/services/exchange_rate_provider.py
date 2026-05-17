from __future__ import annotations

import json
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"


class ExchangeRateProviderError(RuntimeError):
    pass


def yahoo_symbol(from_code: str, to_code: str) -> str:
    from_code = from_code.upper()
    to_code = to_code.upper()
    if from_code == "BTC":
        return "BTC-USD" if to_code == "USD" else f"BTC-{to_code}"
    return f"{from_code}{to_code}=X"


def fetch_yahoo_rate(from_code: str, to_code: str) -> Decimal:
    from_code = from_code.upper()
    to_code = to_code.upper()
    if from_code.upper() == to_code.upper():
        return Decimal("1")
    if from_code == "BTC" and to_code != "USD":
        return fetch_yahoo_rate("BTC", "USD") * fetch_yahoo_rate("USD", to_code)

    symbol = yahoo_symbol(from_code, to_code)
    request = Request(
        YAHOO_CHART_URL.format(symbol=symbol),
        headers={"User-Agent": "finance-tracker/1.0"},
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ExchangeRateProviderError(f"Could not fetch {from_code}->{to_code} from Yahoo Finance") from exc

    try:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
        value = meta.get("regularMarketPrice") or meta.get("previousClose")
    except (KeyError, IndexError, TypeError) as exc:
        raise ExchangeRateProviderError(f"Yahoo Finance returned an unexpected response for {symbol}") from exc

    if value is None:
        raise ExchangeRateProviderError(f"Yahoo Finance did not return a price for {symbol}")

    return Decimal(str(value))
