"""Static HTML dashboard rendered from griddy/stats.py's report.

No server and no new dependency: `python -m griddy.dashboard` writes
docs/index.html, a self-contained page (data and charts inline, vanilla JS)
that opens directly from disk or can be served by GitHub Pages from docs/.
"""

from __future__ import annotations

import json
import os

from .stats import build_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "live.jsonl")
OUTPUT_PATH = os.path.join(ROOT, "docs", "index.html")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "dashboard_template.html")


def render(report: dict) -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    return template.replace("__GRIDDY_REPORT__", payload)


def build(output_path: str = OUTPUT_PATH, data_path: str = DATA_PATH) -> str:
    html = render(build_report(data_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return output_path


if __name__ == "__main__":
    written_to = build()
    print(f"[griddy] dashboard written to {written_to}")
