"""Append-only, hash-chained JSONL archive.

Each archive file (data/live.jsonl, data/planned.jsonl, ...) is an
append-only event log. Every line carries:

  seq   - 1-based position in this file
  prev  - sha256 of the previous line's full text ("GENESIS" for line 1)
  hash  - sha256 of this line's canonical text computed WITHOUT the hash
          field, so any reader can recompute and verify it

Tampering with any historical line breaks every hash after it, and the
public git history provides an independent second witness of when each
line appeared. Verification lives in griddy/verify.py.
"""

from __future__ import annotations

import os

from .normalize import canonical_json, sha256_hex

GENESIS = "GENESIS"


def _last_line(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    last = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    return last


def append_events(path: str, events: list[dict]) -> int:
    """Append events to a chained JSONL file. Returns how many were written."""
    if not events:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)

    import json

    last = _last_line(path)
    if last is None:
        prev_hash = GENESIS
        seq = 0
    else:
        prev_hash = sha256_hex(last.encode("utf-8"))
        seq = json.loads(last)["seq"]

    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for event in events:
            seq += 1
            record = dict(event)
            record["seq"] = seq
            record["prev"] = prev_hash
            record.pop("hash", None)
            record["hash"] = sha256_hex(canonical_json(record).encode("utf-8"))
            line = canonical_json(record)
            f.write(line + "\n")
            prev_hash = sha256_hex(line.encode("utf-8"))
    return len(events)


def verify_chain(path: str) -> tuple[bool, str]:
    """Recompute the whole chain of one file. Returns (ok, message)."""
    import json

    if not os.path.exists(path):
        return True, f"{path}: empty (nothing to verify)"

    prev_hash = GENESIS
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("prev") != prev_hash:
                return False, f"{path}:{line_no}: prev-hash mismatch"
            claimed = record.pop("hash", None)
            recomputed = sha256_hex(canonical_json(record).encode("utf-8"))
            if claimed != recomputed:
                return False, f"{path}:{line_no}: line hash mismatch"
            record["hash"] = claimed
            if record.get("seq") != count + 1:
                return False, f"{path}:{line_no}: seq gap (expected {count + 1})"
            count += 1
            prev_hash = sha256_hex(line.encode("utf-8"))
    return True, f"{path}: OK ({count} records)"
