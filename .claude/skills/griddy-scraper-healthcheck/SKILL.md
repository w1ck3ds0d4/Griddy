---
name: griddy-scraper-healthcheck
description: Verify Griddy's hash-chained archive is intact and its GitHub Actions scraper is still running on schedule. Use when asked to check Griddy, check the archive, check the scraper, or investigate a gap in the outage data.
---

# Griddy scraper health check

Griddy's whole value is the archive: an append-only, hash-chained record of
Malta's public outage feeds, written every ~10 minutes by a GitHub Actions cron
(`.github/workflows/scrape.yml`). This check verifies the chain hasn't broken
and the cron hasn't silently stopped or started returning empty feeds.

## 1. Read the pieces first

- `.github/workflows/scrape.yml` - runs hourly (`cron: "7 * * * *"`), then loops
  6 cycles internally (`python -m griddy.run` + `python -m griddy.verify` +
  commit + push), ~10 minutes apart, because GitHub throttles a bare
  `*/10` schedule on shared runners.
- `griddy/archive.py` - the chain format: every JSONL line has `seq` (position),
  `prev` (sha256 of the previous line), `hash` (sha256 of this line minus the
  hash field itself). `GENESIS` marks line 1's `prev`.
- `griddy/verify.py` - re-walks every `data/*.jsonl` file and recomputes the
  chain; exit code 0 means every line checks out.
- `data/heartbeats.jsonl` - one record per cycle regardless of whether anything
  changed, with `ts`, `seq`, and a `sources` block giving each of the three
  feeds' byte size, row/case count, and sha256. This is the source for spotting
  a stalled or reshaped feed even when the outage data itself is quiet.

## 2. Verify the chain

```bash
python -m griddy.verify
```

Run this from the repo root with `requests` installed (`pip install requests`
if needed). `OK` for every file in `data/` means the chain is intact; a `FAIL`
line names the file and the seq where it broke, i.e. potential tampering or a
corrupted write, not something to silently patch. Report it, don't rewrite
history to fix it.

## 3. Check the scraper isn't stalled

```bash
tail -1 data/heartbeats.jsonl
```

- Compare the `ts` field to now. The cron fires hourly and runs 6 cycles roughly
  10 minutes apart inside that hour, so a healthy archive has a heartbeat no
  more than about 20-25 minutes old at any time (allowing for the top of an
  hour plus one missed run). Anything older than an hour means the workflow
  itself stopped firing (check the Actions tab / `gh run list` for the `scrape`
  workflow), not just a quiet outage night.
- Compare `sources.<name>.bytes` and `.cases`/`.rows` against a few heartbeats
  back. A source suddenly reporting a very different byte size or a `cases`/
  `rows` count of 0 for several consecutive heartbeats (while the others look
  normal) usually means Enemalta reshaped that endpoint, not that outages
  stopped. Spot this before it silently produces months of gaps.
- A `live.jsonl`/`planned.jsonl`/`planned_page.jsonl` with no new lines for many
  heartbeats in a row, while the corresponding heartbeat sha256 keeps changing,
  is normal (the feed content changed but produced no diffable event). No new
  lines while the sha256 also stays frozen for a long stretch is the signal
  worth flagging: the upstream feed itself may be stuck serving stale data.

## 4. Report

State plainly: chain status (OK/FAIL + file), last heartbeat age, and whether
any of the three sources looks stalled or reshaped. Do not modify `data/` or
`state/` yourself; those are append-only records written by the bot's own git
identity (`griddy-bot`) in CI, never by hand.

## Traps

- Never run `python -m griddy.run` against `main` locally and push the result;
  the bot's cron owns writes to `data/`/`state/`. Local runs for testing are
  fine in a throwaway branch/worktree, just don't commit or push them.
- A single `FAIL` from `verify.py` invalidates every line after it in that file,
  not just the one line named - the whole chain from that point needs
  re-derivation from git history, not a hand-edit.
- `data/live.jsonl` heartbeat bytes can legitimately be tiny (`2` bytes seen in
  practice, i.e. an empty JSON array) when there are currently no live outages;
  that's a healthy quiet reading, not a stalled source.
