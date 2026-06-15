#!/usr/bin/env bash
# selftest.sh — regression guard for the tor-to-brief scripts.
# Runs under macOS stock /bin/bash (3.2). Exits non-zero if any check fails.
#
#   bash .claude/skills/tor-to-brief/scripts/selftest.sh
#
# Covers the bugs we actually hit: bash-4-only syntax, the validate gate, and the
# agent-driven execution model (no claude -p recursion, --exec guard).

set -uo pipefail   # not -e: we want to run every check and tally failures

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
RUN="$SCRIPTS_DIR/run_pipeline.sh"
VALIDATE="$SCRIPTS_DIR/validate_brief.py"
VALIDATE_INTEL="$SCRIPTS_DIR/validate_intelligence.py"
SAMPLE_TOR="$SKILL_DIR/references/sample-tor.md"

PASS=0 FAIL=0
ok()   { PASS=$((PASS+1)); echo "  ✓ $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  ✗ $1"; }
TMP="$(mktemp -d -t tor-selftest.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

echo "── tor-to-brief selftest ─────────────────────────────"
echo "bash: $BASH_VERSION"

# ── T1. bash 3.2 compatibility ────────────────────────────────────────────────
echo "[T1] bash 3.2 compatibility"
for s in "$RUN" "$SCRIPTS_DIR/setup-prototype.sh" "$0"; do
  [ -f "$s" ] || continue
  /bin/bash -n "$s" 2>/dev/null && ok "syntax: $(basename "$s")" || bad "syntax: $(basename "$s")"
done
for p in "$VALIDATE" "$VALIDATE_INTEL" "$SCRIPTS_DIR/validate_flows.py" "$SCRIPTS_DIR/validate_screens.py" "$SCRIPTS_DIR/validate_aesthetic.py" "$SCRIPTS_DIR/audit_prototype.py" "$SCRIPTS_DIR/lint_hardcodes.py"; do
  python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$p" 2>/dev/null && ok "parses: $(basename "$p")" || bad "parses: $(basename "$p")"
done
# bash-4-only constructs that silently break on 3.2
if grep -nE '\$\{[A-Za-z_][A-Za-z_0-9]*(\^\^|,,)\}|\$\{![A-Za-z_]|(^|[^a-z])mapfile|readarray' "$RUN" >/dev/null 2>&1; then
  bad "bash-4-only syntax found in run_pipeline.sh:"; grep -nE '\$\{[A-Za-z_][A-Za-z_0-9]*(\^\^|,,)\}|\$\{![A-Za-z_]|mapfile|readarray' "$RUN" | sed 's/^/      /'
else
  ok "no bash-4-only syntax (\${,,}/\${^^}/\${!var}/mapfile)"
fi

# ── T2. validate_brief.py accepts a valid brief ───────────────────────────────
echo "[T2] validate gate — valid brief passes"
python3 - "$TMP/valid.json" <<'PY'
import json, sys
json.dump({
  "meta": {"project_name":"T","generated_at":"2026-06-12","source_file":"x","tor_confidence":"high"},
  "project_overview": {"objective":"o","scope":"s","out_of_scope":[]},
  "target_users": [{"persona":"p","context":"","pain_points":[]}],
  "core_features": [{"id":"F01","name":"f","description":"","priority":"Must","flows":[]}],
  "user_flows": [{"id":"UF01","name":"u","steps":[]}],
  "constraints": {"technical":[],"business":[],"regulatory":[],"timeline":""},
  "design_direction": {"tone":"","brand_refs":[],"platform":"","breakpoints":[]},
  "success_metrics": [],
  "open_questions": [],
  "scoring_criteria": {"total_score":None,"passing_threshold":None,"categories":[],"minimum_viable":None},
}, open(sys.argv[1],"w"))
PY
python3 "$VALIDATE" "$TMP/valid.json" >/dev/null 2>&1 && ok "valid brief → exit 0" || bad "valid brief should pass but failed"

# ── T3. validate_brief.py rejects invalid briefs ──────────────────────────────
echo "[T3] validate gate — invalid briefs fail"
# missing a required top-level key
python3 -c "import json;d=json.load(open('$TMP/valid.json'));d.pop('core_features');json.dump(d,open('$TMP/no_features.json','w'))"
python3 "$VALIDATE" "$TMP/no_features.json" >/dev/null 2>&1 && bad "missing core_features should fail" || ok "missing required key → exit 1"
# bad priority
python3 -c "import json;d=json.load(open('$TMP/valid.json'));d['core_features'][0]['priority']='Urgent';json.dump(d,open('$TMP/bad_prio.json','w'))"
python3 "$VALIDATE" "$TMP/bad_prio.json" >/dev/null 2>&1 && bad "bad priority should fail" || ok "invalid priority → exit 1"

# ── T4. agent-driven prep mode: stages prompts, no recursion ──────────────────
echo "[T4] execution model — prep mode stages, no recursion"
if [ -f "$SAMPLE_TOR" ]; then
  OUT="$TMP/run"; mkdir -p "$OUT"
  CLAUDECODE=1 /bin/bash "$RUN" --tor "$SAMPLE_TOR" --out "$OUT" >"$OUT/log.txt" 2>&1
  rc=$?
  [ "$rc" = "0" ] && ok "prep run exit 0" || bad "prep run exit $rc"
  [ -f "$OUT/.prompt_step1.txt" ] && [ -f "$OUT/.prompt_intel.txt" ] && [ -f "$OUT/.prompt_aesthetic.txt" ] && [ -f "$OUT/.prompt_flows.txt" ] && [ -f "$OUT/.prompt_step3.txt" ] && ok "step1 + 2.5 + 2.6 + flows + screens prompts staged" || bad "prompts not staged"
  grep -q "AGENT ACTIONS" "$OUT/log.txt" && ok "AGENT ACTIONS checklist printed" || bad "no AGENT ACTIONS block"
else
  bad "sample-tor.md missing — cannot run T4"
fi

# ── T5. --exec recursion guard refuses inside a session ───────────────────────
echo "[T5] execution model — --exec refused inside a session"
CLAUDECODE=1 /bin/bash "$RUN" --tor "$SAMPLE_TOR" --out "$TMP/run2" --exec >"$TMP/exec.log" 2>&1
rc=$?
{ [ "$rc" != "0" ] && grep -q "recursion" "$TMP/exec.log"; } && ok "--exec refused (exit $rc, recursion guard)" || bad "--exec should refuse inside CLAUDECODE session"

