"""Data models for portfolio / DMAT integration."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Holding:
    """A single equity / stock holding."""
    symbol: str
    isin: str = ""
    name: str = ""
    exchange: str = "NSE"
    quantity: int = 0
    avg_price: float = 0.0
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    day_change: float = 0.0
    day_change_pct: float = 0.0
    invested_value: float = 0.0
    current_value: float = 0.0
    segment: str = "EQ"
    broker: str = ""
    account_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MFHolding:
    """A single mutual fund holding."""
    scheme_code: str = ""
    scheme_name: str = ""
    folio: str = ""
    units: float = 0.0
    avg_nav: float = 0.0
    current_nav: float = 0.0
    invested_value: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    broker: str = ""
    account_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BrokerAccount:
    """A linked broker / DMAT account."""
    id: str
    broker: str
    client_id: str = ""
    display_name: str = ""
    api_key: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expiry: str = ""
    last_synced: str = ""
    status: str = "active"
    auth_type: str = "oauth"   # oauth | api_key | totp | manual
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        # Never expose tokens in API responses
        d.pop("access_token", None)
        d.pop("refresh_token", None)
        d.pop("api_key", None)
        return d


@dataclass
class PortfolioSummary:
    """Aggregated portfolio overview."""
    total_invested: float = 0.0
    total_current: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    day_pnl: float = 0.0
    day_pnl_pct: float = 0.0
    num_stocks: int = 0
    num_mf: int = 0
    num_accounts: int = 0
    holdings: list[Holding] = field(default_factory=list)
    mf_holdings: list[MFHolding] = field(default_factory=list)
    sector_allocation: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["holdings"] = [h.to_dict() for h in self.holdings]
        d["mf_holdings"] = [m.to_dict() for m in self.mf_holdings]
        return d
