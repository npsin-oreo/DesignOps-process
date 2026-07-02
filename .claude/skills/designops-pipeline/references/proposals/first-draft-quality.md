# Proposal — Make the FIRST draft hit the quality bar (A–J)

**Status:** Draft / not yet implemented
**Author:** dogfooding retrospective (PARICH WMS, `output-2/`)
**Date:** 2026-07-02

## Why this exists

On the PARICH WMS dogfood, the generated **draft 1** passed all 8 validators + 11 audit
gates + critique 8.1/10 — yet it was **not** what the reviewer expected. It took a long
manual polish pass (dual-mode responsive shell, a 12/8/4 grid system, control-size parity,
modal reachability, unified surfaces) to reach the bar the reviewer *expected to see in
draft 1*.

The gates all passed because **every check is static** (lint / parse / contrast-from-CSS).
Nothing rendered the app, so the real gaps were invisible to the pipeline.

This proposal lists the fixes (A–J) that would let the **first** draft reach that bar,
split into two tracks:

- **Structural plainness (A–G)** — mobile-only cramped column, no app-shell, inconsistent
  control sizing, no grid, unreachable modals, non-responsive. This is what the reviewer
  actually flagged.
- **Aesthetic plainness (H–J)** — flat white cards, no depth/tint, accent unused, generic
  empty states. Separate "taste/richness" axis; `gate 6` only checks tokens are *applied*,
  not *used richly* ("brand colour slapped on a neutral skeleton" passes today).

## Root causes (why draft 1 missed)

1. **No device/viewport dimension in the intent artifacts.** The PRD persona table split
   office (desk) vs frontline (mobile), but the pipeline never extracted it into a
   directive → built mobile-only (`max-w-md`) everywhere → no gate could catch it.
2. **No layout system in the design tokens or scaffold.** The aesthetic layer stops at
   color / type / radius. Grid, gutter, container widths, control-height scale, and spacing
   rhythm were left to ad-hoc per-screen decisions → inconsistency.
3. **DS component sizing gotchas are invisible.** `NativeSelect` routes `className` to its
   wrapper and hardcodes the inner `<select>` to `h-8`/`text-sm`, so a select rendered 32px
   while inputs were 48px — a real bug that passed **all** gates.
4. **Static-only audit.** No gate renders the app, so responsive breakage, control-height
   mismatch, unreachable modals, and surface inconsistency are all unobservable.
5. **Critique scores blind.** Step 4.6's judge scores from code + `screen-inventory.json`,
   not rendered screenshots at multiple breakpoints, so it gave 8.1 to something with
   visible flaws.

## The fixes

### Track 1 — Structural (A–G)

| ID | Fix | Root | File / gate | Acceptance |
|----|-----|------|-------------|------------|
| **A** | Add a **device dimension** per `user_type` (`primary_device`: desktop/mobile/both) → roll up to `design_directives.responsive` (per-role target). | #1 | `intelligence.json` + `validate_intelligence.py` | Validator rejects an intelligence file whose user_types don't declare a device; directive names which roles are desk vs mobile. |
| **B** | Add a **layout axis** to the aesthetic tokens: grid columns per breakpoint (4/8/12), gutter (24px), container max-widths, control-height scale (mobile 48 / desktop 40), min touch target, radius. Emit as tokens. | #2 | `aesthetic.json` `axis_tokens` + `validate_aesthetic.py` | Aesthetic file carries a `layout` axis; validator checks the grid/gutter/heights are present and internally consistent (e.g. touch-min ≤ mobile control height). |
| **C** | **Scaffold defaults**: ship `components/layout.tsx` (`Grid`/`Col`/`Stack`, per-breakpoint spans) + the `[data-slot]` control-parity overrides (native-select height = input height; desktop `lg:h-10`) so form controls match and a grid exists from screen 1. | #2, #3 | `setup-prototype.sh` (+ generated `globals.css`) | A fresh scaffold renders a select and an input at equal height on both mobile and desktop, and exposes the grid primitives. |
| **D** | **DS component usage-notes / gotchas** fed into the contract lint: `NativeSelect`→wrapper className, `disabled` button inside `AlertDialogTrigger` is an anti-pattern (modal never opens), etc. | #3 | DS inventory (a `component-notes.json`) + `lint_component_contracts.py` (gate 4) | Gate 4 flags a disabled trigger and a raw `h-*` on `NativeSelect` (which no-ops). |
| **E** | **Turn on the runtime audit (Step 4.7b) as a real gate, expanded.** Render every screen at mobile / tablet / desktop and assert: (1) control-height parity within a form, (2) each screen's primary CTA opens a dialog or navigates (reachability), (3) no fixed `max-w-md` on a desktop-role screen, (4) background/surface consistency across breakpoints. | #3, #4 | `references/runtime-audit/` → new gate in `audit_prototype.py` (skips cleanly w/o Playwright) | With Playwright present, the gate blocks on: mismatched control heights, an unreachable primary CTA, a desktop-role screen locked to phone width, or a surface color that differs by breakpoint. |
| **F** | **Feed rendered screenshots (per breakpoint) into the critique** so the judge scores what is actually visible. | #5 | Step 4.6 (critique input) | `critique.json` references the screenshot set; judge notes cite what was seen. |
| **G** | **POC convention: prefill valid demo defaults** so every gated action is reachable in a walkthrough (documented, not per-screen guesswork). | #4 | `commands/generate-prototype.md` / poc-patterns | Generated forms open with valid seed values; every confirm dialog is reachable in the built prototype. |

