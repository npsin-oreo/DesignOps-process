<div align="center">

# 🎨 DesignOps Pipeline — TOR → Prototype

**Drop in a project brief → get a clear written spec and a working demo app —
with accessibility and design quality checked automatically along the way.**

Powered by Claude Code · Next.js 16 · shadcn/ui · Tailwind v4

`Model A (imports @npsin-oreo/design-system)` · `WCAG-gated` · `138-brand aesthetic library` · `10-gate audit (renders + looks)` · `169/169 selftest` · `CI on every PR`

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
         ▼  3.7   edge cases per Must screen (UI Stack × CORRECT)  edge-cases.json      →  validate_edgecases.py
         │
         ▼  4     scaffold Next.js prototype (grid + control-parity from screen 1)   output/prototype/
         │
         ▼  4.6   scored critique (7 dims incl. richness + Nielsen + anti-slop) → auto-fix
         ▼  4.7   audit GATE — audit_prototype.py (10 gates)   docs/audit-report.md     🔴 exit 1 = blocked
         │          tokens · WCAG (light+dark) · copy · contracts · fonts
         │          · fidelity family (theme+font+axes) · directive · screens · edges
         ▼  4.7b  runtime audit (optional) — renders + LOOKS: axe · states · structure
         │          (control-parity/phone-lock) · richness (anti-plain) · focus-trap · taste   (Playwright)
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
| 🛡️ **Real gates, not vibes** | Every stage has a zero-dependency validator. The audit gate is a *script* with **10 gates** — hardcodes · WCAG contrast (light + dark) · UX copy · component-contracts · font-imports · a **fidelity family** (theme + font + non-colour axes all applied) · directive-fidelity · screen-coverage · edge-coverage · **render structure** — exit 1 blocks handoff. `finalize-prototype.sh` chains it (`--strict`) with the critique + usability integrity checks so the audit can't be skipped. |
| 👁️ **It renders, then looks** | The one runtime gate (Playwright) renders each screen at mobile + desktop and catches what source can't: a 32px select next to a 48px input, a phone-locked desktop column, a flat greyscale skeleton — the failures that passed every *static* gate on a real dogfood. Degrades cleanly without a browser. |
| 🧵 **Intent makes it to the build** | A traceability spine carries the contractual scope end-to-end: every **Must** feature and scored must-have is provably served by a task, a screen, and a built route — plus a per-role **device dimension** (desktop/mobile/both) so a build can't quietly go mobile-only. Checked, not assumed. |
| 🔁 **Scored quality loop** | Step 4.6 critique = **7 weighted dimensions** (incl. **richness/identity**, scored from the render) + Nielsen's 10 heuristics + an anti-slop gate (Banned Defaults) — a flat "brand colour on a neutral skeleton" can't score high just because its tokens exist. |
| 🧩 **19 design skills, folded in** | ux-writing, brandkit (DTCG tokens), image-to-code, migrate-design-system, performance, governance — vendored into the skill. See [`references/SKILLS.md`](.claude/skills/designops-pipeline/references/SKILLS.md). |
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
| **2.5** | Product Intelligence — 10 dims → `design_directives` (+ feature traceability + per-role **device**) | `intelligence.json` | `validate_intelligence.py` |
| **2.6** | Aesthetic Direction — full identity theme + **layout axis** + **usage** directives | `aesthetic.json` · `brand.config.json` | `validate_aesthetic.py` |
| **3** | Refine user flows from directives | `flows.json` | `validate_flows.py` |
| **3.5** | Screens from flows + DS mapping (+ feature/scoring coverage) | `screen-inventory.json` · `design-first-draft.md` | `validate_screens.py` |
| **3.7** | Edge-Case Analysis (UI Stack × CORRECT) per Must screen | `edge-cases.json` | `validate_edgecases.py` |
| **4** | Scaffold the Next.js prototype (grid + control-parity from screen 1) | `output/prototype/` | — |
| **4.6** | Scored critique (7 dims, richness from render) → auto-fix critical + quick wins | `docs/critique.md` · `critique.json` | `validate_critique.py` |
| **4.7** | **Audit gate** — 10 gates (token · WCAG · copy · contracts · font-import · fidelity family · directive · screens · edges · render) · `finalize-prototype.sh` chains it `--strict` + critique + usability | `docs/audit-report.md` | `audit_prototype.py` 🔴 exit 1 |
| **4.7b** | Runtime audit (opt-in) — renders + looks: axe · states · **structure** · **richness** · focus-trap | — | Playwright |
| **4.8** | Storybook QA (opt-in) | — | `addon-a11y` axe pass |
| **5** | Figma output (5 pages: Cover/Foundations/Components/Screens/Flows) — generated from artifacts | Figma file | `figma_prep.py` + Figma MCP |