# ── T6. Product Intelligence Layer gate ───────────────────────────────────────
echo "[T6] intelligence gate — valid passes, invariants fail"
python3 - "$TMP/intel.json" <<'PY'
import json, sys
json.dump({
 "meta":{"source_brief":"brief.json","generated_at":"2026-06-12","schema_version":"1.0","overall_confidence":"medium","human_reviewed":False},
 "user_types":[{"id":"UT01","name":"Op","role_category":"operator","relationship":"primary","primary_surface":"console",
   "expertise":{"domain":"expert","tool":"intermediate","usage_frequency":"daily","training_provided":"yes"},
   "source":"stated","evidence":["personas[0]"],"confidence":"high"}],
 "user_goals":[{"id":"G01","user_type_ref":"UT01","statement":"act safely and quickly","job_type":"functional","priority":"must","success_signal":"fewer errors","evidence":["TOR:objective"]}],
 "core_tasks":[{"id":"T01","name":"submit order","user_type_ref":"UT01","goal_ref":"G01","frequency":"frequent","trigger":"user","steps_estimate":3,"evidence":["UF01"]}],
 "workflow_complexity":{"overall_score":3,"per_workflow":[]},
 "data_density":{"overall_band":3,"per_surface":[]},
 "error_tolerance":{"overall":"zero","reversibility":"irreversible","critical_actions":[{"task_ref":"T01","consequence":"harm","recommended_safeguards":["double-confirm"]}]},
 "accessibility_needs":{"wcag_target":"AA_plus","default_floor":"WCAG 2.2 AA","specific_needs":[],"motion_sensitivity":False,"drivers":["clinical"]},
 "compliance_requirements":[{"id":"C01","name":"HIPAA","scope":"medical","source":"stated","mandatory":True,"ui_implications":["audit trail"],"confidence":"high"}],
 "decision_criticality":{"overall":"safety_critical","decision_points":[{"task_ref":"T01","stakes":"safety","who_bears_consequence":"user","info_completeness_need":"high","recommended_patterns":["double-confirm"]}]},
 "design_directives":{"density_target":3,"guidance_level":"expert","safeguard_level":"maximal","a11y_target":"AA_plus","mandatory_flows":["audit_log"],"navigation_model":"workspace","trust_emphasis":"high"},
 "open_questions":[]
}, open(sys.argv[1],"w"))
PY
python3 "$VALIDATE_INTEL" "$TMP/intel.json" >/dev/null 2>&1 && ok "valid intelligence → exit 0" || bad "valid intelligence should pass"
# invariant: safety_critical ⇒ error_tolerance low/zero
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d['error_tolerance']['overall']='high';json.dump(d,open('$TMP/i_bad1.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_bad1.json" >/dev/null 2>&1 && bad "safety_critical+high tolerance should fail" || ok "invariant safety_critical⇒low/zero → exit 1"
# invariant: design_directives.a11y_target must equal accessibility_needs.wcag_target
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d['design_directives']['a11y_target']='AAA';json.dump(d,open('$TMP/i_bad2.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_bad2.json" >/dev/null 2>&1 && bad "a11y rollup mismatch should fail" || ok "invariant a11y rollup match → exit 1"
# missing top-level key
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d.pop('design_directives');json.dump(d,open('$TMP/i_bad3.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_bad3.json" >/dev/null 2>&1 && bad "missing design_directives should fail" || ok "missing required key → exit 1"

# ── T7. Flows gate (Step 3) ───────────────────────────────────────────────────
echo "[T7] flows gate — valid passes, nav_model mismatch fails"
cat > "$TMP/i2.json" <<'PY'
{"meta":{},"user_types":[{"id":"UT01"}],"user_goals":[{"id":"G01"}],"core_tasks":[],
 "workflow_complexity":{},"data_density":{},"error_tolerance":{},"accessibility_needs":{},
 "compliance_requirements":[],"decision_criticality":{},
 "design_directives":{"navigation_model":"hub_spoke","mandatory_flows":["consent"]}}
PY
cat > "$TMP/flows.json" <<'PY'
{"meta":{},"navigation_model":"hub_spoke","flows":[
 {"id":"FL01","name":"Book","source_flow_ref":"UF01","user_type_ref":"UT01","goal_ref":"G01","steps":[{"n":1,"action":"pick","decision":false,"safeguard":null}],"entry":"home","exit":"done","directives_applied":[]},
 {"id":"FL02","name":"Consent","source_flow_ref":null,"user_type_ref":"UT01","goal_ref":"G01","steps":[{"n":1,"action":"accept","decision":true,"safeguard":"opt-in"}],"entry":"first","exit":"home","directives_applied":["mandatory"]}],
 "mandatory_flows":[{"name":"consent","reason":"PDPA","injected":true}]}
PY
python3 "$SCRIPTS_DIR/validate_flows.py" "$TMP/flows.json" "$TMP/i2.json" >/dev/null 2>&1 && ok "valid flows → exit 0" || bad "valid flows should pass"
python3 -c "import json;d=json.load(open('$TMP/flows.json'));d['navigation_model']='single';json.dump(d,open('$TMP/fl_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_flows.py" "$TMP/fl_bad.json" "$TMP/i2.json" >/dev/null 2>&1 && bad "nav mismatch should fail" || ok "nav_model must match directive → exit 1"

# ── T8. Screens gate (Step 3.5) ───────────────────────────────────────────────
echo "[T8] screens gate — valid passes, coverage gap fails"
cat > "$TMP/screens.json" <<'PY'
{"meta":{},"screens":[
 {"id":"SC01","name":"Book","flow_refs":["FL01"],"user_type_ref":"UT01","priority":"Must","purpose":"x","layout_primitive":"form","components":["Card"],"gaps":[],"directive_drivers":[]},
 {"id":"SC02","name":"Consent","flow_refs":["FL02"],"user_type_ref":"UT01","priority":"Must","purpose":"x","layout_primitive":"card","components":["Card","Checkbox"],"gaps":[],"directive_drivers":[]}]}
PY
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/screens.json" "$TMP/flows.json" >/dev/null 2>&1 && ok "valid screens (full coverage) → exit 0" || bad "valid screens should pass"
python3 -c "import json;d=json.load(open('$TMP/screens.json'));d['screens']=d['screens'][:1];json.dump(d,open('$TMP/sc_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/sc_bad.json" "$TMP/flows.json" >/dev/null 2>&1 && bad "uncovered flow should fail" || ok "flow→screen coverage enforced → exit 1"

# ── T9. Aesthetic gate (Step 2.6) ─────────────────────────────────────────────
echo "[T9] aesthetic gate — valid passes, fake brand + low contrast fails"
# brand library must be vendored for a named_system to resolve
[ -d "$SCRIPTS_DIR/../references/aesthetics/design-systems/library" ] && ok "brand library vendored" || bad "brand library not vendored"
cat > "$TMP/aes_intel.json" <<'PY'
{"design_directives":{"a11y_target":"AA","density_target":4}}
PY
cat > "$TMP/aesthetic.json" <<'PY'
{"meta":{"version":"1"},
 "brief_inference":{"domain":"dev SaaS","audience_tone":"technical","mood_adjective":"precise","motion_depth":"subtle","rationale":"trust+experts → calm engineered system"},
 "direction":{"type":"named_system","name":"linear-app","category":"Productivity & SaaS","spec_ref":"references/aesthetics/design-systems/library/linear-app/DESIGN.md","why_fit":"expert, dense, high trust"},
 "tokens":{"primary":"oklch(0.55 0.18 264)","background":"oklch(0.16 0.01 264)","foreground":"oklch(0.97 0 0)","radius":"0.5rem","font_sans":"Inter, sans-serif"},
 "contrast_checks":[{"pair":"foreground/background","fg_hex":"#f7f7f8","bg_hex":"#191a23"},{"pair":"primary-foreground/primary","fg_hex":"#ffffff","bg_hex":"#5b5bd6"}],
 "constraints":{"a11y_target":"AA","density_target":4},
 "brand_config":{"project_name":"Devflow","primary":"oklch(0.55 0.18 264)","radius":"0.5rem","font_sans":"Inter, sans-serif"}}
PY
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aesthetic.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && ok "valid aesthetic → exit 0" || bad "valid aesthetic should pass"
# fake brand must fail (does not resolve in the vendored library)
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['direction']['name']='totally-made-up';json.dump(d,open('$TMP/aes_brand.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_brand.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "fake brand should fail" || ok "named_system must resolve in library → exit 1"
# contrast computed from hex must gate (not the self-reported number)
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['contrast_checks'][0]['fg_hex']='#3a3b45';json.dump(d,open('$TMP/aes_contrast.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_contrast.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "low contrast should fail" || ok "contrast recomputed from hex enforced → exit 1"
# a11y_target must echo design_directives
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['constraints']['a11y_target']='AAA';json.dump(d,open('$TMP/aes_a11y.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_a11y.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "a11y mismatch should fail" || ok "a11y_target must equal directive → exit 1"

# ── T10. Audit gate (Step 4.7) — runs real scripts over a fake prototype ──────
echo "[T10] audit gate — clean passes, hardcode + low-contrast block"
PROTO="$TMP/proto"; mkdir -p "$PROTO/app" "$PROTO/components"
# a theme with strong contrast (near-black text on white, light + dark)
cat > "$PROTO/app/globals.css" <<'CSS'
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.15 0 0);
  --primary: oklch(0.2 0 0);
  --primary-foreground: oklch(0.98 0 0);
}
.dark {
  --background: oklch(0.15 0 0);
  --foreground: oklch(0.98 0 0);
  --primary: oklch(0.9 0 0);
  --primary-foreground: oklch(0.15 0 0);
}
CSS
# a clean screen — only token refs, no hardcodes
cat > "$PROTO/app/page.tsx" <<'TSX'
export default function Page() {
  return <div className="bg-background text-foreground">hello</div>;
}
TSX
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA >/dev/null 2>&1 && ok "clean prototype → exit 0 (PASS)" || bad "clean prototype should pass"
# inject a hardcoded hex + a raw palette utility → token gate must block
cat > "$PROTO/app/bad.tsx" <<'TSX'
export const C = () => <div style={{ color: "#ff0000" }} className="bg-gray-500">x</div>;
TSX
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA >/dev/null 2>&1 && bad "hardcode should block" || ok "hardcoded hex + bg-gray-500 → exit 1 (BLOCKED)"
rm -f "$PROTO/app/bad.tsx"
# low-contrast theme (foreground ~ background) → contrast gate must block
cat > "$PROTO/app/globals.css" <<'CSS'
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.9 0 0);
  --primary: oklch(0.95 0 0);
  --primary-foreground: oklch(0.92 0 0);
}
CSS
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA >/dev/null 2>&1 && bad "low contrast should block" || ok "foreground≈background → exit 1 (BLOCKED)"

# ── result ────────────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────────────"
echo "PASS: $PASS   FAIL: $FAIL"
[ "$FAIL" = "0" ] && { echo "✓ selftest green"; exit 0; } || { echo "✗ selftest failed"; exit 1; }
