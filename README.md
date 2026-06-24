<div align="center">

# 🎨 DesignOps Pipeline — TOR → Prototype

**Drop in a project brief → get a clear written spec and a working demo app —
with accessibility and design quality checked automatically along the way.**

Powered by Claude Code · Next.js 16 · shadcn/ui · Tailwind v4

`Model A (imports @npsin-oreo/design-system)` · `WCAG-gated` · `138-brand aesthetic library` · `11-gate audit` · `127/127 selftest`

</div>

---

## In plain words

You hand it a **project brief** (a TOR — the document that says what to build). It reads the brief,
figures out who the users are and what matters to them, picks a look and feel, plans the screens, and
**builds a clickable demo app** — then checks its own work for accessibility and quality before
handing it off.

> **Goes in:** a brief (PDF / Word / Notion / Google Docs).
> **Comes out:** a clear written spec **+** a working demo you can open in a browser.

Think of it as an assembly line for the early design of an app: each station does one job and won't
pass the work on until it's correct. Good for designers, PMs, and engineers who want to go from
"here's the scope" to "here's something to react to" fast.

---

## How it works (the pipeline)

Every stage produces a file and passes through a **gate** (an automatic check) before the next stage
runs. It works for any kind of product — there are no fixed industry templates.

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
         ▼  4.7b  runtime audit (optional) — axe · states · focus-trap · taste   (Playwright)
         ▼  4.8   Storybook QA (optional, opt-in)
         │
         ▼  5     Figma output — 5 pages, generated from artifacts   figma_prep.py + Figma MCP
```

---

## ✨ Highlights

| | |
|---|---|
| 🧠 **Product Intelligence** | Infers 10 measurable dimensions (each with evidence + confidence) → an open `design_directives` object. No fixed industry presets. |
| 🎨 **Aesthetic Direction** | Picks one of **138 named design systems** (apple, linear, stripe, resend…) or an archetype, then resolves the **full identity token set** (surfaces, text, accent, border + dark theme — not just primary), **contrast-checked**, so the look actually flows into the prototype. Optionally infers it from a TOR mockup. |
| 🛡️ **Real gates, not vibes** | Every stage has a zero-dependency validator. The audit gate is a *script* with **8 checks** — hardcodes · WCAG contrast (light + dark) · UX copy · component-contracts · font-imports · theme-fidelity · directive-fidelity · screen-coverage — exit 1 blocks handoff. |
| 🧵 **Intent makes it to the build** | A traceability spine carries the contractual scope end-to-end: every **Must** feature and scored must-have is provably served by a task, a screen, and a built route — checked, not assumed. |
| 🔁 **Scored quality loop** | Step 4.6 critique = 6 weighted dimensions + Nielsen's 10 heuristics + an anti-slop gate (Banned Defaults). |
| 🧩 **19 design skills, folded in** | ux-writing, brandkit (DTCG tokens), image-to-code, migrate-design-system, performance, governance — vendored, standalone. See [`references/SKILLS.md`](.claude/skills/designops-pipeline/references/SKILLS.md). |
| 📦 **Model A (imports the DS)** | The build **imports** `@npsin-oreo/design-system` (looloo) from GitHub Packages — never vendored. Needs `GITHUB_TOKEN`. The brand library + token kit ship with the skill. |

---

## 🚀 Quick start

```bash
# 1. Place your TOR at docs/tor.pdf  (or try the bundled sample — see below)
export GITHUB_TOKEN=$(gh auth token)   # required — import the DS package from GitHub Packages

# 2. Run the full pipeline (DS inventory from the looloo source sibling)
bash .claude/skills/designops-pipeline/scripts/run_pipeline.sh --tor docs/tor.pdf --ds ../looloo-design-system --out ./output

# 3. Generate the prototype from the draft (inside Claude Code)
/generate-prototype --all

# 4. Run it
cd output/prototype && npm install && npm run dev   # → http://localhost:3000
```

> 📱 **Test on a phone:** the dev server prints a `Network: http://<lan-ip>:3000` URL — open it on a
> phone on the same Wi-Fi. The scaffolded `next.config.ts` auto-allows your LAN IPs, so the page
> hydrates and works (Next blocks cross-origin dev HMR otherwise). Most TORs here are mobile-first.

