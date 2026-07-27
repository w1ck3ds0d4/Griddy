"""Fetchers for Enemalta's public outage feeds.

Three sources, all public, no auth:
  - GetOutages: live (unplanned) outages, JSON.
  - GetPlannedOutages: planned works, JSON with case IDs and feeder geometry.
  - Planned-Outages6.php: the public HTML table (has locality names, which
    the planned JSON lacks), used as a cross-check source.

Every fetcher returns (payload_bytes, parsed_or_none). We always keep the
raw bytes so the archive can store a content hash of exactly what the
public endpoint served, even when parsing fails.
"""

from __future__ import annotations

import json

import requests

USER_AGENT = "Griddy/0.1 (open outage archive; github.com/w1ck3ds0d4/Griddy)"
TIMEOUT = 30

LIVE_URL = "https://mobilegis.enemalta.com.mt/mobilegis_rest/api/currentoutages/GetOutages"
PLANNED_URL = "https://mobilegis.enemalta.com.mt/mobilegis_Rest/api/currentoutages/GetPlannedOutages"
PLANNED_PAGE_URL = "https://enemalta.com.mt/Planned-Outages6.php"


def _get(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content


def fetch_live() -> tuple[bytes, list | None]:
    raw = _get(LIVE_URL)
    try:
        return raw, json.loads(raw)
    except ValueError:
        return raw, None


def fetch_planned() -> tuple[bytes, list | None]:
    raw = _get(PLANNED_URL)
    try:
        return raw, json.loads(raw)
    except ValueError:
        return raw, None


def fetch_planned_page() -> tuple[bytes, str | None]:
    raw = _get(PLANNED_PAGE_URL)
    try:
        return raw, raw.decode("utf-8", errors="replace")
    except Exception:
        return raw, None
