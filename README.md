<div align="center">

# 🎨 DesignOps Pipeline — TOR → Prototype

**Drop in a TOR → get a brief, a product-intelligence read, a committed visual direction,
user flows, a screen inventory, and a POC prototype that has already passed a scored critique
and a script-enforced audit.**

Powered by Claude Code · Next.js 16 · shadcn/ui · Tailwind v4

`Standalone` · `Offline-ready` · `WCAG-gated` · `138-brand aesthetic library` · `41/41 selftest`

</div>

---

## Overview

This repo turns a **TOR** (Terms of Reference) — or any project brief — into a **structured
requirement + a working prototype**, automatically. Every stage emits a JSON artifact behind its
own validator gate, so the chain is contract-driven end to end. It is **industry-agnostic**: no
fixed presets — the product is read as a vector of measurable dimensions.

```
  TOR (PDF / DOCX / Notion / GDocs)
         │
         ▼  1+2   read TOR → factual brief                    brief.md · brief.json    →  validate_brief.py
         │
         ▼  2.5   Product Intelligence (10 dims)              intelligence.json        →  validate_intelligence.py
         │          → design_directives
         │
         ▼  2.6   Aesthetic Direction (138-brand library)     aesthetic.json           →  validate_aesthetic.py
         │          → brand.config.json                          + brand.config.json       (contrast from hex)
         │
         ▼  3     refine user flows from directives           flows.json               →  validate_flows.py
         │
         ▼  3.5   screens from flows (full coverage)          screen-inventory.json    →  validate_screens.py
         │          + human draft                                + design-first-draft.md
         │
         ▼  4     scaffold Next.js prototype                  output/prototype/
         │
         ▼  4.6   scored critique (6 dims + Nielsen + anti-slop) → auto-fix
         ▼  4.7   audit GATE — audit_prototype.py              docs/audit-report.md     🔴 exit 1 = blocked
         │          tokens · WCAG contrast (light+dark) · no-emoji
         ▼  4.8   Storybook QA (optional, opt-in)
         │
         ▼  5     Figma screens (separate, Figma MCP)
```

---

## ✨ Highlights

| | |
|---|---|
| 🧠 **Product Intelligence** | Infers 10 measurable dimensions (each with evidence + confidence) → an open `design_directives` object. No fixed industry presets. |
| 🎨 **Aesthetic Direction** | Picks one of **138 named design systems** (apple, linear, stripe, resend…) or an archetype, resolves it to **contrast-checked** tokens. Optionally infers the look from a TOR mockup. |
| 🛡️ **Real gates, not vibes** | Every stage has a zero-dependency validator. The audit gate is a *script* that recomputes WCAG contrast from `globals.css` (oklch→sRGB, light + dark) and lints for hardcodes + emoji — exit 1 blocks handoff. |
| 🔁 **Scored quality loop** | Step 4.6 critique = 6 weighted dimensions + Nielsen's 10 heuristics + an anti-slop gate (Banned Defaults). |
| 🧩 **19 design skills, folded in** | ux-writing, brandkit (DTCG tokens), image-to-code, migrate-design-system, performance, governance — vendored, standalone. See [`references/SKILLS.md`](.claude/skills/tor-to-brief/references/SKILLS.md). |
| 📦 **Standalone** | The whole pipeline depends on no external repo — design system, brand library, and token kit are all vendored in. |

---

## 🚀 Quick start

```bash
# 1. Place your TOR at docs/tor.pdf  (or try the bundled sample — see below)

# 2. Run the full pipeline (standalone — no --ds needed)
bash .claude/skills/tor-to-brief/scripts/run_pipeline.sh --tor docs/tor.pdf --out ./output

# 3. Generate the prototype from the draft (inside Claude Code)
/generate-prototype --all

# 4. Run it
cd output/prototype && npm install && npm run dev   # → http://localhost:3000
```

> 💡 No TOR handy? Use the bundled sample (Thai HIS TOR — also proves non-English reading):
> `--tor .claude/skills/tor-to-brief/references/sample-tor.md`

> ⚠️ **Run inside Claude Code.** The runner does deterministic prep (extract TOR, scan the DS,
> stage prompts) and prints an agent checklist; Claude does the reading & generation. In a plain
> terminal it only stages prompt files and produces no artifacts.

---

## 🔧 Pipeline at a glance

| Step | What it does | Output | Gate |
|------|--------------|--------|------|
| **1+2** | Read TOR → 8 categories + scoring criteria | `brief.md` · `brief.json` | `validate_brief.py` |
| **2.5** | Product Intelligence — 10 dims → `design_directives` | `intelligence.json` | `validate_intelligence.py` |
| **2.6** | Aesthetic Direction — pick + resolve tokens | `aesthetic.json` · `brand.config.json` | `validate_aesthetic.py` |
| **3** | Refine user flows from directives | `flows.json` | `validate_flows.py` |
| **3.5** | Screens from flows + DS mapping | `screen-inventory.json` · `design-first-draft.md` | `validate_screens.py` |
| **4** | Scaffold the Next.js prototype | `output/prototype/` | — |
| **4.6** | Scored critique → auto-fix critical + quick wins | `docs/critique.md` | (agent) |
| **4.7** | **Audit gate** — token + WCAG + no-emoji | `docs/audit-report.md` | `audit_prototype.py` 🔴 exit 1 |
| **4.8** | Storybook QA (opt-in) | — | `addon-a11y` axe pass |
| **5** | Figma screens | Figma file | (Figma MCP) |

