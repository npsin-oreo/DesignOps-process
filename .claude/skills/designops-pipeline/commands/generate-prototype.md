# /generate-prototype

Generate a Next.js POC prototype from `design-first-draft.md` using `shadcn-skills-design-starter`.

**Usage:**
```
/generate-prototype
/generate-prototype --screen login
/generate-prototype --screen dashboard,booking
/generate-prototype --all
```

---

## Step 0 — Read required inputs (do this before anything else)

Read these files in order. Stop and report if any required file is missing.

### Required
```
1. output/brief.json                  ← facts: personas · features · flows · scoring
2. output/intelligence.json           ← design_directives (density, a11y, safeguards, nav, mandatory_flows)
3. output/flows.json                   ← refined user flows (Step 3)
4. output/screen-inventory.json        ← the build manifest: screens, flow_refs, layout_primitive, components, gaps
5. output/design-first-draft.md        ← human breakdown (JSX, decisions) for reference
```

Build from `screen-inventory.json` (one page per screen; `layout_primitive` → the shell;
`components` → the imports; `gaps` → GapPlaceholder). Cross-check the human draft for JSX detail.

**Read `design_directives` from `intelligence.json`** (Step 2.5) — it drives the whole build:
| directive | drives |
|-----------|--------|
| `density_target` (1-5) | layout primitive (cards / table+virtualization / dashboard) |
| `guidance_level` | onboarding, empty-state copy, tooltip density |
| `safeguard_level` | confirm / undo / preview-before-commit on destructive actions |
| `a11y_target` (AA/AA_plus/AAA) | component variants + the Step 4.7 audit target |
| `navigation_model` | app shell (single / wizard / hub_spoke / workspace) |
| `mandatory_flows` | screens you MUST inject (e.g. consent, audit_log) |
| `trust_emphasis` | evidence-on-demand / transparency affordances |

If `intelligence.json` is missing → stop and run Step 2.5 first; do not guess these.
If `meta.overall_confidence=low` → produce wireframe-level output + flag a human gate.

### Optional — brand override
```
3. brand.config.json                  ← project-specific color / font / radius overrides
```

**`brand.config.json` lookup order:**
1. `./brand.config.json` (project root)
2. `./output/brand.config.json`  ← auto-written by pipeline **Step 2.6 (Aesthetic Direction)**
3. `./.claude/brand.config.json`

> If the pipeline ran Step 2.6, `output/aesthetic.json` holds the full chosen direction —
> the named system / archetype, the `mood_adjective` the screens must earn, and
> contrast-verified tokens. `output/brand.config.json` is its ready-to-apply subset.
> Read `aesthetic.json` for the *why* (mood, motion, why_fit) before generating screens.

If found → apply overrides in Step 1.  
If not found → continue with neutral theme defaults, log:
```
[generate-prototype] ℹ brand.config.json not found — using neutral theme defaults
```

**`brand.config.json` schema:**
```json
{
  "project_name": "My App",
  "primary":   "oklch(0.35 0.18 264)",
  "secondary": "oklch(0.96 0.01 264)",
  "accent":    "oklch(0.96 0.04 264)",
  "destructive": "oklch(0.577 0.245 27.325)",
  "radius":    "0.5rem",
  "font_sans": "\"Noto Sans Thai\", sans-serif",
  "font_mono": "\"JetBrains Mono\", monospace",
  "dark_mode": true
}
```

All fields are optional. Only override keys that are present — leave the rest at defaults.

---

## Step 1 — Prepare prototype base

### 1a. Prepare prototype base

Use the setup script with `--ds-auto` (graceful Model A default):

```bash
bash .claude/skills/designops-pipeline/scripts/setup-prototype.sh --out ./output --ds-auto
```

