"""Upstox v2 API adapter.

API docs: https://upstox.com/developer/api-documentation/
Developer registration: https://account.upstox.com/developer/apps (free)

Auth flow:  OAuth2 authorization code → access_token (valid 1 day).
"""
from __future__ import annotations

import logging
import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding

logger = logging.getLogger("financegpt.portfolio.broker.upstox")

_BASE = "https://api.upstox.com/v2"
_AUTH = "https://api.upstox.com/v2/login/authorization/dialog"


class UpstoxBroker(BaseBroker):
    BROKER_ID = "upstox"
    BROKER_NAME = "Upstox"
    AUTH_TYPE = "oauth"
    SUPPORTS_API = True
    SUPPORTS_MF = False
    WEBSITE = "https://upstox.com"
    DEVELOPER_URL = "https://account.upstox.com/developer/apps"

    def get_auth_url(self, redirect_uri: str) -> str:
        return (
            f"{_AUTH}?response_type=code&client_id={self.api_key}"
            f"&redirect_uri={redirect_uri}"
        )

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        r = requests.post(f"{_BASE}/login/authorization/token", data={
            "code": auth_code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        r.raise_for_status()
        data = r.json()
        self.access_token = data.get("access_token", "")
        return {
            "access_token": self.access_token,
            "refresh_token": data.get("refresh_token", ""),
            "client_id": data.get("user_id", ""),
        }

    def get_holdings(self) -> list[Holding]:
        r = requests.get(
            f"{_BASE}/portfolio/long-term-holdings",
            headers=self._headers(),
        )
        r.raise_for_status()
        items = r.json().get("data", [])
        holdings = []
        for item in items:
            qty = item.get("quantity", 0)
            if qty <= 0:
                continue
            symbol = item.get("tradingsymbol", "")
            # Upstox format: "NSE_EQ|INE002A01018" in instrument_token
            exchange = "NSE"
            itoken = item.get("instrument_token", "")
            if itoken.startswith("BSE"):
                exchange = "BSE"
            holdings.append(Holding(
                symbol=symbol,
                isin=item.get("isin", ""),
                name=item.get("company_name", symbol),
                exchange=exchange,
                quantity=qty,
                avg_price=item.get("average_price", 0.0),
                current_price=item.get("last_price", 0.0),
                pnl=item.get("pnl", 0.0),
                day_change=item.get("day_change", 0.0),
                day_change_pct=item.get("day_change_percentage", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings
