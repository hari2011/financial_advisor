"""Paytm Money adapter — CSV import only.

Paytm Money has discontinued its public trading API.
Users can export holdings from the Paytm Money app.
"""
from __future__ import annotations

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding


class PaytmMoneyBroker(BaseBroker):
    BROKER_ID = "paytm_money"
    BROKER_NAME = "Paytm Money"
    AUTH_TYPE = "manual"
    SUPPORTS_API = False
    SUPPORTS_MF = True
    WEBSITE = "https://www.paytmmoney.com"
    DEVELOPER_URL = ""

    CSV_SIGNATURES = ["Stock Name", "ISIN", "Shares", "Average Price"]

    def get_auth_url(self, redirect_uri: str) -> str:
        return ""

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        return {}

    def get_holdings(self) -> list[Holding]:
        return []
