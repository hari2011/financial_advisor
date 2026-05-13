"""Motilal Oswal adapter — CSV import only.

Motilal Oswal's API (MO Investor) has limited public access.
Users can export holdings from the MO Investor app/website.
"""
from __future__ import annotations

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding


class MotilalBroker(BaseBroker):
    BROKER_ID = "motilal"
    BROKER_NAME = "Motilal Oswal"
    AUTH_TYPE = "manual"
    SUPPORTS_API = False
    SUPPORTS_MF = False
    WEBSITE = "https://www.motilaloswal.com"
    DEVELOPER_URL = ""

    CSV_SIGNATURES = ["Scrip Name", "ISIN", "Qty", "Avg Cost"]

    def get_auth_url(self, redirect_uri: str) -> str:
        return ""

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        return {}

    def get_holdings(self) -> list[Holding]:
        return []
