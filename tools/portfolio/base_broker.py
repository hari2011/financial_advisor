"""Abstract base class for broker adapters.

Every broker adapter must subclass ``BaseBroker`` and implement the three
abstract methods: ``get_auth_url``, ``authenticate``, ``get_holdings``.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from tools.portfolio.models import Holding, MFHolding

logger = logging.getLogger("financegpt.portfolio.broker")


class BaseBroker(ABC):
    """Unified interface for all Indian stock-broker APIs."""

    BROKER_ID: str = ""          # e.g. "zerodha"
    BROKER_NAME: str = ""        # e.g. "Zerodha (Kite)"
    AUTH_TYPE: str = "oauth"     # oauth | api_key | totp | manual
    SUPPORTS_API: bool = True
    SUPPORTS_MF: bool = False
    WEBSITE: str = ""
    DEVELOPER_URL: str = ""      # Where users register for API access

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = "", **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self._extra = kwargs

    # ── Auth ──

    @abstractmethod
    def get_auth_url(self, redirect_uri: str) -> str:
        """Return the URL the user should visit to authorise the app."""
        ...

    @abstractmethod
    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        """Exchange *auth_code* (or TOTP / request-token) for an access token.

        Returns ``{"access_token": ..., "refresh_token": ..., ...}``.
        """
        ...

    def refresh_access_token(self) -> dict:
        """Refresh an expired token.  Returns updated token dict."""
        return {}

    def is_authenticated(self) -> bool:
        return bool(self.access_token)

    # ── Data ──

    @abstractmethod
    def get_holdings(self) -> list[Holding]:
        """Fetch equity / stock holdings from the broker."""
        ...

    def get_mf_holdings(self) -> list[MFHolding]:
        """Fetch mutual-fund holdings.  Override when supported."""
        return []

    def get_positions(self) -> list[dict]:
        """Fetch open intraday / F&O positions.  Optional."""
        return []

    # ── Helpers ──

    def _headers(self) -> dict:
        """Default auth headers — override per broker as needed."""
        return {"Authorization": f"Bearer {self.access_token}"}

    @classmethod
    def info(cls) -> dict:
        """Public metadata about this broker adapter."""
        return {
            "id": cls.BROKER_ID,
            "name": cls.BROKER_NAME,
            "auth_type": cls.AUTH_TYPE,
            "supports_api": cls.SUPPORTS_API,
            "supports_mf": cls.SUPPORTS_MF,
            "website": cls.WEBSITE,
            "developer_url": cls.DEVELOPER_URL,
        }
