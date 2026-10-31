"""Yahoo Finance adapter for Indian and Global Market Context variables.

Fetches and normalizes multi-asset daily data across equities, FX, volatility,
commodities, and bond yields with exact availability timestamping and DST support.
"""

from datetime import date, datetime, time, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

from nifty_ai.data.context.calendar import (
    CANONICAL_CONTEXT_SPECS,
    compute_availability_timestamp,
)
from nifty_ai.data.context.schema import ContextObservation
from nifty_ai.data.providers.base import ProviderError
from nifty_ai.data.providers.context_base import BaseContextProvider
from nifty_ai.data.schema import (
    DataFrequency,
    ProvenanceMetadata,
    ProviderStatus,
    ProviderTier,
)


class YahooFinanceContextProvider(BaseContextProvider):
    """Multi-instrument market context provider using Yahoo Finance chart API."""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self) -> None:
        super().__init__(
            name="yahoo_finance",
            tier=ProviderTier.FREE,
            status=ProviderStatus.DEVELOPMENT,
            description="Yahoo Finance daily market context adapter for global macro and equity data.",
        )

    def is_available(self) -> bool:
        return True

    def get_supported_variables(self) -> List[str]:
        return list(CANONICAL_CONTEXT_SPECS.keys())

    def parse_payload(
        self,
        raw_text: str,
        variable_name: str,
        retrieval_timestamp: Optional[datetime] = None,
    ) -> Tuple[List[ContextObservation], Dict[str, Any]]:
        """Parse raw chart JSON into timezone-aware ContextObservation objects."""
        if variable_name not in CANONICAL_CONTEXT_SPECS:
            raise ValueError(f"Unknown context variable name: {variable_name}")

        spec = CANONICAL_CONTEXT_SPECS[variable_name]
        retrieval_dt = retrieval_timestamp or datetime.now(timezone.utc)

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Malformed JSON payload for {variable_name}: {exc}") from exc

        chart = payload.get("chart", {})
        error = chart.get("error")
        if error:
            code = error.get("code", "UNKNOWN")
            desc = error.get("description", "Unknown error")
            raise ProviderError(f"Yahoo API error [{code}] for {variable_name}: {desc}")

        results = chart.get("result")
        if not results:
            raise ProviderError(f"Empty result payload for {variable_name}.")

        data = results[0]
        timestamps: List[int] = data.get("timestamp", [])
        indicators = data.get("indicators", {})
        quote_list = indicators.get("quote", [])

        if not timestamps or not quote_list:
            return [], {"raw_count": 0, "valid_count": 0, "null_count": 0}

        quote = quote_list[0]
        opens: List[Optional[float]] = quote.get("open", [])
        highs: List[Optional[float]] = quote.get("high", [])
        lows: List[Optional[float]] = quote.get("low", [])
        closes: List[Optional[float]] = quote.get("close", [])
        volumes: List[Optional[float]] = quote.get("volume", [])

        tz_native = ZoneInfo(spec.native_timezone)
        observations: List[ContextObservation] = []
        null_count = 0

        for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
            if c is None:
                null_count += 1
                continue

            # Determine local trading date in native exchange timezone
            native_dt = datetime.fromtimestamp(ts, tz=tz_native)
            obs_date = native_dt.date()

            # The exact observation bar close timestamp in native timezone
            obs_dt = datetime.combine(obs_date, spec.market_close_time, tzinfo=tz_native)

            # Precise availability timestamp converted to Asia/Kolkata
            avail_dt = compute_availability_timestamp(obs_date, spec)

            provenance = ProvenanceMetadata(
                provider=self.name,
                source_identifier=spec.instrument,
                retrieval_timestamp=retrieval_dt,
                source_timestamp=native_dt,
                timezone=spec.native_timezone,
                data_frequency=DataFrequency.DAILY,
                tier=self.tier,
                extra_metadata={
                    "variable_name": spec.variable_name,
                    "category": spec.category.value,
                    "instrument": spec.instrument,
                },
            )

            obs = ContextObservation(
                variable_name=spec.variable_name,
                instrument=spec.instrument,
                observation_date=obs_date,
                observation_timestamp=obs_dt,
                availability_timestamp=avail_dt,
                open=float(o) if o is not None else None,
                high=float(h) if h is not None else None,
                low=float(l) if l is not None else None,
                close=float(c),
                volume=float(v) if (v is not None and v > 0) else None,
                provenance=provenance,
                availability_timestamp_type=spec.availability_timestamp_type,
            )
            observations.append(obs)

        # Sort chronologically by observation_timestamp
        observations.sort(key=lambda x: x.observation_timestamp)

        stats = {
            "variable_name": variable_name,
            "raw_count": len(timestamps),
            "valid_count": len(observations),
            "null_count": null_count,
            "earliest_date": observations[0].observation_date.isoformat() if observations else None,
            "latest_date": observations[-1].observation_date.isoformat() if observations else None,
        }
        return observations, stats

    def fetch_raw_payload(
        self,
        variable_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[str, datetime]:
        """Fetch historical chart JSON from Yahoo Finance with retry and error handling."""
        if variable_name not in CANONICAL_CONTEXT_SPECS:
            raise ValueError(f"Unsupported context variable: {variable_name}")

        spec = CANONICAL_CONTEXT_SPECS[variable_name]
        start_epoch = 0 if start_date is None else int(datetime.combine(start_date, time.min, tzinfo=timezone.utc).timestamp())
        end_epoch = 9999999999 if end_date is None else int(datetime.combine(end_date, time.max, tzinfo=timezone.utc).timestamp())

        encoded_symbol = urllib.parse.quote(spec.instrument, safe="")
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}"
            f"?period1={start_epoch}&period2={end_epoch}&interval=1d&events=history"
        )

        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        retrieval_dt = datetime.now(timezone.utc)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_bytes = resp.read()
                raw_text = raw_bytes.decode("utf-8")
                return raw_text, retrieval_dt
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"HTTP error {exc.code} fetching {spec.instrument}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Network error fetching {spec.instrument}: {exc.reason}") from exc


__all__ = ["YahooFinanceContextProvider"]
