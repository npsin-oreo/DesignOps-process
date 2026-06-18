# Proposal — 3-repo architecture (Model A: shared DS + per-project theme)

> **Decision locked:** Model A (one shared DS, themed per project) · DesignOps **keeps Step 2.6**
> (the Designer defines aesthetic direction down to the token values). DS repo owns the *system*;
> DesignOps owns the *theme*; Dev owns the product.

## One-liner

A single dev-maintained **Design System** repo ships components + a **token contract**. DesignOps
reasons about a TOR and, via Step 2.6, the Designer resolves a per-project **theme** (`brand.config.json`)
— that is "the DS of this project". DesignOps generates a **Product repo** that *imports* the DS and
drops in the theme. No DS code is copied; the look is a thin token layer the Designer controls.

## The three repos

| Repo | Owner | Contains | Does NOT |
|------|-------|----------|----------|
| **`design-system`** | **Dev** | components (52), `lib`, hooks, **token contract** (`tokens.css` `@theme` names), component styling that *reads* tokens, Storybook, published as `@acme/ds` | decide a project's colors/fonts; hold business logic |
| **`designops`** | **Designer / DesignOps** | reasoning (intelligence + `rationale`/`trade_offs`), structure (flows/screens/blueprint), **Step 2.6 Aesthetic → `brand.config.json` (token VALUES)**, the generators + gates | own component code; copy the DS; write business logic |
| **`product-<x>`** | **Dev** | `import @acme/ds`, the project's `brand.config.json`, `generated/` (blueprint shells, regen-safe) + `src/` (business logic) | re-implement components; vendor the DS |

## Ownership of "the look" — the clean split

```
DS repo  → token NAMES/contract + how components consume them   (the SYSTEM, theme-agnostic)
              --primary, --background, --foreground, --radius, --font-sans …  (@theme)
DesignOps 2.6 → token VALUES per project = brand.config.json     (the THEME, Designer-driven)
              { "primary":"oklch(.45 .15 250)", "radius":"0.5rem", "font_sans":"Inter" }
Product  → import DS + apply brand.config → rendered look
```

So **the Designer still defines direction at implementation level** (real oklch values, radius, type),
but never touches component code. Dev evolves the component system without touching any project's brand.

## The seam that makes Model A safe — the **token contract**

The DS repo publishes the canonical list of themeable tokens (the `@theme` variable names). Step 2.6's
`brand.config.json` may only set keys in that contract. This is the one rule that keeps the two repos
in sync:

```
brand.config.json keys  ⊆  DS token contract        (DesignOps can't theme a token the DS ignores)
DS renames/removes a token  → major version bump      (so product lockfiles don't silently break)
```

- `validate_aesthetic.py` already recomputes WCAG contrast from the resolved hex (stays in DesignOps —
  it owns values). **Add:** check `brand.config` keys against the DS token contract (fetched from the
  pinned `@acme/ds` version), so a typo'd/renamed token fails the gate instead of rendering wrong.
- Because `brand.config.json` lives in the **product repo** (dev-editable), the product CI re-runs the
  same contrast + contract check — the gate travels with the file.

## End-to-end flow

```
TOR ─► designops:
        1+2 brief → 2.3 research → 2.4 competitive → 2.5 intelligence (+rationale/trade_offs)
        → 2.6 aesthetic (Designer)  →  brand.config.json   (the project theme)
        → 3 flows → 3.5 screens → blueprint
        → GENERATE product-<x> repo:
             package.json   : "@acme/ds": "^1.x"          (import, pinned)
             app/globals.css: @import "tailwindcss"; @import "@acme/ds/tokens.css";
                              @source "node_modules/@acme/ds/dist";   (gotcha #1)
             brand.config.json (from 2.6)                  ← the DS of THIS project
             generated/  (blueprint shells)  +  src/ (dev logic)
   dev ─► npm install · npm run dev · fills src/ · maintains
designops ─► regenerate generated/ + brand.config via PR  (never touches src/)
```

## What's already proven (this repo) vs what's new

| Piece | Status | Evidence |
|-------|--------|----------|
| DS → importable package (`@acme/ds`) | ✅ proven | `docs/ds-split/package/` — tsup 55 js+dts, consumer tsc+runtime EXIT 0 |
| `@/`→`#` so it imports cleanly | ✅ proven | `docs/ds-split/codemod/` — tsc + `next build` 65/65 |
| import-not-copy + Tailwind `@source` | ✅ proven | `setup-prototype.sh --ds-import`; `next build` utilities in CSS |
| token preset (theme-able) | ✅ proven | `docs/ds-split/package/` `tokens.preset.example.css` |
| regen-safe `generated/` vs `src/` | ✅ proven | `docs/ds-split/boundary/` — POINT 8 ENFORCED |
| Step 2.6 → brand.config (token values) | ✅ exists today | `aesthetic.json` + `brand.config.json` + `validate_aesthetic.py` |
| **token-contract check** (brand keys ⊆ DS contract) | ⬜ new | small add to `validate_aesthetic.py` + DS ships `token-contract.json` |
| **product scaffold generator** (Phase 4) | ⬜ new | emits Product repo: import + brand.config + generated/+src/ |
| **regenerate-by-PR** | ⬜ new | DesignOps opens PR to product, guard blocks edits outside `generated/` |

## Versioning & maintenance

- `@acme/ds` semver; product **pins** it in lockfile → audit/contrast run against the exact tokens shipped.
- Dev evolves DS → publishes minor/patch → products bump when ready. Breaking token rename = major.
- DesignOps regenerates a product's `generated/` + `brand.config.json` via PR; dev reviews & merges; `src/` is off-limits to the bot (CODEOWNERS + CI guard).

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| brand.config themes a token the DS doesn't expose (drift) | token-contract gate (keys ⊆ contract), checked in both repos |
| version skew (product on old DS, audit on new tokens) | product pins DS; CI resolves tokens from the *installed* version |
| Designer ships a brand that fails WCAG | `validate_aesthetic.py` recomputes contrast from hex (already does) + product CI re-checks |
| regenerate clobbers dev logic | `generated/` vs `src/` boundary + guard (proven) |
| Tailwind doesn't style imported components | mandatory `@source node_modules/@acme/ds/dist` in scaffold (proven) |

## Migration phases (builds on `MIGRATION-PLAN.md`)

1. **Token contract** — DS ships `token-contract.json` (the `@theme` names); extend `validate_aesthetic.py` to check brand keys ⊆ it.
2. **Extract `design-system` repo** — convert to `@acme/ds` package (codemod + tsup recipe, both proven), publish.
3. **Product scaffold generator** — DesignOps Step 4 emits the Product repo (import + brand.config + generated/+src/) instead of a copied prototype.
4. **Regenerate-by-PR + CODEOWNERS/guard** — wire the boundary into real CI.
5. **Cross-repo validation** — audit/contrast gates run in the product against the pinned DS + its brand.config.

## Open decisions (small)

- Registry for `@acme/ds` (GitHub Packages vs npm private) — see `package/PUBLISH.md`.
- Whether `brand.config.json` is committed by DesignOps (PR) or by the Designer in the product repo directly — recommend **DesignOps PR**, dev/Designer review.
