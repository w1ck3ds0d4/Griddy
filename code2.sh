#!/usr/bin/env bash
set -euo pipefail
OWNER="w1ck3ds0d4"
REPOS=(
  griddy w1ck3ds0d4 purrmadeath glassvault lodestar warchest steamroulette
  securecheck rimdocplus prooflog nanofarm mimicme glassvault.tools
  euroflow da-task-alert cradesk-kit cradesk-inline cradesk cra-check
  blueflame aktivpath university-work threatlens veilbreak grainwallet
)
for repo in "${REPOS[@]}"; do
  echo "Locking $OWNER/$repo to squash-only..."
  gh api -X PATCH "repos/$OWNER/$repo" \
    -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
    --silent && echo "  done" || echo "  FAILED"
done