---

## 🧠 Product Intelligence Layer (Step 2.5)

Between the brief and the UI, the pipeline infers **10 measurable product dimensions** — each with
**evidence + confidence** — and rolls them up into an open **`design_directives`** object. Any
domain is expressible as a vector; there are no fixed presets.

`User Types (+ primary_device) · Expertise · Goals · Core Tasks · Workflow Complexity · Data Density · Error Tolerance · Accessibility · Compliance · Decision Criticality`

```
design_directives = { density_target 1–5, guidance_level, safeguard_level,
                      a11y_target, mandatory_flows[], navigation_model, trust_emphasis,
                      responsive: { target: desktop|mobile|both, desktop_roles[], mobile_roles[] } }
```

Each `user_type` declares a **`primary_device`** (desktop/mobile/both) that rolls up into
`responsive` — so a split desk/frontline audience becomes a directive the build (and the render
phone-lock gate) honour, instead of a silent mobile-only column.

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
- **Layout axis** — a `layout` axis (grid columns 4/8/12, gutter, container widths, control-height
  scale, touch target) so structure is a *token* the scaffold applies from screen 1, not an ad-hoc
  per-screen guess. Verified in the build by the fidelity family (axis sub).
- **Usage directives** — a `usage` block says *how* to apply the identity richly (tinted surfaces,
  elevation tiers, where the accent lands, a hero moment, empty states with content), so the render
  anti-plain check + the critique richness dimension have something to enforce.
- **Gate** — `validate_aesthetic.py` **recomputes WCAG contrast from the hex values itself**
  (never trusts the agent), requires the chosen system to resolve in the library, demands the full
  light+dark identity set, checks the layout invariants (touch ≤ control height, grid non-decreasing),
  and forces `a11y_target`/`density_target` to echo `design_directives`.

Output `aesthetic.json` + a ready-to-apply `output/brand.config.json` (carrying the whole theme) for
`/generate-prototype` — and the audit **fidelity family (gate 6)** blocks if the build regresses to neutral.

**Beyond colour — themeable axes + DS-native theming.** `@npsin-oreo/design-system@0.3.0` exposes
**`axis_tokens`** in its contract — non-colour design axes (`ease · duration · leading · tracking ·
weight_heading · container · section`). So a product can theme typography/motion/layout, not just
colour, from one config. The multi-product path: `brand.config.json` → `npx ds-brand-build` →
`app/brand.css` → `@import "./brand.css"` in `globals.css`. The DS root stays the single source of
token **names** (`token-contract.json`: colour + scalar + axis); each product is one config. The
token tiers are **primitive → semantic → component** (Tailwind's `@theme`/`--color-*` is the
*utility-binding* layer, not a tier). Gates 2 and 6 follow the local `@import`, so this verifies
end-to-end without losing any check.

---

## 🔁 Quality loop — scored, then gated

**Step 4.6 — Critique (scored)** · [`critique-framework.md`](.claude/skills/designops-pipeline/references/critique-framework.md) → [`design-review.md`](.claude/skills/designops-pipeline/references/design-review.md)

