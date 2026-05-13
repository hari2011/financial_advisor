"""Groww adapter — CSV import only (no public API).

Groww does not offer a public trading/portfolio API.
Users can export their holdings as CSV from the Groww app/website:
  App → Portfolio → ⋮ → Download Statement → Holdings
"""
from __future__ import annotations

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding, MFHolding


class GrowwBroker(BaseBroker):
    BROKER_ID = "groww"
    BROKER_NAME = "Groww"
    AUTH_TYPE = "manual"
    SUPPORTS_API = False
    SUPPORTS_MF = True
    WEBSITE = "https://groww.in"
    DEVELOPER_URL = ""

    # CSV column mappings for auto-detection
    CSV_SIGNATURES = [
        "Symbol", "Company Name", "Quantity", "Avg. Cost",   # Groww stocks
        "Scheme Name", "Folio", "Units",                     # Groww MF
    ]

    def get_auth_url(self, redirect_uri: str) -> str:
        return ""

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        return {}

    def get_holdings(self) -> list[Holding]:
        return []  # Use csv_import.py instead

    def get_mf_holdings(self) -> list[MFHolding]:
        return []  # Use csv_import.py instead
