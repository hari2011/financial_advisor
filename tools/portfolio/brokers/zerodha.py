"""Zerodha Kite Connect adapter.

API docs: https://kite.trade/docs/connect/v3/
Developer registration: https://developers.kite.trade/ (₹2000/month)

Auth flow:
  1. User visits Kite login URL → enters credentials
  2. Redirect back with ``request_token``
  3. Exchange request_token + api_secret → access_token (valid 1 day)
"""
from __future__ import annotations

import hashlib
import logging

import requests

from tools.portfolio.base_broker import BaseBroker
from tools.portfolio.models import Holding, MFHolding

logger = logging.getLogger("financegpt.portfolio.broker.zerodha")

_BASE = "https://api.kite.trade"
_LOGIN = "https://kite.zerodha.com/connect/login"


class ZerodhaBroker(BaseBroker):
    BROKER_ID = "zerodha"
    BROKER_NAME = "Zerodha (Kite Connect)"
    AUTH_TYPE = "oauth"
    SUPPORTS_API = True
    SUPPORTS_MF = True
    WEBSITE = "https://zerodha.com"
    DEVELOPER_URL = "https://developers.kite.trade/"

    # ── Auth ──

    def get_auth_url(self, redirect_uri: str) -> str:
        return f"{_LOGIN}?v=3&api_key={self.api_key}&redirect_uri={redirect_uri}"

    def authenticate(self, auth_code: str, redirect_uri: str = "") -> dict:
        checksum = hashlib.sha256(
            (self.api_key + auth_code + self.api_secret).encode()
        ).hexdigest()
        r = requests.post(f"{_BASE}/session/token", data={
            "api_key": self.api_key,
            "request_token": auth_code,
            "checksum": checksum,
        })
        r.raise_for_status()
        data = r.json().get("data", {})
        self.access_token = data.get("access_token", "")
        return {
            "access_token": self.access_token,
            "refresh_token": data.get("refresh_token", ""),
            "client_id": data.get("user_id", ""),
        }

    def _headers(self) -> dict:
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
        }

    # ── Data ──

    def get_holdings(self) -> list[Holding]:
        r = requests.get(f"{_BASE}/portfolio/holdings", headers=self._headers())
        r.raise_for_status()
        items = r.json().get("data", [])
        holdings = []
        for item in items:
            if item.get("quantity", 0) <= 0:
                continue
            holdings.append(Holding(
                symbol=item.get("tradingsymbol", ""),
                isin=item.get("isin", ""),
                name=item.get("tradingsymbol", ""),
                exchange=item.get("exchange", "NSE"),
                quantity=item.get("quantity", 0),
                avg_price=item.get("average_price", 0.0),
                current_price=item.get("last_price", 0.0),
                pnl=item.get("pnl", 0.0),
                day_change=item.get("day_change", 0.0),
                day_change_pct=item.get("day_change_percentage", 0.0),
                broker=self.BROKER_ID,
            ))
        return holdings

    def get_mf_holdings(self) -> list[MFHolding]:
        try:
            r = requests.get(f"{_BASE}/mf/holdings", headers=self._headers())
            r.raise_for_status()
            items = r.json().get("data", [])
        except Exception:
            return []
        mf = []
        for item in items:
            mf.append(MFHolding(
                scheme_name=item.get("fund", ""),
                folio=item.get("folio", ""),
                units=item.get("quantity", 0.0),
                avg_nav=item.get("average_price", 0.0),
                current_nav=item.get("last_price", 0.0),
                invested_value=item.get("average_price", 0) * item.get("quantity", 0),
                current_value=item.get("last_price", 0) * item.get("quantity", 0),
                pnl=item.get("pnl", 0.0),
                broker=self.BROKER_ID,
            ))
        return mf

    def get_positions(self) -> list[dict]:
        r = requests.get(f"{_BASE}/portfolio/positions", headers=self._headers())
        r.raise_for_status()
        data = r.json().get("data", {})
        return data.get("net", [])
