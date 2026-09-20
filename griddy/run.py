"""One scrape cycle: fetch all sources, diff against the last-known state,
append events to the chained archive, refresh state/current.json.

Event kinds written to the archive:
  appeared  - a case is visible now and was not before
  updated   - a case is still visible but its content changed
  cleared   - a case was visible last cycle and is gone now (for live
              outages this is the moment the lights came back, which is
              what a compensation claim needs)
  heartbeat - written EVERY cycle to data/heartbeats.jsonl with content
              hashes of each raw payload; this is the evidence of absence
              ("no outage was published for my street at 14:20")

Run: python -m griddy.run
"""

from __future__ import annotations

import datetime
import json
import os
import sys

from . import fetch
from .archive import append_events
from .normalize import (
    canonical_json,
    normalize_live_case,
    normalize_planned_case,
    parse_planned_page,
    planned_page_key,
    sha256_hex,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
STATE_PATH = os.path.join(ROOT, "state", "current.json")


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"live": {}, "planned": {}, "planned_page": {}}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def _diff(now_map: dict, before_map: dict, ts: str, source: str) -> list[dict]:
    """Compare {key: case} maps and emit appeared/updated/cleared events."""
    events = []
    for key, case in sorted(now_map.items()):
        if key not in before_map:
            events.append({"ts": ts, "source": source, "event": "appeared", "key": key, "case": case})
        elif canonical_json(case) != canonical_json(before_map[key]):
            events.append({"ts": ts, "source": source, "event": "updated", "key": key, "case": case})
    for key, case in sorted(before_map.items()):
        if key not in now_map:
            events.append({"ts": ts, "source": source, "event": "cleared", "key": key, "case": case})
    return events


def _live_key(case: dict) -> str:
    """Live cases carry no stable id we can rely on, so identity is the
    content hash of the normalized case."""
    return sha256_hex(canonical_json(case).encode("utf-8"))[:16]


def run_cycle() -> int:
    ts = _now_utc()
    state = _load_state()
    heartbeat = {"ts": ts, "event": "heartbeat", "sources": {}}
    total_written = 0
    failures = []

    # --- live (unplanned) outages ---
    try:
        raw, parsed = fetch.fetch_live()
        heartbeat["sources"]["live"] = {
            "sha256": sha256_hex(raw),
            "bytes": len(raw),
            "cases": len(parsed) if isinstance(parsed, list) else None,
        }
        if isinstance(parsed, list):
            now_map = {}
            for case in parsed:
                norm = normalize_live_case(case)
                now_map[_live_key(norm)] = norm
            events = _diff(now_map, state.get("live", {}), ts, "live")
            total_written += append_events(os.path.join(DATA_DIR, "live.jsonl"), events)
            state["live"] = now_map
    except Exception as exc:  # network errors must never kill the cycle
        failures.append(f"live: {exc}")
        heartbeat["sources"]["live"] = {"error": str(exc)}

    # --- planned outages (JSON API) ---
    try:
        raw, parsed = fetch.fetch_planned()
        heartbeat["sources"]["planned"] = {
            "sha256": sha256_hex(raw),
            "bytes": len(raw),
            "cases": len(parsed) if isinstance(parsed, list) else None,
        }
        if isinstance(parsed, list):
            now_map = {}
            for case in parsed:
                norm = normalize_planned_case(case)
                key = norm.get("CaseID") or _live_key(norm)
                now_map[key] = norm
            events = _diff(now_map, state.get("planned", {}), ts, "planned")
            total_written += append_events(os.path.join(DATA_DIR, "planned.jsonl"), events)
            state["planned"] = now_map
    except Exception as exc:
        failures.append(f"planned: {exc}")
        heartbeat["sources"]["planned"] = {"error": str(exc)}

    # --- planned outages (public HTML page, has locality names) ---
    try:
        raw, text = fetch.fetch_planned_page()
        heartbeat["sources"]["planned_page"] = {"sha256": sha256_hex(raw), "bytes": len(raw)}
        if text:
            rows = parse_planned_page(text)
            heartbeat["sources"]["planned_page"]["rows"] = len(rows)
            now_map = {planned_page_key(r): r for r in rows}
            events = _diff(now_map, state.get("planned_page", {}), ts, "planned_page")
            total_written += append_events(os.path.join(DATA_DIR, "planned_page.jsonl"), events)
            state["planned_page"] = now_map
    except Exception as exc:
        failures.append(f"planned_page: {exc}")
        heartbeat["sources"]["planned_page"] = {"error": str(exc)}

    append_events(os.path.join(DATA_DIR, "heartbeats.jsonl"), [heartbeat])
    _save_state(state)

    print(f"[griddy] {ts} events={total_written} failures={failures or 'none'}")
    # Partial failure is fine (we archived what we could); total failure is not.
    return 1 if len(failures) == 3 else 0


if __name__ == "__main__":
    sys.exit(run_cycle())
