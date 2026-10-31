"""Yahoo Finance daily market data provider for NIFTY AI.

Implements BaseMarketDataProvider for the development tier using the public
chart API, parsing daily bars into NormalizedMarketRecord instances.
"""

from datetime import date, datetime, time, timezone
import json
import time as time_module
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

from nifty_ai.data.providers.base import (
    BaseMarketDataProvider,
    ProviderError,
    ProviderNotAvailableError,
)
from nifty_ai.data.schema import (
    DataFrequency,
    NormalizedMarketRecord,
    ProvenanceMetadata,
    ProviderStatus,
    ProviderTier,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Canonical symbol mapping
SYMBOL_MAPPING: Dict[str, str] = {
    "NIFTY 50": "^NSEI",
    "NIFTY": "^NSEI",
    "^NSEI": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "^NSEBANK": "^NSEBANK",
    "INDIA VIX": "^INDIAVIX",
    "^INDIAVIX": "^INDIAVIX",
}


class YahooFinanceMarketProvider(BaseMarketDataProvider):
    """Yahoo Finance historical daily data provider for development and testing.

    Note: This is a development-tier provider. It is NOT the official exchange
    reference provider (NSEOfficialMarketProvider is reserved for authoritative archives).
    """

    EARLIEST_NIFTY_DATE = date(2007, 9, 17)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self) -> None:
        super().__init__(
            name="yahoo_finance",
            tier=ProviderTier.FREE,
            status=ProviderStatus.DEVELOPMENT,
            description="Yahoo Finance daily market data adapter for development.",
        )

    def is_available(self) -> bool:
        """Provider is active and available for development ingestion."""
        return True

    def get_supported_symbols(self) -> List[str]:
        return list(SYMBOL_MAPPING.keys())

    def resolve_symbol(self, symbol: str) -> str:
        """Map canonical index symbol to Yahoo Finance ticker."""
        normalized = symbol.strip().upper()
        if normalized in SYMBOL_MAPPING:
            return SYMBOL_MAPPING[normalized]
        # Return as-is if already formatted
        return symbol

    def parse_chart_response(
        self,
        raw_json_str: str,
        canonical_symbol: str,
        retrieval_timestamp: Optional[datetime] = None,
    ) -> Tuple[List[NormalizedMarketRecord], Dict[str, Any]]:
        """Parse raw Yahoo Finance chart API JSON into NormalizedMarketRecord instances.

        This pure parser does not perform network operations, making it deterministic
        and safe for offline testing.
        """
        retrieval_dt = retrieval_timestamp or datetime.now(timezone.utc)
        try:
            payload = json.loads(raw_json_str)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Malformed JSON response from Yahoo Finance: {exc}") from exc

        chart = payload.get("chart", {})
        error = chart.get("error")
        if error:
            code = error.get("code", "UNKNOWN")
            desc = error.get("description", "Unknown error")
            raise ProviderError(f"Yahoo Finance API error [{code}]: {desc}")

        results = chart.get("result")
        if not results:
            raise ProviderError("Empty result payload returned from Yahoo Finance.")

        data = results[0]
        timestamps: List[int] = data.get("timestamp", [])
        indicators = data.get("indicators", {})
        quote_list = indicators.get("quote", [])

        if not timestamps or not quote_list:
            return [], {
                "raw_count": 0,
                "valid_count": 0,
                "null_count": 0,
                "null_dates": [],
            }

        quote = quote_list[0]
        opens: List[Optional[float]] = quote.get("open", [])
        highs: List[Optional[float]] = quote.get("high", [])
        lows: List[Optional[float]] = quote.get("low", [])
        closes: List[Optional[float]] = quote.get("close", [])
        volumes: List[Optional[float]] = quote.get("volume", [])

        records: List[NormalizedMarketRecord] = []
        null_dates: List[str] = []

        for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
            # Compute trading date in Asia/Kolkata
            source_dt = datetime.fromtimestamp(ts, tz=MARKET_TIMEZONE)
            trading_d = source_dt.date()

            # Detect null session (e.g. market holidays / exchange closures included as nulls)
            if o is None or h is None or l is None or c is None:
                null_dates.append(trading_d.isoformat())
                continue

            # Standardize market close timestamp strictly to 15:30:00 IST on trading_date
            # to guarantee zero look-ahead bias
            bar_timestamp = datetime.combine(trading_d, time(15, 30, 0), tzinfo=MARKET_TIMEZONE)

            provenance = ProvenanceMetadata(
                provider=self.name,
                source_identifier=canonical_symbol,
                retrieval_timestamp=retrieval_dt,
                source_timestamp=source_dt,
                timezone="Asia/Kolkata",
                data_frequency=DataFrequency.DAILY,
                tier=self.tier,
                extra_metadata={"raw_source_ticker": self.resolve_symbol(canonical_symbol)},
            )

            vol_val = float(v) if (v is not None and v > 0) else 0.0

            record = NormalizedMarketRecord(
                timestamp=bar_timestamp,
                trading_date=trading_d,
                symbol=canonical_symbol,
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=vol_val,
                provenance=provenance,
                status="finalized",
            )
            records.append(record)

        # Sort chronologically by timestamp
        records.sort(key=lambda r: r.timestamp)

        stats = {
            "raw_count": len(timestamps),
            "valid_count": len(records),
            "null_count": len(null_dates),
            "null_dates": null_dates,
        }
        return records, stats

    def fetch_raw_payload(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[str, datetime]:
        """Fetch raw JSON response string from Yahoo Finance chart API.

        Performs network request with timeout and error handling.
        """
        ticker = self.resolve_symbol(symbol)
        start = start_date or self.EARLIEST_NIFTY_DATE
        end = end_date or datetime.now(MARKET_TIMEZONE).date()

        if start > end:
            raise ValueError(f"start_date ({start}) cannot be after end_date ({end}).")

        # Convert to Unix epoch seconds
        start_dt = datetime.combine(start, time(0, 0, 0), tzinfo=MARKET_TIMEZONE)
        end_dt = datetime.combine(end, time(23, 59, 59), tzinfo=MARKET_TIMEZONE)
        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        encoded_ticker = urllib.parse.quote(ticker)
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}?"
            f"period1={period1}&period2={period2}&interval=1d&events=history"
        )

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json",
            },
        )

        retrieval_dt = datetime.now(timezone.utc)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                if status_code != 200:
                    raise ProviderError(
                        f"Yahoo Finance returned non-200 status code: {status_code}"
                    )
                raw_bytes = resp.read()
                raw_text = raw_bytes.decode("utf-8")
                return raw_text, retrieval_dt
        except urllib.error.HTTPError as http_err:
            if http_err.code == 429:
                raise ProviderError(
                    f"Yahoo Finance rate limit reached (HTTP 429): {http_err.reason}"
                ) from http_err
            raise ProviderError(
                f"Yahoo Finance HTTP error [{http_err.code}]: {http_err.reason}"
            ) from http_err
        except urllib.error.URLError as url_err:
            raise ProviderError(
                f"Network error connecting to Yahoo Finance: {url_err.reason}"
            ) from url_err
        except TimeoutError as to_err:
            raise ProviderError("Connection timed out contacting Yahoo Finance.") from to_err
        except Exception as exc:
            raise ProviderError(f"Unexpected error fetching from Yahoo Finance: {exc}") from exc

    def fetch_daily_ohlcv(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[NormalizedMarketRecord]:
        """Download and normalize daily OHLCV bars from Yahoo Finance."""
        raw_text, retrieval_dt = self.fetch_raw_payload(symbol, start_date, end_date)
        records, _ = self.parse_chart_response(
            raw_text,
            canonical_symbol=symbol,
            retrieval_timestamp=retrieval_dt,
        )
        return records


__all__ = ["YahooFinanceMarketProvider", "SYMBOL_MAPPING"]
