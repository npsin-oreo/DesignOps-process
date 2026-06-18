#!/usr/bin/env bash
# Proves "import, not copy" end-to-end with no network: installs the DS as a
# file: dependency into a mock product repo, then runs it.
set -euo pipefail
cd "$(dirname "$0")/consumer"

echo "→ installing @acme/ds-poc into product repo (file: dep, offline)…"
npm install --no-audit --no-fund --silent

echo "→ confirming DS landed in node_modules as a package (not vendored source)…"
ls node_modules/@acme/ds-poc >/dev/null && echo "   node_modules/@acme/ds-poc present"

echo "→ running the product app that IMPORTS the DS…"
echo "------------------------------------------------------------"
node app.mjs
