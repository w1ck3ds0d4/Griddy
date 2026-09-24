# Security

Griddy is a scheduled scraper and static-archive generator. It has no server,
no user accounts, and no inbound attack surface of its own; its security
posture is mostly about the integrity of the archive and what the scraper
touches.

## Current posture

### What the code touches

- **Network**: outbound only, to Enemalta's public outage feeds (live API,
  planned API, planned HTML page). No inbound listener.
- **Secrets**: none. The scraper runs unauthenticated against public feeds
  and needs no API key or credential.
- **Files**: reads and appends to `data/*.jsonl` and `state/current.json`,
  and writes the generated `docs/index.html`. Nothing outside the repo
  checkout is touched.
- **Permissions**: `scrape.yml` and `ci.yml` request only what they need
  (`contents: read`, plus `contents: write` in the scrape workflow to commit
  new archive rows). No secrets, no external services beyond the two
  Enemalta feeds.

### Data-integrity model

Every line in `data/*.jsonl` carries `seq`, `prev` (hash of the previous
line), and `hash` (hash of the line itself), so the whole archive re-verifies
from genesis with `python -m griddy.verify`. Tampering with, reordering, or
deleting a line breaks the chain at exactly that point. Git history is a
second, independent witness to when each commit landed; the timestamps that
matter for a claim are the ones inside the JSONL records themselves.

Personal data from the upstream feeds (`InCharge`, `AffectedAccountNos`) is
stripped in `griddy/normalize.py` before anything reaches the archive.

### Known weaknesses

- Records are hash-chained but not yet signed, so integrity is provable but
  not yet attributable to a specific signing key; ProofLog signing
  integration is the next roadmap item that closes this.
- The archive trusts the host clock for ordering between scrape cycles;
  there is no external trusted timestamp.
- The scraper depends entirely on Enemalta's public feeds staying reachable
  and truthful; a feed outage or falsified upstream data would show up as a
  gap or an incorrect record, not a chain-verification failure.

## Reporting a problem

If you find a data-integrity issue (a broken chain, an incorrect archived
outage, or a way to make the scraper record something false), please use
GitHub's private vulnerability reporting on this repository (Security tab,
"Report a vulnerability") rather than a public issue. Include the affected
record's sequence number or timestamp and what you expected to see instead.

## Disclosure policy

Coordinated disclosure. Once a fix lands, the issue is noted in the
changelog.