> 💡 No TOR handy? Use the bundled sample (Thai HIS TOR — also proves non-English reading):
> `--tor .claude/skills/designops-pipeline/references/sample-tor.md`

> ⚠️ **Run inside Claude Code.** The runner does deterministic prep (extract TOR, scan the DS,
> stage prompts) and prints an agent checklist; Claude does the reading & generation. In a plain
> terminal it only stages prompt files and produces no artifacts.

---

## 🔧 Pipeline at a glance

| Step | What it does | Output | Gate |
|------|--------------|--------|------|
| **1+2** | Read TOR → 8 categories + scoring criteria | `brief.md` · `brief.json` | `validate_brief.py` |
| **2.5** | Product Intelligence — 10 dims → `design_directives` (+ feature traceability) | `intelligence.json` | `validate_intelligence.py` |
| **2.6** | Aesthetic Direction — resolve the full identity theme | `aesthetic.json` · `brand.config.json` | `validate_aesthetic.py` |
| **3** | Refine user flows from directives | `flows.json` | `validate_flows.py` |
| **3.5** | Screens from flows + DS mapping (+ feature/scoring coverage) | `screen-inventory.json` · `design-first-draft.md` | `validate_screens.py` |
| **4** | Scaffold the Next.js prototype | `output/prototype/` | — |
| **4.6** | Scored critique → auto-fix critical + quick wins | `docs/critique.md` | (agent) |
| **4.7** | **Audit gate** — 8 checks (token · WCAG · copy · contracts · font · theme · directive · screens) | `docs/audit-report.md` | `audit_prototype.py` 🔴 exit 1 |
| **4.8** | Storybook QA (opt-in) | — | `addon-a11y` axe pass |
| **5** | Figma output (5 pages: Cover/Foundations/Components/Screens/Flows) — generated from artifacts | Figma file | `figma_prep.py` + Figma MCP |

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
wireframe-level output + a human gate). Spec: [`intelligence-layer.md`](.claude/skills/designops-pipeline/references/intelligence-layer.md).

---

## 🎨 Aesthetic Direction (Step 2.6)

`design_directives` decides the *functional* shape; Step 2.6 decides the **look**. It commits a
visual direction and resolves it into concrete tokens — so the prototype earns a real aesthetic
instead of the neutral shadcn default ("design slop").

- **138-brand library** — `references/aesthetics/design-systems/library/<name>/DESIGN.md`
  (apple, linear-app, stripe, vercel, notion, resend, brutalism, glassmorphism, luxury…).
  Browse: `python3 …/aesthetics/scripts/design_systems.py list | search <term> | show <name>`.
- **Anti-slop first** — name the one `mood_adjective` the result must earn before any token.
- **From a mockup** — if the TOR ships a screenshot, infer the direction from it ([`image-to-code.md`](.claude/skills/designops-pipeline/references/image-to-code.md)).
- **Full identity, not just a primary** — it resolves the whole semantic set (surfaces, text
  hierarchy, accent, border) for **light *and* dark**, so the chosen system's character actually
  lands instead of a brand colour slapped on a neutral skeleton.
- **Gate** — `validate_aesthetic.py` **recomputes WCAG contrast from the hex values itself**
  (never trusts the agent), requires the chosen system to resolve in the library, demands the full
  light+dark identity set, and forces `a11y_target`/`density_target` to echo `design_directives`.

Output `aesthetic.json` + a ready-to-apply `output/brand.config.json` (carrying the whole theme) for
`/generate-prototype` — and audit **gate 6** blocks if the build regresses to neutral.

---

## 🔁 Quality loop — scored, then gated

**Step 4.6 — Critique (scored)** · [`critique-framework.md`](.claude/skills/designops-pipeline/references/critique-framework.md) → [`design-review.md`](.claude/skills/designops-pipeline/references/design-review.md)

