"""Verify every chained archive file. Anyone can run this after cloning:

    python -m griddy.verify

Exit code 0 means every line of every archive recomputes cleanly.
"""

from __future__ import annotations

import glob
import os
import sys

from .archive import verify_chain

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    paths = sorted(glob.glob(os.path.join(ROOT, "data", "*.jsonl")))
    if not paths:
        print("no archive files yet")
        return 0
    failed = False
    for path in paths:
        ok, message = verify_chain(path)
        print(("OK   " if ok else "FAIL ") + message)
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
