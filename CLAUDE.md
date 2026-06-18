# CLAUDE.md
# Place this file at the root of any project that uses the designops-pipeline skill

## Environment — self-contained

This project is **standalone** — the core pipeline (TOR → brief → draft → prototype) depends on no external repo.

| Path | Role | When used |
|------|------|-----------|
| `./design-system/` | **DS (vendored, in-repo)** — shadcn-skills-design-starter source-only (~2MB, 52 components, no node_modules) | Step 3 (`--ds` default) + base for the POC prototype |

> The standalone DS is being split into an imported package `@npsin-oreo/design-system` (Model A).
> Theming is owned by Step 2.6 → `brand.config.json` → the product scaffold. The old `--handoff`
> Step 4.5 token-bridge (pushing tokens into a whitelabel repo) is **deprecated** and not part of
> this flow — see `docs/ds-split/`.

`run_pipeline.sh` auto-resolves `--ds` in this order: `TOR_DS_PATH` env → `./design-system` (in-repo) → `../shadcn-skills-design-starter` (fallback)

```bash
# Core pipeline — standalone, no --ds needed (uses ./design-system automatically)
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --out ./output
```

> Note: `./design-system` is source-only — when building the actual prototype, the pipeline copies it to `output/prototype/` and runs `npm install` once there.

---

## Commands

### `/generate-prototype`
Generate Next.js POC screens from `design-first-draft.md`.  
Full spec: `.claude/skills/designops-pipeline/commands/generate-prototype.md`

```bash
/generate-prototype            # show Screen Inventory, then ask which screen to build
/generate-prototype --screen login
/generate-prototype --screen login,booking,dashboard
/generate-prototype --all      # generate every screen, ordered by priority
```

**brand.config.json** (optional) — place at the project root to override the neutral theme:
```json
{
  "project_name": "My App",
  "primary":   "oklch(0.35 0.18 264)",
  "radius":    "0.5rem",
  "font_sans": "\"Noto Sans Thai\", sans-serif"
}
```

---

## Skills

### designops-pipeline
Turns a TOR → design brief → first draft → POC prototype automatically, with a **quality loop**.

**Pipeline:** Step 1+2 brief (facts) → **Step 2.3 User Research** (`research.json`) + **Step 2.4 Competitive Analysis** (`competitive.json`) → **Step 2.5 Product Intelligence** (`intelligence.json` → `design_directives`, consumes the UX evidence) → **Step 2.6 Aesthetic Direction** (`aesthetic.json` + `brand.config.json`, the visual/taste layer) → **Step 3 Flows** (`flows.json`, refined from directives) → **Step 3.5 Screen Inventory** (`screen-inventory.json` + `design-first-draft.md`, flow→screen coverage) → Step 4 prototype → **Step 4.6 critique** → **Step 4.7 audit gate** → **Step 4.8 Usability Test** (`usability.json`) → Step 5 Figma. Each stage has its own JSON artifact + validator gate.

**UX layers (2.3 / 2.4 / 4.8)** are **hybrid + honesty-gated.** Each declares `meta.evidence_mode` (`inferred` | `hybrid` | `evidence_backed`) + `inputs_provided`. With no real inputs everything is `source:"inferred"` (a hypothesis, confidence ≤ medium) — the validators (`validate_research.py`, `validate_competitive.py`, `validate_usability.py`) reject any item marked `evidence` whose ref isn't in `inputs_provided` (no fabricated research), and usability must set `not_real_user_testing:true` with simulated walkthroughs only. Specs: `references/{user-research,competitive-analysis,usability-test}-layer.md`.

**Product Intelligence Layer** (Step 2.5) infers 10 measurable dimensions (user types/expertise/goals/tasks, workflow complexity, data density, error tolerance, accessibility, compliance, decision criticality) → an open `design_directives` object. Replaces the old fixed industry presets; industry-agnostic. Spec: `references/intelligence-layer.md`; gate: `scripts/validate_intelligence.py`.

**Aesthetic Direction Layer** (Step 2.6) commits a *visual* direction `design_directives` doesn't cover — picks one of **138 named design systems** (apple, linear-app, stripe, resend…) or an archetype from the vendored brand library, then resolves it into concrete, **contrast-checked** tokens. Output `aesthetic.json` + a ready-to-apply `brand.config.json`. Library + browser + anti-slop guide: `references/aesthetics/` (`scripts/design_systems.py list|search|show`); gate: `scripts/validate_aesthetic.py` (recomputes WCAG contrast from hex — never trusts the agent's self-reported ratio).

