# Phase 5 — wire DesignOps to import `@npsin-oreo/design-system`

Status of the final phase. The no-credential parts are **done + verified**; two steps need
your token/decision.

## ✅ Done (no credential) — verified

### B. `setup-prototype.sh --ds-import` → real DS scaffold (DesignOps repo, uncommitted)
Generates a **buildable Next product that imports the DS** (not a copy), matched to the real
`@npsin-oreo/design-system` shape (source `.tsx` export):
```bash
bash .claude/skills/designops-pipeline/scripts/setup-prototype.sh \
  --out ./output --ds-import                       # defaults to @npsin-oreo/design-system
# tarball/path: add --ds-pkg <spec> --ds-name @npsin-oreo/design-system
```
It writes: `package.json`, `next.config.ts` (**`transpilePackages: ["@npsin-oreo/design-system"]`** —
required for source `.tsx`), `postcss.config.mjs`, `tsconfig.json`, `app/layout.tsx`, a placeholder
`app/page.tsx`, and `app/globals.css`:
```css
@import "@npsin-oreo/design-system/styles.css";
@source "../node_modules/@npsin-oreo/design-system/components";   /* gotcha #1 */
```
then installs the DS + Next + Tailwind. **Verified:** `next build` green, DS in `node_modules`
(import, 0 vendored source). The default rsync path is untouched — `--ds-import` is opt-in.

### A. Publish readiness (DS repo, branch `chore/strip-to-ds-package`)
- `publishConfig` → GitHub Packages (default for the `@npsin-oreo` scope)
- `prepublishOnly` regenerates `token-contract.json` + `primitives.css`
- `.npmrc.example` for auth; `.npmrc` gitignored

### C. Token-contract gate wired into Step 2.6 (DesignOps repo, uncommitted)
`run_pipeline.sh` resolves a contract from `TOR_DS_CONTRACT` or an installed
`@npsin-oreo/design-system/token-contract.json` and passes it to `validate_aesthetic.py`.
**Unset → behaviour unchanged** (back-compatible). When set, 2.6 may only theme tokens the DS exposes.

## ⬜ Remaining — needs your credential / decision

### 1. Publish the DS (token required)
```bash
cd ~/Desktop/Personal\ Use/Hand-off-test
git checkout chore/strip-to-ds-package      # or merge to main first
cp .npmrc.example .npmrc                     # set GITHUB_TOKEN (packages:write)
npm version patch                            # 0.1.2 → 0.1.3 (or your call)
npm publish                                  # prepublishOnly regenerates artifacts
```

### 2. Flip the pipeline default (the one step that touches the live pipeline)
Only after publish + a green import-mode run:
- generate prototypes with `--ds-import` instead of rsync, OR make it the default in `run_pipeline.sh`
- retire in-repo `./design-system` (keep one release as fallback)

## Safety
- DS work is on branch `chore/strip-to-ds-package` (4 commits, **unpushed**); `main` of Hand-off untouched.
- DesignOps changes (`setup-prototype.sh`, `run_pipeline.sh`, `validate_aesthetic.py`, `selftest.sh`)
  are **uncommitted** and back-compatible: no `--ds-import`, no `TOR_DS_CONTRACT`, no contract installed
  → the current pipeline runs exactly as before. `./design-system` UNTOUCHED. selftest 60/0.