---

## 🧠 Product Intelligence Layer (Step 2.5)

Between the brief and the UI, the pipeline infers **10 measurable product dimensions** — each with
**evidence + confidence** — and rolls them up into an open **`design_directives`** object. Any
domain is expressible as a vector; there are no fixed presets.

`User Types · Expertise · Goals · Core Tasks · Workflow Complexity · Data Density · Error Tolerance · Accessibility · Compliance · Decision Criticality`

```
design_directives = { density_target 1–5, guidance_level, safeguard_level,
                      a11y_target, mandatory_flows[], navigation_model, trust_emphasis }
```

`validate_intelligence.py` enforces **cross-dimension invariants** (e.g. `safety_critical ⇒
error_tolerance low/zero`, public-sector ⇒ AAA) and **confidence gating** (low confidence →
wireframe-level output + a human gate). Spec: [`intelligence-layer.md`](.claude/skills/tor-to-brief/references/intelligence-layer.md).

---

## 🎨 Aesthetic Direction (Step 2.6)

`design_directives` decides the *functional* shape; Step 2.6 decides the **look**. It commits a
visual direction and resolves it into concrete tokens — so the prototype earns a real aesthetic
instead of the neutral shadcn default ("design slop").

- **138-brand library** — `references/aesthetics/design-systems/library/<name>/DESIGN.md`
  (apple, linear-app, stripe, vercel, notion, resend, brutalism, glassmorphism, luxury…).
  Browse: `python3 …/aesthetics/scripts/design_systems.py list | search <term> | show <name>`.
- **Anti-slop first** — name the one `mood_adjective` the result must earn before any token.
- **From a mockup** — if the TOR ships a screenshot, infer the direction from it ([`image-to-code.md`](.claude/skills/tor-to-brief/references/image-to-code.md)).
- **Gate** — `validate_aesthetic.py` **recomputes WCAG contrast from the hex values itself**
  (never trusts the agent), requires the chosen system to resolve in the library, and forces
  `a11y_target`/`density_target` to echo `design_directives`.

Output `aesthetic.json` + a ready-to-apply `output/brand.config.json` for `/generate-prototype`.

---

## 🔁 Quality loop — scored, then gated

**Step 4.6 — Critique (scored)** · [`critique-framework.md`](.claude/skills/tor-to-brief/references/critique-framework.md) → [`design-review.md`](.claude/skills/tor-to-brief/references/design-review.md)

- Score **6 weighted dimensions** (Hierarchy 20 · Consistency 20 · Accessibility 20 · Usability 20 · Responsiveness 10 · Performance 10) → weighted overall (≤6 = rework).
- Flag **Nielsen's 10 heuristics** by number · run the **anti-slop gate** (Banned Defaults: pure #000/#fff, identical cards, rainbow accents, emoji-as-icons, em-dash copy…).
- Auto-fix every 🔴 Critical + ⚡ Quick Win; log the rest for Dev.

**Step 4.7 — Audit gate (a real script)** · `audit_prototype.py`

```bash
python3 .claude/skills/tor-to-brief/scripts/audit_prototype.py \
  output/prototype --a11y AA --report output/prototype/docs/audit-report.md
```

| # | Gate | How it's checked | Result |
|---|------|------------------|--------|
| 1 | **Token compliance** | `lint_hardcodes.py` — no raw hex/px/ms or `bg-gray-500`-style palette | 🔴 block |
| 2 | **WCAG contrast** | recomputes ratios from `globals.css` (oklch→sRGB), light **and** dark, at the a11y target | 🔴 block |
| 3 | **UX copy** | `check_no_emoji.py` — no emoji / em-dash in product UI | 🔴 block |

> **Exit 1 = BLOCKED** — handoff/Figma is blocked until it passes. Categories are machine-checked,
> not eyeballed.

---

## 🧩 Folded design skills

All 19 skills from `shadcn-skills-design-starter` are vendored into the pipeline. The
generation-time ones are wired into steps; the situational ones are available on demand.
Full map: [`references/SKILLS.md`](.claude/skills/tor-to-brief/references/SKILLS.md).

| Skill | Where it plugs in |
|-------|-------------------|
| **ux-writing** | copy rules in Step 3.5 / 4 + audit gate 3 (no emoji/dash) |
| **image-to-code** | Step 2.6 input — infer the aesthetic from a TOR mockup |
| **brandkit** | Step 2.6 deepening — full **DTCG** token foundation (`references/tokens/`, 450 tokens) |
| **migrate-design-system** | bridge to Material / Apple / Fluent / Carbon (role crosswalk) |
| **performance** | optional Core-Web-Vitals add-on |
| **governance** | living-DS maintenance (SemVer / deprecation) — out of the generation loop |

