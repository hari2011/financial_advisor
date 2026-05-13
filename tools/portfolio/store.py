"""SQLite storage layer for portfolio data.

Tables:
  broker_accounts  — linked DMAT / broker accounts
  holdings         — equity holdings per account
  mf_holdings      — mutual fund holdings per account
"""
from __future__ import annotations

import os
import sqlite3
import threading
import logging
from datetime import datetime
from typing import Optional

from tools.portfolio.models import BrokerAccount, Holding, MFHolding

logger = logging.getLogger("financegpt.portfolio.store")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
_DB_PATH = os.path.join(_DB_DIR, "portfolio.db")
_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS broker_accounts (
    id TEXT PRIMARY KEY,
    broker TEXT NOT NULL,
    client_id TEXT DEFAULT '',
    display_name TEXT DEFAULT '',
    api_key TEXT DEFAULT '',
    access_token TEXT DEFAULT '',
    refresh_token TEXT DEFAULT '',
    token_expiry TEXT DEFAULT '',
    last_synced TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    auth_type TEXT DEFAULT 'oauth',
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    isin TEXT DEFAULT '',
    name TEXT DEFAULT '',
    exchange TEXT DEFAULT 'NSE',
    quantity INTEGER DEFAULT 0,
    avg_price REAL DEFAULT 0.0,
    segment TEXT DEFAULT 'EQ',
    FOREIGN KEY (account_id) REFERENCES broker_accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mf_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    scheme_code TEXT DEFAULT '',
    scheme_name TEXT DEFAULT '',
    folio TEXT DEFAULT '',
    units REAL DEFAULT 0.0,
    avg_nav REAL DEFAULT 0.0,
    invested_value REAL DEFAULT 0.0,
    FOREIGN KEY (account_id) REFERENCES broker_accounts(id) ON DELETE CASCADE
);
"""


def _get_conn() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    with _lock:
        conn = _get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()


_init_db()


# ──────────────────── Account CRUD ────────────────────

def save_account(acct: BrokerAccount):
    with _lock:
        conn = _get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO broker_accounts
               (id, broker, client_id, display_name, api_key, access_token,
                refresh_token, token_expiry, last_synced, status, auth_type, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (acct.id, acct.broker, acct.client_id, acct.display_name,
             acct.api_key, acct.access_token, acct.refresh_token,
             acct.token_expiry, acct.last_synced, acct.status,
             acct.auth_type, acct.created_at),
        )
        conn.commit()
        conn.close()


def get_account(account_id: str) -> Optional[BrokerAccount]:
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM broker_accounts WHERE id = ?", (account_id,)
        ).fetchone()
        conn.close()
    if not row:
        return None
    return BrokerAccount(**dict(row))


def list_accounts() -> list[BrokerAccount]:
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM broker_accounts WHERE status != 'deleted' ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
    return [BrokerAccount(**dict(r)) for r in rows]


def delete_account(account_id: str):
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM holdings WHERE account_id = ?", (account_id,))
        conn.execute("DELETE FROM mf_holdings WHERE account_id = ?", (account_id,))
        conn.execute("DELETE FROM broker_accounts WHERE id = ?", (account_id,))
        conn.commit()
        conn.close()


def update_account_token(account_id: str, access_token: str,
                         refresh_token: str = "", expiry: str = ""):
    with _lock:
        conn = _get_conn()
        conn.execute(
            """UPDATE broker_accounts
               SET access_token=?, refresh_token=?, token_expiry=?
               WHERE id=?""",
            (access_token, refresh_token, expiry, account_id),
        )
        conn.commit()
        conn.close()


def mark_synced(account_id: str):
    ts = datetime.utcnow().isoformat()
    with _lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE broker_accounts SET last_synced=? WHERE id=?",
            (ts, account_id),
        )
        conn.commit()
        conn.close()


# ──────────────────── Holdings CRUD ────────────────────

def save_holdings(account_id: str, holdings: list[Holding]):
    """Replace all holdings for an account (full sync)."""
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM holdings WHERE account_id = ?", (account_id,))
        for h in holdings:
            conn.execute(
                """INSERT INTO holdings
                   (account_id, symbol, isin, name, exchange, quantity, avg_price, segment)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (account_id, h.symbol, h.isin, h.name, h.exchange,
                 h.quantity, h.avg_price, h.segment),
            )
        conn.commit()
        conn.close()


def get_holdings(account_id: Optional[str] = None) -> list[Holding]:
    """Get holdings, optionally filtered by account."""
    with _lock:
        conn = _get_conn()
        if account_id:
            rows = conn.execute(
                "SELECT h.*, b.broker FROM holdings h JOIN broker_accounts b ON h.account_id=b.id WHERE h.account_id=?",
                (account_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT h.*, b.broker FROM holdings h JOIN broker_accounts b ON h.account_id=b.id WHERE b.status='active'"
            ).fetchall()
        conn.close()
    result = []
    for r in rows:
        d = dict(r)
        result.append(Holding(
            symbol=d["symbol"], isin=d.get("isin", ""), name=d.get("name", ""),
            exchange=d.get("exchange", "NSE"), quantity=d.get("quantity", 0),
            avg_price=d.get("avg_price", 0.0), segment=d.get("segment", "EQ"),
            broker=d.get("broker", ""), account_id=d.get("account_id", ""),
        ))
    return result


# ──────────────────── MF Holdings CRUD ────────────────────

def save_mf_holdings(account_id: str, holdings: list[MFHolding]):
    """Replace all MF holdings for an account (full sync)."""
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM mf_holdings WHERE account_id = ?", (account_id,))
        for m in holdings:
            conn.execute(
                """INSERT INTO mf_holdings
                   (account_id, scheme_code, scheme_name, folio, units, avg_nav, invested_value)
                   VALUES (?,?,?,?,?,?,?)""",
                (account_id, m.scheme_code, m.scheme_name, m.folio,
                 m.units, m.avg_nav, m.invested_value),
            )
        conn.commit()
        conn.close()


def get_mf_holdings(account_id: Optional[str] = None) -> list[MFHolding]:
    with _lock:
        conn = _get_conn()
        if account_id:
            rows = conn.execute(
                "SELECT m.*, b.broker FROM mf_holdings m JOIN broker_accounts b ON m.account_id=b.id WHERE m.account_id=?",
                (account_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.*, b.broker FROM mf_holdings m JOIN broker_accounts b ON m.account_id=b.id WHERE b.status='active'"
            ).fetchall()
        conn.close()
    result = []
    for r in rows:
        d = dict(r)
        result.append(MFHolding(
            scheme_code=d.get("scheme_code", ""), scheme_name=d.get("scheme_name", ""),
            folio=d.get("folio", ""), units=d.get("units", 0.0),
            avg_nav=d.get("avg_nav", 0.0), invested_value=d.get("invested_value", 0.0),
            broker=d.get("broker", ""), account_id=d.get("account_id", ""),
        ))
    return result
