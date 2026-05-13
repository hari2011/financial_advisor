"""5Paisa API adapter.

API docs: https://www.5paisa.com/developerapi
Developer registration: https://dev.5paisa.com/ (free)

Auth flow:  TOTP / OAuth → access token.
"""
from __future__ import annotations

import logging
import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding

logger = logging.getLogger("financegpt.portfolio.broker.fivepaisa")

_BASE = "https://Openapi.5paisa.com"


class FivePaisaBroker(BaseBroker):
    BROKER_ID = "fivepaisa"
    BROKER_NAME = "5Paisa"
    AUTH_TYPE = "totp"
    SUPPORTS_API = True
    SUPPORTS_MF = False
    WEBSITE = "https://www.5paisa.com"
    DEVELOPER_URL = "https://www.5paisa.com/developerapi"

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = "", **kwargs):
        super().__init__(api_key, api_secret, access_token, **kwargs)
        self.client_code = kwargs.get("client_code", "")
        self.encryption_key = kwargs.get("encryption_key", "")

    def get_auth_url(self, redirect_uri: str) -> str:
        return (
            f"https://dev-openapi.5paisa.com/WebVendorLogin/VLogin/Index?"
            f"VendorKey={self.api_key}&ResponseURL={redirect_uri}"
        )

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        """``auth_code`` is the RequestToken from 5Paisa OAuth callback."""
        r = requests.post(
            f"{_BASE}/VendorsAPI/Service1.svc/V2/LoginRequestMobileNewbyEmail",
            json={
                "head": {"appName": self.api_key, "appVer": "1.0",
                         "key": self.encryption_key, "osName": "WEB",
                         "requestCode": "5PLoginV2"},
                "body": {"RequestToken": auth_code,
                         "EncryKey": self.encryption_key},
            },
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json().get("body", {})
        self.access_token = data.get("JWTToken", "") or data.get("Token", "")
        self.client_code = data.get("ClientCode", self.client_code)
        return {
            "access_token": self.access_token,
            "client_id": self.client_code,
        }

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_holdings(self) -> list[Holding]:
        r = requests.post(
            f"{_BASE}/VendorsAPI/Service1.svc/V3/Holding",
            json={
                "head": {"appName": self.api_key, "appVer": "1.0",
                         "key": self.encryption_key, "osName": "WEB",
                         "requestCode": "5PHolding"},
                "body": {"ClientCode": self.client_code},
            },
            headers=self._headers(),
        )
        r.raise_for_status()
        items = r.json().get("body", {}).get("Data", [])
        holdings = []
        for item in items:
            qty = item.get("Quantity", 0)
            if qty <= 0:
                continue
            holdings.append(Holding(
                symbol=item.get("ScripName", ""),
                isin=item.get("ISIN", ""),
                name=item.get("ScripName", ""),
                exchange=item.get("Exch", "NSE"),
                quantity=qty,
                avg_price=item.get("AvgRate", 0.0),
                current_price=item.get("CurrentPrice", 0.0) or item.get("LTP", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings
