#!/usr/bin/env bash
# designops-pipeline pipeline runner
#
# Execution model (IMPORTANT):
#   This script does the DETERMINISTIC work — extract TOR text, scan the design system,
#   validate brief.json, stage prompts — and hands GENERATION to the agent.
#   • Default (agent-driven): inside Claude Code, it stages prompts + prints an
#     "AGENT ACTIONS" checklist, then exits. The active session does the generation.
#     It never calls `claude -p` (that would spawn a nested session and hang).
#   • --exec (headless standalone): only from a plain shell OUTSIDE a session, it runs
#     `claude -p` per step. Refused if CLAUDECODE is set (recursion guard).
#
# Usage:
#   Full pipeline:  run_pipeline.sh --tor <path> --ds <path> [--out <dir>] [--handoff <path>] [--brand <name>]
#   Step 1+2 only:  run_pipeline.sh --tor <path> [--out <dir>]
#   Step 3 only:    run_pipeline.sh --brief <path> --ds <path> [--out <dir>]
#   With bridge:    run_pipeline.sh --tor <path> --handoff <path/to/Hand-off-test> [--brand <name>]
#   Headless:       run_pipeline.sh --tor <path> --exec        # outside Claude Code only
#
# Env vars:
#   TOR_OUTPUT_DIR    — output directory (default: ./tor-output)
#   TOR_DS_PATH       — design system path override (default: ../shadcn-skills-design-starter)
#   TOR_HANDOFF_PATH  — Hand-off-test repo path (if set, runs the bridge automatically)
#   TOR_BRAND_NAME    — brand name for brand.config.json (default: poc-brand)

set -euo pipefail

# ── defaults ──────────────────────────────────────────────────────────────────
TOR_FILE=""
TOR_TEXT=""
DS_PATH=""
# Auto-resolve shadcn-skills-design-starter as default DS
# Lookup order: env var → in-repo vendored DS → project-root sibling
_resolve_default_ds() {
  # 1. env var override
  [[ -n "${TOR_DS_PATH:-}" ]] && { echo "$TOR_DS_PATH"; return; }
  # 2. in-repo vendored DS (./design-system) — self-contained default
  local project_root in_repo
  project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
  in_repo="$project_root/design-system"
  [[ -d "$in_repo" ]] && { echo "$in_repo"; return; }
  # 3. project-root sibling (../shadcn-skills-design-starter) — fallback
  local sibling
  sibling="$(cd "$project_root" && cd .. && pwd)/shadcn-skills-design-starter"
  [[ -d "$sibling" ]] && { echo "$sibling"; return; }
  echo ""
}
BRIEF_JSON=""
OUT_DIR="${TOR_OUTPUT_DIR:-./tor-output}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXEC_MODE=0
# Are we already inside a Claude Code session? (set by the harness)
IN_SESSION=0
[[ -n "${CLAUDECODE:-}" ]] && IN_SESSION=1
# Accumulates the ordered checklist of generation steps for the active agent
ACTIONS_FILE="$(mktemp -t tor-actions.XXXXXX)"
trap 'rm -f "$ACTIONS_FILE"' EXIT

# ── parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --tor)       TOR_FILE="$2";  shift 2 ;;
    --tor-text)  TOR_TEXT="$2";  shift 2 ;;
    --ds)        DS_PATH="$2";   shift 2 ;;
    --brief)     BRIEF_JSON="$2"; shift 2 ;;
    --out)       OUT_DIR="$2";   shift 2 ;;
    --handoff)   export TOR_HANDOFF_PATH="$2";  shift 2 ;;
    --brand)     export TOR_BRAND_NAME="$2";    shift 2 ;;
    --exec)      EXEC_MODE=1; shift ;;
    *) echo "[designops-pipeline] ERROR: unknown flag $1"; exit 1 ;;
  esac
done

# ── helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[designops-pipeline] $*"; }
err()  { echo "[designops-pipeline] ERROR: $*" >&2; exit 1; }
step() { echo ""; echo "[designops-pipeline] ▶ $*"; echo "────────────────────────────────"; }

# _generate <prompt_file> <label> <output_hint>
# Default: stage the step for the active agent (no recursion).
# --exec:  run `claude -p` headlessly — refused inside a session (recursion guard).
_generate() {
  local prompt_file="$1" label="$2" out_hint="$3"
  if [[ "$EXEC_MODE" == "1" ]]; then
    if [[ "$IN_SESSION" == "1" ]]; then
      err "--exec refused by recursion guard: already inside a Claude Code session (CLAUDECODE is set).
  Running 'claude -p' here spawns a nested session and hangs.
  → Drop --exec so THIS session generates from the staged prompt, or run --exec from a plain shell."
    fi
    command -v claude &>/dev/null || err "--exec needs the 'claude' CLI on PATH"
    log "exec: claude -p → $label"
    claude -p "$(cat "$prompt_file")" --output-format text >/dev/null
    log "✓ claude finished: $label"
  else
    printf '  [ ] %s\n        prompt:  %s\n        output:  %s\n' "$label" "$prompt_file" "$out_hint" >> "$ACTIONS_FILE"
    log "staged: $label → $prompt_file"
  fi
}

# ── validate inputs ───────────────────────────────────────────────────────────
if [[ -z "$TOR_FILE" && -z "$TOR_TEXT" && -z "$BRIEF_JSON" ]]; then
  err "you must provide at least one input:
  --tor <path>        TOR file (PDF or DOCX)
  --tor-text \"<text>\" TOR text directly
  --brief <path>      skip steps 1+2, use an existing brief.json"
fi

if [[ -n "$TOR_FILE" && ! -f "$TOR_FILE" ]]; then
  err "file not found: $TOR_FILE"
fi

if [[ -n "$BRIEF_JSON" && ! -f "$BRIEF_JSON" ]]; then
  err "file not found: $BRIEF_JSON"
fi

# ── setup output dir ──────────────────────────────────────────────────────────
mkdir -p "$OUT_DIR"
log "Output directory: $OUT_DIR"

# ── step 1+2: TOR → brief ─────────────────────────────────────────────────────
if [[ -z "$BRIEF_JSON" ]]; then
  step "Step 1+2 — Reading TOR & generating brief"

  # Build claude prompt context
  TOR_CONTEXT=""
  if [[ -n "$TOR_FILE" ]]; then
    EXT="${TOR_FILE##*.}"
    EXT=$(printf '%s' "$EXT" | tr '[:upper:]' '[:lower:]')   # bash 3.2 safe lowercasing (avoid bash-4 expansion)
    case "$EXT" in
      pdf)
        log "Extracting text from PDF: $TOR_FILE"
        if command -v pdftotext &>/dev/null; then
          TOR_CONTEXT=$(pdftotext -layout "$TOR_FILE" - 2>/dev/null || true)
        fi
        if [[ -z "$TOR_CONTEXT" ]]; then
          log "pdftotext empty or unavailable — will pass file path to Claude directly"
          TOR_CONTEXT="[PDF_FILE:$TOR_FILE]"
        fi
        ;;
      docx)
        log "Extracting text from DOCX: $TOR_FILE"
        if command -v python3 &>/dev/null; then
          TOR_CONTEXT=$(python3 -c "
import sys
try:
    from docx import Document
    doc = Document('$TOR_FILE')
    print('\n'.join(p.text for p in doc.paragraphs if p.text.strip()))
except Exception as e:
    print('[DOCX_FILE:$TOR_FILE]')
" 2>/dev/null || echo "[DOCX_FILE:$TOR_FILE]")
        else
          TOR_CONTEXT="[DOCX_FILE:$TOR_FILE]"
        fi
        ;;
      md|txt)
        TOR_CONTEXT=$(cat "$TOR_FILE")
        ;;
      *)
        err "unsupported format: .$EXT (supported: pdf, docx, md, txt)"
        ;;
    esac
  elif [[ -n "$TOR_TEXT" ]]; then
    TOR_CONTEXT="$TOR_TEXT"
  fi

  # Write prompt file for Claude Code to execute
  PROMPT_FILE="$OUT_DIR/.prompt_step1.txt"
  cat > "$PROMPT_FILE" << PROMPT
Read the TOR below and produce 2 output files per the designops-pipeline SKILL.md:

1. Save "$OUT_DIR/brief.md" — Markdown for humans to review
2. Save "$OUT_DIR/brief.json" — JSON schema for the AI to consume next

Use the 8 main categories: PROJECT_OVERVIEW, TARGET_USERS, CORE_FEATURES, USER_FLOWS,
CONSTRAINTS, DESIGN_DIRECTION, SUCCESS_METRICS, OPEN_QUESTIONS

If the TOR doesn't state a category → set null, don't make it up.
A feature with no priority → default to Should.

TOR content:
---
$TOR_CONTEXT
---
PROMPT

  _generate "$PROMPT_FILE" "Step 1+2 — read TOR → write brief" "$OUT_DIR/brief.md + $OUT_DIR/brief.json"

  BRIEF_JSON="$OUT_DIR/brief.json"
fi

# ── validate brief.json ───────────────────────────────────────────────────────
if [[ -f "$BRIEF_JSON" ]]; then
  step "Validating brief.json"
  python3 "$SKILL_DIR/scripts/validate_brief.py" "$BRIEF_JSON" || {
    err "brief.json validation failed — fix it first, or re-run steps 1+2"
  }
  log "✓ brief.json valid"
else
  log "brief.json doesn't exist yet — Claude Code will create it after steps 1+2"
fi

# ── step 2.3: brief → user research (UX) ──────────────────────────────────────
# Personas / JTBD / pain points as structured EVIDENCE for the intelligence layer.
# Hybrid: pure inference unless real research inputs are provided (honesty-gated).
RESEARCH_JSON="$OUT_DIR/research.json"
if [[ ! -f "$RESEARCH_JSON" ]]; then
  step "Step 2.3 — User Research Layer (brief → research.json)"
  PROMPT_RESEARCH="$OUT_DIR/.prompt_research.txt"
  cat > "$PROMPT_RESEARCH" << PROMPT
Read "$BRIEF_JSON" (and any provided research inputs) and produce "$RESEARCH_JSON"
following $SKILL_DIR/references/user-research-layer.md (the User Research Layer).

Declare meta.evidence_mode + meta.inputs_provided FIRST. With no real inputs, every item is
source:"inferred" (a hypothesis, confidence <= medium) — never fabricate evidence. Produce
personas, jobs_to_be_done, pain_points, behavioral_assumptions (+ a research_question for every
high-risk one), and feeds_intelligence so Step 2.5 can consume them.
PROMPT
  _generate "$PROMPT_RESEARCH" "Step 2.3 — brief → user research" "$RESEARCH_JSON"
fi
if [[ -f "$RESEARCH_JSON" ]]; then
  step "Validating research.json"
  python3 "$SKILL_DIR/scripts/validate_research.py" "$RESEARCH_JSON" "$BRIEF_JSON" || {
    err "research.json validation failed — fix it first, or re-run Step 2.3"
  }
  log "✓ research.json valid"
fi

# ── step 2.4: brief + research → competitive analysis (UX) ────────────────────
COMPETITIVE_JSON="$OUT_DIR/competitive.json"
if [[ ! -f "$COMPETITIVE_JSON" ]]; then
  step "Step 2.4 — Competitive Analysis Layer (brief + research → competitive.json)"
  PROMPT_COMP="$OUT_DIR/.prompt_competitive.txt"
  cat > "$PROMPT_COMP" << PROMPT
Read "$BRIEF_JSON" and "$RESEARCH_JSON" (and any provided competitor URLs/teardowns) and produce
"$COMPETITIVE_JSON" following $SKILL_DIR/references/competitive-analysis-layer.md.

Declare meta.evidence_mode + meta.inputs_provided FIRST. With no real competitor inputs, every
item is source:"inferred" (market hypotheses, not a verified teardown). Mark conventions
"follow" unless you justify "break" with a reason; name the table_stakes. Fill feeds for Step 2.5/2.6.
PROMPT
  _generate "$PROMPT_COMP" "Step 2.4 — brief + research → competitive analysis" "$COMPETITIVE_JSON"
fi
if [[ -f "$COMPETITIVE_JSON" ]]; then
  step "Validating competitive.json"
  python3 "$SKILL_DIR/scripts/validate_competitive.py" "$COMPETITIVE_JSON" "$BRIEF_JSON" || {
    err "competitive.json validation failed — fix it first, or re-run Step 2.4"
  }
  log "✓ competitive.json valid"
fi

# ── step 2.5: brief → product intelligence ────────────────────────────────────
# Stage the prompt unconditionally (like step 1+2 / step 3) so it appears in the
# AGENT ACTIONS checklist even before brief.json exists — the agent produces brief
# first, then intelligence (the prompt references brief.json by path).
INTEL_JSON="$OUT_DIR/intelligence.json"
if [[ ! -f "$INTEL_JSON" ]]; then
  step "Step 2.5 — Product Intelligence Layer (brief → intelligence.json)"
  PROMPT_INTEL="$OUT_DIR/.prompt_intel.txt"
  cat > "$PROMPT_INTEL" << PROMPT
Read "$BRIEF_JSON" and produce "$INTEL_JSON" following
$SKILL_DIR/references/intelligence-layer.md (the Product Intelligence Layer).

Infer 10 measurable product dimensions — User Types, User Expertise, User Goals,
Core Tasks, Workflow Complexity, Data Density, Error Tolerance, Accessibility Needs,
Compliance Requirements, Decision Criticality — each with evidence + confidence, then
roll them up into design_directives. Obey the cross-dimension invariants in the reference.

Fact vs interpretation: brief.json = stated facts, intelligence.json = inference.
Never restate the brief — infer what it implies. No evidence → confidence:"low" + an open_question.

If "$RESEARCH_JSON" exists, use feeds_intelligence as evidence: personas → user_types,
jobs_to_be_done → user_goals, pain_points/behavioral_assumptions → error_tolerance/open_questions
(evidence-backed research raises confidence; inferred research stays a hypothesis). If
"$COMPETITIVE_JSON" exists, use its feeds for data_density + expected patterns.
PROMPT
  _generate "$PROMPT_INTEL" "Step 2.5 — brief → product intelligence" "$INTEL_JSON"
fi

# validate intelligence.json (gate)
if [[ -f "$INTEL_JSON" ]]; then
  step "Validating intelligence.json"
  python3 "$SKILL_DIR/scripts/validate_intelligence.py" "$INTEL_JSON" "$BRIEF_JSON" || {
    err "intelligence.json validation failed — fix it first, or re-run Step 2.5"
  }
  log "✓ intelligence.json valid"
elif [[ -f "$BRIEF_JSON" ]]; then
  log "intelligence.json not generated yet — flows (Step 3) need its design_directives"
fi

# ── step 2.6 (Aesthetic): brief + intelligence → aesthetic.json ───────────────
# Picks a *visual direction* (one of 138 named systems in the brand library, or an
# archetype) and resolves it into concrete, contrast-checked tokens. This is the
# "taste" layer that design_directives (functional) does not cover — it gives the
# prototype a real look instead of the neutral shadcn default ("design slop").
AESTHETIC_JSON="$OUT_DIR/aesthetic.json"
AESTHETICS_DIR="$SKILL_DIR/references/aesthetics"
# Stage whenever a brief exists (like flows/intelligence) — the prompt references
# intelligence.json by PATH; the agent produces it earlier in the same run.
if [[ ! -f "$AESTHETIC_JSON" ]]; then
  step "Step 2.6 — Aesthetic Direction (brief + intelligence → aesthetic.json)"
  PROMPT_AES="$OUT_DIR/.prompt_aesthetic.txt"
  cat > "$PROMPT_AES" << PROMPT
Read "$BRIEF_JSON" (facts) and "$INTEL_JSON" (design_directives, user_types, tone), then
produce "$AESTHETIC_JSON" — a committed visual direction resolved into concrete tokens.

The brand library (138 named design systems) is vendored at:
  $AESTHETICS_DIR/design-systems/library/<name>/DESIGN.md
Browse it with:
  python3 $AESTHETICS_DIR/scripts/design_systems.py list        # all systems by category
  python3 $AESTHETICS_DIR/scripts/design_systems.py search <term>
  python3 $AESTHETICS_DIR/scripts/design_systems.py show <name>

Process (anti-slop — deciding BEFORE generating; see $AESTHETICS_DIR/taste/design-taste.md):
1. Brief Inference: name the domain, audience & tone, the ONE mood adjective the result must
   earn, and motion depth (none|subtle|expressive). Generating before deciding = slop.
