#!/usr/bin/env bash
set -euo pipefail
git fetch origin main
git checkout main
git reset --hard origin/main
git checkout --orphan squash-tmp
git add -A
git commit -m "Griddy: tamper-evident archive of Malta's power outages"
git branch -D main
git branch -m main
git push origin main --force