"""ICICI Direct Breeze API adapter.

API docs: https://api.icicidirect.com/apiuser/home
Developer registration: https://api.icicidirect.com/apiuser/home (free)

Auth flow:  API session token obtained via ICICI Direct web login.
"""
from __future__ import annotations

import logging
import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding

logger = logging.getLogger("financegpt.portfolio.broker.icici_direct")

_BASE = "https://api.icicidirect.com/breezeapi/api/v1"


class ICICIDirectBroker(BaseBroker):
    BROKER_ID = "icici_direct"
    BROKER_NAME = "ICICI Direct (Breeze)"
    AUTH_TYPE = "api_key"
    SUPPORTS_API = True
    SUPPORTS_MF = False
    WEBSITE = "https://www.icicidirect.com"
    DEVELOPER_URL = "https://api.icicidirect.com/apiuser/home"

    def get_auth_url(self, redirect_uri: str) -> str:
        return (
            f"https://api.icicidirect.com/apiuser/login?"
            f"api_key={self.api_key}"
        )

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        """``auth_code`` is the session token from ICICI Direct login."""
        r = requests.get(
            f"{_BASE}/customerdetails",
            headers={
                "Content-Type": "application/json",
                "X-SessionToken": auth_code,
                "apikey": self.api_key,
            },
        )
        r.raise_for_status()
        self.access_token = auth_code
        data = r.json().get("Success", {})
        return {
            "access_token": self.access_token,
            "client_id": data.get("demat_id", ""),
        }

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-SessionToken": self.access_token,
            "apikey": self.api_key,
        }

    def get_holdings(self) -> list[Holding]:
        r = requests.get(
            f"{_BASE}/portfolioholdings",
            headers=self._headers(),
            params={"exchange_code": "NSE"},
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("Success", [])
        if not isinstance(items, list):
            return []
        holdings = []
        for item in items:
            qty = item.get("quantity", 0)
            if qty <= 0:
                continue
            holdings.append(Holding(
                symbol=item.get("stock_code", ""),
                isin=item.get("isin_code", ""),
                name=item.get("company_name", ""),
                exchange=item.get("exchange_code", "NSE"),
                quantity=qty,
                avg_price=item.get("average_price", 0.0),
                current_price=item.get("current_market_price", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings
