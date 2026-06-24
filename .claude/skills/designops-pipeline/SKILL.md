---
name: designops-pipeline
description: >
  End-to-end DesignOps pipeline: turn a TOR (Terms of Reference) file or project brief into a
  structured requirement AND a POC prototype that has passed a scored critique + a script audit.
  Outputs both Markdown (for humans) and JSON artifacts (for AI agents) at every stage.
  Use this skill whenever the user mentions "read TOR", "summarize TOR", "turn TOR into a requirement",
  "brief requirement from TOR", "designops-pipeline", "tor-to-brief" (the former name),
  "drop a TOR", "design brief from spec", or wants the AI to read a spec/scope document and produce
  a design requirement or prototype. Supports PDF, DOCX, and Notion/Google Docs URLs.
  In Claude Code, run `scripts/run_pipeline.sh` to chain the full pipeline automatically.
  Step 2.5 (Product Intelligence Layer) infers 10 measurable product dimensions and derives an
  open design_directives object (density, a11y target, safeguards, navigation) — industry-agnostic.
  Step 2.6 (Aesthetic Direction) picks one of 138 named design systems or an archetype and resolves
  it into the full identity token set (surfaces/text/accent/border + dark theme, not just primary),
  contrast-checked, + a signature → aesthetic.json + a brand.config.json that carries the whole theme.
  Step 3.7 (Edge-Case Analysis → edge-cases.json) enumerates the non-happy-path conditions every Must
  screen must survive, via UI Stack × CORRECT, severity driven by the Step 2.5 directives.
  Step 4 builds a POC prototype from a ready-made component library + mock data, Step 4.6 runs a
  scored critique (6 weighted dimensions + Nielsen + anti-slop + a separate judge pass), Step 4.7 is a runnable audit gate
  (audit_prototype.py — 11 gates: tokens + WCAG contrast in light/dark + no-emoji + component contracts + no remote-font @import + theme fidelity + directive fidelity + screen coverage + edge-case coverage + font fidelity + axis fidelity) before handoff.
  UX layers feed the pipeline: Step 2.3 (User Research → research.json: personas/JTBD/pains) and
  Step 2.4 (Competitive Analysis → competitive.json) supply evidence to Step 2.5; Step 4.8
  (Usability Test → usability.json: heuristic + automated + simulated persona walkthrough) runs on
  the built prototype. All three are HYBRID (infer-then-override) and honesty-gated — nothing is
  marked evidence without a declared input, and usability never claims a real-user test.
---

# designops-pipeline

> Turn a TOR → design brief → first draft  
> 3 chainable steps with a validation gate between them

---

## Overview

```
TOR (PDF / DOCX / Notion / GDocs)
        │
        ▼  Step 1+2
  ┌─────────────┐     ┌──────────────────┐
  │  brief.md   │     │  brief.json      │
  │  (humans)   │     │  (AI consumes)   │
  └─────────────┘     └────────┬─────────┘
                               │  validate_brief.py
                               ▼  Step 2.3 User Research · Step 2.4 Competitive (UX, hybrid)
                    ┌─────────────────────────────┐
                    │  research.json              │  personas / JTBD / pains
                    │  competitive.json           │  ← validate_research.py / validate_competitive.py
                    └──────────┬──────────────────┘     (honesty-gated: no fabricated evidence)
                               ▼  Step 2.5  Product Intelligence Layer (consumes UX evidence)
                    ┌─────────────────────┐
                    │  intelligence.json  │  10 dims → design_directives
                    └──────────┬──────────┘
                               │  validate_intelligence.py (+ cross-dim invariants)
                               ▼  Step 2.6  Aesthetic Direction (138-brand library)
                    ┌─────────────────────────────┐
                    │  aesthetic.json             │  pick system/archetype → tokens
                    │  + brand.config.json        │  ← validate_aesthetic.py (contrast from hex)
                    └──────────┬──────────────────┘
                               ▼  Step 3  Flows (refine user_flows from directives)
                    ┌─────────────────────┐
                    │  flows.json         │  ← validate_flows.py
                    └──────────┬──────────┘
                               ▼  Step 3.5  Screen Inventory & Component Mapping
                    ┌──────────────────────────────┐
                    │  screen-inventory.json       │  ← validate_screens.py (flow→screen coverage)
                    │  + design-first-draft.md     │     (human breakdown view)
                    └──────────┬───────────────────┘
                               ▼  Step 3.7  Edge-Case Analysis (UI Stack × CORRECT)
                    ┌──────────────────────────────┐
                    │  edge-cases.json             │  ← validate_edgecases.py (trace + directive floors)
                    └──────────┬───────────────────┘
                               │
                               ▼  Step 4
              ┌────────────────────────────────┐
              │  poc-delivery/                 │
              │  ├── design-system/            │
              │  │   ├── tokens.json           │
              │  │   ├── tokens.css            │
              │  │   └── spacing.md            │
              │  └── screens/                  │
              │      ├── [screen].html         │
              │      └── ...                   │
              └────────────────────────────────┘
                               │
                               ▼  Step 4.6  critique (4-layer + judge) → fix
                               ▼  Step 4.7  audit gate (11 gates: token + WCAG + … + font + axis fidelity)
                               │            🔴 critical = block handoff
                               ▼  Step 5 (separate pipeline)
              ┌────────────────────────────────┐
              │  Figma MCP                     │
              │  read HTML → build Figma screens│
              └────────────────────────────────┘
```

**Output path** — all files are saved to `{OUTPUT_DIR}`:
1. env var `TOR_OUTPUT_DIR` if set
2. `--out` flag passed to the script
3. default: `./tor-output/` (created automatically)

---

## Quick start (Claude Code)

```bash
# Full pipeline — TOR → brief → draft → POC delivery
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh \
  --tor ./docs/tor.pdf \
  --ds ../looloo-design-system \
  --out ./output

# Steps 1+2 only (no design system yet)
bash run_pipeline.sh --tor ./docs/tor.pdf --out ./output

# Step 3 only (brief.json already exists)
bash run_pipeline.sh --brief ./output/brief.json --ds ../looloo-design-system --out ./output

# Step 4 only (design-first-draft.md + DS already exist)
bash run_pipeline.sh --draft ./output/design-first-draft.md --ds ../looloo-design-system --out ./output
```

### Execution model (how the script and the agent split work)

`run_pipeline.sh` is **agent-driven** — it does the deterministic work and hands generation to you (the active session):

1. The script **extracts** the TOR text, **scans** the design system inventory, and **stages** prompt files (`{OUTPUT_DIR}/.prompt_step1.txt`, `.prompt_step3.txt`).
2. It prints an **`▶▶ AGENT ACTIONS`** checklist — generate each output **in this session, in order**: read `.prompt_step1.txt` → write `brief.md` + `brief.json`; then read `.prompt_step3.txt` → write `design-first-draft.md`.
3. After writing `brief.json`, run the gate: `python3 scripts/validate_brief.py {OUTPUT_DIR}/brief.json`.