### Track 2 — Aesthetic richness (H–J)

| ID | Fix | File / gate | Acceptance |
|----|-----|-------------|------------|
| **H** | Aesthetic layer emits **usage directives**, not just token values: tinted semantic surfaces, elevation tiers, where accent goes, a hero moment per key screen, empty states with content. | `aesthetic.json` (new `usage` block) + `validate_aesthetic.py` | Aesthetic file specifies *how* to apply identity (surfaces/elevation/accent/hero), not only hex/type. |
| **I** | **Anti-plain runtime check** — extend the render-based anti-slop in 4.7b to flag: all-flat-white cards (no tint), no accent usage on a screen, no elevation hierarchy, generic/blank empty states. | `references/runtime-audit/` | Gate warns (or blocks at high strictness) when a screen is visually flat / identity-unused. |
| **J** | **Critique adds a "visual richness / identity usage" dimension**, scored from screenshots (builds on F). | `validate_critique.py` (add dimension) | Each screen scores a richness dimension; a flat "neutral skeleton" can't score high just because tokens exist. |

## Phase 1 build decisions (resolved before implementation)

Two seams the fixes above don't specify, decided here so Phase 1 can be built without re-litigating:

### D0 · The render gate (E) must NOT participate in `--strict`

`audit_prototype.py`'s `_ok()` counts a **skipped** gate (`None`) as a **failure under `--strict`**,
and `finalize-prototype.sh` runs the audit `--strict` by default on a *complete* build. If the render
gate (fix E) were added to the ordinary `skippable` set, then a complete build on any machine **without
Playwright** would flip from "skipped cleanly" to **BLOCKED** — breaking the existing "degrades without
Playwright" contract (Step 4.7b) and any CI runner that has no browser.

**Decision:** the render gate is registered in a **separate `render_optional` tuple**, evaluated with
plain `_ok(v, strict=False)` regardless of the global `--strict`. So:
- no Playwright → the gate prints `—` and **never blocks**, even under `--strict`;
- Playwright present + a real render failure → the gate returns `False` and **blocks** (strict or not).

This keeps the render check honest when it *can* run, without making a headless browser a hard
dependency of the audit. (If the project later wants render checks mandatory, that becomes an explicit
`--require-render` flag, not a side effect of `--strict`.)

### D1 · The layout axis (B) extends the existing `axes` block — no new plumbing

Gate 11 (`lint_axis_fidelity.py`) already reads `aesthetic.json` → `axes.<facet>.resolved` for
type/shape/spacing/motion. The layout axis is added as an **optional 7th `axes.layout`** with a
`resolved` block (grid/gutter/container/control-height/touch-min), **not** a new top-level field and
**not** a new validator. It is directive-derived (`source: "intelligence"`, from `density_target` +
the new `responsive` directive), so it sits outside the coherence source-count and does not disturb
the existing 6-axis composition rules. `validate_aesthetic.py` iterates only the required 6, so the
new axis is fully back-compatible; gate 11 (fix B, later task) verifies its `resolved` metrics landed
in `globals.css`. Token contract in `references/aesthetics/README.md` § "layout axis".

## Rollout phasing

- **Phase 1 (highest ROI, structural):** B + C + E — **IMPLEMENTED**. Layout axis (B1-B3:
  `axes.layout` + `validate_aesthetic.py` invariants + gate 11 token check), scaffold defaults
  (C1 `Grid`/`Col`/`Stack` + `@theme` layout tokens, C2 `[data-slot]` control-parity), and the
  render gate (E1 `verify_structure.mjs` + E2 gate 12 in `audit_prototype.py`, outside `--strict`
  per D0 + E3 selftest T21/T22). A layout system from screen 1 + a rendering gate catches the
  majority of what went wrong this round.
- **Phase 2:** A + D + G. Make dual-mode a first-class traceable requirement, teach the
  lint the DS gotchas, codify demo-prefill.
- **Phase 3 (richness):** F + H + I + J. Close the "clean but plain" gap with usage
  directives, an anti-plain detector, and a screenshot-based critique dimension.

## The one-line thesis

The pipeline can only see **static code + tokens**. Everything that made draft 1 miss
(responsive fit, control sizing, modal reachability, surface consistency, visual richness)
is only visible when the app is **rendered**. So the two highest-leverage moves are:
**(B/C) give layout a real token + scaffold so structure exists by default**, and
**(E/I) add a runtime gate that renders and looks** — then feed what it sees back into the
critique (F/J).

## Reference case

`output-2/` (PARICH WMS) is the worked example: the draft-1 state vs the polished state is
the before/after this proposal is calibrated against. See memory `[[parich-wms-example]]`.
