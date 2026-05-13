"""CDSL / NSDL Consolidated Account Statement (CAS) PDF parser.

CAS is the universal demat statement — covers ALL brokers under one PAN.
Users download it from:
  • CDSL: https://www.cdslindia.com/Publications/CASRequest.html
  • NSDL: https://nsdlcas.nsdl.com/

The PDF has a predictable structure:
  - Header: PAN, name, date range
  - Section: EQUITY (ISIN, company, quantity, free/locked balance)
  - Section: MUTUAL FUNDS (folio, scheme, units, NAV, value)
"""
from __future__ import annotations

import re
import logging
from typing import Optional

from tools.portfolio.models import Holding, MFHolding

logger = logging.getLogger("financegpt.portfolio.cas_parser")

# ── Regex patterns for CAS PDF content ──
_PAN_RE = re.compile(r"\bPAN\s*:\s*([A-Z]{5}\d{4}[A-Z])\b", re.I)
_ISIN_RE = re.compile(r"\b(INE[A-Z0-9]{7}\d{3})\b")
_FOLIO_RE = re.compile(r"Folio\s*(?:No\.?|Number)?\s*:?\s*(\S+)", re.I)
_UNITS_RE = re.compile(r"([\d,]+\.\d+)\s*(?:units?)?", re.I)

# Equity row: ISIN  CompanyName  Qty  FreeBalance
_EQ_ROW_RE = re.compile(
    r"(INE[A-Z0-9]{7}\d{3})\s+"
    r"(.+?)\s+"
    r"(\d[\d,]*)\s+"          # total quantity
    r"(\d[\d,]*)"             # free balance
)

# MF row patterns vary — we look for scheme name + units + NAV + value
_MF_VALUE_RE = re.compile(
    r"([\d,]+\.\d{2,4})\s+"   # units
    r"([\d,]+\.\d{2,4})\s+"   # NAV
    r"([\d,]+\.\d{2})"        # value
)


def _clean_num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_cas_pdf(file_path: str, password: str = "") -> dict:
    """Parse a CAS PDF and return holdings.

    Args:
        file_path: Path to the CAS PDF file.
        password: PDF password (usually PAN in lowercase + DOB as ddmmyyyy,
                  or PAN + DOB as DDMONYYYY).

    Returns:
        {
            "pan": str,
            "holdings": [Holding, ...],
            "mf_holdings": [MFHolding, ...],
            "errors": [str, ...],
        }
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {"pan": "", "holdings": [], "mf_holdings": [],
                "errors": ["PyMuPDF not installed"]}

    errors: list[str] = []
    holdings: list[Holding] = []
    mf_holdings: list[MFHolding] = []
    pan = ""

    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    return {"pan": "", "holdings": [], "mf_holdings": [],
                            "errors": ["Incorrect PDF password"]}
            else:
                return {"pan": "", "holdings": [], "mf_holdings": [],
                        "errors": ["PDF is password-protected. "
                                   "Password is usually: PAN (lowercase) + DOB (ddmmyyyy)"]}

        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        return {"pan": "", "holdings": [], "mf_holdings": [],
                "errors": [f"Failed to read PDF: {e}"]}

    # Extract PAN
    pan_match = _PAN_RE.search(full_text)
    if pan_match:
        pan = pan_match.group(1).upper()

    # Split text into lines for parsing
    lines = full_text.split("\n")

    # Detect sections
    in_equity = False
    in_mf = False
    current_section = ""

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        upper = line_stripped.upper()

        # Section detection
        if any(kw in upper for kw in ["EQUITY", "DEMAT HOLDING", "STOCK HOLDING",
                                        "SECURITIES HELD"]):
            in_equity = True
            in_mf = False
            current_section = "equity"
            continue
        if any(kw in upper for kw in ["MUTUAL FUND", "MF HOLDING", "UNIT HOLDING",
                                       "SCHEME NAME"]):
            in_equity = False
            in_mf = True
            current_section = "mf"
            continue
        if any(kw in upper for kw in ["TOTAL", "GRAND TOTAL", "SUMMARY",
                                       "DISCLAIMER", "NOTE:"]):
            in_equity = False
            in_mf = False
            continue

        # Parse equity rows
        if in_equity:
            eq_match = _EQ_ROW_RE.search(line_stripped)
            if eq_match:
                isin = eq_match.group(1)
                name = eq_match.group(2).strip()
                qty = int(_clean_num(eq_match.group(3)))
                if qty > 0:
                    holdings.append(Holding(
                        symbol=_isin_to_symbol(isin, name),
                        isin=isin,
                        name=name,
                        quantity=qty,
                        broker="cas_import",
                    ))
                continue

            # Fallback: just ISIN on a line
            isin_match = _ISIN_RE.search(line_stripped)
            if isin_match:
                isin = isin_match.group(1)
                # Look at next lines for name + quantity
                name_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                qty_line = lines[i + 2].strip() if i + 2 < len(lines) else ""
                name = name_line if name_line and not name_line[0].isdigit() else ""
                qty = _extract_first_int(qty_line) or _extract_first_int(name_line)
                if qty and qty > 0:
                    holdings.append(Holding(
                        symbol=_isin_to_symbol(isin, name),
                        isin=isin,
                        name=name,
                        quantity=qty,
                        broker="cas_import",
                    ))

        # Parse mutual fund rows
        if in_mf:
            val_match = _MF_VALUE_RE.search(line_stripped)
            if val_match:
                units = _clean_num(val_match.group(1))
                nav = _clean_num(val_match.group(2))
                value = _clean_num(val_match.group(3))
                # Scheme name from previous non-numeric line
                scheme_name = ""
                for j in range(i - 1, max(i - 5, -1), -1):
                    prev = lines[j].strip()
                    if prev and not prev[0].isdigit() and len(prev) > 5:
                        scheme_name = prev
                        break
                # Folio from nearby lines
                folio = ""
                context = " ".join(lines[max(0, i - 3):i + 1])
                folio_match = _FOLIO_RE.search(context)
                if folio_match:
                    folio = folio_match.group(1)

                if units > 0:
                    mf_holdings.append(MFHolding(
                        scheme_name=scheme_name,
                        folio=folio,
                        units=units,
                        current_nav=nav,
                        current_value=value,
                        invested_value=0.0,  # CAS may not include cost basis
                        broker="cas_import",
                    ))

    if not holdings and not mf_holdings:
        errors.append("No holdings found — the PDF format may not be recognized. "
                       "Try exporting a fresh CAS from CDSL or NSDL.")

    return {
        "pan": pan,
        "holdings": holdings,
        "mf_holdings": mf_holdings,
        "errors": errors,
    }


def _isin_to_symbol(isin: str, name: str = "") -> str:
    """Best-effort ISIN → NSE symbol mapping.

    For a production system, maintain a full ISIN→symbol mapping table.
    Here we extract a reasonable symbol from the company name.
    """
    if not name:
        return isin
    # Take first word, uppercase, remove suffixes
    parts = name.upper().split()
    symbol = parts[0] if parts else isin
    for suffix in ["LIMITED", "LTD", "LTD.", "INDUSTRIES", "INDIA", "CORPORATION"]:
        symbol = symbol.replace(suffix, "")
    return symbol.strip() or isin


def _extract_first_int(text: str) -> int | None:
    """Extract the first integer from a string."""
    m = re.search(r"(\d[\d,]*)", text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None
