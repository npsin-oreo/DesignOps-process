#!/usr/bin/env bash
# setup-prototype.sh — Step 4 base setup (Model A: IMPORT the design system as a package).
#
# This pipeline is a CONSUMER of @npsin-oreo/design-system (the looloo design system). It never
# vendors/copies the DS — it installs the published package and imports components from it. The DS
# lives in node_modules and is IMMUTABLE: customise via brand-scoped [data-slot=*] rules + token
# overrides in globals.css (Step 2.6 theme), never by editing components.
#
#   export GITHUB_TOKEN=$(gh auth token)   # GitHub Packages requires auth, even for public packages
#   bash .claude/skills/designops-pipeline/scripts/setup-prototype.sh --out ./output
#                                        [--ds-pkg @npsin-oreo/design-system@0.2.0] [--ds-name …] [--ds-registry …]
#
# bash 3.2 safe.

set -uo pipefail

OUT="./output"
# Pinned default DS version (security: never float to `latest` — a republished/compromised `latest`
# would flow straight into builds). Bump this when adopting a new published DS release.
DS_VERSION="0.2.0"
IMPORT_PKG="@npsin-oreo/design-system@${DS_VERSION}"  # install spec (pinned; override with --ds-pkg)
DS_NAME=""             # bare package name for CSS @import/@source + transpilePackages (default from IMPORT_PKG)
# Registry for the DS scope. The DS publishes to GitHub Packages, which requires auth even for public
# packages — import writes a scaffold .npmrc binding the scope there with a ${GITHUB_TOKEN} authToken.
# Set --ds-registry "" for a plain public-npm package or a tarball/path spec (then no .npmrc/token).
DS_REGISTRY="https://npm.pkg.github.com"

while [ $# -gt 0 ]; do
  case "$1" in
    --out)         OUT="$2"; shift 2 ;;
    --ds-pkg)      IMPORT_PKG="$2"; shift 2 ;;      # install spec (name@version or path/tarball)
    --ds-name)     DS_NAME="$2"; shift 2 ;;         # bare name for CSS (needed if --ds-pkg is a tarball/path)
    --ds-registry) DS_REGISTRY="$2"; shift 2 ;;     # registry for the DS scope ("" = public npm, no .npmrc)
    *) echo "[setup-prototype] ERROR: unknown flag $1" >&2; exit 1 ;;
  esac
done

# Bare CSS/import name: from --ds-name, else strip a trailing @version off the spec.
if [ -z "$DS_NAME" ]; then
  case "$IMPORT_PKG" in
    *.tgz|./*|../*|/*) DS_NAME="@npsin-oreo/design-system" ;;   # tarball / path → use default (or --ds-name)
    @*/*@*) DS_NAME="${IMPORT_PKG%@*}" ;;      # @scope/name@version → strip version
    @*/*)   DS_NAME="$IMPORT_PKG" ;;           # @scope/name (bare scoped) → as-is
    *@*)    DS_NAME="${IMPORT_PKG%@*}" ;;      # name@version → strip version
    *)      DS_NAME="$IMPORT_PKG" ;;           # bare unscoped name
  esac
fi

log() { echo "[setup-prototype] $*"; }
err() { echo "[setup-prototype] ERROR: $*" >&2; exit 1; }

command -v npm >/dev/null 2>&1 || err "npm required"
PROTO="$OUT/prototype"
mkdir -p "$PROTO/app" "$PROTO/lib"

# ── scaffold a minimal, buildable Next product that IMPORTS the DS ──────────────
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
# tsconfig WITH an @/* path alias — screens import the DS from the package but their own
# composites/mocks from @/components/portal, @/lib/* (which live in the product).
[ -f "$PROTO/tsconfig.json" ] || cat > "$PROTO/tsconfig.json" <<'JSON'
{ "compilerOptions": { "target": "ES2022", "lib": ["dom", "dom.iterable", "esnext"],
  "module": "esnext", "moduleResolution": "bundler", "jsx": "preserve", "strict": true,
  "noEmit": true, "esModuleInterop": true, "skipLibCheck": true, "plugins": [{ "name": "next" }],
  "baseUrl": ".", "paths": { "@/*": ["./*"] } },
  "include": ["**/*.ts", "**/*.tsx", ".next/types/**/*.ts"] }
JSON
# cn(): the DS package does NOT export lib/utils, so the product owns this one tiny helper.
[ -f "$PROTO/lib/utils.ts" ] || cat > "$PROTO/lib/utils.ts" <<'TS'
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
TS
[ -f "$PROTO/app/layout.tsx" ] || cat > "$PROTO/app/layout.tsx" <<'TSX'
import "./globals.css";
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
TSX
[ -f "$PROTO/app/page.tsx" ] || cat > "$PROTO/app/page.tsx" <<TSX
import { Button } from "$DS_NAME/button";
// placeholder — /generate-prototype fills app/ with the real screens (imported from $DS_NAME/*).
export default function Page() {
  return <main className="flex min-h-svh items-center justify-center"><Button>It works</Button></main>;
}
TSX
# CSS entry: DS all-in-one styles + scan the DS components so Tailwind emits their classes.
# Step 2.6's theme overrides (:root/.dark + @theme) are appended AFTER this @import.
CSS="$PROTO/app/globals.css"
if [ ! -f "$CSS" ] || ! grep -q "@source.*$DS_NAME" "$CSS" 2>/dev/null; then
  cat > "$CSS" <<CSS
@import "$DS_NAME/styles.css";
@source "../node_modules/$DS_NAME/components";   /* gotcha #1 — else components render unstyled */
CSS
  log "wrote Tailwind wiring → $CSS (@import styles + @source components)"
fi

# ── .npmrc so npm can fetch a scoped DS from GitHub Packages (auth required) ────
# SECURITY (dependency confusion): the `<scope>:registry=` line BINDS the whole DS scope to GitHub
# Packages, so npm never resolves @<scope>/* from public npmjs — even though the name is unclaimed
# there. Keep this line; do not loosen the scope.
NEEDS_TOKEN=0
case "$IMPORT_PKG" in
  *.tgz|./*|../*|/*) : ;;                          # local spec — no registry auth needed
  @*/*)
    if [ -n "$DS_REGISTRY" ]; then
      DS_SCOPE="${DS_NAME%%/*}"                    # @npsin-oreo
      REG_HOST="${DS_REGISTRY#*://}"               # npm.pkg.github.com
      [ -f "$PROTO/.npmrc" ] || cat > "$PROTO/.npmrc" <<NPMRC
${DS_SCOPE}:registry=${DS_REGISTRY}
//${REG_HOST}/:_authToken=\${GITHUB_TOKEN}
NPMRC
      log "wrote $PROTO/.npmrc ($DS_SCOPE → $DS_REGISTRY, auth via \${GITHUB_TOKEN})"
      NEEDS_TOKEN=1
    fi
    ;;
esac
# Model A is NOT standalone: a scoped GitHub-Packages install hard-requires a token. No fallback.
if [ "$NEEDS_TOKEN" = "1" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
  err "GITHUB_TOKEN is required to install $DS_NAME from $DS_REGISTRY (GitHub Packages needs auth even for public packages).
       Run:  export GITHUB_TOKEN=\$(gh auth token)   then re-run. (This pipeline imports the DS; it is not standalone.)"
fi

log "Installing $DS_NAME ($IMPORT_PKG, pinned) + Next/Tailwind (imported, NOT copied)…"
# --save-exact pins the DS to an exact version (no caret) so the committed lockfile is reproducible
# and a republished version can't silently flow into a later install.
( cd "$PROTO" \
    && npm install "$IMPORT_PKG" --save-exact --no-audit --no-fund \
    && npm install next react react-dom clsx tailwind-merge --no-audit --no-fund \
    && npm install -D tailwindcss @tailwindcss/postcss typescript @types/node @types/react @types/react-dom --no-audit --no-fund ) \
  || err "npm install failed (is '$IMPORT_PKG' published+readable / GITHUB_TOKEN valid / spec correct?)"

log "✓ prototype ready → $PROTO — DS imported from $DS_NAME, not copied"
log "  components are immutable (node_modules) — theme via Step 2.6 token + [data-slot=*] overrides"
log "  add screens under $PROTO/app, then: cd $PROTO && npm run dev"
