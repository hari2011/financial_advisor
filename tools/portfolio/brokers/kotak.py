"""Kotak Neo API adapter.

API docs: https://neotradeapi.kotaksecurities.com/devportal/
Developer registration: https://neotradeapi.kotaksecurities.com/ (free)

Auth flow:  OAuth2 → access_token.
"""
from __future__ import annotations

import logging
import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding

logger = logging.getLogger("financegpt.portfolio.broker.kotak")

_BASE = "https://gw-napi.kotaksecurities.com"


class KotakBroker(BaseBroker):
    BROKER_ID = "kotak"
    BROKER_NAME = "Kotak Securities (Neo)"
    AUTH_TYPE = "oauth"
    SUPPORTS_API = True
    SUPPORTS_MF = False
    WEBSITE = "https://www.kotaksecurities.com"
    DEVELOPER_URL = "https://neotradeapi.kotaksecurities.com/devportal/"

    def get_auth_url(self, redirect_uri: str) -> str:
        return (
            f"https://neotradeapi.kotaksecurities.com/login?"
            f"consumer_key={self.api_key}&redirect_uri={redirect_uri}"
        )

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        r = requests.post(
            f"{_BASE}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
            },
            headers={"Authorization": f"Basic {self.api_key}:{self.api_secret}"},
        )
        r.raise_for_status()
        data = r.json()
        self.access_token = data.get("access_token", "")
        return {
            "access_token": self.access_token,
            "refresh_token": data.get("refresh_token", ""),
            "client_id": data.get("sid", ""),
        }

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "sid": self._extra.get("sid", ""),
            "Auth": self._extra.get("auth", ""),
        }

    def get_holdings(self) -> list[Holding]:
        r = requests.get(
            f"{_BASE}/Portfolio/v1.0/portfolio/holdings",
            headers=self._headers(),
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("data", [])
        if not isinstance(items, list):
            return []
        holdings = []
        for item in items:
            qty = item.get("quantity", 0) or item.get("totalQuantity", 0)
            if qty <= 0:
                continue
            holdings.append(Holding(
                symbol=item.get("symbol", "") or item.get("tradingSymbol", ""),
                isin=item.get("isin", ""),
                name=item.get("companyName", "") or item.get("symbol", ""),
                exchange=item.get("exchange", "NSE"),
                quantity=qty,
                avg_price=item.get("averagePrice", 0.0),
                current_price=item.get("lastPrice", 0.0) or item.get("ltp", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings
