"""Normalize raw feed payloads into small, archive-friendly case records.

Two rules drive everything here:

1. Privacy by design. The upstream feeds can contain personal data that has
   no archival value for outage evidence: employee names (InCharge) and
   customer account numbers (AffectedAccountNos). Both are dropped before
   anything is written to the public archive.

2. Keep the archive small but provable. Feeder geometry (WKT linestrings)
   can be megabytes per case. We do not store it; we store a sha256 of the
   canonical geometry string instead, so anyone who later obtains the same
   geometry can prove it matches what we saw, without us hoarding megabytes
   in git history.
"""

from __future__ import annotations

import ast
import hashlib
import html.parser
import json
import re

PRIVACY_STRIPPED_FIELDS = ("InCharge", "AffectedAccountNos")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj) -> str:
    """Stable serialization used for hashing and for chain entries."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _geometry_digest(value) -> str:
    """Hash any geometry-bearing structure into one short digest."""
    return sha256_hex(canonical_json(value).encode("utf-8"))


def _parse_embedded_list(value):
    """Transformers/StreetList arrive as Python-repr-ish strings, e.g.
    "[{'TransformerId': '866', ...}]". Parse defensively; on failure return
    the raw string so nothing is silently lost."""
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        try:
            return json.loads(value)
        except ValueError:
            return value


def normalize_live_case(case: dict) -> dict:
    """Live outage case from GetOutages. Field names observed in the map
    client: X, Y, PolygonGeometry, CentroidGeometry, OutageType, plus
    whatever else the API adds. Unknown fields are kept (minus privacy and
    geometry), so schema drift is captured rather than dropped."""
    out = {}
    geometry = {}
    for key, value in case.items():
        if key in PRIVACY_STRIPPED_FIELDS:
            continue
        if "geometry" in key.lower():
            geometry[key] = value
            continue
        out[key] = value
    if geometry:
        out["geometry_sha256"] = _geometry_digest(geometry)
    return out


def normalize_planned_case(case: dict) -> dict:
    """Planned case from GetPlannedOutages: CaseID, StartDate, EndDate,
    Transformers (with heavy WKT), StreetList, InCharge, AffectedAccountNos."""
    out = {
        "CaseID": str(case.get("CaseID", "")),
        "StartDate": case.get("StartDate"),
        "EndDate": case.get("EndDate"),
    }
    streets = _parse_embedded_list(case.get("StreetList"))
    if streets:
        out["streets"] = streets

    transformers = _parse_embedded_list(case.get("Transformers"))
    if isinstance(transformers, list):
        slim = []
        for t in transformers:
            if not isinstance(t, dict):
                continue
            entry = {"TransformerId": t.get("TransformerId")}
            feeders = t.get("FeederList")
            if isinstance(feeders, list):
                entry["feeders"] = [f.get("FeederNo") for f in feeders if isinstance(f, dict)]
            slim.append(entry)
        if slim:
            out["transformers"] = slim
    if transformers:
        out["transformers_sha256"] = _geometry_digest(transformers)
    return out


class _PlannedPageParser(html.parser.HTMLParser):
    """Parses the Planned-Outages6.php table.

    Structure observed: visible rows are City | From | To | toggle-icon,
    each followed by a hidden detail row (id="rowN") whose first cell holds
    the affected street list."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_cell = False
        self._cells = []
        self._current = []
        self._hidden_row = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self._cells = []
            self._hidden_row = str(attrs.get("id", "")).startswith("row")
        elif tag == "td":
            self._in_cell = True
            self._current = []

    def handle_endtag(self, tag):
        if tag == "td" and self._in_cell:
            self._in_cell = False
            self._cells.append(" ".join("".join(self._current).split()))
        elif tag == "tr" and self._cells:
            self.rows.append((self._hidden_row, self._cells))
            self._cells = []

    def handle_data(self, data):
        if self._in_cell:
            self._current.append(data)


_BOILERPLATE = re.compile(
    r"^Due to scheduled maintenance works.*following areas\s*:\s*,?\s*", re.IGNORECASE
)


def parse_planned_page(page_html: str) -> list[dict]:
    """Return [{city, from, to, streets}] from the public HTML table."""
    parser = _PlannedPageParser()
    parser.feed(page_html)
    results = []
    for hidden, cells in parser.rows:
        if hidden:
            if results and cells:
                detail = _BOILERPLATE.sub("", cells[0])
                streets = [s.strip() for s in detail.split(",") if s.strip()]
                results[-1]["streets"] = streets
            continue
        if len(cells) >= 3:
            results.append(
                {
                    "city": cells[0].strip(),
                    "from": cells[1].strip(),
                    "to": cells[2].strip(),
                    "streets": [],
                }
            )
    return results


def planned_page_key(row: dict) -> str:
    """Identity for an HTML planned row (the page has no case ids).

    Streets are part of the identity: two distinct works can share the same
    city and time window (observed twice for Paola on 2026-07-29), so
    city+times alone would collide and silently drop one of them."""
    basis = canonical_json(
        {"city": row["city"], "from": row["from"], "to": row["to"], "streets": row.get("streets", [])}
    )
    return sha256_hex(basis.encode("utf-8"))[:16]
