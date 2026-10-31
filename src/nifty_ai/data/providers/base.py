"""Abstract base classes and interfaces for data providers in NIFTY AI.

Decouples ingestion logic from specific financial data vendors, enabling seamless
swapping between development feeds, official exchange archives, and production APIs.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional
from nifty_ai.data.schema import (
    NormalizedMacroRecord,
    NormalizedMarketRecord,
    NormalizedNewsRecord,
    ProviderStatus,
    ProviderTier,
)


class ProviderError(Exception):
    """Base exception for data provider operations."""
    pass


class ProviderNotAvailableError(ProviderError):
    """Raised when a requested provider is not active or available in the current phase."""
    pass


class BaseDataProvider(ABC):
    """Base class for all external data sources."""

    def __init__(
        self,
        name: str,
        tier: ProviderTier,
        status: ProviderStatus,
        description: str = "",
    ) -> None:
        self.name = name
        self.tier = tier
        self.status = status
        self.description = description

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is operational and credentials/network are configured."""
        pass

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name={self.name!r} "
            f"tier={self.tier.value} status={self.status.value}>"
        )


class BaseMarketDataProvider(BaseDataProvider):
    """Abstract interface for equity index and asset price data providers."""

    @abstractmethod
    def fetch_daily_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedMarketRecord]:
        """Fetch daily OHLCV bars normalized to NormalizedMarketRecord.

        Args:
            symbol: Target symbol or index identifier (e.g. 'NIFTY 50', '^NSEI').
            start_date: Start of historical window (inclusive).
            end_date: End of historical window (inclusive).

        Returns:
            List of chronologically ordered NormalizedMarketRecord objects.
        """
        pass

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Return list of supported symbol identifiers."""
        pass


class BaseMacroDataProvider(BaseDataProvider):
    """Abstract interface for global and macroeconomic context data providers."""

    @abstractmethod
    def fetch_macro_series(
        self,
        indicator_name: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedMacroRecord]:
        """Fetch macro indicator observations normalized to NormalizedMacroRecord.

        Args:
            indicator_name: Target indicator (e.g. 'INDIA_VIX', 'BRENT_CRUDE', 'USD_INR').
            start_date: Start of historical window (inclusive).
            end_date: End of historical window (inclusive).

        Returns:
            List of chronologically ordered NormalizedMacroRecord objects.
        """
        pass

    @abstractmethod
    def get_supported_indicators(self) -> List[str]:
        """Return list of supported indicator identifiers."""
        pass


class BaseNewsDataProvider(BaseDataProvider):
    """Abstract interface for financial news and economic intelligence providers."""

    @abstractmethod
    def fetch_news(
        self,
        start_time: datetime,
        end_time: datetime,
        symbols: Optional[List[str]] = None,
    ) -> List[NormalizedNewsRecord]:
        """Fetch financial news articles/headlines within a point-in-time window.

        Args:
            start_time: Window opening timestamp (timezone-aware).
            end_time: Window closing timestamp (timezone-aware, <= snapshot cutoff).
            symbols: Optional list of relevant entity symbols to filter.

        Returns:
            List of point-in-time NormalizedNewsRecord objects.
        """
        pass


__all__ = [
    "ProviderError",
    "ProviderNotAvailableError",
    "BaseDataProvider",
    "BaseMarketDataProvider",
    "BaseMacroDataProvider",
    "BaseNewsDataProvider",
]