- Score **7 weighted dimensions** (Hierarchy 20 · Consistency 15 · Accessibility 20 · Usability 15 · Responsiveness 10 · Performance 10 · **Richness/identity 10**) → weighted overall (≤6 = rework). **Richness is scored from the render** (via `capture_screens.mjs` screenshots + the anti-plain report), so a flat neutral skeleton can't score high on tokens alone.
- **Separate judge pass** (pass/fail) — `judge_verdict:false` caps the overall at 2.0; looks never rescue a broken core task. `validate_critique.py` enforces the cap.
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
| 4 | **Component contracts** | `lint_component_contracts.py` — icon-only buttons need a name, every `DialogContent` a `DialogTitle`, labelled `Input` a matching `FieldLabel htmlFor`; plus **DS gotchas** (`component-notes.json`: a height utility on `<NativeSelect>` no-ops → block; a disabled modal trigger → advisory) | 🔴 block |
| 5 | **Font imports** | `lint_font_imports.py` — no remote-font CSS `@import` (500s the Turbopack dev server; use `next/font`) | 🔴 block |
| 6 | **Fidelity family** | did the committed Step 2.6 direction get applied? ONE gate, three sub-checks: **theme colours** (`lint_theme_fidelity.py` — no regression to neutral) · **font** (`lint_font_fidelity.py` — committed `font_sans` reaches the build) · **non-colour axes** (`lint_axis_fidelity.py` — type/shape/motion + layout tokens land in `@theme`). Blocks if any sub fails. | 🔴 block |
| 7 | **Directive fidelity** | `lint_directive_fidelity.py` — the build honors `design_directives`: destructive actions guarded when `safeguard_level` is on, an empty-state when `guidance_level` is guided (density/nav advisory) | 🔴 block |
| 8 | **Screen coverage** | `lint_screen_coverage.py` — every **Must** screen in `screen-inventory.json` was built as an `app/<route>/page.tsx` rendering its declared loading/empty/error states | 🔴 block |
| 9 | **Edge-case coverage** | `lint_edge_coverage.py` — every **Must** edge in `edge-cases.json` is handled in its screen (empty/error/loading/partial state · inline validation · destructive confirm) | 🔴 block |
| 10 | **Render structure** *(optional)* | `verify_structure.mjs` (Playwright) — renders at mobile+desktop for control-height parity, surface consistency, and phone-lock. **Always evaluated outside `--strict`**: a skip never blocks, only a real render failure does. Needs a build + Playwright. | 🔴 block (when it runs) |

> Gates 6-9 auto-discover their source artifact (`brand.config.json` / `aesthetic.json` /
> `intelligence.json` / `screen-inventory.json` / `edge-cases.json`) beside the prototype, or take
> `--theme` / `--aesthetic` / `--intel` / `--screens` / `--edges`, and skip cleanly when absent.
> Gates 2 and 6 also follow a local `@import "./brand.css"` (DS-native theming — see below).
> Gate 10 (render) is **render-optional** — it never blocks a machine without Playwright, even under
> `--strict` — and auto-derives `--desktop-role` from `intelligence.json`'s `responsive` target.
>
> **`finalize-prototype.sh` is the enforcement seam:** it always runs the audit (`--strict` on a
> complete build, so a skipped artifact-backed gate counts as a failure) plus the critique +
> usability integrity checks — so the audit can't be silently forgotten before handoff.
> `bash …/scripts/finalize-prototype.sh output/prototype --a11y AA`

> **Exit 1 = BLOCKED** — handoff/Figma is blocked until it passes. Categories are machine-checked,
> not eyeballed. It audits the **generated surface only** (`components/ui` and any `docs/` dir are
> auto-excluded), so just point it at the prototype — no `--scan` needed; add `--include-vendored` to audit everything.

**Step 4.7b — Runtime audit (optional)** · [`runtime-audit/`](.claude/skills/designops-pipeline/references/runtime-audit/README.md)

