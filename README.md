<div align="center">

# 🎨 DesignOps Project — TOR → Prototype Pipeline

**Drop in a TOR file → get a design brief, first draft, and a POC prototype that has already passed critique + audit**

Powered by Claude Code · Next.js 16 · shadcn/ui · Tailwind v4

`Standalone` · `Offline-ready` · `WCAG-aware`

</div>

---

## Overview

This repo is a **DesignOps pipeline** that turns a TOR (Terms of Reference) document or project brief
into a **structured requirement + working prototype** automatically — complete with a quality loop
(critique + audit) that makes the UI polished and standards-compliant before it reaches Dev or Figma.

> Built for dashboards, admin panels, HIS/healthcare, fintech, and government TOR projects.

```
  TOR (PDF / DOCX / Notion / GDocs)
          │
          ▼  Step 1+2  ── read TOR → factual brief
   ┌──────────────┐   ┌──────────────────┐
   │  brief.md    │   │  brief.json      │  ← validate_brief.py (gate)
   │  (humans)    │   │  (AI consumes)   │
   └──────────────┘   └────────┬─────────┘
                               │
                               ▼  Step 2.5 ── Product Intelligence Layer (10 dims → design_directives)
                      ┌─────────────────────┐
                      │  intelligence.json   │  ← validate_intelligence.py (gate + cross-dim invariants)
                      └──────────┬──────────┘
                               │
                               ▼  Step 3   ── refine user flows from directives
                      ┌─────────────────────┐
                      │  flows.json          │  ← validate_flows.py
                      └──────────┬──────────┘
                               ▼  Step 3.5 ── screens from flows (flow→screen coverage)
                      ┌──────────────────────────────┐
                      │ screen-inventory.json        │  ← validate_screens.py
                      │ + design-first-draft.md      │
                      └──────────┬───────────────────┘
                               │
                               ▼  Step 4   ── scaffold Next.js prototype (POC component library)
                      ┌─────────────────────┐
                      │  output/prototype/   │
                      └──────────┬──────────┘
                               │
                               ▼  Step 4.6  critique (4-layer) → auto-fix
                               ▼  Step 4.7  audit gate (token + WCAG)   🔴 critical = block
                               │
                               ▼  Step 5   ── Figma screens (separate pipeline)
```

---

## ✨ Highlights

| | |
|---|---|
| 🧠 **Smart TOR reading** | Filters out non-product content, extracts 8 categories, detects scoring tables and maps them back to features |
| 🧠 **Product Intelligence Layer** | Infers 10 measurable product dimensions → an open `design_directives` object (density, a11y, safeguards, nav) — industry-agnostic, no fixed presets |
| 🧩 **POC Component Library** | Assembles the prototype from ready-made parts (KPICard, StatusBadge, DataTable, Empty/Error/Loading) + realistic mock data |
| 🔁 **Quality Loop** | 4-layer critique + audit gate (token compliance + WCAG) before handoff |
| 📦 **Standalone** | The core pipeline depends on no external repo — the design system is vendored in |
| ✅ **Validation gates** | `validate_brief.py` checks the schema before the next step · audit blocks UI that fails standards |

---

## 📁 Repo structure

```
Designops-project-test/
├── .claude/
│   └── skills/
│       └── tor-to-brief/              # 🛠 core skill
│           ├── SKILL.md               #    full pipeline spec
│           ├── commands/
│           │   └── generate-prototype.md
│           ├── scripts/
│           │   ├── run_pipeline.sh    #    runner — chains every step
│           │   ├── validate_brief.py  #    schema gate
│           │   └── bridge-tokens.mjs  #    token bridge → handoff repo
│           └── references/
│               ├── poc-patterns.md       # component library + mock data
│               ├── critique-framework.md # 4-layer critique
│               ├── audit-checklist.md    # token + WCAG checklist
│               ├── shadcn-prototype.md
│               └── sample-tor.md         # sample TOR for testing
├── design-system/                     # 🎨 vendored DS (shadcn, 52 components)
├── docs/
│   └── tor.pdf                        # 📄 drop your TOR here
├── output/                            # 📤 generated files (auto-created)
└── CLAUDE.md                          # project context for Claude Code
```

