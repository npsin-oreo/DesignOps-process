#!/usr/bin/env bash
# Proves point 8: "DesignOps can regenerate the Blueprint layer but must not rewrite business logic."
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PROD="$HERE/product"
BP="$PROD/generated/blueprints/booking.blueprint.json"
pass=true
check(){ if eval "$2"; then echo "PASS  $1"; else echo "FAIL  $1"; pass=false; fi; }

src_hash(){ find "$PROD/src" -type f -print0 | sort -z | xargs -0 shasum | shasum | awk '{print $1}'; }

echo "→ initial regenerate + run"
bash "$HERE/regenerate.sh" >/dev/null
OUT1="$(node "$PROD/app.mjs")"
TOTAL1="$(node -e "process.stdout.write(String(JSON.parse(process.argv[1]).total))" "$OUT1")"
SRC1="$(src_hash)"
echo "   run #1: $OUT1"

echo "→ simulate a DESIGN change (add a 'summary' region) + regenerate"
cp "$BP" "$BP.bak"
node -e "const f=process.argv[1],j=require(f);j.regions.push({slot:'summary',components:['Card']});require('fs').writeFileSync(f,JSON.stringify(j,null,2))" "$BP"
bash "$HERE/regenerate.sh" >/dev/null
OUT2="$(node "$PROD/app.mjs")"
TOTAL2="$(node -e "process.stdout.write(String(JSON.parse(process.argv[1]).total))" "$OUT2")"
SRC2="$(src_hash)"
echo "   run #2: $OUT2"

# 1. generated layer actually changed (the new region shows up)
check "regenerate updated the generated screen (layout changed)" '[ "$OUT1" != "$OUT2" ]'
# 2. src/ is byte-for-byte identical — bot never touched business logic
check "src/ unchanged after regenerate (hash identical)" '[ "$SRC1" = "$SRC2" ]'
# 3. business logic still produces the same result (logic survived)
check "business logic intact (total $TOTAL1 == $TOTAL2)" '[ "$TOTAL1" = "$TOTAL2" ]'
# 4. every generated file carries the @generated marker
check "generated files marked @generated" 'grep -ql "@generated" "$PROD/generated/screens/booking.mjs" "$PROD/generated/contracts/booking.mjs"'

echo "→ CI guard"
# 5. bot touching src/ → blocked
if bash "$HERE/guard.sh" designops-bot product/src/bindings/booking.mjs >/dev/null 2>&1; then
  echo "FAIL  guard should block bot editing src/"; pass=false
else echo "PASS  guard blocks bot editing src/ → exit 1"; fi
# 6. bot touching only generated/ → allowed
if bash "$HERE/guard.sh" designops-bot product/generated/screens/booking.mjs >/dev/null 2>&1; then
  echo "PASS  guard allows bot editing generated/ → exit 0"
else echo "FAIL  guard should allow bot editing generated/"; pass=false; fi

mv "$BP.bak" "$BP"                       # restore blueprint
bash "$HERE/regenerate.sh" >/dev/null    # restore generated to baseline
echo ""
$pass && { echo "✅ POINT 8 ENFORCED — regenerate touches only generated/, logic survives"; exit 0; } \
      || { echo "❌ boundary not enforced"; exit 1; }