Renders the built page in headless Chrome (Playwright) to catch what source can't show — **axe-core**
(button/link names, image alt, `lang`, ARIA, landmarks, heading order), **hover/focus-state contrast**,
**structure** (control-height parity, surface consistency, phone-lock — this is what surfaces into audit
gate 10), **richness** (anti-plain: flat cards, no identity colour, no elevation, blank empty states),
modal **focus-trap**, plus a render-based **anti-slop** report. `capture_screens.mjs` writes the
mobile+desktop PNG set the Step 4.6 critique scores richness from. Opt-in; skips cleanly without Playwright.
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
| `--ds <path>` | looloo design-system **source** checkout, read for inventory/token-contract only (default: `../looloo-design-system`) |
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
│   │   ├── validate_{brief,intelligence,flows,screens,aesthetic,critique,edgecases}.py
│   │   ├── audit_prototype.py            #    Step 4.7 gate (10: token·WCAG·copy·contracts·font·fidelity-family·directive·screen·edge·render)
│   │   ├── lint_{hardcodes,component_contracts,font_imports,theme/font/axis_fidelity,…}.py
│   │   ├── setup-prototype.sh            #    scaffolds Grid/Col/Stack + control-parity + @theme layout tokens
│   │   └── selftest.sh                   #    169/169 regression guard (CI runs it on every PR)
│   └── references/
│       ├── aesthetics/                   #    🎨 138-brand library + taste + contrast.py
│       ├── runtime-audit/                #    Playwright gates: structure · richness · axe · capture_screens
│       ├── tokens/                       #    DTCG token foundation + validators (brandkit)
│       ├── ux-writing/                   #    voice-tone + check_no_emoji.py
│       ├── storybook/                    #    opt-in QA template (Step 4.8)
│       ├── component-notes.json          #    DS gotchas fed to gate 4 (NativeSelect, disabled trigger)
│       ├── proposals/first-draft-quality.md  #  the A–J plan (structure + richness), fully implemented
│       ├── design-review.md · critique-framework.md · audit-checklist.md
│       ├── intelligence-layer.md · poc-patterns.md · shadcn-prototype.md
│       ├── image-to-code.md · brandkit.md · migrate-design-system.md
│       ├── performance.md · governance.md · mobile-usability.md · SKILLS.md
│       └── sample-tor.md
│                                          # DS is imported (@npsin-oreo/design-system) — not in-repo
├── .github/workflows/selftest.yml        # 🤖 CI — runs selftest on every PR
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
| `edge-cases.json` | AI (non-happy-path contract) | 3.7 |
| `prototype/` | Dev (Next.js app) | 4 |
| `prototype/docs/critique.md` · `critique.json` · `audit-report.md` | Designer/Dev · gate · QA/Lead | 4.6 / 4.7 |
| `prototype/docs/poc-handoff.md` | Dev handoff | 6 |

---

## ✅ Requirements

| Requirement | Needed for | Notes |
|-------------|-----------|-------|
| **Claude Code** | reading the TOR + generating every artifact | **Required.** Without it the runner only stages prompts and produces no output. |
| **Python ≥ 3.9** | every validator + audit gate + DS inventory scan | **Stdlib only — no `pip install`.** (3.9+ for `list[str]` typing.) |
| **Node.js ≥ 18** | building the prototype (`npm install && npm run dev`) | The build **imports** `@npsin-oreo/design-system` into `output/prototype/node_modules` (needs network + `GITHUB_TOKEN`). |
| **`GITHUB_TOKEN`** | installing the DS package from GitHub Packages | **Required** for the build — `export GITHUB_TOKEN=$(gh auth token)`. Public packages still need auth on GitHub Packages. |
| **poppler** (`pdftotext`) | better PDF text extraction | Optional — falls back to Claude reading the PDF. `brew install poppler`. |
| Playwright · Lighthouse · Figma MCP | Steps 4.7b / performance / 5 | Optional — these steps **skip cleanly** when the tool is absent. |

