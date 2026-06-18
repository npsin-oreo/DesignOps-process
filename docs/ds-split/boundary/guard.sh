#!/usr/bin/env bash
# CI guard: a designops bot PR may only touch product/generated/**.
# Any file outside that tree from the bot is a boundary violation → fail the PR.
#
# Usage:  guard.sh <author> <changed-file>...
#   (in CI: guard.sh "$PR_AUTHOR" $(git diff --name-only origin/main))
set -euo pipefail
BOT="designops-bot"
author="${1:?usage: guard.sh <author> <changed-file>...}"; shift || true

if [[ "$author" != "$BOT" ]]; then
  echo "guard: author '$author' is not the bot — no restriction"; exit 0
fi

violations=()
for f in "$@"; do
  # bot may write generated/** anywhere under a product; nothing else.
  [[ "$f" == *"/generated/"* || "$f" == generated/* ]] && continue
  violations+=("$f")
done

if (( ${#violations[@]} )); then
  echo "::error:: designops-bot PR touched files OUTSIDE generated/ (boundary / point 8 violation):"
  printf '   ✗ %s\n' "${violations[@]}"
  exit 1
fi
echo "guard: bot PR touches only generated/ — OK"
exit 0
