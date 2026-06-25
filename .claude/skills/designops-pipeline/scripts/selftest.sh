#!/usr/bin/env bash
# selftest.sh — regression guard for the designops-pipeline scripts.
# Runs under macOS stock /bin/bash (3.2). Exits non-zero if any check fails.
#
#   bash .claude/skills/designops-pipeline/scripts/selftest.sh
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

echo "── designops-pipeline selftest ─────────────────────────────"
echo "bash: $BASH_VERSION"

# ── T1. bash 3.2 compatibility ────────────────────────────────────────────────
echo "[T1] bash 3.2 compatibility"
for s in "$RUN" "$SCRIPTS_DIR/setup-prototype.sh" "$SCRIPTS_DIR/finalize-prototype.sh" "$0"; do
  [ -f "$s" ] || continue
  /bin/bash -n "$s" 2>/dev/null && ok "syntax: $(basename "$s")" || bad "syntax: $(basename "$s")"
done
for p in "$VALIDATE" "$VALIDATE_INTEL" "$SCRIPTS_DIR/validate_flows.py" "$SCRIPTS_DIR/validate_screens.py" "$SCRIPTS_DIR/validate_aesthetic.py" "$SCRIPTS_DIR/validate_research.py" "$SCRIPTS_DIR/validate_competitive.py" "$SCRIPTS_DIR/validate_usability.py" "$SCRIPTS_DIR/validate_critique.py" "$SCRIPTS_DIR/validate_edgecases.py" "$SCRIPTS_DIR/audit_prototype.py" "$SCRIPTS_DIR/lint_hardcodes.py" "$SCRIPTS_DIR/lint_edge_coverage.py" "$SCRIPTS_DIR/lint_font_fidelity.py" "$SCRIPTS_DIR/lint_axis_fidelity.py" "$SCRIPTS_DIR/../references/ux-writing/scripts/check_no_emoji.py"; do
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
 "design_directives":{"density_target":3,"guidance_level":"expert","safeguard_level":"maximal","a11y_target":"AA_plus","mandatory_flows":["audit_log"],"navigation_model":"workspace","trust_emphasis":"high","rationale":"safety_critical + irreversible actions drive maximal safeguards and expert density","trade_offs":[{"decision":"confirmation friction","chose":"double-confirm on critical actions","over":"one-click speed","because":"error_tolerance is zero"}]},
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
# reasoning trace: rationale required; malformed trade_off rejected
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d['design_directives'].pop('rationale');json.dump(d,open('$TMP/i_bad4.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_bad4.json" >/dev/null 2>&1 && bad "missing rationale should fail" || ok "design_directives.rationale required → exit 1"
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d['design_directives']['trade_offs']=[{'decision':'x'}];json.dump(d,open('$TMP/i_bad5.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_bad5.json" >/dev/null 2>&1 && bad "incomplete trade_off should fail" || ok "trade_off needs decision/chose/over/because → exit 1"
# feature traceability (with brief): every Must feature must be served by a task/goal
cat > "$TMP/brief_intel.json" <<'PY'
{"meta":{"project_name":"x","generated_at":"n","source_file":"t"},"project_overview":{"objective":"o"},"target_users":[{"persona":"p"}],"core_features":[{"id":"F1","name":"Submit order","priority":"Must"},{"id":"F2","name":"History","priority":"Should"}],"user_flows":[],"constraints":{},"open_questions":[],"scoring_criteria":{}}
PY
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d['core_tasks'][0]['feature_refs']=['F1'];json.dump(d,open('$TMP/i_feat_ok.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_feat_ok.json" "$TMP/brief_intel.json" >/dev/null 2>&1 && ok "Must feature served by a task → exit 0" || bad "feature_refs coverage should pass"
python3 -c "import json;d=json.load(open('$TMP/intel.json'));d['core_tasks'][0]['feature_refs']=['F2'];json.dump(d,open('$TMP/i_feat_bad.json','w'))"
python3 "$VALIDATE_INTEL" "$TMP/i_feat_bad.json" "$TMP/brief_intel.json" >/dev/null 2>&1 && bad "unserved Must feature should fail" || ok "Must feature → task traceability enforced → exit 1"

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
{"meta":{"must_have_features":["F1","F2"]},"screens":[
 {"id":"SC01","name":"Book","route":"book","flow_refs":["FL01"],"feature_refs":["F1"],"states":["loading","empty"],"user_type_ref":"UT01","priority":"Must","purpose":"x","layout_primitive":"form","components":["Card"],"gaps":[],"directive_drivers":[]},
 {"id":"SC02","name":"Consent","route":"consent","flow_refs":["FL02"],"feature_refs":["F2"],"states":["error"],"user_type_ref":"UT01","priority":"Must","purpose":"x","layout_primitive":"card","components":["Card","Checkbox"],"gaps":[],"directive_drivers":[]}]}
PY
cat > "$TMP/brief_sc.json" <<'PY'
{"meta":{"project_name":"x","generated_at":"now","source_file":"t"},"project_overview":{"objective":"o"},"target_users":[{"persona":"p"}],"core_features":[{"id":"F1","name":"Book","priority":"Must"},{"id":"F2","name":"Consent","priority":"Must"}],"user_flows":[{"id":"FL01","name":"a"},{"id":"FL02","name":"b"}],"constraints":{},"open_questions":[],"scoring_criteria":{"minimum_viable":{"must_have_features":["F1","F2"]}}}
PY
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/screens.json" "$TMP/flows.json" >/dev/null 2>&1 && ok "valid screens (full coverage) → exit 0" || bad "valid screens should pass"
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/screens.json" "$TMP/flows.json" "$TMP/brief_sc.json" >/dev/null 2>&1 && ok "feature + scoring coverage (brief) → exit 0" || bad "full feature/scoring coverage should pass"
python3 -c "import json;d=json.load(open('$TMP/screens.json'));d['screens']=d['screens'][:1];json.dump(d,open('$TMP/sc_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/sc_bad.json" "$TMP/flows.json" >/dev/null 2>&1 && bad "uncovered flow should fail" || ok "flow→screen coverage enforced → exit 1"
# Must feature F2 left with no screen → fails against the brief (contractual scope dropped)
python3 -c "import json;d=json.load(open('$TMP/screens.json'));d['screens'][1]['feature_refs']=[];json.dump(d,open('$TMP/sc_feat.json','w'))"
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/sc_feat.json" "$TMP/flows.json" "$TMP/brief_sc.json" >/dev/null 2>&1 && bad "uncovered Must feature should fail" || ok "Must feature → screen coverage enforced → exit 1"
# Must screen without a route → fails (gate 8 can't locate the built page)
python3 -c "import json;d=json.load(open('$TMP/screens.json'));d['screens'][0].pop('route');json.dump(d,open('$TMP/sc_route.json','w'))"
python3 "$SCRIPTS_DIR/validate_screens.py" "$TMP/sc_route.json" "$TMP/flows.json" >/dev/null 2>&1 && bad "Must screen without route should fail" || ok "Must screen requires route → exit 1"

# ── T9. Aesthetic gate (Step 2.6) ─────────────────────────────────────────────
echo "[T9] aesthetic gate — valid passes, fake brand + low contrast fails"
# brand library must be vendored for a named_system to resolve
[ -d "$SCRIPTS_DIR/../references/aesthetics/design-systems/library" ] && ok "brand library vendored" || bad "brand library not vendored"
cat > "$TMP/aes_intel.json" <<'PY'
{"design_directives":{"a11y_target":"AA","density_target":4}}
PY
# full identity theme (light + dark) — the bridge must carry the WHOLE look, not just primary
cat > "$TMP/aesthetic.json" <<'PY'
{"meta":{"version":"2"},
 "brief_inference":{"domain":"dev SaaS","audience_tone":"technical","mood_adjective":"precise","motion_depth":"subtle","rationale":"trust+experts → calm engineered system"},
 "direction":{"type":"named_system","name":"linear-app","category":"Productivity & SaaS","spec_ref":"references/aesthetics/design-systems/library/linear-app/DESIGN.md","why_fit":"expert, dense, high trust"},
 "signature":{"border_style":"translucent","elevation":"layered","type_weight":"medium","tracking":"tight"},
 "tokens":{"radius":"0.5rem","font_sans":"Inter, sans-serif","font_mono":"Berkeley Mono, monospace",
   "colors":{
     "light":{"background":"#ffffff","foreground":"#18181b","card":"#ffffff","card-foreground":"#18181b","popover":"#ffffff","popover-foreground":"#18181b","primary":"#4338ca","primary-foreground":"#ffffff","secondary":"#f4f4f5","secondary-foreground":"#18181b","muted":"#f4f4f5","muted-foreground":"#52525b","accent":"#eef2ff","accent-foreground":"#3730a3","destructive":"#dc2626","border":"#e4e4e7","input":"#e4e4e7","ring":"#4338ca"},
     "dark":{"background":"#08090a","foreground":"#f7f8f8","card":"#0f1011","card-foreground":"#f7f8f8","popover":"#0f1011","popover-foreground":"#f7f8f8","primary":"#7170ff","primary-foreground":"#0f1011","secondary":"#191a1b","secondary-foreground":"#f7f8f8","muted":"#191a1b","muted-foreground":"#8a8f98","accent":"#28282c","accent-foreground":"#f7f8f8","destructive":"#ef4444","border":"#23252a","input":"#28282c","ring":"#7170ff"}}},
 "contrast_checks":[
   {"pair":"foreground/background","fg_hex":"#18181b","bg_hex":"#ffffff"},
   {"pair":"primary-foreground/primary","fg_hex":"#ffffff","bg_hex":"#4338ca"},
   {"pair":"card-foreground/card","fg_hex":"#18181b","bg_hex":"#ffffff"},
   {"pair":"secondary-foreground/secondary","fg_hex":"#18181b","bg_hex":"#f4f4f5"},
   {"pair":"muted-foreground/background","fg_hex":"#52525b","bg_hex":"#ffffff"},
   {"pair":"accent-foreground/accent","fg_hex":"#3730a3","bg_hex":"#eef2ff"}],
 "constraints":{"a11y_target":"AA","density_target":4,"dark_mode":true},
 "brand_config":{"project_name":"Devflow","radius":"0.5rem","font_sans":"Inter, sans-serif","font_mono":"Berkeley Mono, monospace",
   "colors":{
     "light":{"background":"#ffffff","foreground":"#18181b","card":"#ffffff","card-foreground":"#18181b","popover":"#ffffff","popover-foreground":"#18181b","primary":"#4338ca","primary-foreground":"#ffffff","secondary":"#f4f4f5","secondary-foreground":"#18181b","muted":"#f4f4f5","muted-foreground":"#52525b","accent":"#eef2ff","accent-foreground":"#3730a3","destructive":"#dc2626","border":"#e4e4e7","input":"#e4e4e7","ring":"#4338ca"},
     "dark":{"background":"#08090a","foreground":"#f7f8f8","card":"#0f1011","card-foreground":"#f7f8f8","popover":"#0f1011","popover-foreground":"#f7f8f8","primary":"#7170ff","primary-foreground":"#0f1011","secondary":"#191a1b","secondary-foreground":"#f7f8f8","muted":"#191a1b","muted-foreground":"#8a8f98","accent":"#28282c","accent-foreground":"#f7f8f8","destructive":"#ef4444","border":"#23252a","input":"#28282c","ring":"#7170ff"}}}}
PY
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aesthetic.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && ok "valid aesthetic (full identity) → exit 0" || bad "valid aesthetic should pass"
# narrow theme (primary only, no identity set) must now FAIL — the anti-'plain' fix
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['tokens']={'primary':'#4338ca','background':'#fff','foreground':'#111','radius':'0.5rem','font_sans':'Inter'};d['brand_config']={'project_name':'X','primary':'#4338ca','radius':'0.5rem','font_sans':'Inter'};json.dump(d,open('$TMP/aes_narrow.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_narrow.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "narrow (primary-only) theme should fail" || ok "full identity set required → exit 1 (anti-plain)"
# fake brand must fail (does not resolve in the vendored library)
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['direction']['name']='totally-made-up';json.dump(d,open('$TMP/aes_brand.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_brand.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "fake brand should fail" || ok "named_system must resolve in library → exit 1"
# contrast computed from hex must gate (light-gray foreground on white → fails)
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['contrast_checks'][0]['fg_hex']='#c9cdd3';json.dump(d,open('$TMP/aes_contrast.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_contrast.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "low contrast should fail" || ok "contrast recomputed from hex enforced → exit 1"
# a11y_target must echo design_directives
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['constraints']['a11y_target']='AAA';json.dump(d,open('$TMP/aes_a11y.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_a11y.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && bad "a11y mismatch should fail" || ok "a11y_target must equal directive → exit 1"
# optional token-contract check: tokens must be ⊆ the DS contract (passed as 3rd arg)
cat > "$TMP/contract.json" <<'PY'
{"package":"@npsin-oreo/design-system","color_tokens":["background","foreground","card","card-foreground","popover","popover-foreground","primary","primary-foreground","secondary","secondary-foreground","muted","muted-foreground","accent","accent-foreground","destructive","border","input","ring"],"scalar_tokens":["radius","font_sans","font_mono"]}
PY
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aesthetic.json" "$TMP/aes_intel.json" "$TMP/contract.json" >/dev/null 2>&1 && ok "tokens ⊆ contract → exit 0" || bad "valid tokens within contract should pass"
python3 -c "import json;d=json.load(open('$TMP/aesthetic.json'));d['tokens']['glow_accent']='oklch(0.7 0.2 30)';json.dump(d,open('$TMP/aes_contract_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_aesthetic.py" "$TMP/aes_contract_bad.json" "$TMP/aes_intel.json" "$TMP/contract.json" >/dev/null 2>&1 && bad "token outside contract should fail" || ok "token not in DS contract → exit 1 (BLOCKED)"

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
# --strict: the same clean prototype has no artifacts beside it, so gates 6-11 skip — under
# --strict a skipped gate counts as a failure, so this must BLOCK (guards the silent-skip gap).
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA --strict >/dev/null 2>&1 && bad "--strict should block when artifact-backed gates are skipped" || ok "--strict turns skipped gates into a block → exit 1 (BLOCKED)"
# finalize-prototype.sh wrapper: --no-strict on the clean prototype (no critique/usability
# artifacts) chains the gates and passes; default (strict) blocks on the skipped gates.
if [ -f "$SCRIPTS_DIR/finalize-prototype.sh" ]; then
  bash "$SCRIPTS_DIR/finalize-prototype.sh" "$PROTO" --a11y AA --no-strict >/dev/null 2>&1 && ok "finalize-prototype --no-strict → all gates pass (exit 0)" || bad "finalize-prototype --no-strict should pass on the clean prototype"
  bash "$SCRIPTS_DIR/finalize-prototype.sh" "$PROTO" --a11y AA >/dev/null 2>&1 && bad "finalize-prototype (strict default) should block on skipped gates" || ok "finalize-prototype default is strict → exit 1 (BLOCKED)"
fi
# inject a hardcoded hex + a raw palette utility → token gate must block
cat > "$PROTO/app/bad.tsx" <<'TSX'
export const C = () => <div style={{ color: "#ff0000" }} className="bg-gray-500">x</div>;
TSX
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA >/dev/null 2>&1 && bad "hardcode should block" || ok "hardcoded hex + bg-gray-500 → exit 1 (BLOCKED)"
rm -f "$PROTO/app/bad.tsx"
# emoji in UI copy → ux-writing gate (gate 3) must block
printf 'export const E = () => <button>Launch \xf0\x9f\x9a\x80</button>;\n' > "$PROTO/app/emoji.tsx"
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA >/dev/null 2>&1 && bad "emoji should block" || ok "emoji in UI copy → exit 1 (BLOCKED)"
rm -f "$PROTO/app/emoji.tsx"
# vendored DS internals (components/ui) must be auto-excluded — a hardcode there does NOT block,
# but --include-vendored re-includes it and DOES block.
mkdir -p "$PROTO/components/ui"
printf 'export const V = () => <div style={{ color: "#abcabc" }}>x \xf0\x9f\x9a\x80</div>;\n' > "$PROTO/components/ui/fake.tsx"
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA >/dev/null 2>&1 && ok "components/ui auto-excluded → still PASS" || bad "vendored components/ui should be auto-excluded"
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO" --a11y AA --include-vendored >/dev/null 2>&1 && bad "--include-vendored should block on the vendored hardcode" || ok "--include-vendored re-includes DS → exit 1 (BLOCKED)"
rm -rf "$PROTO/components/ui"
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
# gate 6 — theme fidelity: a committed brand.config theme must actually be applied in globals.css
PF="$TMP/protoF"; mkdir -p "$PF/app"
printf '<div className="bg-card text-foreground p-4">Hello</div>\n' > "$PF/app/page.tsx"
cat > "$PF/brand.config.json" <<'PY'
{"project_name":"Devflow","radius":"0.5rem","font_sans":"Inter",
 "colors":{"light":{"background":"oklch(1 0 0)","foreground":"oklch(0.2 0 0)","card":"oklch(1 0 0)","card-foreground":"oklch(0.2 0 0)","primary":"oklch(0.45 0.2 264)","primary-foreground":"oklch(1 0 0)","secondary":"oklch(0.96 0 0)","secondary-foreground":"oklch(0.2 0 0)","muted":"oklch(0.96 0 0)","muted-foreground":"oklch(0.45 0 0)","accent":"oklch(0.9 0.05 264)","accent-foreground":"oklch(0.3 0.12 264)","border":"oklch(0.9 0 0)"}}}
PY
faithful_css() { cat > "$PF/app/globals.css" <<'CSS'
:root {
  --background: oklch(1 0 0); --foreground: oklch(0.2 0 0);
  --card: oklch(1 0 0); --card-foreground: oklch(0.2 0 0);
  --primary: oklch(0.45 0.2 264); --primary-foreground: oklch(1 0 0);
  --secondary: oklch(0.96 0 0); --secondary-foreground: oklch(0.2 0 0);
  --muted: oklch(0.96 0 0); --muted-foreground: oklch(0.45 0 0);
  --accent: oklch(0.9 0.05 264); --accent-foreground: oklch(0.3 0.12 264);
  --border: oklch(0.9 0 0);
}
CSS
}
faithful_css
# the fixture's brand.config commits font_sans:"Inter" → apply it so gate 10 (font fidelity) is satisfied,
# keeping this case focused on gate 6 (theme colour fidelity).
printf 'import { Inter } from "next/font/google";\nconst f = Inter({ variable: "--font-sans" });\n' > "$PF/app/layout.tsx"
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PF" --a11y AA >/dev/null 2>&1 && ok "committed theme applied → fidelity PASS (exit 0)" || bad "faithful theme should pass gate 6"
# regress --primary to a neutral gray (still high contrast) — only fidelity should catch it
faithful_css; python3 -c "import re,io;p='$PF/app/globals.css';s=open(p).read().replace('--primary: oklch(0.45 0.2 264)','--primary: oklch(0.3 0 0)').replace('--accent: oklch(0.9 0.05 264)','--accent: oklch(0.92 0 0)');open(p,'w').write(s)"
python3 "$SCRIPTS_DIR/audit_prototype.py" "$PF" --a11y AA >/dev/null 2>&1 && bad "neutral regression should block on fidelity" || ok "primary/accent regressed to neutral → exit 1 (BLOCKED by gate 6)"
# gate 6 extended (Phase 3): a committed semantic token (warning) missing from globals.css must block
faithful_css
SEMTHEME="$TMP/sem_theme.json"
python3 -c "import json;d=json.load(open('$PF/brand.config.json'));d['colors']['light']['warning']='#f5a623';d['colors']['light']['warning-foreground']='#0d0d0d';json.dump(d,open('$SEMTHEME','w'))"
python3 "$SCRIPTS_DIR/lint_theme_fidelity.py" "$PF/app/globals.css" "$SEMTHEME" >/dev/null 2>&1 && bad "committed warning missing from globals should block" || ok "extended semantic committed but not applied → blocked (gate 6)"
# add the token to globals → passes again
python3 -c "p='$PF/app/globals.css';s=open(p).read().replace('--border: oklch(0.9 0 0);','--border: oklch(0.9 0 0); --warning: #f5a623; --warning-foreground: #0d0d0d;');open(p,'w').write(s)"
python3 "$SCRIPTS_DIR/lint_theme_fidelity.py" "$PF/app/globals.css" "$SEMTHEME" >/dev/null 2>&1 && ok "extended semantic applied → exit 0" || bad "applied semantic token wrongly blocked"
faithful_css
# gate 7 — directive fidelity: build must honor safeguard_level / guidance_level
GD="$TMP/protoG"; mkdir -p "$GD/app/users"
printf '{"design_directives":{"safeguard_level":"strict","guidance_level":"guided","density_target":2,"navigation_model":"single"}}' > "$GD/intelligence.json"
printf 'export default function P(){return <div><AlertDialog/><Empty/><button variant="destructive" onDelete={handleDelete}>Delete</button></div>}\n' > "$GD/app/users/page.tsx"
python3 "$SCRIPTS_DIR/lint_directive_fidelity.py" "$GD" "$GD/intelligence.json" >/dev/null 2>&1 && ok "directives honored (confirm+empty present) → exit 0" || bad "honored directives should pass gate 7"
printf 'export default function P(){return <div><Empty/><button variant="destructive" onDelete={handleDelete}>Delete</button></div>}\n' > "$GD/app/users/page.tsx"
python3 "$SCRIPTS_DIR/lint_directive_fidelity.py" "$GD" "$GD/intelligence.json" >/dev/null 2>&1 && bad "destructive w/o confirm should fail" || ok "safeguard: destructive needs AlertDialog → exit 1 (gate 7)"
# gate 8 — screen coverage: every Must screen built as a route with its states
SG="$TMP/protoS"; mkdir -p "$SG/app/dashboard"
printf '{"screens":[{"id":"S1","name":"Dashboard","route":"dashboard","priority":"Must","states":["empty"]}]}' > "$SG/screen-inventory.json"
printf 'export default function P(){return <Empty>Nothing here yet</Empty>}\n' > "$SG/app/dashboard/page.tsx"
python3 "$SCRIPTS_DIR/lint_screen_coverage.py" "$SG" "$SG/screen-inventory.json" >/dev/null 2>&1 && ok "Must screen built with empty state → exit 0" || bad "built screen should pass gate 8"
rm -rf "$SG/app/dashboard"
python3 "$SCRIPTS_DIR/lint_screen_coverage.py" "$SG" "$SG/screen-inventory.json" >/dev/null 2>&1 && bad "missing Must route should fail" || ok "Must screen not built → exit 1 (gate 8)"
# wired into audit_prototype: intelligence.json beside prototype is picked up
# (capture into a var — piping to `grep -q` + pipefail makes the SIGPIPE'd python fail the pipeline)
AUD_OUT="$(python3 "$SCRIPTS_DIR/audit_prototype.py" "$GD" --a11y AA 2>&1)"
case "$AUD_OUT" in *"directive=FAIL"*) ok "audit_prototype runs gate 7 (directive)";; *) bad "gate 7 not wired into audit_prototype";; esac
# Step 4.7b runtime audit — scripts present; orchestrator degrades gracefully (no Playwright → exit 0)
RT="$SCRIPTS_DIR/../references/runtime-audit/scripts"
[ -f "$RT/audit_runtime.mjs" ] && [ -f "$RT/axe_audit.mjs" ] && [ -f "$RT/verify_states.mjs" ] && ok "runtime-audit scripts vendored" || bad "runtime-audit scripts missing"
if command -v node >/dev/null 2>&1; then
  for s in audit_runtime axe_audit verify_states verify_focustrap taste_audit; do node --check "$RT/$s.mjs" 2>/dev/null || bad "runtime script $s.mjs syntax"; done
  echo '<!doctype html><html lang="en"><head><title>x</title></head><body><button>Go</button></body></html>' > "$TMP/rt.html"
  node "$RT/audit_runtime.mjs" "$TMP/rt.html" >/dev/null 2>&1 && ok "runtime audit skips cleanly w/o Playwright → exit 0" || bad "runtime audit should skip (exit 0) without Playwright"
else
  ok "node absent — runtime-audit syntax/skip checks N/A"
fi

# ── T11. Folded skills — DTCG token foundation gates (brandkit) ───────────────
echo "[T11] brandkit/DTCG gates + folded-skill assets present"
REFS="$SCRIPTS_DIR/../references"
[ -f "$REFS/ux-writing/voice-tone.md" ] && ok "ux-writing vendored" || bad "ux-writing missing"
[ -f "$REFS/image-to-code.md" ] && [ -f "$REFS/brandkit.md" ] && [ -f "$REFS/migrate-design-system.md" ] && ok "image-to-code/brandkit/migrate refs present" || bad "folded-skill refs missing"
[ -f "$REFS/performance.md" ] && [ -f "$REFS/governance.md" ] && [ -f "$REFS/SKILLS.md" ] && ok "performance/governance/SKILLS index present" || bad "capability docs missing"
[ -f "$REFS/mobile-usability.md" ] && ok "mobile-usability reference present" || bad "mobile-usability.md missing"
if [ -f "$REFS/tokens/scripts/validate_tokens.py" ]; then
  python3 "$REFS/tokens/scripts/validate_tokens.py" >/dev/null 2>&1 && ok "DTCG validate_tokens → exit 0" || bad "DTCG tokens should be valid"
  python3 "$REFS/tokens/scripts/validate_contrast.py" >/dev/null 2>&1 && ok "DTCG validate_contrast → exit 0" || bad "DTCG required contrast should pass"
else
  bad "DTCG token kit not vendored"
fi

# ── T12. UX layers — User Research / Competitive / Usability honesty gates ────
echo "[T12] UX layers (2.3 research · 2.4 competitive · 4.8 usability)"
[ -f "$REFS/user-research-layer.md" ] && [ -f "$REFS/competitive-analysis-layer.md" ] && [ -f "$REFS/usability-test-layer.md" ] && ok "UX layer references present" || bad "UX layer references missing"

# research — valid (inferred mode) passes; fabricated evidence fails
cat > "$TMP/research.json" <<'JSON'
{ "meta": { "schema_version": "1.0", "evidence_mode": "inferred", "inputs_provided": [], "overall_confidence": "medium" },
  "personas": [{ "id": "P01", "name": "Op", "primary": true, "tech_proficiency": "intermediate", "goals_ref": ["JTBD01"], "source": "inferred", "evidence": [], "confidence": "medium" }],
  "jobs_to_be_done": [{ "id": "JTBD01", "persona_ref": "P01", "when": "a", "want": "b", "so_that": "c", "priority": "must", "source": "inferred", "evidence": [], "confidence": "medium" }],
  "pain_points": [], "behavioral_assumptions": [], "research_questions": [], "feeds_intelligence": {} }
JSON
python3 "$SCRIPTS_DIR/validate_research.py" "$TMP/research.json" >/dev/null 2>&1 && ok "valid research (inferred) → exit 0" || bad "valid research should pass"
python3 -c "import json;d=json.load(open('$TMP/research.json'));d['personas'][0]['source']='evidence';d['personas'][0]['evidence']=['x:ghost'];json.dump(d,open('$TMP/research_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_research.py" "$TMP/research_bad.json" >/dev/null 2>&1 && bad "fabricated evidence should fail" || ok "evidence not in inputs_provided → exit 1 (BLOCKED)"

# competitive — valid passes; convention 'break' without reason fails
cat > "$TMP/competitive.json" <<'JSON'
{ "meta": { "schema_version": "1.0", "evidence_mode": "inferred", "inputs_provided": [], "overall_confidence": "medium" },
  "competitors": [{ "id": "CMP01", "name": "Rival", "type": "direct", "source": "inferred", "evidence": [], "confidence": "medium" }],
  "feature_benchmark": [], "ux_pattern_conventions": [{ "id": "PC01", "pattern": "left-nav", "convention": "follow", "source": "inferred", "evidence": [], "confidence": "low" }],
  "differentiation": [], "table_stakes": [], "feeds": {} }
JSON
python3 "$SCRIPTS_DIR/validate_competitive.py" "$TMP/competitive.json" >/dev/null 2>&1 && ok "valid competitive (inferred) → exit 0" || bad "valid competitive should pass"
python3 -c "import json;d=json.load(open('$TMP/competitive.json'));d['ux_pattern_conventions'][0]['convention']='break';json.dump(d,open('$TMP/competitive_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_competitive.py" "$TMP/competitive_bad.json" >/dev/null 2>&1 && bad "break w/o reason should fail" || ok "convention break needs reason → exit 1 (BLOCKED)"

# usability — valid passes; claiming a real test fails
cat > "$TMP/usability.json" <<'JSON'
{ "meta": { "schema_version": "1.0", "not_real_user_testing": true, "methods_used": ["heuristic"], "overall_confidence": "medium", "human_validation_required": true },
  "heuristic_findings": [{ "id": "H01", "heuristic": "Status", "screen": "x", "severity": 1, "issue": "i", "recommendation": "r", "method": "heuristic", "evidence": "", "confidence": "medium" }],
  "persona_walkthroughs": [], "severity_summary": {}, "top_issues": [], "limitations": ["no real participants"] }
JSON
python3 "$SCRIPTS_DIR/validate_usability.py" "$TMP/usability.json" >/dev/null 2>&1 && ok "valid usability (simulated) → exit 0" || bad "valid usability should pass"
python3 -c "import json;d=json.load(open('$TMP/usability.json'));d['meta']['not_real_user_testing']=False;json.dump(d,open('$TMP/usability_bad.json','w'))"
python3 "$SCRIPTS_DIR/validate_usability.py" "$TMP/usability_bad.json" >/dev/null 2>&1 && bad "fake real test should fail" || ok "not_real_user_testing must be true → exit 1 (BLOCKED)"

# ── T13. setup-prototype — Model A import-only (no vendored/rsync path) ────────
echo "[T13] setup-prototype — import-only (no copy/rsync, token hard-required)"
SETUP="$SCRIPTS_DIR/setup-prototype.sh"
bash -n "$SETUP" 2>/dev/null && ok "setup-prototype.sh parses (bash -n)" || bad "setup-prototype.sh syntax error"
# import is the ONLY mode — the vendored/copy flags + rsync path must be GONE
grep -q -- '--ds-auto' "$SETUP" || grep -q 'rsync' "$SETUP" && bad "vendored/rsync path still present (should be import-only)" || ok "no --ds-auto / rsync path (import-only)"
grep -q '_authToken' "$SETUP" && grep -q 'DS_REGISTRY' "$SETUP" && ok "scaffold .npmrc (scope → registry) wired" || bad "scaffold .npmrc wiring missing"
# token is HARD-required (no fallback)
grep -q 'GITHUB_TOKEN is required' "$SETUP" && grep -q 'NEEDS_TOKEN' "$SETUP" && ok "GITHUB_TOKEN hard-required (no fallback)" || bad "token requirement not enforced"
# default pkg pinned to a published version + exact install
grep -qE 'DS_VERSION="[0-9]' "$SETUP" && grep -qE 'IMPORT_PKG="@npsin-oreo/design-system@\$\{DS_VERSION\}"' "$SETUP" && ok "default import pkg pinned (no floating latest)" || bad "default DS version not pinned"
grep -q -- '--save-exact' "$SETUP" && ok "DS installed with --save-exact (reproducible)" || bad "--save-exact missing"
# scaffold owns cn (package doesn't export it) + the @/* path alias
grep -q 'lib/utils.ts' "$SETUP" && grep -q 'twMerge' "$SETUP" && ok "scaffolds local cn (lib/utils.ts)" || bad "cn scaffold missing"
grep -q '"@/\*": \["./\*"\]' "$SETUP" && ok "scaffold tsconfig has @/* path alias" || bad "@/* path alias missing"
grep -q 'dependency confusion' "$SETUP" && ok "dependency-confusion note on scope→registry binding" || bad "dependency-confusion guard note missing"
# Tailwind v4 auto-source-detection must NOT scan binary dirs (webp/png in public, next/image
# cache in .next) — else it emits garbage classes and Turbopack/Lightning CSS 500s on every route.
grep -q '@source not "../public"' "$SETUP" && ok "globals.css excludes public/ from Tailwind scan (gotcha #2)" || bad "missing @source not ../public (binary scan trap)"
grep -q '@source not "../.next"' "$SETUP" && ok "globals.css excludes .next/ from Tailwind scan (gotcha #3)" || bad "missing @source not ../.next (next/image cache binary scan trap)"
grep -q '\.gitignore' "$SETUP" && grep -qE '/\.next/' "$SETUP" && ok "scaffold writes a Next .gitignore (node_modules/.next/out)" || bad "scaffold .gitignore missing"
# behaviour: no token → errors with the export hint (no silent fallback)
OUT="$( (unset GITHUB_TOKEN; bash "$SETUP" --out "$TMP/spA" 2>&1) )"; rm -rf "$TMP/spA"
echo "$OUT" | grep -q 'GITHUB_TOKEN is required' && ok "no token → hard error (not fallback)" || bad "missing token should hard-error"

# ── T14. Step 5 Figma output spec + figma_prep ────────────────────────────────
echo "[T14] Step 5 Figma — spec/recipes present + figma_prep runs"
FG="$REFS/figma"
for f in output-spec 01-variables 02-components 03-screens 04-flows mcp-gotchas; do
  [ -f "$FG/$f.md" ] || bad "missing references/figma/$f.md"
done
[ -f "$FG/output-spec.md" ] && [ -f "$FG/mcp-gotchas.md" ] && ok "figma spec + recipes + gotchas present" || bad "figma references incomplete"
python3 -c "import ast,sys; ast.parse(open('$SCRIPTS_DIR/figma_prep.py').read())" 2>/dev/null && ok "figma_prep.py parses" || bad "figma_prep.py syntax error"
# minimal fixtures
cat > "$TMP/tok.json" <<'JSON'
{"$metadata":{"tokenSetOrder":["tw-colors/Mode 1","brand-color/Mode 1","tokens/Mode 1"]},
"tw-colors/Mode 1":{"pink":{"700":{"$value":"#be185d","$type":"color"}},"white":{"$value":"#ffffff","$type":"color"},"gray":{"900":{"$value":"#111827","$type":"color"}}},
"brand-color/Mode 1":{"primary":{"500":{"$value":"#be185d","$type":"color"}},"coral":{"500":{"$value":"#ff0000","$type":"color"}},"cerulean-blue":{"500":{"$value":"#0000ff","$type":"color"}}},
"tokens/Mode 1":{"16":{"$value":"16px","$type":"dimension"},"al":{"$value":"{16}","$type":"dimension"}}}
JSON
echo '{"brand_config":{"primary":"#be185d","font_sans":"Nunito"},"tokens":{"secondary":"#fce7f3"}}' > "$TMP/aes.json"
echo '{"meta":{"platform":"mobile-first"},"screens":[{"id":"SCR1","name":"Home","components":["button","card"]}]}' > "$TMP/scr.json"
echo '{"flows":[{"id":"FL1","name":"A","steps":[{"action":"x"}]}]}' > "$TMP/flw.json"
if python3 "$SCRIPTS_DIR/figma_prep.py" --tokens "$TMP/tok.json" --aesthetic "$TMP/aes.json" --screens "$TMP/scr.json" --flows "$TMP/flw.json" --out "$TMP/fb" >/dev/null 2>&1; then
  ok "figma_prep runs on fixtures → exit 0"
else bad "figma_prep failed on fixtures"; fi
[ -f "$TMP/fb/theme.json" ] && [ -f "$TMP/fb/manifest.json" ] && ok "emits theme.json + manifest.json" || bad "figma_prep outputs missing"
python3 -c "import json,sys; d=json.load(open('$TMP/fb/theme.json')); sys.exit(0 if len(d)==19 else 1)" 2>/dev/null && ok "theme has 19 semantic tokens" || bad "theme token count wrong"
python3 -c "import json,glob,sys; bc=[f for f in glob.glob('$TMP/fb/vars_*brand-color*.json')][0]; items=json.load(open(bc))['items']; n=[i[0] for i in items]; sys.exit(0 if not any('coral' in x or 'cerulean' in x for x in n) and any('primary' in x for x in n) else 1)" 2>/dev/null && ok "brand-color trimmed (no cerulean/coral, keeps primary)" || bad "brand-color trim failed"
python3 -c "import json,sys; m=json.load(open('$TMP/fb/manifest.json')); sys.exit(0 if m['device']['name']=='Mobile' and m['font_default']=='Noto Sans Thai' else 1)" 2>/dev/null && ok "manifest device=Mobile + default font=Noto Sans Thai" || bad "manifest device/font wrong"

# ── T15. validate_critique — judge pattern + score cap (Step 4.6) ─────────────
echo "[T15] validate_critique — judge verdict caps the self-score"
VC="$SCRIPTS_DIR/validate_critique.py"
_crit() { printf '%s' "$1" > "$TMP/crit.json"; }
GOOD_SCREENS='"screens":[{"name":"Booking","score":7.5,"dimensions":{"hierarchy":8,"consistency":8,"a11y":7,"usability":7,"responsiveness":7,"performance":7}}]'
# valid, judge passes
_crit "{\"judge_verdict\":true,\"overall_score\":7.4,$GOOD_SCREENS,\"what_worked\":[\"clear primary action\"]}"
python3 "$VC" "$TMP/crit.json" >/dev/null 2>&1 && ok "valid critique (judge pass) → exit 0" || bad "valid critique rejected"
# judge fails but score stays high → must BLOCK (the cap rule)
_crit "{\"judge_verdict\":false,\"judge_reason\":\"submit dead\",\"overall_score\":7.0,$GOOD_SCREENS}"
python3 "$VC" "$TMP/crit.json" >/dev/null 2>&1 && bad "judge=false + score 7.0 not blocked (cap rule broken)" || ok "judge=false + high score → blocked (cap enforced)"
# judge fails and score honestly capped → exit 0
_crit "{\"judge_verdict\":false,\"judge_reason\":\"submit dead\",\"overall_score\":2.0,$GOOD_SCREENS}"
python3 "$VC" "$TMP/crit.json" >/dev/null 2>&1 && ok "judge=false + score 2.0 → exit 0 (cap satisfied)" || bad "honestly-capped critique rejected"
# judge=false without a reason → block
_crit "{\"judge_verdict\":false,\"overall_score\":2.0,$GOOD_SCREENS}"
python3 "$VC" "$TMP/crit.json" >/dev/null 2>&1 && bad "judge=false without judge_reason not blocked" || ok "judge=false needs judge_reason → blocked"
# missing judge_verdict entirely → block
_crit "{\"overall_score\":7.4,$GOOD_SCREENS}"
python3 "$VC" "$TMP/crit.json" >/dev/null 2>&1 && bad "missing judge_verdict not blocked" || ok "missing judge_verdict → blocked"
# out-of-range dimension score → block
_crit "{\"judge_verdict\":true,\"overall_score\":7.4,\"screens\":[{\"name\":\"X\",\"score\":7,\"dimensions\":{\"hierarchy\":11,\"consistency\":8,\"a11y\":7,\"usability\":7,\"responsiveness\":7,\"performance\":7}}]}"
python3 "$VC" "$TMP/crit.json" >/dev/null 2>&1 && bad "dimension score 11 not blocked" || ok "dimension score out of 1..10 → blocked"

# ── T16. validate_edgecases — front edge-case spine (Step 3.7) ────────────────
echo "[T16] validate_edgecases — traceability + directive floors"
VE="$SCRIPTS_DIR/validate_edgecases.py"
cat > "$TMP/ec_scr.json" <<'JSON'
{"meta":{},"screens":[
 {"id":"SCR_BOOK","name":"Booking","priority":"Must","layout_primitive":"form","flow_refs":["FL_BOOK"],"states":["error","empty"],"components":["form"],"route":"/book"},
 {"id":"SCR_DASH","name":"Dashboard","priority":"Must","layout_primitive":"dashboard","flow_refs":["FL_BOOK"],"states":["empty","error"],"components":["chart"],"route":"/dash"}]}
JSON
cat > "$TMP/ec_flw.json" <<'JSON'
{"navigation_model":"hub_spoke","flows":[{"id":"FL_BOOK","name":"Book","steps":[{"action":"x"}]}]}
JSON
cat > "$TMP/ec_intel.json" <<'JSON'
{"data_density":{"overall_band":5},"error_tolerance":{"overall":"zero"},"decision_criticality":{"overall":"safety_critical"},"design_directives":{"guidance_level":"guided","safeguard_level":"strict"}}
JSON
cat > "$TMP/ec_good.json" <<'JSON'
{"meta":{},"edge_cases":[
 {"id":"EC1","ui_state":"error","correct_dim":"reference","category":"network","trigger":"API 502","expected_handling":"error + retry, keep values","severity":"must","maps_to_screen":"SCR_BOOK","maps_to_flow":"FL_BOOK"},
 {"id":"EC2","ui_state":"error","correct_dim":"conformance","category":"validation","trigger":"bad phone","expected_handling":"inline FieldError + aria-invalid","severity":"must","maps_to_screen":"SCR_BOOK"},
 {"id":"EC3","ui_state":"empty","correct_dim":"existence","category":"data","trigger":"no appts","expected_handling":"empty state + primary action","severity":"must","maps_to_screen":"SCR_BOOK"},
 {"id":"EC4","ui_state":"error","correct_dim":"reference","category":"network","trigger":"dash load fail","expected_handling":"error + retry","severity":"must","maps_to_screen":"SCR_DASH"},
 {"id":"EC5","ui_state":"empty","correct_dim":"existence","category":"data","trigger":"new user","expected_handling":"empty state + book CTA","severity":"must","maps_to_screen":"SCR_DASH"},
 {"id":"EC6","ui_state":"partial","correct_dim":"cardinality","category":"data","trigger":"100s rows","expected_handling":"truncate + show more","severity":"must","maps_to_screen":"SCR_DASH"},
 {"id":"EC7","ui_state":"error","correct_dim":"time","category":"destructive","trigger":"cancel appt","expected_handling":"type-to-confirm; undo within 5s","severity":"must","maps_to_screen":"SCR_BOOK"}]}
JSON
python3 "$VE" "$TMP/ec_good.json" "$TMP/ec_scr.json" "$TMP/ec_flw.json" "$TMP/ec_intel.json" >/dev/null 2>&1 && ok "valid full edge-case set (all floors satisfied) → exit 0" || bad "valid edge-case set rejected"
# standalone — no cross-files → structure only, exit 0
python3 "$VE" "$TMP/ec_good.json" >/dev/null 2>&1 && ok "standalone (no artifacts) → graceful exit 0" || bad "standalone run failed"
# orphan maps_to_screen → block
echo '{"edge_cases":[{"id":"E1","ui_state":"error","severity":"must","expected_handling":"x","maps_to_screen":"NOPE"}]}' > "$TMP/ec_x.json"
python3 "$VE" "$TMP/ec_x.json" "$TMP/ec_scr.json" >/dev/null 2>&1 && bad "orphan maps_to_screen not blocked" || ok "orphan maps_to_screen → blocked"
# bad enums → block
echo '{"edge_cases":[{"id":"E1","ui_state":"glitch","correct_dim":"vibes","severity":"maybe","maps_to_screen":"SCR_BOOK"}]}' > "$TMP/ec_x.json"
python3 "$VE" "$TMP/ec_x.json" "$TMP/ec_scr.json" >/dev/null 2>&1 && bad "bad ui_state/correct_dim/severity not blocked" || ok "bad enums → blocked"
# declared empty/error state with no edge → block (declared states need a reason)
# NB: capture to a var first — under `set -o pipefail`, `python(exit 1) | grep` returns python's
# exit, so a direct pipe would mis-read a correct block as a failure.
echo '{"edge_cases":[{"id":"E1","ui_state":"loading","category":"net","trigger":"x","expected_handling":"spinner","severity":"could","maps_to_screen":"SCR_BOOK"}]}' > "$TMP/ec_x.json"
OUT="$(python3 "$VE" "$TMP/ec_x.json" "$TMP/ec_scr.json" 2>&1)"
echo "$OUT" | grep -q "declares state" && ok "declared state with no edge → blocked" || bad "declared-state-needs-reason not enforced"
# directive floor: zero error_tolerance forces a must input-validation edge on input screens.
# Provide the error edge (satisfies the error floor) but NO validation edge, so the message under
# test is the validation one specifically.
echo '{"edge_cases":[{"id":"E1","ui_state":"error","correct_dim":"reference","category":"network","trigger":"x","expected_handling":"err+retry","severity":"must","maps_to_screen":"SCR_BOOK"}]}' > "$TMP/ec_x.json"
OUT="$(python3 "$VE" "$TMP/ec_x.json" "$TMP/ec_scr.json" "$TMP/ec_flw.json" "$TMP/ec_intel.json" 2>&1)"
echo "$OUT" | grep -q "input-validation edge" && ok "error_tolerance=zero floor (validation edge) → blocked" || bad "error_tolerance floor not enforced"
# directive floor: high criticality forces destructive edge to must → block when 'should'
echo '{"edge_cases":[{"id":"E1","ui_state":"error","category":"destructive","trigger":"x","expected_handling":"confirm","severity":"should","maps_to_screen":"SCR_BOOK"}]}' > "$TMP/ec_x.json"
echo '{"data_density":{"overall_band":2},"error_tolerance":{"overall":"high"},"decision_criticality":{"overall":"high"},"design_directives":{"guidance_level":"expert","safeguard_level":"standard"}}' > "$TMP/ec_hi.json"
OUT="$(python3 "$VE" "$TMP/ec_x.json" "$TMP/ec_scr.json" "$TMP/ec_flw.json" "$TMP/ec_hi.json" 2>&1)"
echo "$OUT" | grep -q "destructive edge" && ok "criticality=high floor (destructive→must) → blocked" || bad "destructive floor not enforced"

# ── T17. lint_edge_coverage — gate 9 (back end of the edge-case spine) ─────────
echo "[T17] lint_edge_coverage — Must edge must be handled in the built screen"
LEC="$SCRIPTS_DIR/lint_edge_coverage.py"
PROTO9="$TMP/proto9"; mkdir -p "$PROTO9/app/book" "$PROTO9/app/dash"
cat > "$TMP/c9_scr.json" <<'JSON'
{"meta":{},"screens":[
 {"id":"SCR_BOOK","name":"Booking","priority":"Must","layout_primitive":"form","route":"/book"},
 {"id":"SCR_DASH","name":"Dashboard","priority":"Must","layout_primitive":"dashboard","route":"/dash"}]}
JSON
cat > "$TMP/c9_edges.json" <<'JSON'
{"edge_cases":[
 {"id":"EC1","ui_state":"error","correct_dim":"conformance","category":"validation","severity":"must","expected_handling":"x","maps_to_screen":"SCR_BOOK"},
 {"id":"EC2","ui_state":"empty","category":"data","severity":"must","expected_handling":"x","maps_to_screen":"SCR_DASH"},
 {"id":"EC3","ui_state":"error","category":"destructive","severity":"must","expected_handling":"x","maps_to_screen":"SCR_BOOK"}]}
JSON
printf 'export default function P(){return <form><FieldError/><input aria-invalid/><AlertDialog>cannot be undone</AlertDialog></form>}' > "$PROTO9/app/book/page.tsx"
printf 'export default function P(){return <div>charts only</div>}' > "$PROTO9/app/dash/page.tsx"
# DASH has no empty state → block
python3 "$LEC" "$PROTO9" "$TMP/c9_edges.json" "$TMP/c9_scr.json" >/dev/null 2>&1 && bad "missing empty-state handling not blocked" || ok "Must empty edge unhandled → blocked (gate 9)"
# add the empty state → pass
printf 'export default function P(){return <div>No data yet. Get started.</div>}' > "$PROTO9/app/dash/page.tsx"
python3 "$LEC" "$PROTO9" "$TMP/c9_edges.json" "$TMP/c9_scr.json" >/dev/null 2>&1 && ok "all Must edges handled (validation+confirm+empty) → exit 0" || bad "handled edges wrongly blocked"
# should/could edges never block (only must)
echo '{"edge_cases":[{"id":"E1","ui_state":"partial","category":"data","severity":"should","expected_handling":"x","maps_to_screen":"SCR_DASH"}]}' > "$TMP/c9_x.json"
python3 "$LEC" "$PROTO9" "$TMP/c9_x.json" "$TMP/c9_scr.json" >/dev/null 2>&1 && ok "should/could edge → never blocks" || bad "non-must edge should not block"
# audit_prototype wires gate 9 (edges= in summary)
echo "$(python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO9" --edges "$TMP/c9_edges.json" --screens "$TMP/c9_scr.json" 2>&1)" | grep -q "edges=" && ok "audit_prototype reports gate 9 (edges=)" || bad "gate 9 not wired into audit_prototype"

# ── T18. lint_font_fidelity — gate 10 (committed font actually applied) ───────
echo "[T18] lint_font_fidelity — committed font_sans must reach the build"
LFF="$SCRIPTS_DIR/lint_font_fidelity.py"
PROTO10="$TMP/proto10"; mkdir -p "$PROTO10/app"
echo '{"project_name":"X","font_sans":"\"Inter\", \"Noto Sans Thai\", sans-serif","radius":"0.5rem"}' > "$TMP/bc10.json"
# build still on the default font → block
printf 'import { Geist } from "next/font/google";\nconst f = Geist({ variable: "--font-sans" });\n' > "$PROTO10/app/layout.tsx"
printf ':root { --font-sans: var(--font-sans); }\n' > "$PROTO10/app/globals.css"
python3 "$LFF" "$PROTO10" "$TMP/bc10.json" >/dev/null 2>&1 && bad "font no-op (Geist) not blocked" || ok "committed Inter absent from build → blocked (gate 10)"
# build loads the committed family → pass
printf 'import { Inter, Noto_Sans_Thai } from "next/font/google";\nconst f = Inter({ variable: "--font-sans" });\n' > "$PROTO10/app/layout.tsx"
python3 "$LFF" "$PROTO10" "$TMP/bc10.json" >/dev/null 2>&1 && ok "committed Inter applied in layout → exit 0" || bad "applied font wrongly blocked"
# no font_sans committed → skip cleanly (exit 0)
echo '{"project_name":"X","radius":"0.5rem"}' > "$TMP/bc10b.json"
python3 "$LFF" "$PROTO10" "$TMP/bc10b.json" >/dev/null 2>&1 && ok "no font_sans committed → graceful skip" || bad "no-font theme should skip, not block"
# audit wires gate 10 (fontfid= in summary)
echo "$(python3 "$SCRIPTS_DIR/audit_prototype.py" "$PROTO10" --theme "$TMP/bc10.json" 2>&1)" | grep -q "fontfid=" && ok "audit_prototype reports gate 10 (fontfid=)" || bad "gate 10 not wired into audit_prototype"

# ── T19. validate_aesthetic — axes composition (coherence gate) ───────────────
echo "[T19] validate_aesthetic — per-axis composition + coherence cap"
VA="$SCRIPTS_DIR/validate_aesthetic.py"
# builds $TMP/aesthetic.json (direction.name=linear-app) earlier; inject an axes block N ways.
_axes() {  # $1 = python dict literal for d['axes'] ; $2 = primary_system
  python3 -c "
import json,sys
d=json.load(open('$TMP/aesthetic.json'))
d['primary_system']='$2'
d['axes']=$1
json.dump(d,open('$TMP/aes_axes.json','w'))"
}
R='"rationale":"fits"'
# all six axes from the primary (linear-app) → coherent, exit 0
_axes "{ax:{'source':'linear-app',$R} for ax in ['color','typography','shape','elevation','spacing','motion']}" "linear-app"
python3 "$VA" "$TMP/aes_axes.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && ok "single-system axes (all linear-app) → exit 0" || bad "coherent single-system axes rejected"
# one justified override from a 2nd real system (openai) → 2 systems, within cap, exit 0
_axes "{**{ax:{'source':'linear-app',$R} for ax in ['color','shape','elevation','spacing','motion']}, 'typography':{'source':'openai',$R}}" "linear-app"
python3 "$VA" "$TMP/aes_axes.json" "$TMP/aes_intel.json" >/dev/null 2>&1 && ok "one justified override (2 systems) → exit 0" || bad "a justified 2-system composition should pass"
# THREE systems → coherence cap blocks
_axes "{**{ax:{'source':'linear-app',$R} for ax in ['color','shape','elevation','spacing']}, 'typography':{'source':'openai',$R}, 'motion':{'source':'clean',$R}}" "linear-app"
OUT="$(python3 "$VA" "$TMP/aes_axes.json" "$TMP/aes_intel.json" 2>&1)"; echo "$OUT" | grep -q "cap is 2" && ok "3 systems → coherence cap blocks" || bad "coherence cap not enforced"
# override with no rationale → blocks
_axes "{**{ax:{'source':'linear-app',$R} for ax in ['color','shape','elevation','spacing','motion']}, 'typography':{'source':'openai'}}" "linear-app"
OUT="$(python3 "$VA" "$TMP/aes_axes.json" "$TMP/aes_intel.json" 2>&1)"; echo "$OUT" | grep -q "must be justified" && ok "override without rationale → blocks" || bad "unjustified override not blocked"
# color axis sourced from a non-palette system → blocks (palette comes from direction.name)
_axes "{**{ax:{'source':'linear-app',$R} for ax in ['typography','shape','elevation','spacing','motion']}, 'color':{'source':'openai',$R}}" "linear-app"
OUT="$(python3 "$VA" "$TMP/aes_axes.json" "$TMP/aes_intel.json" 2>&1)"; echo "$OUT" | grep -q "axes.color.source" && ok "color axis must match direction.name → blocks" || bad "color/direction mismatch not blocked"

# ── T20. lint_axis_fidelity — gate 11 (non-colour axes applied) ───────────────
echo "[T20] lint_axis_fidelity — type/shape/motion axes must reach the build"
LAF="$SCRIPTS_DIR/lint_axis_fidelity.py"
cat > "$TMP/axes_aes.json" <<'JSON'
{"axes":{
 "typography":{"resolved":{"base_line_height":1.65,"heading_weight_cap":600}},
 "shape":{"resolved":{"pill_slots":["badge"]}},
 "motion":{"resolved":{"easing":"cubic-bezier(0.16, 1, 0.3, 1)"}}}}
JSON
# globals with all axes applied → pass
cat > "$TMP/axes_ok.css" <<'CSS'
@theme inline { --text-base--line-height: 1.65; }
@layer base {
  h1, h2, h3 { font-weight: 600; }
  [data-slot="badge"] { @apply rounded-full; }
  :root { --ease-out-soft: cubic-bezier(0.16, 1, 0.3, 1); }
  [data-slot="button"] { transition-timing-function: var(--ease-out-soft); }
}
CSS
python3 "$LAF" "$TMP/axes_ok.css" "$TMP/axes_aes.json" >/dev/null 2>&1 && ok "all axes applied → exit 0" || bad "applied axes wrongly blocked"
# motion easing declared but missing from globals → block
cat > "$TMP/axes_nomotion.css" <<'CSS'
@theme inline { --text-base--line-height: 1.65; }
@layer base { h1 { font-weight: 600; } [data-slot="badge"] { @apply rounded-full; } }
CSS
OUT="$(python3 "$LAF" "$TMP/axes_nomotion.css" "$TMP/axes_aes.json" 2>&1)"; echo "$OUT" | grep -q "easing" && ok "motion easing declared-not-applied → blocked" || bad "missing easing not blocked"
# pill slot declared but no rounded-full rule → block
cat > "$TMP/axes_nopill.css" <<'CSS'
@theme inline { --text-base--line-height: 1.65; }
@layer base { h1 { font-weight: 600; } :root { --ease-out-soft: cubic-bezier(0.16, 1, 0.3, 1); } [data-slot="button"] { transition-timing-function: var(--ease-out-soft); } }
CSS
OUT="$(python3 "$LAF" "$TMP/axes_nopill.css" "$TMP/axes_aes.json" 2>&1)"; echo "$OUT" | grep -q "pill_slots" && ok "pill shape declared-not-applied → blocked" || bad "missing pill not blocked"
# no axes block → graceful skip (exit 0)
echo '{"meta":{}}' > "$TMP/axes_none.json"
python3 "$LAF" "$TMP/axes_ok.css" "$TMP/axes_none.json" >/dev/null 2>&1 && ok "no axes block → graceful skip" || bad "no-axes should skip, not block"

# ── result ────────────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────────────"
echo "PASS: $PASS   FAIL: $FAIL"
[ "$FAIL" = "0" ] && { echo "✓ selftest green"; exit 0; } || { echo "✗ selftest failed"; exit 1; }
