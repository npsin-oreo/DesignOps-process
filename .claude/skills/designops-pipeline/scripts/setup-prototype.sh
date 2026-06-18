#!/usr/bin/env bash
# setup-prototype.sh — Step 4 base setup, fast + correct.
#
# Copies the design system into {OUT}/prototype and installs deps. Two speedups,
# both keeping a REAL node_modules (a symlinked/shared node_modules breaks tsc's
# @types/react resolution — proven, don't do it):
#   1. Reuse: if a prototype already has node_modules matching the current lockfile,
#      only the source is refreshed — no reinstall.
#   2. npm ci --prefer-offline: lockfile-exact, uses npm's own (~/.npm) cache, skips
#      audit/fund. The first install is the one-time cost; repeats are fast.
#
#   bash .claude/skills/designops-pipeline/scripts/setup-prototype.sh --out ./output [--ds ./design-system]
#
# Import mode (point 5 — install the DS as a package instead of copying it):
#   bash …/setup-prototype.sh --out ./output --ds-import [--ds-pkg @acme/ds@1.0.0]
#
# bash 3.2 safe.

set -uo pipefail

DS="./design-system"
OUT="./output"
IMPORT_MODE=0          # default: copy (rsync) the DS — unchanged behavior
AUTO_MODE=0            # --ds-auto: prefer import (Model A) when possible, else fall back to rsync
# Pinned default DS version (security: never float to `latest` — a republished/compromised
# `latest` would flow straight into builds). Bump this when adopting a new DS release.
DS_VERSION="0.1.2"
IMPORT_PKG="@npsin-oreo/design-system@${DS_VERSION}"  # install spec for --ds-import (pinned; override with --ds-pkg)
DS_NAME=""             # bare package name for CSS @import/@source (defaults from IMPORT_PKG)
# Registry for the DS scope. The DS publishes to GitHub Packages, which requires auth even
# for public packages — so import-mode writes a scaffold .npmrc pointing the scope there with
# an ${GITHUB_TOKEN} authToken. Empty (or a tarball/path spec) → skip the .npmrc (public npm).
DS_REGISTRY="https://npm.pkg.github.com"
while [ $# -gt 0 ]; do
  case "$1" in
    --ds)          DS="$2"; shift 2 ;;
    --out)         OUT="$2"; shift 2 ;;
    --ds-import)   IMPORT_MODE=1; shift ;;          # IMPORT the DS package instead of copying
    --ds-auto)     AUTO_MODE=1;   shift ;;          # graceful: import when possible, else rsync fallback
    --ds-pkg)      IMPORT_PKG="$2"; shift 2 ;;      # install spec (name@version or path/tarball)
    --ds-name)     DS_NAME="$2"; shift 2 ;;         # bare name for CSS (needed if --ds-pkg is a tarball/path)
    --ds-registry) DS_REGISTRY="$2"; shift 2 ;;     # registry for the DS scope ("" = public npm, no .npmrc)
    *) echo "[setup-prototype] ERROR: unknown flag $1" >&2; exit 1 ;;
  esac
