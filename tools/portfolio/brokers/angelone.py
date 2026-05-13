"""Angel One SmartAPI adapter.

API docs: https://smartapi.angelone.in/docs
Developer registration: https://smartapi.angelone.in/ (free)

Auth flow:  API key + client ID + password + TOTP → JWT access token.
"""
from __future__ import annotations

import logging
import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding

logger = logging.getLogger("financegpt.portfolio.broker.angelone")

_BASE = "https://apiconnect.angelone.in"


class AngelOneBroker(BaseBroker):
    BROKER_ID = "angelone"
    BROKER_NAME = "Angel One (SmartAPI)"
    AUTH_TYPE = "totp"
    SUPPORTS_API = True
    SUPPORTS_MF = False
    WEBSITE = "https://www.angelone.in"
    DEVELOPER_URL = "https://smartapi.angelone.in/"

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = "", **kwargs):
        super().__init__(api_key, api_secret, access_token, **kwargs)
        self.client_id = kwargs.get("client_id", "")
        self.password = kwargs.get("password", "")

    def get_auth_url(self, redirect_uri: str) -> str:
        # Angel One uses direct login, not OAuth redirect
        return "https://smartapi.angelone.in/docs"

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        """``auth_code`` is the TOTP from authenticator app."""
        r = requests.post(
            f"{_BASE}/rest/auth/angelbroking/user/v1/loginByPassword",
            json={
                "clientcode": self.client_id,
                "password": self.password,
                "totp": auth_code,
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": self.api_key,
            },
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        self.access_token = data.get("jwtToken", "")
        return {
            "access_token": self.access_token,
            "refresh_token": data.get("refreshToken", ""),
            "client_id": self.client_id,
        }

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": self.api_key,
        }

    def get_holdings(self) -> list[Holding]:
        r = requests.get(
            f"{_BASE}/rest/secure/angelbroking/portfolio/v1/getHolding",
            headers=self._headers(),
        )
        r.raise_for_status()
        items = r.json().get("data", [])
        if not items:
            return []
        holdings = []
        for item in items:
            qty = item.get("quantity", 0)
            if qty <= 0:
                continue
            holdings.append(Holding(
                symbol=item.get("tradingsymbol", ""),
                isin=item.get("isin", ""),
                name=item.get("tradingsymbol", ""),
                exchange=item.get("exchange", "NSE"),
                quantity=qty,
                avg_price=item.get("averageprice", 0.0),
                current_price=item.get("ltp", 0.0),
                pnl=item.get("profitandloss", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings
