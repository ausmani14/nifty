"""Provider registry and adapter stubs for NIFTY AI.

Provides centralized registration and resolution of data providers, allowing
flexible configuration across free/development and official/reference sources.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from nifty_ai.data.providers.base import (
    BaseDataProvider,
    BaseMacroDataProvider,
    BaseMarketDataProvider,
    BaseNewsDataProvider,
    ProviderNotAvailableError,
)
from nifty_ai.data.schema import (
    NormalizedMacroRecord,
    NormalizedMarketRecord,
    NormalizedNewsRecord,
    ProviderStatus,
    ProviderTier,
)


class NSEOfficialMarketProvider(BaseMarketDataProvider):
    """National Stock Exchange of India official daily bhavcopy and reports provider."""

    def __init__(self) -> None:
        super().__init__(
            name="nse_official",
            tier=ProviderTier.OFFICIAL,
            status=ProviderStatus.REFERENCE,
            description="NSE India official daily bhavcopy and settlement archives.",
        )

    def is_available(self) -> bool:
        # Phase 1: Reference adapter defined; offline in Phase 1.
        return False

    def get_supported_symbols(self) -> List[str]:
        return ["NIFTY 50", "NIFTY BANK", "INDIA VIX"]

    def fetch_daily_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedMarketRecord]:
        raise ProviderNotAvailableError(
            f"NSEOfficialMarketProvider: Data ingestion is scheduled for Phase 2. "
            f"No live downloads or synthetic data are permitted in Phase 1."
        )


from nifty_ai.data.providers.yahoo import YahooFinanceMarketProvider


class GlobalMacroAdapter(BaseMacroDataProvider):
    """Global macroeconomic context data provider (Crude, DXY, US Yields)."""

    def __init__(self) -> None:
        super().__init__(
            name="global_macro_adapter",
            tier=ProviderTier.FREE,
            status=ProviderStatus.PLANNED,
            description="Composite global and macroeconomic indicator provider.",
        )

    def is_available(self) -> bool:
        return False

    def get_supported_indicators(self) -> List[str]:
        return ["BRENT_CRUDE", "WTI_CRUDE", "USD_INR", "DXY", "US_10Y_YIELD"]

    def fetch_macro_series(
        self,
        indicator_name: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedMacroRecord]:
        raise ProviderNotAvailableError(
            f"GlobalMacroAdapter: Macro ingestion is scheduled for Phase 9."
        )


class FinancialNewsAdapter(BaseNewsDataProvider):
    """Financial news and economic sentiment provider."""

    def __init__(self) -> None:
        super().__init__(
            name="financial_news_adapter",
            tier=ProviderTier.FREE,
            status=ProviderStatus.PLANNED,
            description="Financial news headlines and sentiment aggregator.",
        )

    def is_available(self) -> bool:
        return False

    def fetch_news(
        self,
        start_time: datetime,
        end_time: datetime,
        symbols: Optional[List[str]] = None,
    ) -> List[NormalizedNewsRecord]:
        raise ProviderNotAvailableError(
            f"FinancialNewsAdapter: News intelligence ingestion is scheduled for Phase 10."
        )


class ProviderRegistry:
    """Registry maintaining active and available data providers."""

    def __init__(self) -> None:
        self._market_providers: Dict[str, BaseMarketDataProvider] = {}
        self._macro_providers: Dict[str, BaseMacroDataProvider] = {}
        self._news_providers: Dict[str, BaseNewsDataProvider] = {}

    def register_market_provider(self, provider: BaseMarketDataProvider) -> None:
        """Register a market data provider instance."""
        self._market_providers[provider.name] = provider

    def register_macro_provider(self, provider: BaseMacroDataProvider) -> None:
        """Register a macro data provider instance."""
        self._macro_providers[provider.name] = provider

    def register_news_provider(self, provider: BaseNewsDataProvider) -> None:
        """Register a news data provider instance."""
        self._news_providers[provider.name] = provider

    def get_market_provider(self, name: str) -> BaseMarketDataProvider:
        """Retrieve a registered market data provider by name."""
        if name not in self._market_providers:
            raise KeyError(
                f"Market provider '{name}' not found. "
                f"Available: {list(self._market_providers.keys())}"
            )
        return self._market_providers[name]

    def get_macro_provider(self, name: str) -> BaseMacroDataProvider:
        """Retrieve a registered macro data provider by name."""
        if name not in self._macro_providers:
            raise KeyError(
                f"Macro provider '{name}' not found. "
                f"Available: {list(self._macro_providers.keys())}"
            )
        return self._macro_providers[name]

    def get_news_provider(self, name: str) -> BaseNewsDataProvider:
        """Retrieve a registered news data provider by name."""
        if name not in self._news_providers:
            raise KeyError(
                f"News provider '{name}' not found. "
                f"Available: {list(self._news_providers.keys())}"
            )
        return self._news_providers[name]

    def list_market_providers(self) -> List[BaseMarketDataProvider]:
        """Return all registered market providers."""
        return list(self._market_providers.values())

    def list_macro_providers(self) -> List[BaseMacroDataProvider]:
        """Return all registered macro providers."""
        return list(self._macro_providers.values())

    def list_news_providers(self) -> List[BaseNewsDataProvider]:
        """Return all registered news providers."""
        return list(self._news_providers.values())


# Module-level default registry initialized with baseline adapter stubs
default_registry = ProviderRegistry()
default_registry.register_market_provider(NSEOfficialMarketProvider())
default_registry.register_market_provider(YahooFinanceMarketProvider())
default_registry.register_macro_provider(GlobalMacroAdapter())
default_registry.register_news_provider(FinancialNewsAdapter())


__all__ = [
    "NSEOfficialMarketProvider",
    "YahooFinanceMarketProvider",
    "GlobalMacroAdapter",
    "FinancialNewsAdapter",
    "ProviderRegistry",
    "default_registry",
]
