"""Dhan API adapter.

API docs: https://dhanhq.co/docs/v2/
Developer registration: https://dhanhq.co/ (free)

Auth flow:  Access token generated from Dhan web dashboard.
"""
from __future__ import annotations

import logging
import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding

logger = logging.getLogger("financegpt.portfolio.broker.dhan")

_BASE = "https://api.dhan.co/v2"


class DhanBroker(BaseBroker):
    BROKER_ID = "dhan"
    BROKER_NAME = "Dhan"
    AUTH_TYPE = "api_key"
    SUPPORTS_API = True
    SUPPORTS_MF = False
    WEBSITE = "https://dhan.co"
    DEVELOPER_URL = "https://dhanhq.co/docs/v2/"

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = "", **kwargs):
        super().__init__(api_key, api_secret, access_token, **kwargs)
        self.client_id = kwargs.get("client_id", "")

    def get_auth_url(self, redirect_uri: str) -> str:
        # Dhan uses dashboard-generated access token, no OAuth redirect
        return "https://dhanhq.co/docs/v2/"

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        """``auth_code`` is the access token from Dhan dashboard."""
        self.access_token = auth_code
        return {"access_token": self.access_token, "client_id": self.client_id}

    def _headers(self) -> dict:
        return {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
        }

    def get_holdings(self) -> list[Holding]:
        r = requests.get(f"{_BASE}/holdings", headers=self._headers())
        r.raise_for_status()
        items = r.json()
        if not isinstance(items, list):
            items = items.get("data", [])
        holdings = []
        for item in items:
            qty = item.get("totalQty", 0) or item.get("quantity", 0)
            if qty <= 0:
                continue
            exchange = "NSE"
            exch_seg = item.get("exchangeSegment", "")
            if "BSE" in str(exch_seg):
                exchange = "BSE"
            holdings.append(Holding(
                symbol=item.get("tradingSymbol", ""),
                isin=item.get("isin", ""),
                name=item.get("tradingSymbol", ""),
                exchange=exchange,
                quantity=qty,
                avg_price=item.get("avgCostPrice", 0.0),
                current_price=item.get("lastTradedPrice", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings
