"""Abstract base provider interface for market context data."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.data.context.schema import ContextObservation
from nifty_ai.data.schema import ProviderStatus, ProviderTier


class BaseContextProvider(ABC):
    """Abstract interface for ingesting multi-asset market context variables."""

    def __init__(
        self,
        name: str,
        tier: ProviderTier = ProviderTier.FREE,
        status: ProviderStatus = ProviderStatus.DEVELOPMENT,
        description: str = "",
    ) -> None:
        self.name = name
        self.tier = tier
        self.status = status
        self.description = description

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider connection or data access is active."""
        pass

    @abstractmethod
    def get_supported_variables(self) -> List[str]:
        """List canonical variable names supported by this provider."""
        pass

    @abstractmethod
    def parse_payload(
        self,
        raw_text: str,
        variable_name: str,
        retrieval_timestamp: Optional[datetime] = None,
    ) -> Tuple[List[ContextObservation], Dict[str, Any]]:
        """Parse raw response text into normalized ContextObservation records."""
        pass


__all__ = ["BaseContextProvider"]