> The script **never calls `claude -p`** by default — inside Claude Code that would spawn a nested session and hang. For true headless use **from a plain shell** (outside a session) add `--exec`; it's refused if `CLAUDECODE` is set (recursion guard).

---

## Step 1+2 — TOR Reader & Brief Writer

### Input

| Input | How to read it |
|-------|----------------|
| PDF | `pdf-reading` skill → `pdfplumber` · rasterize if it contains diagrams |
| DOCX | `docx` skill → `python-docx` |
| Notion URL | Notion MCP: `notion-fetch` |
| Google Docs URL | Google Drive MCP: `read_file_content` |
| Plain text | Read from the `--tor-text` flag or the conversation |

No input → halt immediately:
```
[designops-pipeline] ERROR: no TOR input found
Specify with --tor <path> or --tor-text "<text>"
```

---

### Filter out non-product content before extracting

A TOR often mixes in content unrelated to product requirements — identify and drop it first, then extract the 8 categories.

**Drop (don't use):**

| Type | Example |
|------|---------|
| PR / branding copy | "This project will elevate the organization's image..." |
| Procurement procedures | Bid submission · contract terms · penalties |
| Org history / intro with no requirement | "Our agency was founded in 1997..." |
| Budget and finance | Project budget · payment milestones |
| General legal boilerplate (not a product constraint) | Procurement act · government regulations |
| Responsible parties / committee structure | Signatory names · advisory board |

**Keep (extract these):**

| Type | Reason |
|------|--------|
| Feature / functional requirement | Core input of the brief |
| User groups / stakeholders | → `TARGET_USERS` |
| Technical / security / compliance constraints that affect the product | → `CONSTRAINTS` |
| Timeline that affects delivery | → `CONSTRAINTS.timeline` |
| KPIs / success metrics | → `SUCCESS_METRICS` |
| Visual reference / brand guideline specified | → `DESIGN_DIRECTION` |
| **Scoring table / scoring rubric** | → `SCORING_CRITERIA` (see below) |

**Rule:** if you're unsure whether a section affects product design → keep it in `OPEN_QUESTIONS`, don't drop it silently.

Log when filtering is done:
```
[designops-pipeline] ✓ Content filter
  Used: ~[X]% of TOR content
  Dropped: ~[Y]% (procurement · intro · legal boilerplate)
```

---

### Extract 8 categories

Analyze the TOR and pull every category — never assume anything the TOR doesn't state.

| # | Category | Content |
|---|----------|---------|
| 1 | `PROJECT_OVERVIEW` | Project name · objective · scope |
| 2 | `TARGET_USERS` | User groups · personas · context |
| 3 | `CORE_FEATURES` | Feature list with priority Must / Should / Could |
| 4 | `USER_FLOWS` | Main flows · entry/exit points |
| 5 | `CONSTRAINTS` | Technical · business · regulatory · timeline |
| 6 | `DESIGN_DIRECTION` | Tone · brand refs · platform |
| 7 | `SUCCESS_METRICS` | KPIs · acceptance criteria |
| 8 | `OPEN_QUESTIONS` | Where the TOR is unclear · conflicting information |
| 9 | `SCORING_CRITERIA` | Scoring table from the TOR · minimum score per criterion |

**Rules:**
- A category the TOR doesn't state → set `null`, don't make it up
- Conflicting information in the TOR → flag it in `OPEN_QUESTIONS`
- A feature with no priority → default `Should`
- **A feature tied to a scoring criterion → priority must always be `Must`**, even if the TOR doesn't state a priority

---

### Scoring Criteria — how to extract

If you find a scoring table in the TOR, extract every criterion and map it back to a feature:

**Steps:**

1. **Find the table** — common names: "Scoring criteria", "Evaluation criteria", "Technical criteria", "Consideration rubric"

2. **Classify each criterion:**

   | Type | How to handle |
   |------|---------------|
   | **Functional** — the system must do it | → map to a feature in `CORE_FEATURES` immediately, priority = `Must` |
   | **Technical** — infrastructure, performance, security | → `CONSTRAINTS.technical` + note the score weight |
   | **Process** — way of working, methodology | → `OPEN_QUESTIONS` since it affects delivery, not design |
   | **Document** — manuals, training plan | → `CONSTRAINTS.business` |

3. **Compute the minimum viable score** — what score the product must reach to pass (if the TOR states a threshold)

**Example output from a scoring table:**

The TOR states:
```
Technical (60 points)
  - Online appointment system     20 points
  - SMS/Email notifications       15 points
  - Patient statistics reports    10 points
  - Data security                 15 points
Price (40 points)
```

Extracted as:
```json
"scoring_criteria": {
  "total_score": 100,
  "passing_threshold": null,
  "categories": [
    {
      "id": "SC01",
      "name": "Technical",
      "weight": 60,
      "items": [
        { "id": "SC01-1", "name": "Online appointment system", "score": 20, "maps_to_feature": "F01", "type": "functional" },
        { "id": "SC01-2", "name": "SMS/Email notifications",   "score": 15, "maps_to_feature": "F02", "type": "functional" },
        { "id": "SC01-3", "name": "Patient statistics reports", "score": 10, "maps_to_feature": "F03", "type": "functional" },
        { "id": "SC01-4", "name": "Data security",             "score": 15, "maps_to_feature": null,  "type": "technical"  }
      ]
    },
    {
      "id": "SC02",
      "name": "Price",
      "weight": 40,
      "items": [],
      "note": "Dropped — does not affect product design"
    }
  ],
  "minimum_viable": {
    "description": "Must satisfy every functional criterion to score full points on SC01",
    "must_have_features": ["F01", "F02", "F03"],
    "must_have_score": 45
  }
}
```

**Cross-check rule:** after extracting scoring_criteria, loop back over `core_features` — if any feature in `must_have_features` isn't in the list yet, add it immediately with priority = `Must`.

---

> **Design interpretation (density, a11y target, safeguards, navigation) is NOT decided here.**
> The brief stays factual. Those are derived in **Step 2.5 — Product Intelligence Layer** as an
> open, per-project `design_directives` object — not a fixed industry preset. See that step below.

---

### Output A — `brief.md`

```markdown
# [Project Name] — Design Brief
> Source: [filename] · Generated: [DATE] · Confidence: high/medium/low

## 1. Project Overview
...

## 2. Target Users
...

## 3. Core Features
| Feature | Priority | Notes |
|---------|----------|-------|
| ...     | Must     | ...   |

## 4. Key User Flows
...

## 5. Constraints
...

## 6. Design Direction
...

## 7. Success Metrics
...

## 8. Open Questions ⚠️
- [ ] Q01 · [question] · impact: blocker/important/nice-to-know

## 9. Scoring Criteria 🎯
> Every item here must be satisfied to pass the evaluation

| Criteria | Score | Feature | Type |
|----------|-------|---------|------|
| [criterion name] | [score]/[total] | F01 | functional |

**Minimum viable:** must score [X] from functional criteria  
**Score-bound features (Must have):** F01, F02, F03
```

### Output B — `brief.json`

```json
{
  "meta": {
    "project_name": "",
    "generated_at": "",
    "source_file": "",
    "tor_confidence": "high | medium | low"
  },
  "project_overview": { "objective": "", "scope": "", "out_of_scope": [] },
  "target_users": [
    { "persona": "", "context": "", "pain_points": [] }
  ],
  "core_features": [
    { "id": "F01", "name": "", "description": "", "priority": "Must | Should | Could", "flows": [] }
  ],
  "user_flows": [
    { "id": "UF01", "name": "", "steps": [], "entry_point": "", "exit_point": "" }
  ],
  "constraints": { "technical": [], "business": [], "regulatory": [], "timeline": "" },
  "design_direction": { "tone": "", "brand_refs": [], "platform": "", "breakpoints": [] },
  "success_metrics": [],
  "open_questions": [
    { "id": "Q01", "question": "", "impact": "blocker | important | nice-to-know" }
  ],
  "scoring_criteria": {
    "total_score": null,
    "passing_threshold": null,
    "categories": [
      {
        "id": "SC01",
        "name": "",
        "weight": 0,
        "items": [
          { "id": "SC01-1", "name": "", "score": 0, "maps_to_feature": "F01", "type": "functional | technical | process | document" }
        ]
      }
    ],
    "minimum_viable": {
      "description": "",
      "must_have_features": [],
      "must_have_score": null
    }
  }
}
```

After generating, log to stdout:
```
[designops-pipeline] ✓ Step 1+2 complete
  → {OUTPUT_DIR}/brief.md
  → {OUTPUT_DIR}/brief.json
  Project: [name] · Features: 3 Must / 2 Should / 1 Could · Open Q: 4
  Scoring: [X] criteria · Must-have features: F01, F02, F03
```

---

## Step 2.5 — Product Intelligence Layer

> **Full spec: `references/intelligence-layer.md`** — read it before generating.

Reads `brief.json` (facts) → produces `intelligence.json` (interpretation). This is the bridge
that stops the pipeline from jumping requirements → UI. It infers **10 measurable product
dimensions**, each with **evidence + confidence**, and rolls them up into **`design_directives`**
that Step 3 consumes:

`User Types · User Expertise · User Goals · Core Tasks · Workflow Complexity · Data Density · Error Tolerance · Accessibility Needs · Compliance Requirements · Decision Criticality`

```
design_directives = { density_target 1-5, guidance_level, safeguard_level,
                      a11y_target, mandatory_flows[], navigation_model, trust_emphasis }
```

Rules: infer (don't restate); **evidence or silence** (ungrounded → `confidence:low` + open_question);
scales not prose; obey the **cross-dimension invariants** (e.g. `safety_critical ⇒ error_tolerance ∈ {low,zero}`; public-sector ⇒ AAA).

Gate: `python3 scripts/validate_intelligence.py {OUTPUT_DIR}/intelligence.json {OUTPUT_DIR}/brief.json`.
If `overall_confidence=low`, the gate emits `constrain_downstream=true` → Step 3/4 produce wireframe-level output + a human gate.

> This replaces the old fixed industry preset — `design_directives` is derived per-project, so any industry is expressible without code changes.

---

## Step 3 — User Flows

Takes `brief.json` (raw `user_flows`) + `intelligence.json` (`design_directives`) → **`flows.json`** — flows *refined* by the directives, not raw copies. No design system needed yet.

Refine each flow:
- `navigation_model` → echo it + shape how flows connect (hub_spoke = home hub + spokes)
- `safeguard_level` → inject confirm / preview / undo steps on risky actions (`step.safeguard`)
- `mandatory_flows` → **add an injected flow** per directive (consent, privacy_notice…) with `source_flow_ref:null`
- `decision_criticality` decision points → mark `step.decision:true` where the user commits a high-stakes choice

```jsonc
flows.json = { meta, navigation_model,
  flows: [{ id, name, source_flow_ref, user_type_ref, goal_ref,
            steps: [{ n, action, decision, safeguard }], entry, exit, directives_applied: [] }],
  mandatory_flows: [{ name, reason, injected }] }
```

Gate: `validate_flows.py {OUTPUT_DIR}/flows.json {OUTPUT_DIR}/intelligence.json {OUTPUT_DIR}/brief.json`
(checks nav_model matches the directive, refs resolve, every directive `mandatory_flow` appears).

---

## Step 3.5 — Screen Inventory & Component Mapping

Takes `flows.json` + `intelligence.json` + a design system → **`screen-inventory.json`** (machine, gated) **+ `design-first-draft.md`** (the human breakdown rendered from it). **Derive screens from flows** (each flow → its screens), mapping components from `design_directives`, not raw features.

```jsonc
screen-inventory.json = { meta, screens: [{ id, name, flow_refs: [], user_type_ref,
  priority: "Must|Should|Could", purpose, layout_primitive,   // card|table|dashboard|form|list|detail|wizard_step|hub
  components: [<from DS inventory>], gaps: [{ name, status: "missing|partial", recommendation }],
  directive_drivers: [] }] }
```

**Coverage rule (enforced):** every flow in `flows.json` must have ≥1 screen; every `screen.flow_refs` must resolve.

Gate: `validate_screens.py {OUTPUT_DIR}/screen-inventory.json {OUTPUT_DIR}/flows.json`.

### Design system input

```bash
--ds ../looloo-design-system/          # local folder
--ds ~/projects/acme-ds/       # absolute path
--ds https://github.com/org/ds # auto git clone → /tmp/ds-repo/
```

No `--ds` → halt immediately:
```
[designops-pipeline] ERROR: specify a design system path with --ds <path>
```

---

### Read the Design System

Scan in this order, stopping when you have enough information:

```
1. README.md / CONTRIBUTING.md     → overview · conventions
2. components/ · src/components/   → component list
3. tokens/ · design-tokens/        → color · spacing · typography
4. docs/ · stories/ (Storybook)    → usage patterns
5. index.ts · index.js             → exported surface
```

Build a component inventory before mapping:
```json
{
  "available_components": ["Button", "Card", "Modal"],
  "token_system": { "colors": [...], "spacing": [...] },
  "conventions": "PascalCase · variant prop pattern"
}
```

---

### Map Features → Components

| Feature | Components used | Gap (must build) | Notes |
|---------|-----------------|------------------|-------|
| Login form | Input · Button · Card | — | |
| Dashboard | DataTable | Chart | needs custom |

---

### Output — `design-first-draft.md`

```markdown
# [Project Name] — Design First Draft
> Source: brief.json + [DS path] · Generated: [DATE]

## Screen Inventory
| Screen | Flow | Priority |
|--------|------|----------|
| Login  | UF01 | Must     |

---

## [Screen Name]

**Purpose:** ...  
**Flow:** UF01 → step 1 → step 2

**Layout:**
- Header: [Component]
- Body:   [Component] + [Component]
- Footer: [Component]

**Component usage:**
\`\`\`jsx
<PageLayout>
  <Header title="..." />
  <ComponentName variant="primary" />
</PageLayout>
\`\`\`

**Design decisions:**
- Use `color.surface.elevated` for the card background — clearer hierarchy
- Use variant `primary` instead of `ghost` — this is the primary action

**Gaps:**
- [ ] No `<Chart>` in the DS yet → needs a new design

---

## Component Gap Report

| Component | Status | Recommendation |
|-----------|--------|----------------|
| Chart     | 🔴 Missing  | recharts + wrap as a DS component |
| DataGrid  | 🟡 Partial  | extend the existing Table |
| Button    | 🟢 Ready    | use as-is |

## Token Usage Guide
| Context | Token | Value |
|---------|-------|-------|
| Page bg | `color.background.base` | #F8F9FA |
| Primary | `color.brand.primary` | #0066FF |
```

After generating, log:
```
[designops-pipeline] ✓ Step 3 complete
  → {OUTPUT_DIR}/design-first-draft.md
  Screens: 4 · Components: 6 existing / 2 gaps
```

---

## Step 3.7 — Edge-Case Analysis

> Read `references/edge-cases-layer.md` first (taxonomy + generation prompt + citations). Runs after
> Screen Inventory, before the build — once flows + screens exist but before anything is coded.

The **front end of the edge-case spine.** Enumerate the non-happy-path conditions every Must screen
has to survive — empty data, bad input, a failed request, a destructive click — so the build has a
contract to satisfy and Step 4.7 **gate 9** has something to verify. Same traceability shape as the
intent spine (`feature → task → flow → screen → route`), with **edge case** as one more contract.

The taxonomy is **not** invented per project — it is the cross-product of two established frameworks
(so a reviewer can trace the reasoning to a source):
- **The UI Stack** (Scott Hurff) — every screen has five states: **Ideal · Empty · Error · Partial ·
  Loading**. The `ui_state` axis; maps onto `screen-inventory.json`'s declared `states`.
- **CORRECT** (Hunt & Thomas, *Pragmatic Unit Testing*) — seven boundary dims for input/data:
  **C**onformance · **O**rdering · **R**ange · **R**eference · **E**xistence · **C**ardinality ·
  **T**ime. The `correct_dim` axis.

Walk every Must screen through the UI Stack, walk its data through CORRECT, then **set severity from
`intelligence.json`, not taste**: low/zero `error_tolerance` forces error + input-validation edges to
`must`; high/safety_critical `decision_criticality` forces destructive confirms (and undo) to `must`;
dense `data_density` forces a partial/overflow edge; `guidance_level=guided` forces an empty edge.

```jsonc
edge-cases.json = { meta: { …, driven_by: { error_tolerance, decision_criticality, … } },
  edge_cases: [{ id, ui_state: "empty|error|partial|loading|ideal",
    correct_dim: "conformance|ordering|range|reference|existence|cardinality|time",  // optional
    category, trigger, expected_handling, severity: "must|should|could",
    maps_to_screen: "<screen-inventory id>", maps_to_flow: "<flows id>" }] }
```

Gate: `validate_edgecases.py {OUTPUT_DIR}/edge-cases.json {OUTPUT_DIR}/screen-inventory.json {OUTPUT_DIR}/flows.json {OUTPUT_DIR}/intelligence.json`
— enforces id/enum structure, **traceability** (every edge maps to a real screen/flow), the
**declared-state-needs-a-reason** rule (a Must screen that declares an empty/error state has ≥1 edge
explaining it), and the **directive floors** above. Cross-file artifacts are optional → the gate
skips dependent checks with a warning when one is absent (runs standalone).

After generating, log:
```
[designops-pipeline] ✓ Step 3.7 edge-case analysis
  → {OUTPUT_DIR}/edge-cases.json
  Edge cases: [N] ([X] must / [Y] should / [Z] could) · floors: error_tol=[…] criticality=[…]
```

---

## Step 4 — POC Delivery Package

Takes `design-first-draft.md` → scaffolds a Next.js prototype that **imports** `@npsin-oreo/design-system` as the base

> Full reference: `references/shadcn-prototype.md`  
> **POC component library + mock data patterns: `references/poc-patterns.md`** — read before generating screens
> Claude Code command: `/generate-prototype` — spec is in `commands/generate-prototype.md`

### Use the POC component library (from `references/poc-patterns.md`)

Instead of scaffolding empty screens, assemble from ready-made patterns so it's presentable immediately:

| Pattern | Use when | Directive that favors it |
|---------|----------|--------------------------|
| `KPICard` | dashboard has a key metric/number | `density_target ≥ 4`, `trust_emphasis high` |
| `StatusBadge` | there's a state (waiting/in-progress/done) | tasks with status; `safeguard_level ≥ strict` |
| `POCDataTable` (+ pagination) | data-heavy list/table | `density_target ≥ 4` |
| `EmptyState` · `ErrorState` · Skeleton | **every main screen** needs at least 1 | always |

**Mock data rule:** must be realistic to the domain — real names, real IDs/record numbers, real document numbers · **never** "User 1" / "Lorem ipsum"
Drive density/safeguards/navigation/a11y from `intelligence.json` → `design_directives` (Step 2.5), not from a fixed preset.

### Import the DS package (Model A)

The build **imports** `@npsin-oreo/design-system` — it never copies a DS. `GITHUB_TOKEN` is required
(GitHub Packages needs auth even for public packages):

```bash
export GITHUB_TOKEN=$(gh auth token)
bash .claude/skills/designops-pipeline/scripts/setup-prototype.sh --out {OUTPUT_DIR}
# optional: --ds-pkg @npsin-oreo/design-system@0.2.0 (pin) · --ds-name · --ds-registry "" (public-npm/tarball)
```

- Installs the **pinned** DS (`--save-exact`) into `node_modules`, writes a scaffold `.npmrc` (scope →
  GitHub Packages) + `transpilePackages` (the DS ships source `.tsx`), an `@/*` tsconfig alias, and a
  local `lib/utils.ts` (`cn`, which the package does not export). **No token → hard error, no fallback.**
- **Components are immutable** (in `node_modules`): screens import from `@npsin-oreo/design-system/<name>`;
  customise via Step 2.6 token + brand-scoped `[data-slot=*]` overrides in `globals.css`, never by editing.
- ⚠️ **Fonts: load via `next/font` in `layout.tsx`, never a CSS `@import` in `globals.css`.** The DS `@import "@npsin-oreo/design-system/styles.css"` is inlined first, so a font `@import` ends up after other rules and breaks the "`@import` must come first" rule — `next build` tolerates it but **Turbopack dev 500s on every route**. Use `next/font/google` (self-hosted; exposes a `--font-*` variable that `--font-sans` points at). The Step 4.7 audit **gate 5** (`lint_font_imports.py`) blocks a remote-font `@import`.
- Always a **real** `node_modules` (never symlinked — a symlinked one breaks tsc's `@types/react` resolution).
- **Version contract:** the published package must track the component API the screens target. Pin it
  (`--ds-pkg …@x.y.z`); a drift (e.g. a missing `AlertAction` export) breaks the build until the DS is
  published to match. Read the DS inventory from a `../looloo-design-system` source checkout (`--ds`).

`@npsin-oreo/design-system` provides:
- shadcn/ui (radix) — 57 components, exported as `@npsin-oreo/design-system/<name>` (+ `/theme-provider`, `/styles.css`, `/token-contract.json`)
- the neutral-theme tokens (Step 2.6 overrides them) · Tailwind v4 wiring · Next.js 16 / React 19 peers

---

### Output structure

```
{OUTPUT_DIR}/prototype/          ← cloned from the starter
├── app/
│   ├── globals.css              ← tokens already live here — don't edit
│   ├── layout.tsx               ← fonts (next/font, NOT a CSS @import) + ThemeProvider + Toaster
│   ├── (auth)/
│   │   └── [screen]/page.tsx    ← auth screens from the brief
│   └── (dashboard)/
│       ├── layout.tsx           ← SidebarProvider + AppSidebar
│       └── [screen]/page.tsx    ← dashboard screens from the brief
├── components/
│   ├── ui/                      ← shadcn components — don't wrap
│   └── [feature]/               ← feature components from the brief
└── docs/
    └── poc-handoff.md           ← handoff doc for Dev
```

---

### Token rules (never violate)

```tsx
// ❌ never hardcode colors, in any case
className="text-gray-500 bg-[#F8F9FA]"
style={{ color: '#111827' }}

// ✅ semantic tokens only
className="text-muted-foreground bg-card"
className="text-destructive bg-background"
```

Token map from Figma → Tailwind (1:1):

| To display | Tailwind class |
|------------|----------------|
| Page background | `bg-background` |
| Card surface | `bg-card text-card-foreground` |
| Primary action | `bg-primary text-primary-foreground` |
| Secondary text | `text-muted-foreground` |
| Hover state | `hover:bg-accent` |
| Error | `text-destructive` |
| Border | `border-border` |
| Input border | `border-input` |
| Focus ring | `ring-ring` |

---

### Screen scaffolding — per screen

Read the `Screen Breakdown` in `design-first-draft.md`, then build:

#### Auth screens
```tsx
// app/(auth)/[screen]/page.tsx — Server Component
export default function LoginPage() {
  return (
    <main className="flex min-h-svh items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>[Screen title]</CardTitle>
          <CardDescription>[Purpose from the brief]</CardDescription>
        </CardHeader>
        <CardContent>
          <[ScreenName]Form />  {/* "use client" lives here */}
        </CardContent>
      </Card>
    </main>
  )
}
```

#### Dashboard screens
```tsx
// app/(dashboard)/[screen]/page.tsx — Server Component
export default function [ScreenName]Page() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">[Screen title]</h1>
          <p className="text-muted-foreground">[Description]</p>
        </div>
        <Button>[Primary action from the brief]</Button>
      </div>
      <[ScreenName]Content />
    </div>
  )
}
```

#### Dashboard layout (create once)
```tsx
// app/(dashboard)/layout.tsx
import { SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/layout/app-sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />  {/* nav items from USER_FLOWS in the brief */}
      <main className="flex-1 overflow-auto">{children}</main>
    </SidebarProvider>
  )
}
```

---

### Component selection from design-first-draft.md

Use components by the appropriate group:

| Use case | Component | Import |
|----------|-----------|--------|
| Container | `Card` + `CardHeader/Content/Footer` | `@/components/ui/card` |
| Form fields | `Field` + `FieldLabel` + `FieldError` | `@/components/ui/field` |
| Text input | `Input` | `@/components/ui/input` |
| Dropdown | `Select` | `@/components/ui/select` |
| Action | `Button` (variant: default/outline/ghost) | `@/components/ui/button` |
| Data list | `Table` + `TableHeader/Body/Row/Cell` | `@/components/ui/table` |
| Status | `Badge` | `@/components/ui/badge` |
| Navigation | `Tabs` | `@/components/ui/tabs` |
| Confirmation | `AlertDialog` | `@/components/ui/alert-dialog` |
| Slide panel | `Sheet` | `@/components/ui/sheet` |
| Loading | `Skeleton` | `@/components/ui/skeleton` |
| No data | `Empty` + `EmptyHeader/Title/Description` | `@/components/ui/empty` |
| Notification | `sonner` (toast) | `@/components/ui/sonner` |
| Pagination | `Pagination` | `@/components/ui/pagination` |
| Search | Combobox pattern (Popover + Command) | compose |
| Date input | DatePicker pattern (Popover + Calendar) | compose |
| Large data | DataTable pattern (Table + Pagination) | compose |

---

### Gap component — when a component isn't in the DS

If `design-first-draft.md` names a component not in the shadcn inventory → create a `GapPlaceholder`:

```tsx
// components/ui/gap-placeholder.tsx
export function GapPlaceholder({ name, spec }: { name: string; spec?: string }) {
  return (
    <div className="flex min-h-16 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-destructive/50 bg-destructive/5 p-4 text-center">
      <span className="text-sm font-medium text-destructive">🔴 {name}</span>
      {spec && <span className="text-xs text-muted-foreground">{spec}</span>}
    </div>
  )
}
```

---

### Coding rules (Tailwind v4 + React 19)

```tsx
// ✅ size-4 instead of w-4 h-4
<Icon className="size-4" />

// ✅ React 19 ComponentProps — no forwardRef needed
function MyComp({ className, ...props }: React.ComponentProps<"div">) {}

// ✅ Server Component by default
// "use client" only where there's: useState · useEffect · event handlers · router hooks
// always push "use client" to the leaf component, never on the page

// ✅ cn() for className merging
import { cn } from "@/lib/utils"
className={cn("base-class", conditional && "extra-class", className)}
```

---

### Accessibility checklist (every item must pass before handoff)

- [ ] `aria-label` on every icon-only `<Button size="icon">`
- [ ] `<DialogTitle>` + `<DialogDescription>` on every Dialog/AlertDialog/Sheet
- [ ] Don't remove `focus-visible:ring-2 focus-visible:ring-ring`
- [ ] Color isn't the only signal — pair it with an icon or text label
- [ ] `alt` on every `<Image>`

---

### `docs/poc-handoff.md` — Dev handoff doc

```markdown
# [Project Name] — POC Handoff

## Tech Stack
Next.js 16 · React 19 · Tailwind CSS v4 · shadcn/ui (radix-nova)

## Run locally
npm install && npm run dev  # http://localhost:3000

## Screen inventory
| Screen | Route | Flow | Priority | Status |
|--------|-------|------|----------|--------|
| [Name] | /[path] | UF01 | Must | ✅ done |

## Component gaps (to implement)
| Component | Screen | Spec | Effort |
|-----------|--------|------|--------|
| [Name]    | [screen] | [brief spec] | M/L/XL |

## Token overrides needed
If the project's brand color differs from the neutral theme → edit `app/globals.css`
Variables to change: `--primary` · `--secondary` · `--accent`

## Open questions
[from OPEN_QUESTIONS in brief.json]
```

After generating, log:
```
[designops-pipeline] ✓ Step 4 complete
  → {OUTPUT_DIR}/prototype/ (Next.js app ready)
  → {OUTPUT_DIR}/prototype/docs/poc-handoff.md
  Screens: [X] · Gap components: [Y] · npm run dev → http://localhost:3000
  Ready to send to Dev ✓ · Ready for Figma MCP (Step 5) ✓
```

---

## Step 4.6 — Critique (quality loop)

> Read `references/critique-framework.md` first (it points to `references/design-review.md` for the full rubric) — runs after Step 4 builds the prototype, before handoff
> This is the "loop" that polishes the UI, instead of scaffold-and-done

After generating the prototype, run a **scored review** of every main screen:

1. Score the **6 weighted dimensions** (Visual Hierarchy 20 · Consistency 20 · Accessibility 20 · Usability 20 · Responsiveness 10 · Performance 10) → compute the overall (≤6 = rework before ship).
2. Run **Nielsen's 10 heuristics**; flag each violation by number (H1…H10).
3. Run the **anti-slop gate** (`aesthetics/taste/design-taste.md` Banned Defaults): pure `#000/#fff`, identical equal-weight cards, everything centered, rainbow accents, emoji-as-icons, colored left-border strips, em-dash/marketing-filler copy → each is a **Major** finding. The screen must earn `aesthetic.json`'s `mood_adjective`.
4. The detailed 4-layer checklist (hierarchy / IA / consistency / context-fit, tied to `design_directives`) is in `critique-framework.md` — use it to find the specifics.
5. **UX copy** (`references/ux-writing/voice-tone.md`): buttons frontload the verb + name the outcome; errors are what→why→how; empty states are value→action; confirm buttons restate the action (type-to-confirm for irreversible ones, per `safeguard_level`). Any bare "No data"/"Error" or "OK"-only confirm is a Major finding.
6. **Mobile usability** (`references/mobile-usability.md`) for mobile-first/responsive products: touch targets ≥44px, primary action in thumb reach, correct input types/keyboards, 320px reflow, no hover-only affordances. Scores the Responsiveness dimension; a miss is at least a Major finding.

Output (per screen or combined): the scored table + a prioritized findings table
`# · Severity (Critical→Major→Minor→Enhancement) · Category · Location · Finding · Recommendation · Heuristic`, plus:
```markdown
### ✅ What's Working              — [2-3 items]
### ⚡ Quick Wins (< 15 min)        — [high-impact fixes]
```

7. **Judge pass (separate from the build).** The agent that built the prototype also wrote the
   scores above, so they skew optimistic. Run one more pass **in a skeptical judge's voice** — its
   only job is a pass/fail: *would a real, demanding user of this product accept this for the job
   it's for?* Look for the failure the optimism glossed over (a dead primary action, an unreachable
   state, a region that "looks done" but is empty). Record a single `judge_verdict` (true|false) +
   `judge_reason`. **A `false` verdict caps `overall_score` at 2.0** — looks never rescue a broken
   core task. Schema + rationale: `references/critique-framework.md` → "Structured output + judge".

**Auto-fix rule:** fix every 🔴 Critical + ⚡ Quick Win immediately in the prototype · log 🟡 High in `poc-handoff.md` for Dev

Save **both** outputs beside the prototype:
- `{OUTPUT_DIR}/prototype/docs/critique.md` — the full prose critique (for the designer)
- `{OUTPUT_DIR}/prototype/docs/critique.json` — the structured scores + judge verdict (for the gate)

Then run the gate (blocks if the judge verdict and the score disagree):
```bash
python3 .claude/skills/designops-pipeline/scripts/validate_critique.py {OUTPUT_DIR}/prototype/docs/critique.json
```

When done, log:
```
[designops-pipeline] ✓ Step 4.6 critique
  Screens reviewed: [X] · Judge verdict: [pass/fail] · Overall: [N]/10 · Critical fixed: [Y] · Quick wins applied: [Z] · High → handoff: [W]
```

---

## Step 4.7 — Audit gate (before handoff/Figma)

> **Run the objective gate first — don't eyeball it:**
> ```bash
> python3 .claude/skills/designops-pipeline/scripts/audit_prototype.py \
>   {OUTPUT_DIR}/prototype --a11y <AA|AAA from design_directives.a11y_target> \
>   --report {OUTPUT_DIR}/prototype/docs/audit-report.md
> ```
> Exit 1 = **BLOCKED**. This recomputes WCAG contrast from globals.css (oklch → sRGB, light + dark)
> and runs `lint_hardcodes.py` over the screens — categories A + B below are **machine-checked**, not
> judged. It audits the **generated surface only**: `components/ui` (vendored shadcn primitives) and
> any `docs/` dir are auto-excluded, so you can point it at the whole prototype (no `--scan` needed).
> Use `--include-vendored` to audit everything. Then read `references/audit-checklist.md` for the qualitative category C items.

Audit the prototype across 3 categories (see the severity matrix in the reference):

| Category | What to check | gate |
|----------|---------------|------|
| **A. Token Compliance** | `audit_prototype.py` → `lint_hardcodes.py`: no raw hex/px/ms or raw Tailwind palette (`bg-gray-500`) that should be a token | 🔴 = block (script) |
| **B. A11y / WCAG** | `audit_prototype.py` recomputes contrast for the essential fg/bg pairs at `design_directives.a11y_target`, light + dark | 🔴 = block (script) |
| **C. Component Quality** | Consistent naming · complete states (hover/focus/disabled/loading/error/empty) · no avoidable `any`. **Component-usage contracts now partly machine-checked by gate 4** (see below) | gate 4 🔴 = block (script) · rest 🟡 = handoff note (agent) |

> `audit_prototype.py` also runs a **UX-copy gate** (gate 3, via `references/ux-writing/scripts/check_no_emoji.py`): no emoji and no em/en-dash in product UI → 🔴 block. Full copy rules: `references/ux-writing/voice-tone.md`.

> …and a **component-contract gate** (gate 4, via `scripts/lint_component_contracts.py`): enforces the Button/Dialog/Field usage contracts from `references/component-contracts.md` as runnable a11y checks — icon-only buttons need an accessible name, every `DialogContent`/`AlertDialogContent` needs a `DialogTitle`, every `Input` with an `id` needs a matching `FieldLabel htmlFor` → 🔴 block. Fuzzier rules (one-primary-per-view, missing `DialogDescription`, destructive-variant, `aria-invalid` on errored fields) print as **advisories** and never fail the gate. Escape a justified case with a `ds-allow-contract` comment.

> …and a **font-loading gate** (gate 5, via `scripts/lint_font_imports.py`): a remote-font CSS `@import` (`fonts.googleapis.com` etc.) in `globals.css` → 🔴 block — it 500s the Turbopack dev server; load fonts with `next/font` instead.

> …and a **theme-fidelity gate** (gate 6, via `scripts/lint_theme_fidelity.py`): the full identity theme Step 2.6 committed in `brand.config.json` (`colors.{light,dark}`) must actually be applied in the prototype's `globals.css`. If `card`/`secondary`/`muted`/`accent`/`border` or the dark set drifted back to the shadcn-neutral default — the "brand colour slapped on a neutral skeleton" regression — it 🔴 blocks. It compares the committed value to the rendered token (oklch→sRGB, same math as gate 2), so it is deterministic, not a judgement call. Discovers `brand.config.json` beside the prototype, or pass `--theme <path>`; skips cleanly when no theme is committed.

> …**directive-fidelity** (gate 7, `scripts/lint_directive_fidelity.py`) and **screen-coverage** (gate 8, `scripts/lint_screen_coverage.py`) close the **intent-traceability spine** — the build must honor the upstream intent, not just look right. Gate 7 reads `intelligence.json`: a destructive action must be guarded by an `AlertDialog`/confirm when `safeguard_level` ∈ {standard,strict,maximal}, and a guided product (`guidance_level=guided`) must render at least one empty-state (density/nav are advisory). Gate 8 reads `screen-inventory.json`: every **Must** screen must exist as a built `app/<route>/page.tsx` and render each declared `state` (loading/empty/error). Both auto-discover their artifact beside the prototype (or `--intel`/`--screens`) and skip cleanly when absent. They are the build-side end of the feature→task→flow→screen→route traceability that `validate_intelligence.py` (every Must `core_feature` is served by a task via `feature_refs`) and `validate_screens.py` (every Must feature + every `scoring_criteria` must-have has a screen) enforce upstream.

> …**edge-case coverage** (gate 9, `scripts/lint_edge_coverage.py`) closes the **edge-case spine** — the back end of Step 3.7. It reads `edge-cases.json`: every **Must** edge case must have detectable handling in the screen it maps to — an empty/error/loading/partial state, inline validation (`FieldError`/`aria-invalid`/schema), or a destructive confirm (`AlertDialog`/type-to-confirm), chosen by the edge's `ui_state`/`category`. It resolves each `maps_to_screen` to a route via `screen-inventory.json` (or scans the whole app as a coarse fallback), auto-discovers `edge-cases.json` beside the prototype (or `--edges`), and skips cleanly when absent. This is the build-side end of the `screen → edge case` traceability that `validate_edgecases.py` enforces upstream (every edge traces to a real screen + the directive floors), so a screen can't ship with only its happy path.

> …**font fidelity** (gate 10, `scripts/lint_font_fidelity.py`) closes the typography half of the Step 2.6 bridge. Gate 6 verifies the committed *colours* are applied; gate 10 verifies the committed **`font_sans`** is too. It reads `brand.config.json` (or `aesthetic.json`), extracts the primary family (e.g. `Inter` from `"Inter", "Noto Sans Thai", …`), and FAILS when neither `app/layout.*` nor `globals.css` references it — i.e. the scaffold kept its default loader (Geist) and the font directive silently no-opped. (Gate 5 only forbids a remote `@import`; gate 6 only checks colours — nothing else caught this, and for a Thai TOR committing `Noto Sans Thai` it is a real regression.) Load the committed family via `next/font` and wire `--font-sans`. Auto-discovers the theme beside the prototype (or `--theme`); skips cleanly when no `font_sans` is committed.

> …**axis fidelity** (gate 11, `scripts/lint_axis_fidelity.py`) extends the same idea to the **non-colour axes**. Step 2.6's `axes` block resolves a system on six facets (color · typography · shape · elevation · spacing · motion); gates 6/10 cover colour + font, gate 11 covers the rest's machine-readable `resolved` metrics. It reads `aesthetic.json` and FAILS when a declared metric isn't in the built `globals.css`: `typography.resolved.base_line_height` / `heading_weight_cap` (the type ramp re-pointed via `@theme --text-*` and a heading weight rule), `shape.resolved.pill_slots[]` (a brand-scoped `[data-slot=…]{ @apply rounded-full }`), `motion.resolved.easing` (defined as a CSS var AND applied to a non-card slot). This catches the "declared but not applied" no-op — the same class as the font bug — for type/shape/motion. **The two bridge techniques it expects are no-hardcode-safe:** re-point Tailwind's `@theme` (sizes in `rem`, line-heights unitless, tracking in `em`) so existing `text-*` utilities inherit the brand without editing JSX, and brand-scoped `[data-slot=*]` rules (`@apply` utility classes + CSS vars, never raw `px`/`ms`) so component specs land without editing `components/ui`. Auto-discovers `aesthetic.json` beside the prototype (or `--aesthetic`); skips cleanly when there's no `axes` block.

> **a11y target** comes from `intelligence.json` → `design_directives.a11y_target` (Step 2.5 already enforced the floor + public-sector ⇒ AAA invariant). Pass it straight to `--a11y` (the script maps `AA_plus`→AAA).

`audit_prototype.py` writes `{OUTPUT_DIR}/prototype/docs/audit-report.md` (gates A + B); append category C notes to it:
```
DesignOps Audit Report — [project]
A. Token Compliance:  [🔴/🟡/🟢] — X violations
B. A11y / WCAG [AA|AAA]: [🔴/🟡/🟢] — X violations
C. Component Quality: [🔴/🟡/🟢] — X issues
CRITICAL → [list to fix before handoff]
```

log:
```
[designops-pipeline] ✓ Step 4.7 audit — [PASS | BLOCKED: X critical]
  → {OUTPUT_DIR}/prototype/docs/audit-report.md
```

If BLOCKED → loop back, fix per the report, and re-audit until it passes before moving to Step 5.

---

## Step 4.7b — Runtime audit (optional)

> Opt-in. Complements the static Step 4.7 by **rendering** the built page (Playwright headless Chrome)
> and checking what source can't show. Template + enable steps: `references/runtime-audit/README.md`.
> Degrades gracefully — without Playwright every gate prints SKIPPED and exits 0 (never blocks default).

Runs on `out/index.html` (after `npm run build`): **axe-core** WCAG A/AA (button/link names, image alt,
`lang`, `<title>`, ARIA, landmarks, heading order), **hover/focus-state contrast** (`verify_states`),
modal **focus-trap** (`verify_focustrap`, when a trigger selector is given), plus a render-based
**anti-slop** report (`taste_audit`, advisory). Blocking gates exit 1.
```bash
# inside output/prototype after build — see references/runtime-audit/README.md
node scripts/runtime/audit_runtime.mjs out/index.html [--dark] [--open=<sel> --dialog=<sel>]
```
This is the layer that catches a nameless button / missing `alt` / no `lang` / a hover color that
fails contrast — none of which the static gate can see.

---

## Step 4.8 — Storybook QA layer (optional)

> Opt-in. Off by default (Storybook + Playwright + Vitest are heavy; default prototype builds stay fast).
> Template + exact enable steps: `references/storybook/README.md`. Lives in the **built prototype** (`output/prototype/`), never in the imported `@npsin-oreo/design-system` package.

Adds a component explorer + **`@storybook/addon-a11y`** (axe-core on every rendered story — a runtime
a11y pass that complements the static `audit_prototype.py` gate) + a light/dark toggle. Enable it when
you want per-component state coverage or a CI a11y gate:
```bash
# inside output/prototype/ (already npm-installed) — see references/storybook/README.md
npm run gen:stories && npm run test-storybook   # headless axe pass
npm run storybook                                # interactive explorer at :6006
```

---

## Step 5 — Figma output (repeatable, generated from artifacts)

> Runs separately after Step 4 — **not part of `run_pipeline.sh`**. Agent-driven via the **Figma
> MCP** (needs the Figma MCP server connected + a target `figma.com/design/...` file).
> No Figma MCP? Skip — Steps 1–4.7 already produce a runnable, audited prototype + handoff doc.

Produces **one Figma file / 5 pages** (Cover · Foundations · Components · Screens · Flows) built
from the pipeline artifacts, in the strict order **variables → components → screens → flows**. Full
contract: **`references/figma/output-spec.md`**.

**Process:**
1. **Prep (deterministic):** `python3 scripts/figma_prep.py --tokens <DS>/tokens.json --aesthetic
   output/aesthetic.json --screens output/screen-inventory.json --flows output/flows.json
   --brief output/brief.json --out /tmp/figbuild` → compact token blobs + `theme.json` +
   `manifest.json` (device size, components, screens, flows). Skips speculative brand hues
   (`cerulean-blue,coral`) by default.
2. Load skills **`figma-use` + `figma-generate-library`**; the MCP tools are deferred as
   `mcp__figma__*` (fetch via `ToolSearch`).
3. **Variables** — import the library layer + trim `brand-color` to primary/secondary + build the
   **Theme** semantic collection (Light/Dark, live-aliased into the library) + set default font
   **Noto Sans Thai** (brand override if `aesthetic.json` names another). Recipe:
   `references/figma/01-variables.md`.
4. **Components** — DS components as variant sets, bound to Theme tokens. `references/figma/02-components.md`.
5. **Screens** — each `screen-inventory.json` entry as a frame at the device size, composed from
   component instances, Theme=Light. `references/figma/03-screens.md`.
6. **Flows** — one flow per Action (screens as nodes + decision diamonds + green happy / red
   error→error-state). `references/figma/04-flows.md`.

Validate each layer with `get_screenshot` before the next. Pitfalls (token-blob size limit,
`setBoundVariableForPaint`, FILL-after-append, font loading, diamond/arrow shapes):
**`references/figma/mcp-gotchas.md`**.

---

## Error handling

| Situation | How to handle it |
|-----------|------------------|
| TOR has little/unclear info | Brief with what's available · add open questions · flag `tor_confidence: low` |
| PDF is scanned | Rasterize page by page → read with vision |
| DS has no README | Scan `components/` directly |
| Component not in the DS | Record in the gap report · don't make it up |
| Scoring table is an image / scanned table | Rasterize that page → read with vision → extract normally |
| A scoring criterion maps to no feature | Create a new feature in `CORE_FEATURES`, priority `Must` · note "derived from scoring" |
| TOR is >60% non-product content | Log a warning · brief with the relevant part · flag `tor_confidence: low` · note in open questions |
| Very little requirement left after filtering | Halt · check with the user before continuing |
| DS has no token files | Build tokens.json from CSS/SCSS variables found in the codebase |
| Component not in the shadcn inventory | Create a `GapPlaceholder` component · record in poc-handoff.md |
| Prototype has a TypeScript error | Run `npm run typecheck` → fix before handoff |
| Critique finds a 🔴 Critical | Fix it in the prototype before the audit · don't let it reach handoff |
| Audit BLOCKED (🔴 critical remaining) | Loop back per `audit-report.md` and re-audit until it passes before Step 5 |
| Public-sector / accessibility-law signal | Step 2.5 sets `a11y_target = AAA` (enforced invariant) · UI copy must be clear, no jargon |
| Ambiguous product context | Don't force a bucket — set each `design_directives` dimension from evidence; low confidence → `constrain_downstream` + open_question |
| `intelligence.json` missing before Step 3 | Run Step 2.5 first — Component Mapping requires `design_directives` |

---

## References

Load when that step triggers — no need to load them all at once.

| File | Load when |
|------|-----------|
| `references/intelligence-layer.md` | Step 2.5 — Product Intelligence Layer (10 dims + design_directives + invariants) |
| `references/shadcn-prototype.md` | Step 4 — detailed prototype scaffolding |
| `references/poc-patterns.md` | Step 4 — component library (KPICard/StatusBadge/DataTable/states) + mock data |
| `references/critique-framework.md` | Step 4.6 — 4-layer critique, per-context templates |
| `references/audit-checklist.md` | Step 4.7 — full token + WCAG audit checklist + severity matrix |
| `references/sample-tor.md` | Sample TOR for testing the pipeline |
| `references/CLAUDE.md.template` | Template for a project that installs this skill |

> `poc-patterns` · `critique-framework` · `audit-checklist` are pulled from the `designops-loop` skill (BUILD/PROTOTYPE/CRITIQUE/AUDIT) and wired into the designops-pipeline pipeline.
