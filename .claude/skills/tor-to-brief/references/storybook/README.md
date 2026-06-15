# Storybook QA layer (Step 4.8 — optional)

An **opt-in** component-preview + automated-a11y layer for the POC prototype. It is NOT enabled
by default: Storybook + Playwright + Vitest are heavy devDeps, and the pipeline keeps the vendored
`design-system/` source-only and every prototype build fast. Turn it on per project, on the
**prototype side only** (`output/prototype/`, which has already run `npm install`).

## What it adds

- **Component explorer** — one story per design-system component (from `components/docs/registry.tsx`).
- **`@storybook/addon-a11y`** — runs axe-core on every rendered story (catches missing labels/roles/
  contrast at runtime — complements the static `audit_prototype.py` gate from Step 4.7).
- **`addon-themes`** — light/dark toggle so you QA both modes.
- **`test-storybook`** — `vitest run --project=storybook` runs the a11y checks headless in CI.

## Enable it (inside `output/prototype/`)

1. Copy the template in:
   ```bash
   cp -R .claude/skills/tor-to-brief/references/storybook/.storybook output/prototype/.storybook
   cp .claude/skills/tor-to-brief/references/storybook/gen-stories.mjs output/prototype/scripts/
   cp .claude/skills/tor-to-brief/references/storybook/vitest.config.ts output/prototype/
   ```
2. Add the devDeps + scripts to `output/prototype/package.json`, then install:
   ```jsonc
   // devDependencies
   "storybook": "^10.4.4", "@storybook/nextjs-vite": "^10.4.4",
   "@storybook/addon-a11y": "^10.4.4", "@storybook/addon-docs": "^10.4.4",
   "@storybook/addon-themes": "^10.4.4", "@storybook/addon-vitest": "^10.4.4",
   "@tailwindcss/vite": "^4.3.1", "vite": "^8.0.16", "vitest": "^4.1.8",
   "@vitest/browser": "^4.1.8", "@vitest/browser-playwright": "^4.1.8", "playwright": "^1.60.0"
   // scripts
   "gen:stories": "node scripts/gen-stories.mjs",
   "storybook": "storybook dev -p 6006",
   "build-storybook": "storybook build",
   "test-storybook": "vitest run --project=storybook"
   ```
   ```bash
   cd output/prototype && npm install && npx playwright install --with-deps chromium
   ```
3. Generate stories + run:
   ```bash
   npm run gen:stories     # one story per registry component
   npm run storybook       # interactive explorer at :6006
   npm run test-storybook  # headless a11y pass (gate-able in CI)
   ```

> `gen-stories.mjs` reads `components/docs/registry.tsx` (present in the vendored design-system) and
> writes `stories/generated/`. Hand-authored playground stories go in `stories/manual/` and are not
> regenerated. Keep this OUT of the vendored `design-system/` — it belongs to the built prototype.
