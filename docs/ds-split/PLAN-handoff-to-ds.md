# Plan — turn `@npsin-oreo/design-system` (Hand-off-test) into THE Design System repo

> Based on the **GitHub clone** (HEAD `457f515`, 16 Jun, "Convert to installable package"), **not**
> the stale local snapshot (8–9 Jun). Target architecture = `PROPOSAL-3-repo.md` (Model A + DesignOps
> keeps Step 2.6). Confirmed by the detailed diff in this folder.

## Starting state (corrected from the diff)

The clone is **already ahead** of where our PoCs assumed:
- ✅ already a publishable package — `exports` / `peerDependencies` / `files`, `private:false`, scoped name
- ✅ imports already **relativized** (`../../lib/utils`) → no `@/`→`#` codemod needed (our codemod was for `./design-system`)
- ✅ 56 components (superset of design-system's 52) · token vocab is a **superset** of design-system's
- ⚠️ ships **whitelabel/brand machinery in-repo** (brand.config/schema, build-brand, multi-brand showcase, tokens.json, WHITELABEL.md) — conflicts with Model A
- ⚠️ **different visual language** from `./design-system` (shadcn-basic vs radix-nova) → the one real decision
- ⚠️ stack drift (next ^15 vs 16) · source-export `.tsx` needs consumer `transpilePackages`

So: most "make it a package" work is **done**. Remaining work = align to Model A (strip theme → contract), wire DesignOps, decide visual language + stack.

---

## Phase 0 — Ground rules (0.5d)
- Move the clone to a permanent home; treat the GitHub repo as the single source of truth.
- **Retire the stale local `../Hand-off-test` snapshot** (8–9 Jun) — never push it (would revert the package conversion).
- Decide the fate of in-repo `./design-system`: keep as **fallback** during transition, retire after Phase 5.
- **Exit:** one canonical DS repo identified; stale copies quarantined.

## Phase 1 — DECISION GATE: visual language 🔴 (the only real fork)
Two design languages exist. Pick the path; the rest of the plan is identical either way.

| | A. Keep clone's look (shadcn-basic) | B. Port radix-nova from `./design-system` |
|---|---|---|
| Work | ~0 | port class-strings of ~50 components + advanced patterns (data-slot, aria-expanded, color-mix, radius tokens) |
| Result | prototypes look "vanilla shadcn" | keeps the look the pipeline produces **today** |
| Risk | visible downgrade vs current output | porting effort + re-test |

**Recommendation:** ship **A now** (fastest path to a working 3-repo), treat **B as a deferred visual refresh** (Phase 6). Architecture first, aesthetics second — they're decoupled.

> Need from you: A or B (or "A now, B later"). Everything below is unaffected by the choice.

## Phase 2 — Strip theme/whitelabel → keep the contract (1–2d)
Align to Model A: DS owns the *system + token contract*; theme *values* move to product/DesignOps.
- **Move out** (to product/DesignOps, not delete blindly): `brand.config.json`, `brand.schema.json`, multi-brand bits (`palettes.ts`, `brands.ts`, `brand-switcher`, `brand-context`), the `(showcase)` app, `WHITELABEL.md`.
- **Keep**: `components/ui`, `lib`, `hooks`, `app/primitives.css` (token primitives), the `@theme` mapping, a **neutral default** `brand.css` for Storybook.
- `build-brand.mjs` becomes a **dev/Storybook** helper, not a publish-time `prebuild` (drop the `pre*` hooks that fork brand).
- **Exit:** package ships components + token contract + neutral default; no per-project brand inside.

## Phase 3 — Token contract + DesignOps 2.6 alignment (1d)
- Extract `token-contract.json` from the `@theme` names (31 `--color-*` + radius + font) — the seam from `PROPOSAL-3-repo.md`.
- Extend DesignOps `validate_aesthetic.py`: **brand.config keys ⊆ token-contract** (fetched from the pinned DS version). Token vocab already ⊇ design-system's, so existing 2.6 output stays valid.
- **Exit:** 2.6 emits a brand.config that provably fits the DS contract; mismatches fail the gate.

## Phase 4 — Stack alignment (0.5–1d)
- Pick one stack for DS + product scaffold. Recommend **align to the DS clone (next ^15 / radix ^1.5 / tw-merge ^2)** since it's the package that ships, and bump the DesignOps product scaffold to match (avoids dual-version skew).
- Note `@base-ui/react` is used in 1 component — keep as a real dep.
- **Exit:** product scaffold + DS on one stack; `next build` of a product green.

## Phase 5 — Wire DesignOps to import it (1d)
- Publish `@npsin-oreo/design-system` to **GitHub Packages** (scope matches the `npmjs`/`@npsin-oreo`); see `package/PUBLISH.md`.
- DesignOps product scaffold:
  - `setup-prototype.sh --ds-import --ds-pkg @npsin-oreo/design-system@<ver> --ds-name @npsin-oreo/design-system`
  - product `next.config`: **`transpilePackages: ["@npsin-oreo/design-system"]`** (source-`.tsx` export needs it)
  - product `globals.css`: `@import "@npsin-oreo/design-system/styles.css"; @source "../node_modules/@npsin-oreo/design-system/components";`
- Retire in-repo `./design-system`; point the pipeline default at the package.
- **Exit:** DesignOps generates a product that imports the published DS, builds, looks right.

## Phase 6 — (deferred) visual refresh if Option B (est. 2–3d)
- Port radix-nova component styling into the DS package; re-run audit/contrast. Independent of everything above.

## Phase 7 — repo hygiene (0.5d)
- `tokens.json` (425 KB figma export) → `tokens/source/` (build input, not runtime); regenerate via `tokens:import`.
- Consolidate `CLAUDE.md` + `AGENTS.md` (overlapping AI rules) into one + a thin pointer.
- Remove the embedded `.claude/skills/shadcn-ui-tailwind-figma` (DS repo shouldn't carry pipeline skills) or keep only if it's a genuine figma-sync helper.
- Keep `DESIGN.md` (the real system spec) + `DEVELOPMENT.md`.

---

## What we DON'T need to redo (clone already did it)
- `@/`→`#` codemod — moot (clone uses relative imports). Our `docs/ds-split/codemod/` was for `./design-system`.
- "make it a package" — done. Our `package/` recipe (tsup→dist + types) is now an **optional upgrade** over their source-`.tsx` export (better tree-shaking/types), not a requirement.
- Tailwind `@source` mechanism — proven; just point it at `@npsin-oreo/design-system/components`.
- regen-safe `generated/`/`src/` boundary — unchanged, lives in the product repo (`boundary/` PoC).

## Risks
| Risk | Mitigation |
|------|------------|
| stale local snapshot pushed → reverts package conversion | quarantine it (Phase 0); only ever use the GitHub clone |
| source-`.tsx` export breaks if consumer lacks `transpilePackages` | scaffold sets it by default (Phase 5) |
| visual language churn (A vs B) | decouple — ship A, defer B; aesthetics don't block architecture |
| version skew (DS next15 vs pipeline next16) | one stack (Phase 4); product pins DS version |
| brand machinery half-removed → broken build | move (not delete) + verify `next build`/Storybook after Phase 2 |

## Effort: ~5–7 days for Phases 0–5 (excl. Phase 6 visual refresh). Phase 1 decision unblocks the rest.
