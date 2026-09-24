# Changelog

All notable changes to Griddy are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/). There is no tagged release
yet; entries below are grouped by notable merged work. Routine scrape
commits (`(data) scrape <timestamp>`) are not listed.

## [Unreleased]
### Added
- `griddy-scraper-healthcheck` skill for verifying chain integrity and cron
  liveness (#7)
- Standard actions: CI, security scan, monthly Dependabot (#5)

### Fixed
- Loop scrape cycles in-job so archive granularity does not depend on
  high-frequency cron
- Offset cron minutes and re-register the schedule

## [Slice 1]
### Added
- Chained public archive of Malta outage feeds: scraper, hash chain,
  live/planned/planned-page/heartbeat data files, and the static dashboard