- Score **6 weighted dimensions** (Hierarchy 20 · Consistency 20 · Accessibility 20 · Usability 20 · Responsiveness 10 · Performance 10) → weighted overall (≤6 = rework).
- Flag **Nielsen's 10 heuristics** by number · run the **anti-slop gate** (Banned Defaults: pure #000/#fff, identical cards, rainbow accents, emoji-as-icons, em-dash copy…).
- **Mobile lens** ([`mobile-usability.md`](.claude/skills/designops-pipeline/references/mobile-usability.md)) for mobile-first products — touch targets ≥44px, thumb reach, correct input types, 320px reflow, no hover-only. Also applied when screens are generated (Step 3.5).
- Auto-fix every 🔴 Critical + ⚡ Quick Win; log the rest for Dev.

**Step 4.7 — Audit gate (a real script)** · `audit_prototype.py`

```bash
python3 .claude/skills/designops-pipeline/scripts/audit_prototype.py \
  output/prototype --a11y AA --report output/prototype/docs/audit-report.md
```

| # | Gate | How it's checked | Result |
|---|------|------------------|--------|
| 1 | **Token compliance** | `lint_hardcodes.py` — no raw hex/px/ms or `bg-gray-500`-style palette | 🔴 block |
| 2 | **WCAG contrast** | recomputes ratios from `globals.css` (oklch→sRGB), light **and** dark, at the a11y target | 🔴 block |
| 3 | **UX copy** | no emoji / em-dash in product UI | 🔴 block |
| 4 | **Component contracts** | `lint_component_contracts.py` — icon-only buttons need a name, every `DialogContent` a `DialogTitle`, labelled `Input` a matching `FieldLabel htmlFor` | 🔴 block |
| 5 | **Font imports** | `lint_font_imports.py` — no remote-font CSS `@import` (500s the Turbopack dev server; use `next/font`) | 🔴 block |
| 6 | **Theme fidelity** | `lint_theme_fidelity.py` — the identity theme Step 2.6 committed in `brand.config.json` is actually applied in `globals.css` (no regression to the neutral default) | 🔴 block |
| 7 | **Directive fidelity** | `lint_directive_fidelity.py` — the build honors `design_directives`: destructive actions guarded when `safeguard_level` is on, an empty-state when `guidance_level` is guided (density/nav advisory) | 🔴 block |
| 8 | **Screen coverage** | `lint_screen_coverage.py` — every **Must** screen in `screen-inventory.json` was built as an `app/<route>/page.tsx` rendering its declared loading/empty/error states | 🔴 block |

> Gates 6-8 auto-discover their source artifact (`brand.config.json` / `intelligence.json` /
> `screen-inventory.json`) beside the prototype, or take `--theme` / `--intel` / `--screens`, and
> skip cleanly when it is absent.

> **Exit 1 = BLOCKED** — handoff/Figma is blocked until it passes. Categories are machine-checked,
> not eyeballed. It audits the **generated surface only** (`components/ui` and any `docs/` dir are
> auto-excluded), so just point it at the prototype — no `--scan` needed; add `--include-vendored` to audit everything.

**Step 4.7b — Runtime audit (optional)** · [`runtime-audit/`](.claude/skills/designops-pipeline/references/runtime-audit/README.md)

Renders the built page in headless Chrome (Playwright) to catch what source can't show — **axe-core**
(button/link names, image alt, `lang`, ARIA, landmarks, heading order), **hover/focus-state contrast**,
modal **focus-trap**, plus a render-based **anti-slop** report. Opt-in; skips cleanly without Playwright.
```bash
node scripts/runtime/audit_runtime.mjs out/index.html   # after npm run build, in the prototype
```

---

## 🧩 Folded design skills

All 19 skills from `shadcn-skills-design-starter` are vendored into the pipeline. The
generation-time ones are wired into steps; the situational ones are available on demand.
Full map: [`references/SKILLS.md`](.claude/skills/designops-pipeline/references/SKILLS.md).

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
├── .claude/skills/designops-pipeline/          # 🛠 the pipeline skill
│   ├── SKILL.md                          #    full spec
│   ├── commands/generate-prototype.md
│   ├── scripts/
│   │   ├── run_pipeline.sh               #    runner — chains every step
│   │   ├── validate_{brief,intelligence,flows,screens,aesthetic}.py
│   │   ├── audit_prototype.py            #    Step 4.7 gate (5: token·WCAG·copy·contracts·font)
│   │   ├── lint_{hardcodes,component_contracts,font_imports}.py
│   │   └── selftest.sh                   #    89/89 regression guard
│   └── references/
│       ├── aesthetics/                   #    🎨 138-brand library + taste + contrast.py
│       ├── tokens/                       #    DTCG token foundation + validators (brandkit)
│       ├── ux-writing/                   #    voice-tone + check_no_emoji.py
│       ├── storybook/                    #    opt-in QA template (Step 4.8)
│       ├── design-review.md · critique-framework.md · audit-checklist.md
│       ├── intelligence-layer.md · poc-patterns.md · shadcn-prototype.md
│       ├── image-to-code.md · brandkit.md · migrate-design-system.md
│       ├── performance.md · governance.md · mobile-usability.md · SKILLS.md
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