done
# Bare CSS name: from --ds-name, else strip a trailing @version off a plain spec,
# else fall back to @acme/ds (a tarball/path can't be a CSS specifier — pass --ds-name).
if [ -z "$DS_NAME" ]; then
  case "$IMPORT_PKG" in
    *.tgz|./*|../*|/*) DS_NAME="@npsin-oreo/design-system" ;;   # tarball / filesystem path → use default (or --ds-name)
    @*/*@*) DS_NAME="${IMPORT_PKG%@*}" ;;      # @scope/name@version → strip version
    @*/*)   DS_NAME="$IMPORT_PKG" ;;           # @scope/name (bare scoped) → as-is
    *@*)    DS_NAME="${IMPORT_PKG%@*}" ;;      # name@version → strip version
    *)      DS_NAME="$IMPORT_PKG" ;;           # bare unscoped name
  esac
fi

log() { echo "[setup-prototype] $*"; }
err() { echo "[setup-prototype] ERROR: $*" >&2; exit 1; }

# ── graceful default (--ds-auto): prefer Model A import, fall back to offline rsync ──
# GitHub Packages needs auth even for public packages, so import is only attempted when
# GITHUB_TOKEN is present; otherwise (and on any import failure) we use the in-repo DS.
if [ "$AUTO_MODE" = "1" ]; then
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    IMPORT_MODE=1
    log "auto: GITHUB_TOKEN present → trying import mode ($IMPORT_PKG), rsync fallback if it fails"
  else
    IMPORT_MODE=0
    log "auto: GITHUB_TOKEN unset → using offline rsync ./design-system (import skipped)"
  fi
fi

# ── import mode (point 5): install the DS as a package, never copy it ──────────
# Self-contained — does NOT touch the rsync/copy path below (which stays the default).
if [ "$IMPORT_MODE" = "1" ]; then
  command -v npm >/dev/null 2>&1 || err "npm required"
  PROTO="$OUT/prototype"
  mkdir -p "$PROTO/app"

  # Scaffold a minimal, buildable Next product that IMPORTS the DS (never a copy).
  [ -f "$PROTO/package.json" ] || cat > "$PROTO/package.json" <<JSON
{ "name": "prototype", "version": "0.0.0", "private": true,
  "scripts": { "dev": "next dev", "build": "next build" } }
JSON
  # The DS ships source .tsx (relative imports) → Next must transpile the package.
  [ -f "$PROTO/next.config.ts" ] || cat > "$PROTO/next.config.ts" <<TS
import type { NextConfig } from "next";
const nextConfig: NextConfig = { transpilePackages: ["$DS_NAME"] };
export default nextConfig;
TS
  [ -f "$PROTO/postcss.config.mjs" ] || cat > "$PROTO/postcss.config.mjs" <<'MJS'
const config = { plugins: { "@tailwindcss/postcss": {} } };
export default config;
MJS
  [ -f "$PROTO/tsconfig.json" ] || cat > "$PROTO/tsconfig.json" <<'JSON'
{ "compilerOptions": { "target": "ES2022", "lib": ["dom", "dom.iterable", "esnext"],
  "module": "esnext", "moduleResolution": "bundler", "jsx": "preserve", "strict": true,
  "noEmit": true, "esModuleInterop": true, "skipLibCheck": true, "plugins": [{ "name": "next" }] },
  "include": ["**/*.ts", "**/*.tsx", ".next/types/**/*.ts"] }
JSON
  [ -f "$PROTO/app/layout.tsx" ] || cat > "$PROTO/app/layout.tsx" <<'TSX'
import "./globals.css";
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
TSX
  [ -f "$PROTO/app/page.tsx" ] || cat > "$PROTO/app/page.tsx" <<TSX
import { Button } from "$DS_NAME/button";
// placeholder — /generate-prototype fills app/ with the real screens.
export default function Page() {
  return <main className="flex min-h-svh items-center justify-center"><Button>It works</Button></main>;
}
TSX
  # CSS entry: DS all-in-one styles + scan the DS components so Tailwind emits their classes.
  CSS="$PROTO/app/globals.css"
  if [ ! -f "$CSS" ] || ! grep -q "@source.*$DS_NAME" "$CSS" 2>/dev/null; then
    cat > "$CSS" <<CSS
@import "$DS_NAME/styles.css";
@source "../node_modules/$DS_NAME/components";   /* gotcha #1 — else components render unstyled */
CSS
    log "wrote Tailwind wiring → $CSS (@import styles + @source components)"
  fi

  # Scaffold .npmrc so `npm install` can fetch a scoped DS from a private registry
  # (GitHub Packages requires auth even for public packages). Skip for tarball/path
  # specs and when --ds-registry "" (plain public-npm package).
  # SECURITY (dependency confusion): the `<scope>:registry=` line BINDS the whole DS scope
  # to GitHub Packages, so npm never resolves @<scope>/* from public npmjs — even though the
  # name is currently unclaimed there. Keep this line; do not loosen the scope.
  case "$IMPORT_PKG" in
    *.tgz|./*|../*|/*) : ;;                        # local spec — no registry auth needed
    @*/*)
      if [ -n "$DS_REGISTRY" ]; then
        DS_SCOPE="${DS_NAME%%/*}"                  # @npsin-oreo  (from @npsin-oreo/design-system)
        REG_HOST="${DS_REGISTRY#*://}"             # npm.pkg.github.com
        if [ ! -f "$PROTO/.npmrc" ]; then
          cat > "$PROTO/.npmrc" <<NPMRC
${DS_SCOPE}:registry=${DS_REGISTRY}
//${REG_HOST}/:_authToken=\${GITHUB_TOKEN}
NPMRC
          log "wrote $PROTO/.npmrc ($DS_SCOPE → $DS_REGISTRY, auth via \${GITHUB_TOKEN})"
        fi
        [ -n "${GITHUB_TOKEN:-}" ] || log "⚠  GITHUB_TOKEN is unset — install of $DS_SCOPE will 401. Run: export GITHUB_TOKEN=\$(gh auth token)"
      fi
      ;;
  esac

  log "Import mode — installing $DS_NAME ($IMPORT_PKG, pinned) + Next/Tailwind (NOT copying the DS)…"
  # --save-exact pins the DS to an exact version in package.json (no caret) so the committed
  # lockfile is reproducible and a republished version can't silently flow into a later install.
  if ( cd "$PROTO" \
        && npm install "$IMPORT_PKG" --save-exact --no-audit --no-fund \
        && npm install next react react-dom --no-audit --no-fund \
        && npm install -D tailwindcss @tailwindcss/postcss typescript @types/node @types/react @types/react-dom --no-audit --no-fund ); then
    log "✓ prototype (import mode) ready → $PROTO — DS imported, not copied (point 5)"
    log "  add screens under $PROTO/app, then: cd $PROTO && npm run dev"
    exit 0
  elif [ "$AUTO_MODE" = "1" ]; then
    log "⚠  import install failed — falling back to offline rsync ./design-system (graceful default)"
    rm -rf "$PROTO"                 # discard the partial import scaffold so rsync starts clean
    IMPORT_MODE=0                   # fall through to the rsync path below
  else
    err "npm install failed (is '$IMPORT_PKG' published+readable / GITHUB_TOKEN set / spec correct?)"
  fi
fi

# resolve in-repo DS default if the given one is missing
if [ ! -d "$DS" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  ALT="$(cd "$SCRIPT_DIR/../../../.." && pwd)/design-system"
  [ -d "$ALT" ] && DS="$ALT" || err "design system not found: $DS"
fi
command -v rsync >/dev/null 2>&1 || err "rsync required"
command -v npm   >/dev/null 2>&1 || err "npm required"

PROTO="$OUT/prototype"
MARKER_REL="node_modules/.tor-lock-hash"

_lock_hash() {  # hash of the design-system lockfile (install fingerprint)
  local lock="$DS/package-lock.json"; [ -f "$lock" ] || lock="$DS/package.json"
  if command -v shasum >/dev/null 2>&1; then shasum "$lock" | awk '{print $1}'
  elif command -v sha1sum >/dev/null 2>&1; then sha1sum "$lock" | awk '{print $1}'
  else cksum "$lock" | awk '{print $1}'; fi
}

# Reusable only if it's a REAL dir (not a symlink) whose install fingerprint
# (marker we wrote) matches the current design-system lockfile.
_can_reuse() {
  [ -d "$PROTO/node_modules" ] || return 1
  [ -L "$PROTO/node_modules" ] && return 1   # never reuse a symlinked one
  [ -f "$PROTO/$MARKER_REL" ] || return 1
  [ "$(cat "$PROTO/$MARKER_REL" 2>/dev/null)" = "$(_lock_hash)" ]
}

if _can_reuse; then
  log "Reusing existing node_modules (lockfile matches) — refreshing source only ⚡"
  rsync -a --delete \
    --exclude node_modules --exclude .next --exclude out --exclude .git --exclude '.DS_Store' \
    "$DS"/ "$PROTO"/ || err "rsync failed"
else
  log "Copying design system → $PROTO"
  mkdir -p "$PROTO"
  rsync -a --delete-excluded \
    --exclude node_modules --exclude .next --exclude out --exclude .git --exclude '.DS_Store' \
    "$DS"/ "$PROTO"/ || err "rsync failed"

  log "Installing deps (npm ci --prefer-offline — first run is the slow one; repeats use npm's cache)…"
  if ! ( cd "$PROTO" && npm ci --prefer-offline --no-audit --no-fund ); then
    log "npm ci failed (lockfile out of sync?) — falling back to npm install"
    ( cd "$PROTO" && npm install --no-audit --no-fund ) || err "npm install failed"
  fi
  # fingerprint the install so the next run can reuse it
  _lock_hash > "$PROTO/$MARKER_REL"
fi

log "✓ prototype ready → $PROTO"
log "  cd $PROTO && npm run dev"
