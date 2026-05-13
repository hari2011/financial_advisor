"""High-level portfolio operations.

Orchestrates broker sync, live price enrichment, and aggregation.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

import yfinance as yf

from tools.portfolio.models import (
    BrokerAccount, Holding, MFHolding, PortfolioSummary,
)
from tools.portfolio import store
from tools.portfolio.broker_registry import get_broker_class, list_brokers
from tools.portfolio.cas_parser import parse_cas_pdf
from tools.portfolio.csv_import import import_holdings_csv

logger = logging.getLogger("financegpt.portfolio.manager")


# ──────────────────── Account management ────────────────────

def add_account(broker_id: str, client_id: str = "",
                display_name: str = "", api_key: str = "",
                access_token: str = "", auth_type: str = "") -> BrokerAccount:
    """Register a new broker account."""
    cls = get_broker_class(broker_id)
    if not cls:
        raise ValueError(f"Unknown broker: {broker_id}")

    acct = BrokerAccount(
        id=str(uuid.uuid4()),
        broker=broker_id,
        client_id=client_id,
        display_name=display_name or cls.BROKER_NAME,
        api_key=api_key,
        access_token=access_token,
        auth_type=auth_type or cls.AUTH_TYPE,
        created_at=datetime.utcnow().isoformat(),
    )
    store.save_account(acct)
    return acct


def get_accounts() -> list[BrokerAccount]:
    return store.list_accounts()


def remove_account(account_id: str):
    store.delete_account(account_id)


def get_auth_url(broker_id: str, api_key: str = "",
                 api_secret: str = "", redirect_uri: str = "") -> str:
    """Get OAuth / login URL for a broker."""
    cls = get_broker_class(broker_id)
    if not cls:
        raise ValueError(f"Unknown broker: {broker_id}")
    adapter = cls(api_key=api_key, api_secret=api_secret)
    return adapter.get_auth_url(redirect_uri)


def complete_auth(account_id: str, auth_code: str,
                  redirect_uri: str = "") -> dict:
    """Complete OAuth for an account and store the token."""
    acct = store.get_account(account_id)
    if not acct:
        raise ValueError(f"Account not found: {account_id}")
    cls = get_broker_class(acct.broker)
    if not cls:
        raise ValueError(f"Unknown broker: {acct.broker}")

    adapter = cls(api_key=acct.api_key, access_token=acct.access_token)
    result = adapter.authenticate(auth_code, redirect_uri)
    token = result.get("access_token", "")
    refresh = result.get("refresh_token", "")
    if token:
        store.update_account_token(account_id, token, refresh)
    return result


# ──────────────────── Sync ────────────────────

def sync_account(account_id: str) -> dict:
    """Fetch latest holdings from a broker API and store them.

    Returns:
        {"holdings": int, "mf_holdings": int, "errors": [str]}
    """
    acct = store.get_account(account_id)
    if not acct:
        return {"holdings": 0, "mf_holdings": 0,
                "errors": [f"Account not found: {account_id}"]}

    cls = get_broker_class(acct.broker)
    if not cls:
        return {"holdings": 0, "mf_holdings": 0,
                "errors": [f"No adapter for broker: {acct.broker}"]}
    if not cls.SUPPORTS_API:
        return {"holdings": 0, "mf_holdings": 0,
                "errors": [f"{cls.BROKER_NAME} doesn't support API sync. "
                           "Use CSV/CAS import instead."]}

    adapter = cls(api_key=acct.api_key, api_secret="",
                  access_token=acct.access_token)
    errors: list[str] = []

    # Equity holdings
    try:
        holdings = adapter.get_holdings()
        for h in holdings:
            h.account_id = account_id
        store.save_holdings(account_id, holdings)
    except Exception as e:
        holdings = []
        errors.append(f"Holdings sync failed: {e}")
        logger.exception("Holdings sync error for %s", account_id)

    # MF holdings (if supported)
    mf_holdings: list[MFHolding] = []
    if cls.SUPPORTS_MF:
        try:
            mf_holdings = adapter.get_mf_holdings()
            for m in mf_holdings:
                m.account_id = account_id
            store.save_mf_holdings(account_id, mf_holdings)
        except Exception as e:
            errors.append(f"MF holdings sync failed: {e}")
            logger.exception("MF sync error for %s", account_id)

    store.mark_synced(account_id)
    return {
        "holdings": len(holdings),
        "mf_holdings": len(mf_holdings),
        "errors": errors,
    }


# ──────────────────── Import ────────────────────

def import_file(file_path: str, account_id: str = "",
                broker_hint: str = "", password: str = "") -> dict:
    """Import holdings from a CSV, Excel, or CAS PDF file.

    If ``account_id`` is provided, holdings are stored under that account.
    Otherwise, a new manual-import account is created.
    """
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        result = parse_cas_pdf(file_path, password=password)
        holdings = result.get("holdings", [])
        mf_holdings = result.get("mf_holdings", [])
        broker = "cas_import"
        errors = result.get("errors", [])
    else:
        result = import_holdings_csv(file_path=file_path, broker_hint=broker_hint)
        holdings = result.get("holdings", [])
        mf_holdings = result.get("mf_holdings", [])
        broker = result.get("broker", "generic")
        errors = result.get("errors", [])

    if not holdings and not mf_holdings:
        return {"account_id": "", "holdings": 0, "mf_holdings": 0,
                "errors": errors or ["No holdings found in file"]}

    # Create or use account
    if not account_id:
        acct = BrokerAccount(
            id=str(uuid.uuid4()),
            broker=broker,
            display_name=f"{broker} import",
            auth_type="manual",
            created_at=datetime.utcnow().isoformat(),
        )
        store.save_account(acct)
        account_id = acct.id

    for h in holdings:
        h.account_id = account_id
    for m in mf_holdings:
        m.account_id = account_id

    if holdings:
        store.save_holdings(account_id, holdings)
    if mf_holdings:
        store.save_mf_holdings(account_id, mf_holdings)

    store.mark_synced(account_id)
    return {
        "account_id": account_id,
        "holdings": len(holdings),
        "mf_holdings": len(mf_holdings),
        "errors": errors,
    }


# ──────────────────── Enrichment ────────────────────

def _enrich_holdings(holdings: list[Holding]) -> list[Holding]:
    """Add live prices from yfinance to holdings."""
    if not holdings:
        return holdings

    # Collect unique symbols → yfinance tickers
    symbols = list({h.symbol for h in holdings if h.symbol})
    nse_tickers = {s: f"{s}.NS" for s in symbols}

    # Batch fetch
    price_map: dict[str, dict] = {}
    try:
        tickers = yf.Tickers(" ".join(nse_tickers.values()))
        for sym, yf_sym in nse_tickers.items():
            try:
                info = tickers.tickers[yf_sym].fast_info
                price_map[sym] = {
                    "price": float(info.get("lastPrice", 0) or info.get("regularMarketPrice", 0) or 0),
                    "prev_close": float(info.get("previousClose", 0) or 0),
                }
            except Exception:
                pass
    except Exception as e:
        logger.warning("Batch price fetch failed: %s", e)

    # Enrich each holding
    for h in holdings:
        live = price_map.get(h.symbol, {})
        if live.get("price"):
            h.current_price = live["price"]
        if h.current_price and h.quantity:
            h.current_value = h.current_price * h.quantity
            h.invested_value = h.avg_price * h.quantity
            h.pnl = h.current_value - h.invested_value
            h.pnl_pct = (h.pnl / h.invested_value * 100) if h.invested_value else 0.0
        prev = live.get("prev_close", 0)
        if prev and h.current_price:
            h.day_change = h.current_price - prev
            h.day_change_pct = (h.day_change / prev) * 100

    return holdings


# ──────────────────── Summary ────────────────────

def get_portfolio_summary(account_id: Optional[str] = None,
                          enrich: bool = True) -> PortfolioSummary:
    """Build an aggregated portfolio summary with live prices."""
    holdings = store.get_holdings(account_id)
    mf_holdings = store.get_mf_holdings(account_id)
    accounts = store.list_accounts()

    if enrich:
        holdings = _enrich_holdings(holdings)

    total_invested = sum(h.invested_value for h in holdings)
    total_current = sum(h.current_value for h in holdings)
    total_pnl = total_current - total_invested
    day_pnl = sum(h.day_change * h.quantity for h in holdings if h.day_change)

    # MF values
    mf_invested = sum(m.invested_value for m in mf_holdings)
    mf_current = sum(m.current_value for m in mf_holdings)
    total_invested += mf_invested
    total_current += mf_current
    total_pnl += (mf_current - mf_invested)

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        total_current=round(total_current, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round((total_pnl / total_invested * 100) if total_invested else 0, 2),
        day_pnl=round(day_pnl, 2),
        day_pnl_pct=round((day_pnl / total_current * 100) if total_current else 0, 2),
        num_stocks=len(holdings),
        num_mf=len(mf_holdings),
        num_accounts=len(accounts),
        holdings=holdings,
        mf_holdings=mf_holdings,
    )


def get_holdings_enriched(account_id: Optional[str] = None) -> list[Holding]:
    """Return enriched holdings list (live prices + P&L)."""
    holdings = store.get_holdings(account_id)
    return _enrich_holdings(holdings)
