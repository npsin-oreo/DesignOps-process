#!/usr/bin/env bash
# Codemod: rewrite the DS's internal alias `@/...` → Node subpath import `#...`
# so the design system can be IMPORTED as a package (point 5) instead of copied.
#
#   @/lib/utils          -> #lib/utils
#   @/components/ui/btn  -> #components/ui/btn
#   @/hooks/use-mobile   -> #hooks/use-mobile
#
# Then add an `imports` map + a matching tsconfig `paths` block to the package.
#
# Usage:  bash codemod.sh <design-system-dir>
# Safe to re-run (idempotent). In the real migration, run on a branch and review the diff.
set -euo pipefail
TARGET="${1:?usage: codemod.sh <design-system-dir>}"
[ -d "$TARGET" ] || { echo "no such dir: $TARGET" >&2; exit 1; }

echo "→ rewriting \"@/  →  \"#  in import specifiers under $TARGET"
# Only ever touches a quote immediately followed by @/  — i.e. module specifiers.
# (verified: the DS has no `@/` outside import specifiers, so this can't hit comments/css)
find "$TARGET" \( -name '*.ts' -o -name '*.tsx' -o -name '*.mts' \) \
  -not -path '*/node_modules/*' -not -path '*/.next/*' -not -path '*/.claude/*' -print0 \
  | xargs -0 perl -pi -e 's/(["\x27])\@\//$1#/g'

echo "→ patching package.json (add imports map) + tsconfig.json (paths #*)"
node - "$TARGET" <<'NODE'
const fs = require("fs"), path = require("path");
const dir = process.argv[2];

// package.json — add subpath imports. Source-resolved (bundler/tsup adds extensions).
const pkgPath = path.join(dir, "package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
pkg.imports = {
  "#lib/*": "./lib/*",
  "#components/*": "./components/*",
  "#hooks/*": "./hooks/*"
};
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n");

// tsconfig.json — mirror the alias so the editor/tsc resolves `#` the same way.
const tsPath = path.join(dir, "tsconfig.json");
if (fs.existsSync(tsPath)) {
  const ts = JSON.parse(fs.readFileSync(tsPath, "utf8"));
  ts.compilerOptions = ts.compilerOptions || {};
  ts.compilerOptions.paths = {
    "#lib/*": ["./lib/*"],
    "#components/*": ["./components/*"],
    "#hooks/*": ["./hooks/*"]
  };
  fs.writeFileSync(tsPath, JSON.stringify(ts, null, 2) + "\n");
}
console.log("   imports + paths written");
NODE

echo "✓ codemod done"
