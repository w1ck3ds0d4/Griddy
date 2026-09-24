# Architecture

Griddy is a Python scraper and static-site generator with no server
component. A GitHub Actions cron drives it; the archive lives in the repo
itself as append-only JSONL, and the dashboard is a self-contained static
HTML file.

## Tech stack

- Python 3.12
- `requests` for HTTP calls to the two Enemalta feeds
- Standard library `hashlib`/`json` for hashing and the JSONL archive
- No database, no web framework, no build step
- GitHub Actions: `scrape.yml` (the cron), `ci.yml` (pytest), `security.yml`

## Component breakdown

`griddy/`:

- `fetch.py`: HTTP calls to the live outage API, planned outage API, and
  planned outage HTML page.
- `normalize.py`: strips personal fields (`InCharge`, `AffectedAccountNos`),
  replaces feeder geometry with a sha256 digest, produces a normalized case
  record.
- `archive.py`: diffs the normalized snapshot against `state/current.json`,
  appends `appeared`/`updated`/`cleared` events (and a `heartbeat` record
  every cycle) to `data/*.jsonl`, computing each line's `seq`, `prev`, and
  `hash`.
- `verify.py`: replays every line in `data/*.jsonl` from genesis and confirms
  each `hash` matches its content and each `prev` matches the prior line.
- `stats.py`: downtime-by-locality, outages-per-week, and
  compensation-eligibility (outages over 6 hours) computed from
  `data/live.jsonl`.
- `dashboard.py` (+ `dashboard_template.html`): renders `stats.py`'s output
  into the static `docs/index.html`.
- `run.py`: the entry point a scrape cycle calls: fetch, normalize, archive.

## Data flow

1. `scrape.yml` runs `python -m griddy.run` on a cron schedule.
2. `run.py` calls `fetch.py` for all three sources, then `normalize.py` on
   each case.
3. `archive.py` diffs against `state/current.json`, appends any new events
   plus a heartbeat to the relevant `data/*.jsonl` file, and updates
   `state/current.json`.
4. After the scheduled cycles for that run, the workflow commits the changed
   `data/`, `state/`, and regenerated `docs/index.html` files to `main`.
5. Anyone can independently run `python -m griddy.verify` against the
   committed `data/*.jsonl` files to confirm the chain has not been altered.

## What Griddy does not do

- No signing yet (see ROADMAP.md); the chain is tamper-evident but not yet
  attributable to a signing key.
- No server or API; the dashboard is a static file, and the archive is read
  by cloning or downloading the repo.
- No independent time source; ordering relies on the scrape cycle's clock
  and, secondarily, git commit history.
