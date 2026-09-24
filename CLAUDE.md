# Griddy

An independent, tamper-evident public archive of Malta's power outages.
Scrapes Enemalta's public feeds on a GitHub Actions cron, appends
hash-chained JSONL events, and publishes a static dashboard. The Wicked Labs
public testbed.

## Commands

```bash
pip install requests
python -m griddy.run          # one scrape cycle
python -m griddy.verify       # re-verify the whole hash chain from genesis
python -m griddy.dashboard    # regenerate docs/index.html

pip install pytest
pytest                        # tests/
python -m py_compile griddy/*.py tests/*.py   # the compile check CI runs
```

There is no build step and no lint configured; CI runs the compile check and
pytest.

## Layout

| Path | What it is |
| --- | --- |
| `griddy/` | The library: fetch, normalize, archive (hash chain), verify, stats, dashboard |
| `tests/` | pytest tests for archive, normalize, stats |
| `data/*.jsonl` | The append-only hash-chained archive (live, planned, planned_page, heartbeats) |
| `state/current.json` | The current snapshot of what is visible right now |
| `docs/index.html` | The generated static dashboard (published via GitHub Pages) |
| `.github/workflows/` | `ci.yml` (test), `scrape.yml` (the cron), `security.yml` |

## Conventions

- Commit format: `(type) lowercase summary` - `feat`, `fix`, `chore`, `docs`.
  No trailing period.
- ASCII hyphens only. No em dashes or en dashes anywhere.
- Feature branch per change set, one PR per branch, squash-merge.
- `data/*.jsonl` and `state/current.json` are the append-only archive: never
  hand-edit or force-rewrite a line, and never resolve one as a merge
  conflict. Every write goes through `griddy/archive.py` so the hash chain
  stays valid.
- Personal fields from the upstream feeds (`InCharge`, `AffectedAccountNos`)
  are stripped before anything touches the archive; see the README's
  Privacy section before adding a new upstream field.

## Do not read

- `data/*.jsonl` (large, append-only, not meant to be read whole; query it
  with `griddy/stats.py` or `griddy/verify.py` instead)
- `docs/index.html` (generated, do not hand-edit)