---

## ✅ Prerequisites

| Requirement | Why | Notes |
|-------------|-----|-------|
| **Claude Code** | The pipeline is driven by Claude — `run_pipeline.sh` calls the `claude` CLI / runs inside Claude Code to do the actual reading & generation | **Required.** Without it the script only writes prompt files and produces no output |
| **Node.js ≥ 18** | Building the prototype (`npm install && npm run dev`) and the token bridge | `node --version` |
| **Python 3** | `validate_brief.py` schema gate + DS inventory scan in Step 3 | `python3 --version` |
| **poppler** (`pdftotext`) | Better text extraction from PDF TORs | Optional — falls back to letting Claude read the PDF directly. macOS: `brew install poppler` |

> ⚠️ **Run this inside Claude Code** (open the repo folder in Claude Code, or have the `claude` CLI on PATH). Running `run_pipeline.sh` in a plain terminal without Claude will just stage prompt files — it won't generate `brief.md`, the draft, or the prototype.

---

## 🚀 Quick start

```bash
# 1. Place your TOR file at docs/tor.pdf

# 2. Run the full pipeline (standalone — no --ds needed)
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --tor docs/tor.pdf \
  --out ./output

# 3. Generate the prototype from the draft (inside Claude Code)
/generate-prototype --all

# 4. Run the prototype
cd output/prototype && npm install && npm run dev
# → http://localhost:3000
```

> 💡 Try the pipeline with the sample TOR:
> `--tor .claude/skills/tor-to-brief/references/sample-tor.md`

---

## 🔧 Pipeline steps

| Step | What it does | Output |
|------|--------------|--------|
| **1+2** | Read TOR → extract 8 categories + scoring criteria + detect preset | `brief.md` · `brief.json` |
| **gate** | `validate_brief.py` checks the schema | pass / halt with error |
| **3** | Read design system → map features → components + gap report | `design-first-draft.md` |
| **4** | Scaffold Next.js prototype from the POC component library | `output/prototype/` |
| **4.6** | 🔁 4-layer critique → auto-fix critical + quick wins | `docs/critique.md` |
| **4.7** | ✅ Audit gate — token compliance + WCAG | `docs/audit-report.md` |
| **5** | Generate Figma screens (separate pipeline) | Figma file |

---

## 🧠 Product Intelligence Layer (Step 2.5)

Between the brief and UI, the pipeline infers **10 measurable product dimensions** from the brief —
each with **evidence + confidence** — and rolls them up into an open **`design_directives`** object
that Component Mapping consumes. No fixed industry presets: any domain is expressible as a vector.

`User Types · User Expertise · User Goals · Core Tasks · Workflow Complexity · Data Density · Error Tolerance · Accessibility Needs · Compliance Requirements · Decision Criticality`

```
design_directives = { density_target 1-5, guidance_level, safeguard_level,
                      a11y_target, mandatory_flows[], navigation_model, trust_emphasis }
```

`validate_intelligence.py` enforces **cross-dimension invariants** (e.g. `safety_critical ⇒ error_tolerance low/zero`; public-sector ⇒ AAA) and **confidence gating** (low confidence → wireframe-level output + a human gate). Full spec: `.claude/skills/tor-to-brief/references/intelligence-layer.md`.

---

## 🔁 Quality Loop

After scaffolding the prototype, the pipeline **doesn't stop** — it loops back to refine quality first:

**Step 4.6 — Critique (4 layers)**
1. Visual Hierarchy — focal point, contrast, spacing rhythm
2. Information Architecture — flow clarity, grouping, label quality
3. Component Consistency — visual + behavioral + spacing
4. Context Fit — density matches the preset, trust signals

