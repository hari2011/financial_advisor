"""HDFC Securities adapter — CSV import only.

HDFC Securities (Blink) has limited public API access.
Users can export holdings from HDFC Securities web/app.
"""
from __future__ import annotations

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding


class HDFCSecBroker(BaseBroker):
    BROKER_ID = "hdfc_sec"
    BROKER_NAME = "HDFC Securities"
    AUTH_TYPE = "manual"
    SUPPORTS_API = False
    SUPPORTS_MF = False
    WEBSITE = "https://www.hdfcsec.com"
    DEVELOPER_URL = ""

    CSV_SIGNATURES = ["Script Name", "ISIN", "Holding Qty", "Avg. Buy Price"]

    def get_auth_url(self, redirect_uri: str) -> str:
        return ""

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        return {}

    def get_holdings(self) -> list[Holding]:
        return []