2. Pick a direction that fits the product intelligence — a named_system from the library
   (read its DESIGN.md) or an archetype from taste/aesthetic-systems.md. Justify the fit
   against intelligence dimensions (trust_emphasis, user_expertise, data_density, domain).
   If the TOR/brief provides reference images, screenshots, or a mockup, INFER the direction
   from them instead (palette/type/spacing/radius/layout) per $SKILL_DIR/references/image-to-code.md,
   then anchor to the closest named_system/archetype. Match the design system, never copy assets.
3. Resolve to tokens (oklch): primary, background, foreground, radius, font_sans (+ font_mono,
   accent if the system uses them). For EVERY contrast pair, also give fg_hex + bg_hex so the
   gate can re-compute the ratio — never self-certify.
4. Obey constraints: constraints.a11y_target MUST equal design_directives.a11y_target and
   constraints.density_target MUST equal design_directives.density_target. A brand color that
   fails the WCAG floor (AA 4.5:1 / AAA 7:1 normal text) must be darkened/lightened —
   taste never overrides accessibility.
5. Emit brand_config { project_name, primary, radius, font_sans } — a ready-to-drop
   brand.config.json whose values EQUAL tokens.* (Step 4 / generate-prototype consumes it).

Shape: { meta, brief_inference{domain,audience_tone,mood_adjective,motion_depth,rationale},
direction{type,name,category,spec_ref,why_fit}, tokens{...}, contrast_checks:[{pair,fg_hex,bg_hex,ratio,large?,ui?}],
constraints{a11y_target,density_target}, brand_config{project_name,primary,radius,font_sans} }
PROMPT
  _generate "$PROMPT_AES" "Step 2.6 — pick + resolve aesthetic direction" "$AESTHETIC_JSON"
fi

# validate aesthetic.json (gate) — recomputes contrast from hex, checks brand resolves
if [[ -f "$AESTHETIC_JSON" ]]; then
  step "Validating aesthetic.json"
  python3 "$SKILL_DIR/scripts/validate_aesthetic.py" "$AESTHETIC_JSON" "$INTEL_JSON" || {
    err "aesthetic.json validation failed — fix it first, or re-run Step 2.6"
  }
  log "✓ aesthetic.json valid"
  # drop brand.config.json at the output root so /generate-prototype picks it up
  if [[ ! -f "$OUT_DIR/brand.config.json" ]]; then
    python3 -c "import json,sys; json.dump(json.load(open('$AESTHETIC_JSON'))['brand_config'], open('$OUT_DIR/brand.config.json','w'), indent=2)" \
      && log "→ wrote $OUT_DIR/brand.config.json (from aesthetic.json)"
  fi
fi

# ── step 3 (Flows): brief + intelligence → flows.json ─────────────────────────
# Refines the brief's raw user_flows using design_directives (navigation_model,
# safeguard_level, mandatory_flows). No design system needed yet.
FLOWS_JSON="$OUT_DIR/flows.json"
if [[ ! -f "$FLOWS_JSON" ]]; then
  step "Step 3 — User Flows (brief + intelligence → flows.json)"
  PROMPT_FLOWS="$OUT_DIR/.prompt_flows.txt"
  cat > "$PROMPT_FLOWS" << PROMPT
Read "$BRIEF_JSON" (user_flows) and "$INTEL_JSON" (design_directives, core_tasks), then
produce "$FLOWS_JSON" — refined user flows, NOT raw copies.

Refine each brief.user_flow using design_directives:
- navigation_model → echo it at top + shape entry/exit and how flows connect (hub_spoke = home hub + spokes)
- safeguard_level → inject confirm / preview / undo steps on risky actions (mark step.safeguard)
- mandatory_flows → ADD an injected flow per directive (e.g. consent, privacy_notice) with source_flow_ref:null
- decision_criticality decision_points → mark step.decision:true where the user commits a high-stakes choice

Shape per flows.json: { meta, navigation_model, flows:[{id,name,source_flow_ref,user_type_ref,goal_ref,
steps:[{n,action,decision,safeguard}],entry,exit,directives_applied:[]}], mandatory_flows:[{name,reason,injected}] }
Each flow.user_type_ref/goal_ref must resolve into intelligence.json. Every design_directives.mandatory_flow must appear as an injected flow.
PROMPT
  _generate "$PROMPT_FLOWS" "Step 3 — refine user flows" "$FLOWS_JSON"