→ Fix every 🔴 Critical + ⚡ Quick Win immediately · log 🟡 High for Dev

**Step 4.7 — Audit gate**

| Category | Checks | Gate |
|----------|--------|------|
| A. Token Compliance | No hardcoded hex/px · radius/shadow follow tokens | 🔴 = block |
| B. A11y / WCAG | Contrast · keyboard nav · focus ring · alt/aria · 44px touch | 🔴 = block |
| C. Component Quality | Naming · complete states · no avoidable `any` | 🟡 = note |

> Any 🔴 CRITICAL remaining → **handoff/Figma is blocked** until it's fixed

---

## ⚙️ Commands & flags

### `run_pipeline.sh`

| Flag | Meaning |
|------|---------|
| `--tor <path>` | TOR file (PDF / DOCX / MD / TXT) |
| `--tor-text "<text>"` | TOR text directly |
| `--ds <path>` | Design system folder or GitHub URL (default: `./design-system`) |
| `--brief <path>` | Reuse an existing brief.json, skipping steps 1+2 |
| `--out <dir>` | Output directory (default: `./tor-output`) |
| `--handoff <path>` | (optional) Handoff repo for the token bridge |
| `--brand <name>` | Brand name for brand.config.json |

### `/generate-prototype` (inside Claude Code)

```bash
/generate-prototype                    # show Screen Inventory, then ask which screen
/generate-prototype --screen login     # a single screen
/generate-prototype --screen login,dashboard
/generate-prototype --all              # every screen, ordered by priority
```

---

## 🧱 Standalone design

The core pipeline depends on **no external repo**:

- The **design system** is vendored at `./design-system/` (source-only ~2MB, 52 components)
  → used for both Step 3 (read the DS) and Step 4 (as the prototype base)
- `run_pipeline.sh` auto-resolves `--ds` in this order:
  `TOR_DS_PATH` env → `./design-system` (in-repo) → `../shadcn-skills-design-starter` (fallback)

### (Optional) Token bridge → handoff repo

```bash
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh \
  --tor docs/tor.pdf --out ./output \
  --handoff ../Hand-off-test --brand my-brand
```

Converts tokens (hex → oklch) into a whitelabel handoff repo and rebuilds it — a separate downstream stage, not part of the core pipeline.

> ⚠️ This step needs a **separate `Hand-off-test` repo** (it reads `Hand-off-test/scripts/lib-oklch.mjs` and writes its `brand.config.json`). That repo is **not bundled here** — skip `--handoff` if you don't have it. The core pipeline (Steps 1–4.7) works fully without it.

---

## 📤 Output files

| File | Audience | Created in step |
|------|----------|-----------------|
| `brief.md` | Designer / PM review | 1+2 |
| `brief.json` | AI agent (facts) | 1+2 |
| `intelligence.json` | AI agent (design_directives) | 2.5 |
| `flows.json` | AI agent (refined flows) | 3 |
| `screen-inventory.json` | AI agent (build manifest) | 3.5 |
| `design-first-draft.md` | Designer iteration | 3.5 |
| `prototype/` | Dev (Next.js app) | 4 |
| `prototype/docs/critique.md` | Designer / Dev | 4.6 |
| `prototype/docs/audit-report.md` | QA / Lead | 4.7 |
| `prototype/docs/poc-handoff.md` | Dev handoff | 6 |

---

## 🧪 Tests

Regression guard for the pipeline scripts (bash 3.2 compat, validate gate, execution model):

```bash
bash .claude/skills/tor-to-brief/scripts/selftest.sh
```

Runs under macOS stock `/bin/bash` (3.2) and exits non-zero on any failure. Run it after editing any script in `.claude/skills/tor-to-brief/scripts/`.

---

## 🧰 Tech stack

`Next.js 16` · `React 19` · `Tailwind CSS v4` · `shadcn/ui (radix-nova)` · `Claude Code`

---

<div align="center">
<sub>Built with ❤️ for the DesignOps team</sub>
</div>
