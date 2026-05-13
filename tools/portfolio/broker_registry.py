"""Broker adapter registry.

Auto-discovers all adapters in the ``brokers/`` sub-package and exposes them
via :func:`get_broker` and :func:`list_brokers`.
"""
from __future__ import annotations

import importlib
import logging
import os

from tools.portfolio.base_broker import BaseBroker

logger = logging.getLogger("financegpt.portfolio.registry")

_BROKER_MAP: dict[str, type[BaseBroker]] = {}

# Broker module names (one .py per broker under brokers/)
_BROKER_MODULES = [
    "zerodha", "upstox", "angelone", "groww", "fivepaisa",
    "icici_direct", "dhan", "kotak", "motilal", "hdfc_sec", "paytm_money",
]


def _discover():
    """Import every broker module and collect BaseBroker subclasses."""
    if _BROKER_MAP:
        return
    for mod_name in _BROKER_MODULES:
        try:
            mod = importlib.import_module(f"tools.portfolio.brokers.{mod_name}")
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if (isinstance(obj, type) and issubclass(obj, BaseBroker)
                        and obj is not BaseBroker and obj.BROKER_ID):
                    _BROKER_MAP[obj.BROKER_ID] = obj
        except Exception as e:
            logger.debug(f"Skipped broker module {mod_name}: {e}")


def get_broker_class(broker_id: str) -> type[BaseBroker] | None:
    """Return the adapter *class* for a given broker ID."""
    _discover()
    return _BROKER_MAP.get(broker_id)


def list_brokers() -> list[dict]:
    """Return metadata for all registered broker adapters."""
    _discover()
    return [cls.info() for cls in _BROKER_MAP.values()]