**Cloning this repo to use elsewhere?** The pipeline is a **consumer of `@npsin-oreo/design-system`**
(Model A) — the build imports the package, it is not standalone. Two things to know:

- **You need access to `@npsin-oreo/design-system` on GitHub Packages** + a `GITHUB_TOKEN`
  (`export GITHUB_TOKEN=$(gh auth token)`). The validators + the pipeline orchestration are pure
  stdlib / bash, but the *build* (`setup-prototype.sh`) installs the DS package.
- Point `--ds` (or `TOR_DS_PATH`) at a **looloo-design-system source checkout** — it is read only for
  the component inventory + `token-contract.json` + DESIGN.md (Steps 2.6 / 3.5); the build still
  imports the published package.

---

## 🧪 Tests

```bash
bash .claude/skills/designops-pipeline/scripts/selftest.sh        # 169/169, runs on macOS stock bash 3.2
```

Covers bash-3.2 compatibility, every validator (valid passes / invalid fails), the full 10-gate audit
(fake brand, low contrast, hardcode, emoji, neutral-theme regression, missing safeguard, unbuilt Must
screen, unhandled edge case, un-applied font/axis, layout-axis invariants, DS gotchas, missing device
directive, missing richness dimension all blocked), feature/scoring/device traceability, the
render/richness runtime scripts (graceful skip without Playwright), the import-only setup, and the DTCG
token gates.
**Run it after editing any script** in `.claude/skills/designops-pipeline/scripts/`.

**CI** — [`.github/workflows/selftest.yml`](.github/workflows/selftest.yml) runs the selftest on every
PR that touches the skill (and on pushes to `main`). The runtime `.mjs` gates self-skip without
Playwright, so CI needs only python3 + node — a green PR means the regression guard actually passed.

---

## 🧱 Model A — consumes the looloo design system

The build **imports** `@npsin-oreo/design-system` (looloo) from GitHub Packages (pinned, currently
**0.3.0**) — the DS is never vendored or copied. Components are immutable
(`@npsin-oreo/design-system/<name>` in `node_modules`); customise via Step 2.6 token +
`[data-slot=*]` overrides, never by editing them. The brand library + DTCG token kit still ship under
`references/`. `run_pipeline.sh` resolves `--ds` (the looloo SOURCE, read only for
inventory/token-contract): `TOR_DS_PATH` env → `../looloo-design-system` sibling. Requires
`GITHUB_TOKEN` (`export GITHUB_TOKEN=$(gh auth token)`).

`setup-prototype.sh` scaffolds the Tailwind-v4 guards every prototype needs: `@source not "../public"`
+ `@source not "../.next"` (v4 auto-source-detection otherwise reads binary `*.webp`/`*.png` as text →
garbage classes → Turbopack 500), a Next `.gitignore`, and a `.vscode/settings.json` that silences the
false "Unknown at rule" lint on `@source`/`@theme`/`@apply`.

The `--handoff` token bridge (hex → oklch into a whitelabel repo) is **deprecated**. Under Model A
the DS is the imported `@npsin-oreo/design-system` package and theming is owned by Step 2.6 → the product
scaffold, so there is no token-bridge step in the normal flow. The flag is kept for back-compat only
against a repo that still ships `brand.config.json` + `npm run brand:build` (never the DS repo).

---

## 📜 License

Pipeline code in this repo is **MIT** — see [`LICENSE`](LICENSE). It **vendors** some third-party
material (shadcn/ui patterns + skills, the brand library, the runtime-audit from ux-ui-agent-skills),
each under its own upstream license — see [`NOTICE`](NOTICE)
for attributions. Verify the upstream terms before redistributing.

---

## 🧰 Tech stack

`Next.js 16` · `React 19` · `Tailwind CSS v4` · `shadcn/ui` · `Claude Code` · `Python 3.9+ (stdlib only)`

<div align="center">
<sub>Built for the DesignOps team · every gate is a script, not a vibe</sub>
</div>
