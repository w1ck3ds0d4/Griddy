"""Downtime statistics and compensation-eligibility estimates, derived from
data/live.jsonl (the archive's unplanned, compensation-relevant outages).

Malta's compensation scheme (see README) pays households EUR 60-110 for a
continuous outage longer than 6 hours; businesses receive more but Enemalta
has not published a fixed figure alongside it. Both numbers are quoted from
the README, not invented here -- if the official schedule turns out to be
tiered rather than flat, only COMPENSATION_THRESHOLD_HOURS and
HOUSEHOLD_COMPENSATION_EUR need to change. Business outages are flagged as
eligible without an amount, since none is published to estimate from.
"""

from __future__ import annotations

import datetime
import json
import os
from collections import defaultdict

COMPENSATION_THRESHOLD_HOURS = 6.0
HOUSEHOLD_COMPENSATION_EUR = (60, 110)


def _parse_ts(ts: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_events(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def group_outages(events: list[dict]) -> list[dict]:
    """Collapse appeared/updated/cleared events into one record per outage.

    A live case's archive key is a content hash (see run.py:_live_key), which
    can change across cycles even though the outage itself is the same. Group
    on OutageId, the field the API itself uses to tie related cases together,
    falling back to the event key for the rare case without one so nothing is
    dropped.
    """
    groups: dict[str, dict] = {}
    order: list[str] = []
    for event in sorted(events, key=lambda e: (e["ts"], e.get("seq", 0))):
        case = event.get("case", {})
        group_id = str(case.get("OutageId") or event["key"])
        g = groups.get(group_id)
        if g is None:
            g = {"localities": set(), "first_seen": event["ts"], "cleared_at": None}
            groups[group_id] = g
            order.append(group_id)
        localities = case.get("Localities")
        if localities:
            g["localities"].update(x.strip() for x in localities.split(",") if x.strip())
        if event["event"] == "cleared":
            g["cleared_at"] = event["ts"]

    outages = []
    for group_id in order:
        g = groups[group_id]
        appeared = _parse_ts(g["first_seen"])
        cleared = _parse_ts(g["cleared_at"]) if g["cleared_at"] else None
        duration_hours = round((cleared - appeared).total_seconds() / 3600, 2) if cleared else None
        outages.append(
            {
                "group_id": group_id,
                "localities": sorted(g["localities"]),
                "appeared": g["first_seen"],
                "cleared": g["cleared_at"],
                "ongoing": cleared is None,
                "duration_hours": duration_hours,
                "compensation_eligible": duration_hours is not None
                and duration_hours >= COMPENSATION_THRESHOLD_HOURS,
            }
        )
    return outages


def locality_stats(outages: list[dict]) -> list[dict]:
    """Per-locality totals for cleared outages (duration needs a cleared event)."""
    per: dict[str, dict] = defaultdict(lambda: {"outages": 0, "downtime_hours": 0.0, "eligible": 0, "longest_hours": 0.0})
    for o in outages:
        if o["duration_hours"] is None:
            continue
        for loc in o["localities"] or ["Unknown"]:
            entry = per[loc]
            entry["outages"] += 1
            entry["downtime_hours"] += o["duration_hours"]
            entry["longest_hours"] = max(entry["longest_hours"], o["duration_hours"])
            if o["compensation_eligible"]:
                entry["eligible"] += 1

    result = [
        {
            "locality": loc,
            "outages": entry["outages"],
            "downtime_hours": round(entry["downtime_hours"], 2),
            "avg_hours": round(entry["downtime_hours"] / entry["outages"], 2),
            "longest_hours": round(entry["longest_hours"], 2),
            "eligible": entry["eligible"],
        }
        for loc, entry in per.items()
    ]
    result.sort(key=lambda r: r["downtime_hours"], reverse=True)
    return result


def weekly_counts(outages: list[dict]) -> list[dict]:
    """Outages per ISO week (by appearance date), for a trend chart."""
    per_week: dict[str, int] = defaultdict(int)
    for o in outages:
        appeared = _parse_ts(o["appeared"])
        week_start = appeared - datetime.timedelta(days=appeared.weekday())
        per_week[week_start.strftime("%Y-%m-%d")] += 1
    return [{"week": week, "outages": count} for week, count in sorted(per_week.items())]


def summary(outages: list[dict]) -> dict:
    cleared = [o for o in outages if o["duration_hours"] is not None]
    eligible = [o for o in cleared if o["compensation_eligible"]]
    total_downtime = sum(o["duration_hours"] for o in cleared)
    return {
        "total_outages": len(outages),
        "ongoing_outages": sum(1 for o in outages if o["ongoing"]),
        "cleared_outages": len(cleared),
        "total_downtime_hours": round(total_downtime, 2),
        "avg_duration_hours": round(total_downtime / len(cleared), 2) if cleared else 0,
        "compensation_eligible_outages": len(eligible),
        "compensation_threshold_hours": COMPENSATION_THRESHOLD_HOURS,
        "household_compensation_eur": list(HOUSEHOLD_COMPENSATION_EUR),
    }


def build_report(live_path: str) -> dict:
    outages = group_outages(load_events(live_path))
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "summary": summary(outages),
        "by_locality": locality_stats(outages),
        "weekly": weekly_counts(outages),
        "outages": sorted(outages, key=lambda o: o["appeared"], reverse=True),
    }