- **`--ds-auto`**: imports the published `@npsin-oreo/design-system` package when `GITHUB_TOKEN` is set (`export GITHUB_TOKEN=$(gh auth token)`), else falls back to the in-repo `./design-system` (rsync, offline). Force with `--ds-import` (package) or omit the flag (rsync copy).
- The rsync path copies the in-repo vendored DS, installs fast (`npm ci --prefer-offline`), and **reuses** a matching `node_modules` so repeat runs are ~instant — standalone/offline.
- First install is the one-time cost; later runs reuse `node_modules` when the lockfile matches.
- Keeps a **real** `node_modules` (never a symlink — a shared/symlinked one breaks tsc's `@types/react` resolution).
- No `./design-system`? Fallback: `git clone https://github.com/npsin-oreo/shadcn-skills-design-starter.git output/prototype && cd output/prototype && npm ci`.

### 1b. Apply brand overrides (if brand.config.json exists)

Edit `output/prototype/app/globals.css` — change only the keys present in brand.config.json, inside the `:root` block:

```css
/* Override example — change only the keys that are present */
:root {
  --primary:    [brand.primary];
  --radius:     [brand.radius];
  /* don't remove other tokens */
}
```

If `font_sans` is overridden → load the font in `app/layout.tsx`, **never** with a CSS `@import`:
- Add the font via `next/font/google` or `next/font/local` (exposes a CSS variable, e.g. `variable: "--font-app"`), apply the variable class on `<html>`, and point `--font-sans: var(--font-app), …` in `:root`.
- ⚠️ **Gotcha — do NOT add `@import url("https://fonts.googleapis.com/…")` to `globals.css`.** The DS `@import "@npsin-oreo/design-system/styles.css"` is inlined first, so a font `@import` lands *after* hundreds of rules and violates the CSS rule "`@import` must precede all other rules". `next build` tolerates it but **Turbopack dev returns 500 on every route**. `next/font` is self-hosted and avoids this entirely.

If `dark_mode: false` → remove the `.dark { … }` block from `globals.css` and remove `ModeToggle` from the layout.

Log:
```
[generate-prototype] ✓ Brand applied
  primary: [value] · radius: [value] · font: [value]
```

---

## Step 2 — Resolve screens to generate

Determine which screens to generate based on the flag:

| Flag | Screens |
|------|---------|
| (none) | Ask the user which screen — show the Screen Inventory first |
| `--screen login` | only the screen named "login" |
| `--screen login,booking` | multiple screens, comma-separated |
| `--all` | every screen in the Screen Inventory |

**Screen Inventory** is read from the `## Screen Inventory` heading in `design-first-draft.md`.

For `--all`, generate screens in this order:
1. Must priority first → top-to-bottom per the Screen Inventory
2. Should priority next
3. Could priority last

---

## Step 3 — Scaffold app structure

Create route groups by the screen type found in brief.json `user_flows`:

### Auth group (if there are auth flows)
```
app/
  (auth)/
    layout.tsx          ← centered layout, no sidebar
    [screen]/
      page.tsx
```

`(auth)/layout.tsx` template:
```tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background p-4">
      {children}
    </div>
  )
}
```

### Dashboard group (if there are dashboard/main app flows)
```
app/
  (dashboard)/
    layout.tsx          ← SidebarProvider + AppSidebar (create once)
    [screen]/
      page.tsx
```

`(dashboard)/layout.tsx` template:
```tsx
import { SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/layout/app-sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1 overflow-auto">{children}</main>
    </SidebarProvider>
  )
}
```

`AppSidebar` nav items → read from `user_flows` in brief.json  
Map each flow to a nav item: `{ title: flow.name, url: "/[slug]", icon: [lucide icon] }`

---

## Step 4 — Generate each screen

> **Read `../references/poc-patterns.md` first** — it has ready-made: `KPICard`, `StatusBadge`,
> `POCDataTable` (+pagination), `EmptyState`, `ErrorState`, Skeleton + mock data patterns.
> Assemble from these instead of writing empty screens → presentable immediately.
>
> **Also read `../references/component-contracts.md`** — the usage contracts for Button / Dialog /
> Field & Input (variant per job, a11y wiring, token mapping). Build to the 🔴 rules up front
> (icon buttons need `aria-label`, `DialogContent` needs `DialogTitle`, `Input` needs a
> `FieldLabel htmlFor`) so the Step 4.7 **gate 4** passes on the first audit.

**Mock data rule:** realistic to the domain (real names, real IDs/record numbers, real document numbers) · never "User 1"/"Lorem ipsum"

For each screen in the resolved list:

### 4a. Read screen spec
From the `## [Screen Name]` section in `design-first-draft.md`:
- Purpose
- Flow reference (UF0X)
- Layout (Header / Body / Footer)
- Component usage
- Design decisions
- Gaps

### 4b. Classify screen type
- Login / Register / Forgot password / OTP → `(auth)` group → `Card`-centered layout
- Dashboard / List / Detail / Settings / Form → `(dashboard)` group → sidebar layout

### 4c. Write page.tsx (Server Component)

**Token rules — never violate:**
```tsx
// ❌ hardcoding, in any case
className="text-gray-500 bg-[#F8F9FA]"

// ✅ semantic tokens only
className="text-muted-foreground bg-card"
```

**Tailwind v4 rules:**
```tsx
// ✅ size-4, not w-4 h-4
// ✅ React.ComponentProps<"div">, not forwardRef
// ✅ "use client" only on leaf components that have state/events
```

**Component selection:**
```
container          →  Card + CardHeader/Content/Footer
form fields        →  Field + FieldLabel + FieldDescription + FieldError
text input         →  Input
dropdown           →  Select
action button      →  Button (default/outline/secondary/ghost/destructive)
data list          →  Table + TableHeader/Body/Row/Cell/Head
status indicator   →  Badge
tabbed content     →  Tabs + TabsList/Trigger/Content
modal confirm      →  AlertDialog
slide panel        →  Sheet
loading state      →  Skeleton (match layout shape)
empty state        →  Empty + EmptyHeader/Title/Description/Content
toast              →  sonner (import { toast } from "sonner")
pagination         →  Pagination
search             →  Popover + Command (combobox pattern)
date picker        →  Popover + Calendar (date-picker pattern)
data table+page    →  Table + Pagination (data-table pattern)
```

### 4d. Extract interactive parts → Client Components

Pattern:
```
app/(dashboard)/[screen]/page.tsx     ← Server Component — layout only
  └── components/[feature]/
        [screen]-form.tsx             ← "use client" — form state
        [screen]-table.tsx            ← "use client" — sorting/filtering
        [screen]-actions.tsx          ← "use client" — button handlers
```

`[screen]-form.tsx` template:
```tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Field, FieldLabel, FieldError } from "@/components/ui/field"

export function [ScreenName]Form() {
  const [loading, setLoading] = useState(false)

  return (
    <div className="flex flex-col gap-4">
      <Field>
        <FieldLabel htmlFor="[field]">[Label]</FieldLabel>
        <Input id="[field]" type="[type]" placeholder="[placeholder]" />
      </Field>
      <Button
        className="w-full"
        disabled={loading}
        onClick={() => setLoading(true)}
      >
        {loading ? "Loading…" : "[Action label]"}
      </Button>
    </div>
  )
}
```

### 4e. Handle component gaps

For each component in this screen's Gap Report:
```tsx
// components/ui/gap-placeholder.tsx (create once)
export function GapPlaceholder({ name, spec }: { name: string; spec?: string }) {
  return (
    <div className="flex min-h-16 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-destructive/50 bg-destructive/5 p-4 text-center">
      <span className="text-sm font-medium text-destructive">🔴 {name}</span>
      {spec && <span className="text-xs text-muted-foreground">{spec}</span>}
    </div>
  )
}
```

Use in page:
```tsx
<GapPlaceholder name="ChartComponent" spec="Bar chart showing monthly data — recharts recommended" />
```

---

## Step 5 — Accessibility pass

Run through every generated file and verify:

- [ ] `aria-label` on every `<Button size="icon">`
- [ ] `<DialogTitle>` + `<DialogDescription>` on every Dialog / AlertDialog / Sheet
- [ ] `focus-visible:ring-2 focus-visible:ring-ring` is not removed
- [ ] Color + icon/text always used together (color isn't the only signal)
- [ ] `alt` on every `<Image>`

---

## Step 5.5 — Critique pass (quality loop)

> Read `../references/critique-framework.md` — critique every main screen across the 4 layers, then fix.

1. **Visual Hierarchy** · 2. **Information Architecture** · 3. **Component Consistency** · 4. **Context Fit** (matches `design_directives`: density / safeguards / guidance / trust?)

- Fix every 🔴 **Critical** + ⚡ **Quick Win** immediately in the prototype
- 🟡 **High** → log in the handoff doc for Dev
- Write the full critique to `output/prototype/docs/critique.md`

## Step 5.6 — Audit gate (before handoff)

> **Run the objective gate — it writes the report and decides PASS/BLOCKED:**
> ```bash
> python3 .claude/skills/designops-pipeline/scripts/audit_prototype.py \
>   output/prototype --a11y <AA|AAA> --report output/prototype/docs/audit-report.md
> ```
> Exit 1 = BLOCKED. It recomputes WCAG contrast from `globals.css` (oklch→sRGB, light + dark) and
> lints the screens for hardcoded values — A + B are machine-checked. Audits the generated surface
> only (`components/ui` + any `docs/` dir auto-excluded; no `--scan` needed, `--include-vendored` to
> audit all). Then read `../references/audit-checklist.md` for the qualitative C items and append them to the report.

| Category | Checks | gate |
|----------|--------|------|
| A. Token Compliance | `audit_prototype.py`→`lint_hardcodes.py`: no raw hex/px/ms or `bg-gray-500`-style palette | 🔴 block (script) |
| B. A11y / WCAG `[AA\|AAA]` | `audit_prototype.py` contrast on essential fg/bg pairs, light + dark | 🔴 block (script) |
| C. Component Quality | naming · complete states · no avoidable `any` | 🟡 note (agent) |
| D. Component contracts | `audit_prototype.py`→`lint_component_contracts.py`: icon-button name · `DialogTitle` · `Input`↔`FieldLabel` (`component-contracts.md`) | 🔴 block (script) |

- a11y target from `aesthetic.json`/`intelligence.json` `design_directives.a11y_target` (AAA for public-sector)
- The script writes `output/prototype/docs/audit-report.md`
- If **BLOCKED** (exit 1) → loop back, fix, re-run until exit 0, then write the handoff doc

## Step 5.7 — Usability Test Layer (simulated — Step 4.8)

> Read `../references/usability-test-layer.md`. A **simulated** usability evaluation — no real
> participants — from three methods: heuristic (Nielsen's 10), automated (restate the Step 5.6
> audit + 4.7b runtime signals as findings with evidence), and AI persona walkthroughs that use
> the personas from `output/research.json`.

1. **Heuristic pass** — evaluate each main screen against Nielsen's 10; rate severity 0–4.
2. **Restate automated signals** — pull axe / contrast / focus-trap findings from Step 5.6 (and 4.7b if run) as `method:"automated"` with `evidence`.
3. **Persona walkthroughs** — walk each primary persona's must-do task through the built flow; flag friction per step (`simulated:true`).
4. Write `output/usability.json`; every severity≥3 needs a `recommendation` and a `top_issues` entry; list `limitations` frankly.

> **Gate (integrity, not the findings themselves):**
> ```bash
> python3 .claude/skills/designops-pipeline/scripts/validate_usability.py \
>   output/usability.json output/research.json
> ```
> Exit 1 = the report claimed a real test (`not_real_user_testing` must be true), used a non-simulated
> method, hid a severe issue from `top_issues`, or omitted `limitations`. Fix and re-run. The findings
> are advisory — feed the top issues into the handoff doc's Quality section below.

## Step 6 — Generate handoff doc

Write `output/prototype/docs/poc-handoff.md`:

```markdown
# [project_name from brand.config.json or brief.json] — POC Handoff

> Generated: [DATE] | Screens: [N] | Stack: Next.js 16 · React 19 · Tailwind v4 · shadcn/ui

## Run locally
\`\`\`bash
cd output/prototype && npm install && npm run dev
# → http://localhost:3000
\`\`\`

## Design strategy (why this shape)
[design_directives.rationale from intelligence.json — the short why, grounded in the dimensions + research/competitive evidence]

Key trade-offs:
| Decision | Chose | Over | Because |
|----------|-------|------|---------|
[rows from design_directives.trade_offs]

## Screen inventory
| Screen | Route | Flow | Priority | Status |
|--------|-------|------|----------|--------|
[rows from the Screen Inventory]

## Component gap report
| Component | Screen | Recommended solution | Effort |
|-----------|--------|----------------------|--------|
[rows from the Gap Report in design-first-draft.md]

## Quality (critique + audit + usability)
- Critique: `docs/critique.md` — 🟡 High items Dev should review: [list]
- Audit: `docs/audit-report.md` — Token [🟢/🟡] · A11y [AA|AAA] [🟢/🟡] · Component [🟢/🟡]
- Usability (simulated): `usability.json` — top issues: [top_issues w/ severity + fix_priority]. NOT a real-user test — validate with users.

## Brand tokens applied
[show only the keys overridden from brand.config.json]
or "using neutral theme defaults" if there's no brand.config.json

## Open questions (from brief.json)
[the full list of OPEN_QUESTIONS]
```

---

## Step 7 — Final check & log

```bash
cd output/prototype && npm run typecheck
```

If there's a TypeScript error → fix it before logging complete.

```
[generate-prototype] ✓ Done

  Directives: density=[1-5] · a11y=[AA|AA_plus|AAA] · safeguards=[level] · nav=[model]
  Brand:   [applied / neutral defaults]
  Screens: [X] generated
    ✓ [screen-name]  →  app/([group])/[path]/page.tsx
    ✓ [screen-name]  →  app/([group])/[path]/page.tsx
  Gaps:    [Y] GapPlaceholder components
  Types:   ✓ pass
  Critique:[C] critical fixed · [Q] quick wins applied
  Audit:   [PASS | BLOCKED] · WCAG [AA|AAA] · token [🟢/🟡]

  npm run dev → http://localhost:3000
  Handoff:    output/prototype/docs/poc-handoff.md
  Critique:   output/prototype/docs/critique.md
  Audit:      output/prototype/docs/audit-report.md
```