---

## ⚙️ Commands & flags

**`run_pipeline.sh`**

| Flag | Meaning |
|------|---------|
| `--tor <path>` | TOR file (PDF / DOCX / MD / TXT) |
| `--tor-text "<text>"` | TOR text directly |
| `--ds <path>` | Design system folder or GitHub URL (default: `./design-system`) |
| `--brief <path>` | Reuse an existing `brief.json`, skipping steps 1+2 |
| `--out <dir>` | Output directory (default: `./tor-output`) |
| `--handoff <path>` · `--brand <name>` | (optional) token bridge → a separate handoff repo |

**`/generate-prototype`** (inside Claude Code)

```bash
/generate-prototype                       # show the Screen Inventory, then ask which screen
/generate-prototype --screen login        # one screen
/generate-prototype --screen login,dashboard
/generate-prototype --all                 # every screen, by priority
```

---

## 📁 Repo structure

```
Designops-project-test/
├── .claude/skills/tor-to-brief/          # 🛠 the pipeline skill
│   ├── SKILL.md                          #    full spec
│   ├── commands/generate-prototype.md
│   ├── scripts/
│   │   ├── run_pipeline.sh               #    runner — chains every step
│   │   ├── validate_{brief,intelligence,flows,screens,aesthetic}.py
│   │   ├── audit_prototype.py            #    Step 4.7 gate (token · WCAG · emoji)
│   │   ├── lint_hardcodes.py
│   │   └── selftest.sh                   #    41/41 regression guard
│   └── references/
│       ├── aesthetics/                   #    🎨 138-brand library + taste + contrast.py
│       ├── tokens/                       #    DTCG token foundation + validators (brandkit)
│       ├── ux-writing/                   #    voice-tone + check_no_emoji.py
│       ├── storybook/                    #    opt-in QA template (Step 4.8)
│       ├── design-review.md · critique-framework.md · audit-checklist.md
│       ├── intelligence-layer.md · poc-patterns.md · shadcn-prototype.md
│       ├── image-to-code.md · brandkit.md · migrate-design-system.md
│       ├── performance.md · governance.md · SKILLS.md
│       └── sample-tor.md
├── design-system/                        # 🎨 vendored DS (shadcn, 52 components, ~2MB)
├── docs/tor.pdf                          # 📄 drop your TOR here
├── output/                               # 📤 generated artifacts (auto-created)
└── CLAUDE.md                             # project context for Claude Code
```

---

## 📤 Output files

| File | Audience | Step |
|------|----------|------|
| `brief.md` · `brief.json` | Designer/PM · AI (facts) | 1+2 |
| `intelligence.json` | AI (design_directives) | 2.5 |
| `aesthetic.json` · `brand.config.json` | AI (visual direction) · theme | 2.6 |
| `flows.json` | AI (refined flows) | 3 |
| `screen-inventory.json` · `design-first-draft.md` | AI (build manifest) · Designer | 3.5 |
| `prototype/` | Dev (Next.js app) | 4 |
| `prototype/docs/critique.md` · `audit-report.md` | Designer/Dev · QA/Lead | 4.6 / 4.7 |
| `prototype/docs/poc-handoff.md` | Dev handoff | 6 |

---

## ✅ Prerequisites

| Requirement | Why |
|-------------|-----|
| **Claude Code** | Drives the reading & generation. Without it the runner only stages prompts. **Required.** |
| **Node.js ≥ 18** | Build the prototype (`npm install && npm run dev`) + the token bridge. |
| **Python 3** | Every validator gate + the DS inventory scan. Zero-dependency. |
| **poppler** (`pdftotext`) | Better PDF text extraction. Optional — falls back to Claude reading the PDF. `brew install poppler`. |

---

## 🧪 Tests

```bash
bash .claude/skills/tor-to-brief/scripts/selftest.sh        # 41/41, runs on macOS stock bash 3.2
```

Covers bash-3.2 compatibility, every validator (valid passes / invalid fails), the aesthetic +
audit gates (fake brand, low contrast, hardcode, emoji all blocked), and the DTCG token gates.
**Run it after editing any script** in `.claude/skills/tor-to-brief/scripts/`.

---

## 🧱 Standalone design

The core pipeline depends on **no external repo**. The design system is vendored at
`./design-system/` (source-only, used for Step 3 *and* as the prototype base); the brand library
and DTCG token kit live under `references/`. `run_pipeline.sh` resolves `--ds` in order:
`TOR_DS_PATH` env → `./design-system` (in-repo) → `../shadcn-skills-design-starter` (fallback).

The optional `--handoff` token bridge (hex → oklch into a whitelabel repo) is a separate downstream
stage and needs a `Hand-off-test` repo that is **not bundled** — skip it if you don't have one.

---

## 🧰 Tech stack

`Next.js 16` · `React 19` · `Tailwind CSS v4` · `shadcn/ui` · `Claude Code` · `Python 3 (stdlib only)`

<div align="center">
<sub>Built for the DesignOps team · every gate is a script, not a vibe</sub>
</div>