## ✅ Requirements

| Requirement | Needed for | Notes |
|-------------|-----------|-------|
| **Claude Code** | reading the TOR + generating every artifact | **Required.** Without it the runner only stages prompts and produces no output. |
| **Python ≥ 3.9** | every validator + audit gate + DS inventory scan | **Stdlib only — no `pip install`.** (3.9+ for `list[str]` typing.) |
| **Node.js ≥ 18** | building the prototype (`npm install && npm run dev`) | The vendored DS is **source-only** — the *first* prototype build runs `npm install` (needs network once); later builds reuse `node_modules` offline. |
| **poppler** (`pdftotext`) | better PDF text extraction | Optional — falls back to Claude reading the PDF. `brew install poppler`. |
| Playwright · Lighthouse · Figma MCP | Steps 4.7b / performance / 5 | Optional — these steps **skip cleanly** when the tool is absent. |

**Cloning this repo to use elsewhere?** It is designed to run **standalone and offline** by default:
no absolute paths, the design system is vendored in-repo, and the validators are pure stdlib. Two
things to know:

- **Don't pass `--ds-import`.** That flag pulls the private `@npsin-oreo/design-system` package; you
  won't have access. The default (and `--ds-auto`) use the in-repo `./design-system` via rsync, which
  is what you want.
- A few doc links point at the author's hosted **Storybook** (`npsin-oreo.github.io`). The same
  contracts are vendored locally in `references/component-variants.generated.md`, so nothing breaks.

---

## 🧪 Tests

```bash
bash .claude/skills/designops-pipeline/scripts/selftest.sh        # 89/89, runs on macOS stock bash 3.2
```

Covers bash-3.2 compatibility, every validator (valid passes / invalid fails), the full 8-gate audit
(fake brand, low contrast, hardcode, emoji, neutral-theme regression, missing safeguard, unbuilt Must
screen all blocked), feature/scoring traceability, and the DTCG token gates.
**Run it after editing any script** in `.claude/skills/designops-pipeline/scripts/`.

---

## 🧱 Standalone design

The core pipeline depends on **no external repo**. The design system is vendored at
`./design-system/` (source-only, used for Step 3 *and* as the prototype base); the brand library
and DTCG token kit live under `references/`. `run_pipeline.sh` resolves `--ds` in order:
`TOR_DS_PATH` env → `./design-system` (in-repo) → `../shadcn-skills-design-starter` (fallback).

The `--handoff` token bridge (hex → oklch into a whitelabel repo) is **deprecated**. Under Model A
the DS is the imported `@npsin-oreo/design-system` package and theming is owned by Step 2.6 → the product
scaffold, so there is no token-bridge step in the normal flow. The flag is kept for back-compat only
against a repo that still ships `brand.config.json` + `npm run brand:build` (never the DS repo).

---

## 📜 License

Pipeline code in this repo is **MIT** — see [`LICENSE`](LICENSE). To stay standalone it **vendors**
third-party material (shadcn/ui, the shadcn-skills-design-starter design system + skills, the
runtime-audit from ux-ui-agent-skills), each under its own upstream license — see [`NOTICE`](NOTICE)
for attributions. Verify the upstream terms before redistributing.

---

## 🧰 Tech stack

`Next.js 16` · `React 19` · `Tailwind CSS v4` · `shadcn/ui` · `Claude Code` · `Python 3.9+ (stdlib only)`

<div align="center">
<sub>Built for the DesignOps team · every gate is a script, not a vibe</sub>
</div>
