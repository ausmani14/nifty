"""Provider abstraction layer for NIFTY AI data ingestion.

Exposes base provider interfaces, concrete adapter stubs, and the global registry.
"""

from nifty_ai.data.providers.base import (
    BaseDataProvider,
    BaseMacroDataProvider,
    BaseMarketDataProvider,
    BaseNewsDataProvider,
    ProviderError,
    ProviderNotAvailableError,
)
from nifty_ai.data.providers.registry import (
    FinancialNewsAdapter,
    GlobalMacroAdapter,
    NSEOfficialMarketProvider,
    ProviderRegistry,
    YahooFinanceMarketProvider,
    default_registry,
)

__all__ = [
    "BaseDataProvider",
    "BaseMarketDataProvider",
    "BaseMacroDataProvider",
    "BaseNewsDataProvider",
    "ProviderError",
    "ProviderNotAvailableError",
    "NSEOfficialMarketProvider",
    "YahooFinanceMarketProvider",
    "GlobalMacroAdapter",
    "FinancialNewsAdapter",
    "ProviderRegistry",
    "default_registry",
]
