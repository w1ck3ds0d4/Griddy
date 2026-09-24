# How It Works

Griddy watches Enemalta's public outage feeds so the record of an outage
survives after it scrolls off the live map. Every few minutes it asks the
same three public sources anyone can ask, writes down what they said, and
chains that record to everything written before it so nobody, including
Daniel, can quietly edit history afterwards.

## What it does

- Scrapes three public sources on a GitHub Actions cron: the live outage
  API, the planned outage API, and the planned outage HTML page (the only
  one with locality names).
- Strips personal data (employee names, customer account references) before
  anything touches the archive; keeps street and locality names since those
  are the outage's public location.
- Diffs each cycle against the last known state and appends
  `appeared`/`updated`/`cleared` events, plus a `heartbeat` record every
  cycle even when nothing changed (evidence of absence: proof of what the
  feeds did and did not report at that moment).
- Hash-chains every line: each carries `seq`, `prev` (hash of the previous
  line), and `hash` (hash of itself), so the archive re-verifies end to end.
- Regenerates a static dashboard (`docs/index.html`) each cycle: downtime by
  locality, outages per week, and which outages cross Malta's 6-hour
  compensation threshold (EUR 60-110 for households, more for businesses).
- Does not phone home beyond the two Enemalta feeds it exists to record.

## How to use it

### Run a scrape cycle locally

```bash
pip install requests
python -m griddy.run
```

### Verify the archive

```bash
python -m griddy.verify
```

Walks `data/*.jsonl` from the first line and confirms every hash and
`prev` link is intact. A broken chain prints exactly where and why.

### Regenerate the dashboard

```bash
python -m griddy.dashboard
```

Writes `docs/index.html` from the current `data/live.jsonl`. Enable GitHub
Pages on the `docs/` folder to publish it; the scrape workflow keeps it
current automatically.

### Check the outage record for a claim

The dashboard's compensation table lists outages over 6 hours with the
documented household range. This is a starting point for Malta's Claim for
Damages form, not the full official schedule, and not affiliated with
Enemalta.

## What it does not do (yet)

The chain proves nothing was edited after the fact, but it is not yet signed
to a specific key (attribution), and there is no public page yet to paste a
hash and confirm it is in the chain. Both are on the roadmap.
