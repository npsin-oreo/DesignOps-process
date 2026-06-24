# CLAUDE.md
# Place this file at the root of any project that uses the designops-pipeline skill

## Environment — Model A (imports the looloo design system)

This pipeline is a **consumer** of `@npsin-oreo/design-system` (the looloo design system). It does
**not** vendor a DS — the build **imports the published package** into `output/prototype/node_modules`
and imports components from `@npsin-oreo/design-system/<name>` (immutable; theme via Step 2.6 token +
`[data-slot=*]` overrides, never by editing components). **Not standalone — needs a `GITHUB_TOKEN`**
(GitHub Packages requires auth even for public packages).

| Path | Role | When used |
|------|------|-----------|
| `@npsin-oreo/design-system` (npm, GitHub Packages) | **DS — imported package**, pinned + `--save-exact` | Step 4 build (`setup-prototype.sh`) |
| `../looloo-design-system` (sibling checkout) | **DS source** — read for component inventory + `token-contract.json` + DESIGN.md only | Step 2.6 / 3.5 (`--ds`) |

> Theming is owned by Step 2.6 → `brand.config.json` → the product scaffold. The old `--handoff`
> Step 4.5 token-bridge (pushing tokens into a whitelabel repo) is **deprecated** and not part of this flow.

`run_pipeline.sh` resolves `--ds` (the looloo SOURCE, for inventory): `TOR_DS_PATH` env → `../looloo-design-system` sibling.

```bash
export GITHUB_TOKEN=$(gh auth token)   # required — import the DS package from GitHub Packages

# Core pipeline (DS inventory from the looloo source; build imports the package)
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --ds  ../looloo-design-system \
  --out ./output
```

> Note: the DS is never copied. `setup-prototype.sh --out ./output` installs the pinned package into
> `output/prototype/node_modules`, scaffolds an importing Next app + `.npmrc`, and a local `lib/utils.ts` (`cn`).

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

**Aesthetic Direction Layer** (Step 2.6) commits a *visual* direction `design_directives` doesn't cover — picks one of **138 named design systems** (apple, linear-app, stripe, resend…) or an archetype from the vendored brand library, then resolves it into the **full identity token set** (surfaces, text hierarchy, accent, border + the dark theme — not just primary), **contrast-checked**, plus a `signature` (border/elevation/type-weight/tracking). Output `aesthetic.json` + a ready-to-apply `brand.config.json` that **carries the whole theme** (`colors.{light,dark}`) so the look actually flows into the prototype instead of "the brand colour slapped on a neutral skeleton". Library + browser + anti-slop guide: `references/aesthetics/` (`scripts/design_systems.py list|search|show`); gate: `scripts/validate_aesthetic.py` (requires the identity set light+dark, recomputes WCAG contrast from hex — never trusts the agent's self-reported ratio). The bridge is closed-loop with Step 4.7 **gate 6 (theme fidelity)**.

**Audit gate** (Step 4.7) is a real runnable check, not agent judgment: `scripts/audit_prototype.py` runs `lint_hardcodes.py` over the screens (no raw hex/px/Tailwind-palette), recomputes WCAG contrast from the prototype's `globals.css` (oklch→sRGB, light + dark) at `design_directives.a11y_target`, checks UX copy (no emoji/em-dash), runs `lint_component_contracts.py` (gate 4 — enforces the Button/Dialog/Field usage contracts: icon-only buttons need an accessible name, every `DialogContent` needs a `DialogTitle`, every labelled `Input` needs a matching `FieldLabel htmlFor`; advisory notes for one-primary-per-view etc.), runs `lint_font_imports.py` (gate 5 — a remote-font CSS `@import` in `globals.css` 🔴 blocks; it 500s the Turbopack dev server, use `next/font`), and runs `lint_theme_fidelity.py` (gate 6 — the full identity theme Step 2.6 committed in `brand.config.json` must actually be applied in `globals.css`; if `card`/`secondary`/`muted`/`accent`/`border` or the dark set regressed to the shadcn-neutral default — "the brand colour slapped on a neutral skeleton" — it 🔴 blocks), runs `lint_directive_fidelity.py` (gate 7 — the build must honor `design_directives`: a destructive action needs an `AlertDialog`/confirm when `safeguard_level` is on, an empty-state when `guidance_level` is guided; density/nav are advisory — reads `intelligence.json`), and runs `lint_screen_coverage.py` (gate 8 — every Must screen in `screen-inventory.json` was actually built as an `app/<route>/page.tsx` rendering its declared loading/empty/error states). Exit 1 = BLOCKED. It audits the generated surface only (`components/ui` + any `docs/` dir auto-excluded; `--include-vendored` to audit all). `references/audit-checklist.md` covers the qualitative category-C items. **Step 4.7b (optional)** adds a runtime gate (`references/runtime-audit/`, vendored from `ux-ui-agent-skills`): renders the built page in Playwright for axe-core a11y, hover/focus-state contrast, modal focus-trap, and render-based anti-slop — skips cleanly without Playwright.

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
