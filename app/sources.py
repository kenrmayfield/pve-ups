"""Dispatch between the UPS source types.

The engine polls through this module and never imports a specific source, so adding a
way to read a UPS is: a model in config.py (a member of the ``UpsSource`` union), a
module with ``poll``/``probe``, a branch here, and the matching i18n keys.

Every source produces the same ``UpsState``, which is why the trigger logic, the host
policy, the fail-safe rules and their whole test suite apply unchanged.

Copyright 2026 Florian Finder
"""

from __future__ import annotations

from . import nut, ups
from .config import NutConfig, SnmpConfig, UpsBase
from .ups import ProbeResult, UpsState


async def poll(cfg: UpsBase) -> UpsState:
    """Read one UPS. Never raises — every source guarantees that for the poll loop."""
    if isinstance(cfg, NutConfig):
        return await nut.poll(cfg)
    if isinstance(cfg, SnmpConfig):
        return await ups.poll(cfg)
    # Unknown type: stay unreachable, which is an alarm and never a shutdown.
    return UpsState(error=f"Unsupported UPS source type: {getattr(cfg, 'type', '?')}")


async def probe(cfg: UpsBase) -> ProbeResult:
    """Per-object diagnosis for the manual test button. Never raises."""
    if isinstance(cfg, NutConfig):
        return await nut.probe(cfg)
    if isinstance(cfg, SnmpConfig):
        return await ups.probe(cfg)
    return ProbeResult(summary=f"Unsupported UPS source type: {getattr(cfg, 'type', '?')}")