fi
if [[ -f "$FLOWS_JSON" ]]; then
  step "Validating flows.json"
  python3 "$SKILL_DIR/scripts/validate_flows.py" "$FLOWS_JSON" "$INTEL_JSON" "$BRIEF_JSON" || {
    err "flows.json validation failed — fix it first, or re-run Step 3"
  }
  log "✓ flows.json valid"
fi

# ── step 3.5 (Screen Inventory): flows + intelligence + DS → screens + draft ───
# Auto-resolve DS if not provided
if [[ -z "$DS_PATH" ]]; then
  DS_PATH="$(_resolve_default_ds)"
  if [[ -n "$DS_PATH" ]]; then
    log "ℹ  --ds not provided → using default: $DS_PATH"
  fi
fi

if [[ -n "$DS_PATH" ]]; then
  step "Step 3.5 — Screen Inventory & Component Mapping (flows + DS)"

  # resolve github URL → clone
  if [[ "$DS_PATH" =~ ^https://github.com ]]; then
    CLONE_DIR="/tmp/tor-ds-repo"
    if [[ ! -d "$CLONE_DIR/.git" ]]; then
      log "Cloning design system repo..."
      git clone --depth 1 "$DS_PATH" "$CLONE_DIR"
    else
      log "Using cached clone at $CLONE_DIR"
    fi
    DS_PATH="$CLONE_DIR"
  fi

  [[ -d "$DS_PATH" ]] || err "design system directory not found: $DS_PATH"

  # Inventory DS structure
  log "Scanning design system at: $DS_PATH"
  DS_INVENTORY=$(python3 - "$DS_PATH" << 'PYEOF'
import os, sys, json

ds_path = sys.argv[1]
result = {"components": [], "tokens": {}, "has_storybook": False, "readme": "", "scanned_dir": None, "scope": None}

# Non-DS dirs to skip when walking — these are app internals, not the design system surface
NOISE_DIRS = {
    "node_modules", "docs", "examples", "example", "demos", "demo", "stories",
    "providers", "provider", "layout", "internal", "__tests__", "tests", "test",
    "hooks", "lib", "utils", "templates", "blocks",
}

def collect(root_dir):
    found = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in NOISE_DIRS]
        for f in files:
            if f.endswith(('.tsx', '.jsx', '.vue', '.svelte')) and not f.endswith(('.test.tsx', '.spec.tsx', '.stories.tsx')):
                name = f.rsplit('.', 1)[0]
                if name not in found and not name.startswith('index'):
                    found.append(name)
    return found

# Prefer a dedicated UI/primitives dir (the real design-system surface) before falling
# back to a broad components/ scan — keeps app internals (docs, layout, providers) out.
UI_DIRS  = ["components/ui", "src/components/ui", "src/ui", "ui", "packages/ui/src", "packages/ui"]
ALL_DIRS = ["components", "src/components", "lib/components", "packages"]

for search_dir in UI_DIRS:
    full = os.path.join(ds_path, search_dir)
    if os.path.isdir(full):
        result["components"] = sorted(collect(full))
        result["scanned_dir"] = search_dir
        result["scope"] = "ui-only (dedicated design-system dir)"
        break
else:
    for search_dir in ALL_DIRS:
        full = os.path.join(ds_path, search_dir)
        if os.path.isdir(full):
            result["components"] = sorted(collect(full))
            result["scanned_dir"] = search_dir
            result["scope"] = "broad (no dedicated ui/ dir; app internals excluded)"
            break

result["component_count"] = len(result["components"])

# Find token files
for token_dir in ["tokens", "design-tokens", "src/tokens", "styles"]:
    full = os.path.join(ds_path, token_dir)
    if os.path.isdir(full):
        result["tokens"]["dir"] = token_dir
        result["tokens"]["files"] = [f for f in os.listdir(full) if f.endswith(('.json','.ts','.css','.scss'))]
        break

# Check for storybook
result["has_storybook"] = any(
    os.path.exists(os.path.join(ds_path, p))
    for p in [".storybook", "stories", "src/stories"]
)

# Read README
for readme in ["README.md", "readme.md", "CONTRIBUTING.md"]:
    p = os.path.join(ds_path, readme)
    if os.path.isfile(p):
        with open(p) as f:
            result["readme"] = f.read()[:2000]
        break

print(json.dumps(result, ensure_ascii=False, indent=2))
PYEOF
)

  # Write step 3 prompt — reference brief.json by PATH (the agent may have just produced it
  # in this same run, so don't embed a possibly-stale copy).
  PROMPT3_FILE="$OUT_DIR/.prompt_step3.txt"

  SCREENS_JSON="$OUT_DIR/screen-inventory.json"
  AES_HINT=""
  [[ -f "$AESTHETIC_JSON" ]] && AES_HINT="
Also read "$AESTHETIC_JSON" (Step 2.6 — the chosen visual direction + resolved tokens).
The Token Usage Guide MUST use aesthetic.json.tokens (primary/background/foreground/radius/
font_sans), and the screen look/JSX must earn brief_inference.mood_adjective. Do not fall back
to the neutral shadcn default when an aesthetic.json exists."

  cat > "$PROMPT3_FILE" << PROMPT
Read "$FLOWS_JSON" (refined flows — Step 3), "$INTEL_JSON" (design_directives), and the
design system inventory below, then produce TWO artifacts:
  1. "$SCREENS_JSON"           — machine screen inventory (gated)
  2. "$OUT_DIR/design-first-draft.md" — the human-readable breakdown built FROM it
$AES_HINT

Derive screens from FLOWS (each flow → its screens), driving every decision from design_directives:
- density_target   → layout_primitive (card / table / dashboard / form / list / detail)
- safeguard_level  → confirm / undo / preview patterns on the screen
- navigation_model → how screens connect (hub_spoke = home hub + spoke screens)
- a11y_target      → component variants + the Step 4.7 audit target
- mandatory_flows  → each injected flow gets its screen(s) (e.g. consent, privacy_notice)
- trust_emphasis   → evidence-on-demand / transparency affordances
Coverage rule: EVERY flow in flows.json must have at least one screen; every screen.flow_refs must resolve.
If meta.overall_confidence=low (constrain_downstream), produce wireframe-level screens + flag a human gate.

screen-inventory.json shape: { meta, screens:[{id,name,flow_refs:[],user_type_ref,priority:Must|Should|Could,
purpose, layout_primitive, components:[from the DS inventory], gaps:[{name,status:missing|partial,recommendation}],
directive_drivers:[]}] }

design system path: $DS_PATH
design system inventory:
$DS_INVENTORY

design-first-draft.md (human view) must contain: Screen Inventory table · Screen Breakdown (per screen: purpose, flow, layout, JSX, decisions tied to a directive) · Component Gap Report · Token Usage Guide.

If the design system is shadcn-skills-design-starter, read its root CLAUDE.md first (patterns, Figma→Tailwind token map, naming).
The component list is in components/ui/. Token reference: .claude/skills/shadcn-ui-design/references/DESIGN.md.

rules:
- Use only components that exist in the inventory; missing → gap "missing"; partial → "partial" + recommendation; don't invent components.
- UI copy follows $SKILL_DIR/references/ux-writing/voice-tone.md: buttons frontload the verb + name the outcome ("Save changes", not "Submit"); errors are what→why→how; empty states are value→action. Per design_directives: error_tolerance low/zero or a safeguard step → the confirm button RESTATES the action ("Delete account", not "OK") and high-stakes/irreversible actions get type-to-confirm (WCAG 3.3.4). No emoji (lucide icons), no em-dash in UI copy.
- If the platform is mobile/responsive, apply $SKILL_DIR/references/mobile-usability.md: touch targets ≥44px with ≥8px spacing (whole row tappable), primary action in thumb reach (bottom), correct input types/keyboards (tel/email/number/date; input font ≥16px), real labels not placeholder-only, single-column reflow with no horizontal scroll at 320px, and NO hover-only affordances (touch has no hover).
PROMPT

  _generate "$PROMPT3_FILE" "Step 3.5 — flows + DS → screen-inventory + draft" "$SCREENS_JSON + $OUT_DIR/design-first-draft.md"

  if [[ -f "$SCREENS_JSON" ]]; then
    step "Validating screen-inventory.json"
    python3 "$SKILL_DIR/scripts/validate_screens.py" "$SCREENS_JSON" "$FLOWS_JSON" || {
      err "screen-inventory.json validation failed — fix it first, or re-run Step 3.5"
    }
    log "✓ screen-inventory.json valid"
  fi

else
  log "--ds not provided → skipping Step 3.5 (screen inventory)"
  log "Run later with: run_pipeline.sh --brief $BRIEF_JSON --ds <path> --out $OUT_DIR"
fi

# ── step 4.5: token bridge → hand-off repo ───────────────────────────────────
TOKENS_JSON="$OUT_DIR/poc-delivery/design-system/tokens.json"
HANDOFF_PATH="${TOR_HANDOFF_PATH:-}"

if [[ -f "$TOKENS_JSON" && -n "$HANDOFF_PATH" ]]; then
  step "Step 4.5 — Bridging tokens to Hand-off repo (hex → oklch)"

  [[ -d "$HANDOFF_PATH" ]] || err "handoff directory not found: $HANDOFF_PATH"

  BRIDGE_SCRIPT="$SKILL_DIR/scripts/bridge-tokens.mjs"
  [[ -f "$BRIDGE_SCRIPT" ]] || err "bridge-tokens.mjs not found — check the skill directory"

  # dry-run first to preview
  log "Preview token conversion:"
  node "$BRIDGE_SCRIPT" \
    --tokens  "$TOKENS_JSON" \
    --handoff "$HANDOFF_PATH" \
    --brand   "${TOR_BRAND_NAME:-poc-brand}" \
    --dry-run

  # confirm, then run
  read -r -p "[designops-pipeline] Confirm updating brand.config.json? [y/N] " CONFIRM
  CONFIRM=$(printf '%s' "$CONFIRM" | tr '[:upper:]' '[:lower:]')   # bash 3.2 compatible
  if [[ "$CONFIRM" == "y" ]]; then
    node "$BRIDGE_SCRIPT" \
      --tokens  "$TOKENS_JSON" \
      --handoff "$HANDOFF_PATH" \
      --brand   "${TOR_BRAND_NAME:-poc-brand}"

    log "Running brand:build in handoff repo..."
    (cd "$HANDOFF_PATH" && npm run brand:build)
    log "✓ brand.css regenerated"
  else
    log "Skipped — you can run it later with:"
    log "  node $BRIDGE_SCRIPT --tokens $TOKENS_JSON --handoff $HANDOFF_PATH"
  fi

elif [[ -f "$TOKENS_JSON" && -z "$HANDOFF_PATH" ]]; then
  log "ℹ  tokens.json is ready but --handoff was not provided"
  log "  Run the bridge later with:"
  log "  node $SKILL_DIR/scripts/bridge-tokens.mjs \\"
  log "    --tokens  $TOKENS_JSON \\"
  log "    --handoff <path/to/Hand-off-test>"
fi

# ── final summary ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
log "✓ Prep complete → $OUT_DIR/"
echo ""
for f in brief.md brief.json design-first-draft.md; do
  if [[ -f "$OUT_DIR/$f" ]]; then
    SIZE=$(wc -c < "$OUT_DIR/$f" | tr -d ' ')
    echo "  ✓ $f ($SIZE bytes)"
  else
    echo "  – $f (not generated yet)"
  fi
done
echo "════════════════════════════════════════"

# ── agent-driven handoff (default mode) ───────────────────────────────────────
if [[ "$EXEC_MODE" != "1" && -s "$ACTIONS_FILE" ]]; then
  echo ""
  echo "▶▶ AGENT ACTIONS — generate these now (this session, in order):"
  cat "$ACTIONS_FILE"
  echo ""
  echo "  Then: python3 $SKILL_DIR/scripts/validate_brief.py $OUT_DIR/brief.json"
  if [[ "$IN_SESSION" != "1" ]]; then
    echo ""
    echo "  (Not in a Claude Code session. Open this repo in Claude Code to process the"
    echo "   staged prompts, or re-run with --exec to generate headlessly.)"
  fi
fi
