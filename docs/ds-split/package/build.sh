#!/usr/bin/env bash
# Build the (already codemod'd) design system into an importable package.
# Prereq: run ../codemod/codemod.sh on the DS first (turns @/ into #-subpaths).
#
# Usage: bash build.sh <design-system-dir>
set -euo pipefail
DS="${1:?usage: build.sh <design-system-dir>}"
HERE="$(cd "$(dirname "$0")" && pwd)"

cp "$HERE/tsup.config.ts" "$HERE/tsconfig.build.json" "$DS/"

cd "$DS"
npm install -D tsup esbuild-plugin-preserve-directives --no-audit --no-fund

# 1. tsup: transpile-only (bundle:false) → one .js per component, "use client" kept at line 1
# 2. tsc: emit matching .d.ts (reads tsconfig paths so internal #... resolves)
npx tsup
npx tsc -p tsconfig.build.json

echo "✓ built dist/ ($(find dist -name '*.js' | wc -l | tr -d ' ') js + $(find dist -name '*.d.ts' | wc -l | tr -d ' ') d.ts)"
echo "  next: merge package.recipe.json into the DS package.json, then \`npm pack\` / publish"
