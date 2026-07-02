# Runtime Audit — Step 4.7b (optional)

The static gate (`scripts/audit_prototype.py`, Step 4.7) reads the source: tokens, contrast from
`globals.css`, no-emoji. It **can't see what only exists once the page renders** — ARIA names,
labels, landmarks, heading order, hover/focus-state contrast, modal focus traps. This layer fills
that gap by rendering the built page in headless Chrome (Playwright) and running real checks.

Vendored from `ux-ui-agent-skills` (v2.3.1). **Opt-in**: needs Playwright, but degrades gracefully —
without it, every gate prints `SKIPPED` and the run exits 0 (never blocks the default flow).

## What it checks (on the built `out/index.html`)

| Gate | Tool | Catches | Blocks? |
|------|------|---------|---------|
| **axe** | `axe_audit.mjs` | axe-core WCAG 2.x A/AA: button/link names, image alt, `lang`, `<title>`, ARIA roles, label associations, landmarks, heading order | 🔴 yes |
| **states** | `verify_states.mjs` | text/bg contrast in **default + hover + focus** (a button that turns the wrong color on hover) | 🔴 yes |
| **structure** | `verify_structure.mjs` | render at mobile+desktop: **control-height parity** within a form (the 32px select next to a 48px input — the NativeSelect className→wrapper bug), **surface consistency** across breakpoints, **phone-lock** (content capped to phone width on desktop — advisory unless `--desktop-role`) | 🔴 yes (phone-lock advisory) |
| **focus-trap** | `verify_focustrap.mjs` | modal traps Tab, has `role=dialog`+`aria-modal`+name, Esc returns focus (WCAG 2.1.2/2.4.3) — only when `--open=<sel>` given | 🔴 yes |
| **taste** | `taste_audit.mjs` | render-based anti-slop (type-scale drama, equal-weight repetition, body measure, palette, pure #000/#fff, whitespace) | advisory (report only) |
| **richness** | `verify_richness.mjs` | render-based **anti-plain** (track I): flat cards (bg==page, no border/shadow), no identity colour (greyscale screen — accent unused), no elevation, blank empty states. The evidence the Step 4.6 critique reads to score its **richness** dimension (track J); the render counterpart to `aesthetic.json`'s `usage` block (track H) | advisory (report only; `--strict-richness` to block) |
| rtl / responsive | `verify_rtl.mjs` · `verify_responsive.mjs` | RTL mirroring · breakpoint behavior (run directly when relevant) | 🔴 yes |

`audit_runtime.mjs` orchestrates axe + states + structure (+ focus-trap if a trigger is given) + the taste report.

> **structure gate (track E)** is the render-based answer to the "clean but plain" first-draft gap: it
> would have caught the PARICH WMS draft-1 failures (a 32px select beside a 48px input, a phone-locked
> desktop column) that green-passed all 11 static gates. It closes the loop on the C1/C2 scaffold —
> those ship a grid + control-parity `[data-slot]` rules, and this gate is what actually *sees* that
> they took effect. Pass `--desktop-role` (from `intelligence.json` → a desktop-target role) to make
> phone-lock a hard block instead of an advisory.

## Enable + run (inside `output/prototype/`, after `npm run build`)

```bash
cd output/prototype
npm i -D playwright && npx playwright install chromium     # one-time (~150MB)

# copy the runtime scripts in (so Playwright resolves from the prototype's node_modules)
mkdir -p scripts/runtime
cp .claude/skills/designops-pipeline/references/runtime-audit/scripts/*.mjs scripts/runtime/

node scripts/runtime/audit_runtime.mjs out/index.html            # light theme
node scripts/runtime/audit_runtime.mjs out/index.html --dark     # dark theme
# a screen with a modal:
node scripts/runtime/audit_runtime.mjs out/<page>/index.html --open="#open-dialog" --dialog="[role=dialog]"
```

Exit 1 = a blocking gate failed (fix and re-run). Exit 0 = pass, or Playwright absent (skipped).

> Proven: on a clean page → 🟢 PASS; on a page with a nameless button / missing `alt` / no `lang` →
> axe reports `button-name`, `image-alt`, `html-has-lang`, `link-name`, `document-title` and the run
> exits 1. This is the layer that the static gate cannot replace.
