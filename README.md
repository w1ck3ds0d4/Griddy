# Griddy

An independent, tamper-evident public archive of Malta's power outages.

Enemalta's live outage map shows only the present moment, and during the July 2026 grid crisis it visibly failed while whole localities sat in the dark. Once an outage scrolls off the map, the public record of it is gone. Griddy scrapes the public feeds every few minutes and writes what they said into an append-only, hash-chained archive, so the record survives and anyone can verify nobody edited it afterwards.

This matters because Malta's compensation scheme pays households EUR 60-110 (and businesses considerably more) for outages longer than 6 hours, and the claim form asks for documentary evidence. The archive is that evidence, held by the public instead of only by the utility.

## How it works

Every cycle (GitHub Actions cron, roughly every 10 minutes):

1. Fetch three public sources: the live outage API, the planned outage API, and the planned outage HTML page (the only source carrying locality names).
2. Normalize each case: strip personal data, replace megabytes of feeder geometry with a sha256 digest.
3. Diff against the last-known state and append `appeared` / `updated` / `cleared` events to `data/*.jsonl`.
4. Write a `heartbeat` record with the content hash of every raw payload, even when nothing changed. This is evidence of absence: proof of what the public feeds did and did not report at that moment.
5. Commit once per hourly run (after all six cycles). The git history is a second, independent witness for when every record appeared; the per-cycle timestamps that matter for that are inside `data/*.jsonl` itself, not the commit boundaries.

Every JSONL line carries `seq`, `prev` (hash of the previous line) and `hash` (hash of the line itself), so the whole archive re-verifies from genesis:

```bash
python -m griddy.verify
```

## Data model

| File | Contents |
|---|---|
| `data/live.jsonl` | unplanned outage events (the compensation-relevant ones) |
| `data/planned.jsonl` | planned works from the JSON API (case IDs, transformers, feeders) |
| `data/planned_page.jsonl` | planned works from the public HTML page (localities, streets) |
| `data/heartbeats.jsonl` | one record per cycle: source content hashes, sizes, counts |
| `state/current.json` | the current snapshot (what is visible right now) |

An outage's `cleared` event marks the moment it left the public feed, which combined with its `appeared` event gives a defensible duration estimate.

## Privacy

The upstream feeds can include employee names (`InCharge`) and customer account references (`AffectedAccountNos`). Neither has archival value for outage evidence, so both are stripped before anything touches the archive. Street and locality names are kept: they are the outage's public location, published by the utility itself.

## Run it locally

```bash
pip install requests
python -m griddy.run
python -m griddy.verify
```

Tests:

```bash
pip install pytest
pytest
```

## Dashboard

```bash
python -m griddy.dashboard
```

Writes a self-contained `docs/index.html` (no server, no build step, no new
dependency) from the current `data/live.jsonl`: downtime by locality, outages
per week, and a table of outages that ran longer than Malta's compensation
threshold (6 hours), with the documented household range (EUR 60-110). The
scrape workflow regenerates it every cycle, so `docs/` always reflects the
latest archive; enable GitHub Pages on the `docs/` folder to publish it.

The compensation figures are what the README above documents, not Enemalta's
full official schedule -- treat the eligibility flag as a starting point for
a claim, not the final amount.

## Roadmap

- Signing: sign each batch so the archive is attributable as well as tamper-evident (ProofLog integration).
- Tracker UI: live and historical view of the archive. Downtime stats and compensation-eligibility are done (see Dashboard); a chained-archive verify view is still open.
- Certificates: locality + date in, a verifiable outage certificate out, formatted for Enemalta's Claim for Damages application.
- Verify page: paste a record hash, confirm it is in the chain.

## Status

Slice 1 (scraper + chained archive): working. See the roadmap for what comes next.

Not affiliated with Enemalta plc. The archive records what Enemalta's own public feeds said; it adds no claims of its own.

## License

This project is licensed under:

- [MIT](LICENSE) - free for any use. See the license for details.