**Audit gate** (Step 4.7) is a real runnable check, not agent judgment: `scripts/audit_prototype.py` runs `lint_hardcodes.py` over the screens (no raw hex/px/Tailwind-palette) and recomputes WCAG contrast from the prototype's `globals.css` (oklch→sRGB, light + dark) at `design_directives.a11y_target`. Exit 1 = BLOCKED. It audits the generated surface only (`components/ui` + any `docs/` dir auto-excluded; `--include-vendored` to audit all). `references/audit-checklist.md` covers the qualitative category-C items. **Step 4.7b (optional)** adds a runtime gate (`references/runtime-audit/`, vendored from `ux-ui-agent-skills`): renders the built page in Playwright for axe-core a11y, hover/focus-state contrast, modal focus-trap, and render-based anti-slop — skips cleanly without Playwright.

**Folded design skills.** All 19 skills from `shadcn-skills-design-starter` are folded into the pipeline (vendored, standalone). The last 6 added — **ux-writing** (copy rules + `audit_prototype.py` gate 3: no emoji/em-dash), **image-to-code** (Step 2.6 infers an aesthetic from a TOR mockup), **brandkit** (Step 2.6 → full DTCG token foundation at `references/tokens/`, gated by `validate_tokens.py`/`validate_contrast.py`), **migrate-design-system** (bridge to Material/Apple/Fluent/Carbon via `aesthetics/design-systems/crosswalk.md`), **performance** (optional CWV add-on), **governance** (living-DS maintenance, out of the generation loop). Capability index + where each plugs in: `references/SKILLS.md`.

> Steps 4.6/4.7 + poc-patterns are pulled from the `designops-loop` skill and wired into the pipeline · references live in `.claude/skills/designops-pipeline/references/`

**Skill location:** `.claude/skills/designops-pipeline/`

**Trigger via command:**
```bash
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh [flags]
```

**Flags:**
| Flag | Meaning | Example |
|------|---------|---------|
| `--tor <path>` | TOR file (PDF or DOCX) | `--tor docs/tor.pdf` |
| `--tor-text "<text>"` | TOR text directly | `--tor-text "..."` |
| `--ds <path>` | Design system folder or GitHub URL | `--ds ./design-system` |
| `--brief <path>` | Reuse an existing brief.json, skipping steps 1+2 | `--brief output/brief.json` |
| `--out <dir>` | Output directory (default: `./tor-output`) | `--out ./output` |

**Environment variable:**
```bash
export TOR_OUTPUT_DIR=./output   # set the default output dir
```

## Common commands

```bash
# Full pipeline — read TOR + build draft from the design system
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --ds  ./design-system \
  --out ./output

# Steps 1+2 only — no design system yet
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --out ./output

# Step 3 only — brief.json already exists
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh \
  --brief ./output/brief.json \
  --ds    ./design-system \
  --out   ./output

# Validate brief.json without running the pipeline
python3 .claude/skills/designops-pipeline/scripts/validate_brief.py ./output/brief.json
```

## Output files

| File | Audience | Created in step |
|------|----------|-----------------|
| `brief.md` | Designer / PM review | 1+2 |
| `brief.json` | AI agent (step 3 input) | 1+2 |
| `research.json` | AI agent (personas/JTBD → intelligence evidence) | 2.3 |
| `competitive.json` | AI agent (benchmark/patterns → intelligence + aesthetic) | 2.4 |
| `aesthetic.json` | AI agent (visual direction + tokens) | 2.6 |
| `brand.config.json` | `/generate-prototype` (theme override) | 2.6 |
| `design-first-draft.md` | Designer iteration | 3 |
| `usability.json` | Dev / designer (simulated usability findings) | 4.8 |

## Recommended project structure

```
my-project/
├── CLAUDE.md                          ← this file
├── .claude/
│   └── skills/
│       └── designops-pipeline/              ← install the skill here
│           ├── SKILL.md
│           └── scripts/
│               ├── run_pipeline.sh
│               └── validate_brief.py
├── docs/
│   └── tor.pdf                        ← TOR input
├── design-system/                     ← DS repo (or symlink)
└── output/                            ← generated files
    ├── brief.md
    ├── brief.json
    └── design-first-draft.md
```
