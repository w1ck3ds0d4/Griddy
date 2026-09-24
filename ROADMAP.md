# Roadmap

**Status:** continue. **Last reviewed:** 2026-09-24.

Griddy is the Wicked Labs public testbed: a running, hash-chained archive of
Malta's power outages, scraped on a cron every cycle. It sits under the
Wicked Labs 4 to 6 hours a week cap, so this roadmap keeps **Now** to a small,
fixed slice rather than a full feature backlog; "done" for now is the archive
staying correct and slowly gaining the pieces (signing, a public verify page)
that turn it into usable compensation-claim evidence.

> How this file is used: Claude Project threads build the first unticked item
> under **Now**, one item per branch and pull request, and tick it in that
> same PR as `- [x] ... (#PR)`. Daniel owns the order and the lists; threads
> never add to Now, Next or Later themselves, they propose under **Ideas**.

## Now
- [ ] **Add SECURITY.md**: the hash-chain integrity model and how to report a
  data-quality issue. Done when: SECURITY.md exists at root.
- [ ] **Add ARCHITECTURE.md and HOW_IT_WORKS.md**: the scrape, diff, hash-chain
  pipeline and a plain-words walkthrough. Done when: both files exist at root.
- [ ] **ProofLog signing integration**: sign each archive batch so it is
  attributable as well as tamper-evident, per the README's existing roadmap
  note. Done when: `griddy/archive.py` signs new batches and `verify.py`
  checks the signature.

## Next
- [ ] **Verify page**: paste a record hash, confirm it is in the chain,
  served from the static dashboard. Done when: `docs/index.html` (or a linked
  page) accepts a hash and reports found/not-found.
- [ ] **Compensation certificate generator**: locality and date range in, a
  verifiable outage certificate out, formatted for Enemalta's Claim for
  Damages application. Done when: a script or dashboard action produces a
  certificate document from `data/live.jsonl`.

## Later
- Chained-archive verify view inside the dashboard (beyond the CLI `verify.py`)
- A CONTRIBUTING.md, once a house template exists
- Broader compensation-schedule coverage beyond the documented EUR 60-110 band

## Ideas
(empty to start; threads add proposals here)

## Done
- [x] Slice 1: scraper plus hash-chained archive across live, planned, and
  planned-page sources, working in production
- [x] Privacy stripping of `InCharge` and `AffectedAccountNos` before archival
- [x] Static dashboard (`docs/index.html`): downtime by locality, outages per
  week, compensation-eligible outages
- [x] `griddy-scraper-healthcheck` skill for verifying chain integrity and
  cron liveness (#7)
