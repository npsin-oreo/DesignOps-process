# CLAUDE.md
# Place this file at the root of any project that uses the tor-to-brief skill

## Environment — self-contained

This project is **standalone** — the core pipeline (TOR → brief → draft → prototype) depends on no external repo.

| Path | Role | When used |
|------|------|-----------|
| `./design-system/` | **DS (vendored, in-repo)** — shadcn-skills-design-starter source-only (~2MB, 52 components, no node_modules) | Step 3 (`--ds` default) + base for the POC prototype |
| `../Hand-off-test/` | **Handoff (optional, outside repo)** — whitelabel target for the token bridge | Step 4.5 only — runs when `--handoff` is passed |

`run_pipeline.sh` auto-resolves `--ds` in this order: `TOR_DS_PATH` env → `./design-system` (in-repo) → `../shadcn-skills-design-starter` (fallback)

```bash
# Core pipeline — standalone, no --ds needed (uses ./design-system automatically)
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --out ./output

# (optional) add the token bridge into the handoff repo
# NOTE: requires a separate Hand-off-test repo (not bundled). Skip --handoff if you don't have it.
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --tor docs/tor.pdf --out ./output \
  --handoff ../Hand-off-test --brand my-brand
```

> Note: `./design-system` is source-only — when building the actual prototype, the pipeline copies it to `output/prototype/` and runs `npm install` once there.

---

## Commands

### `/generate-prototype`
Generate Next.js POC screens from `design-first-draft.md`.  
Full spec: `.claude/skills/tor-to-brief/commands/generate-prototype.md`

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

### tor-to-brief
Turns a TOR → design brief → first draft → POC prototype automatically, with a **quality loop**.

**Pipeline:** Step 1+2 brief (facts) → **Step 2.5 Product Intelligence** (`intelligence.json` → `design_directives`) → **Step 3 Flows** (`flows.json`, refined from directives) → **Step 3.5 Screen Inventory** (`screen-inventory.json` + `design-first-draft.md`, flow→screen coverage) → Step 4 prototype → **Step 4.6 critique** → **Step 4.7 audit gate** → Step 5 Figma. Each stage has its own JSON artifact + validator gate.

**Product Intelligence Layer** (Step 2.5) infers 10 measurable dimensions (user types/expertise/goals/tasks, workflow complexity, data density, error tolerance, accessibility, compliance, decision criticality) → an open `design_directives` object. Replaces the old fixed industry presets; industry-agnostic. Spec: `references/intelligence-layer.md`; gate: `scripts/validate_intelligence.py`.

> Steps 4.6/4.7 + poc-patterns are pulled from the `designops-loop` skill and wired into the pipeline · references live in `.claude/skills/tor-to-brief/references/`

**Skill location:** `.claude/skills/tor-to-brief/`

**Trigger via command:**
```bash
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh [flags]
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
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --ds  ./design-system \
  --out ./output

# Steps 1+2 only — no design system yet
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --out ./output

# Step 3 only — brief.json already exists
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --brief ./output/brief.json \
  --ds    ./design-system \
  --out   ./output

# Validate brief.json without running the pipeline
python3 .claude/skills/tor-to-brief/scripts/validate_brief.py ./output/brief.json
```

## Output files

| File | Audience | Created in step |
|------|----------|-----------------|
| `brief.md` | Designer / PM review | 1+2 |
| `brief.json` | AI agent (step 3 input) | 1+2 |
| `design-first-draft.md` | Designer iteration | 3 |

## Recommended project structure

```
my-project/
├── CLAUDE.md                          ← this file
├── .claude/
│   └── skills/
│       └── tor-to-brief/              ← install the skill here
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
