# Audit Checklist — DesignOps Loop

Full checklist for MODE 4: AUDIT
Read this file every time you enter AUDIT mode.

> **Categories A + B are machine-checked — run the gate, don't eyeball them:**
> ```bash
> python3 .claude/skills/tor-to-brief/scripts/audit_prototype.py \
>   <prototype_dir> --a11y <AA|AAA> --report <prototype_dir>/docs/audit-report.md
> ```
> Exit 1 = BLOCKED. It runs `lint_hardcodes.py` (A) and recomputes WCAG contrast from
> `globals.css` oklch tokens in light + dark (B). Use this checklist for the **category C**
> qualitative items and for fixing whatever the script flags.

---

## A. TOKEN COMPLIANCE

### A1. Color Tokens
- [ ] No hardcoded hex in `className` (e.g. `bg-[#0066FF]`)
- [ ] No hardcoded hex in the `style` prop (e.g. `style={{ color: '#fff' }}`)
- [ ] No Tailwind color utilities that should be a semantic token (e.g. `bg-blue-500` instead of `bg-[var(--color-brand-primary)]`)
- [ ] Every CSS variable declared in `:root` and `[data-theme="dark"]`
- [ ] References fully resolve — no unresolved `{path.to.token}`

### A2. Spacing Tokens
- [ ] No arbitrary px that should be a token (e.g. `p-[18px]` → `p-[var(--spacing-4)]`)
- [ ] The Tailwind spacing scale used matches the token dimension
- [ ] Gap / margin / padding consistent — no magic numbers

### A3. Typography Tokens
- [ ] Font family not hardcoded as a string (e.g. `fontFamily: 'Inter'`)
- [ ] Font size uses the token scale, not an arbitrary value
- [ ] Line height / letter spacing follow tokens if defined

### A4. Border Radius Tokens
- [ ] `--radius` token set is complete
- [ ] No arbitrary `rounded-[6px]` — use `rounded-[var(--radius)]` instead
- [ ] Radius consistent across the page (no mixed system)

### A5. Shadow Tokens
- [ ] Box shadow references a token if the design system defines one
- [ ] No pure-black shadow on a light background (`shadow-black` — lower opacity or use a tinted shadow)

### Severity Classification

| Level | Description | When to fix |
|---|---|---|
| 🔴 CRITICAL | Hardcoded color / spacing that clearly conflicts with a token | before merge |
| 🟡 WARNING | Uses a Tailwind utility instead of a semantic token, but the value matches | this sprint |
| 🔵 INFO | Can be improved but not urgent | backlog |
| 🟢 PASS | Passed | - |

---

## B. A11Y / WCAG 2.1 AA

### B1. Color Contrast
- [ ] Body text ≥ 4.5:1 contrast ratio against the background
- [ ] Large text (18px+ regular / 14px+ bold) ≥ 3:1
- [ ] UI components (button, input border, icon) ≥ 3:1
- [ ] Placeholder text ≥ 4.5:1 (doesn't count as large text)
- [ ] Focus ring ≥ 3:1 against adjacent colors
- [ ] Disabled state: confirm clearly whether it's purposely exempt or a violation

**Recommended tool:** [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

### B2. Keyboard Navigation
- [ ] Tab order logical (top → bottom, left → right)
- [ ] No keyboard trap — the user can tab out of a modal / dropdown
- [ ] Every `focusable` element is accessible by keyboard
- [ ] Skip navigation link at the top of the page (for page-level audits)
- [ ] Custom interactive components (combobox, date picker) are keyboard navigable

### B3. Focus Indicators
- [ ] Focus ring visible on input, button, link, and custom interactive elements
- [ ] No `outline: none` or `outline: 0` without a custom focus style replacing it
- [ ] Focus indicator ≥ 3:1 contrast against the adjacent background

### B4. Screen Reader
- [ ] Every `<img>` has an `alt` attribute — descriptive if meaningful, `alt=""` if decorative
- [ ] Icon-only buttons have an `aria-label` or `<span className="sr-only">`
- [ ] Every form input has an associated `<label>` (htmlFor / aria-labelledby)
- [ ] Error messages linked with `aria-describedby`
- [ ] Dynamic content that changes uses an appropriate `aria-live` region
- [ ] Landmark roles complete: `<header>`, `<main>`, `<nav>`, `<footer>`
- [ ] The page has a single `<h1>` — heading hierarchy doesn't skip levels (no h1→h3)

### B5. Touch & Pointer
- [ ] Touch target at least 44×44px (iOS) / 48×48dp (Android)
- [ ] Spacing between touch targets ≥ 8px
- [ ] Hover-only interactions have a keyboard / touch fallback

### B6. Forms
- [ ] Label always above the input — never use a placeholder as a label
- [ ] Error message below the input — clear + linked with `aria-describedby`
- [ ] Required fields marked with `aria-required="true"` or a visual indicator + legend
- [ ] Text inputs have an appropriate `autocomplete` attribute

### B7. Motion & Animation
- [ ] Every animation with duration > 0.5s respects `prefers-reduced-motion`
- [ ] No content flashing > 3 times per second (seizure risk)
- [ ] Parallax / scroll-hijack has a static fallback
- [ ] Auto-playing media has a pause/stop control

---

## C. COMPONENT STRUCTURE / NAMING

### C1. File & Folder Naming
- [ ] Component files: PascalCase (`MedicationCard.tsx`, `StatusBadge.tsx`)
- [ ] Non-component files: kebab-case (`use-patient-data.ts`, `mock-patients.ts`)
- [ ] Story/test files: `ComponentName.stories.tsx`, `ComponentName.test.tsx`
- [ ] Index barrel exports: `components/index.ts` exports everything

### C2. Component API
- [ ] Props have a TypeScript interface or type (no `any` without a reason)
- [ ] Optional props have default values
- [ ] Callback props use the `on` prefix (`onSubmit`, `onChange`, `onClose`)
- [ ] Boolean props use the `is` / `has` / `should` prefix (`isLoading`, `hasError`)
- [ ] No prop leaks an internal implementation detail

### C3. Variant Pattern
- [ ] Components with variants use `cva` (class-variance-authority) or the same pattern
- [ ] No complex conditional className strings (use the `cn()` helper instead)
- [ ] Variant names match the design token / Figma variant names

### C4. Component Size
- [ ] A component > 200 lines → consider splitting into sub-components
- [ ] Single Responsibility — one component does one thing
- [ ] Custom hooks split out from the component when logic > 20 lines

### C5. Composition Pattern
- [ ] shadcn/ui components are extended by composition, not by modifying the source
- [ ] Compound-components pattern for complex UI (`Card.Root`, `Card.Header`, `Card.Body`)
- [ ] `forwardRef` for input-like components

### C6. State Management
- [ ] Local state doesn't "leak" upward more than necessary
- [ ] No prop drilling beyond 2 levels — if it exceeds, use context or state management
- [ ] Server / Client component boundary is correct (no unnecessary `"use client"`)

---

## D. FIGMA-TO-CODE CONSISTENCY

> **Prerequisite:** you need a Figma URL or screenshot before auditing this category.
> If Figma MCP is available → use `get_design_context` and `get_variable_defs` first.

### D1. Spacing
Check section by section:
- [ ] Padding inside the component (Figma: padding → Code: `p-*` / `px-*` / `py-*`)
- [ ] Gap between children (Figma: auto-layout gap → Code: `gap-*`)
- [ ] Margin / offset between sections

**Common drift:** Figma padding 16px → Code `p-3` (12px) instead of `p-4` (16px)

### D2. Color
- [ ] Fill colors match the CSS variable value
- [ ] Stroke / border colors match the token
- [ ] Opacity matches
- [ ] Gradient matches (direction + stops)

### D3. Typography
- [ ] Font size matches (Figma text style vs Tailwind `text-*`)
- [ ] Font weight matches (`font-medium` = 500, `font-semibold` = 600)
- [ ] Line height matches (Figma: 1.5 vs Code: `leading-relaxed`)
- [ ] Letter spacing matches (Figma: -0.02em vs Code: `tracking-tight`)
- [ ] Text truncation / wrapping behavior matches

### D4. Border Radius
- [ ] Card radius matches
- [ ] Button radius matches
- [ ] Input radius matches
- [ ] Image radius matches

### D5. Shadow & Elevation
- [ ] Drop shadow values match (x, y, blur, spread, color+opacity)
- [ ] Multiple shadow layers complete
- [ ] Inner shadow / inset if present in Figma

### D6. States
- [ ] Default state matches
- [ ] Hover state implemented (if Figma defines it)
- [ ] Focus state implemented
- [ ] Active / pressed state implemented
- [ ] Disabled state implemented
- [ ] Loading state implemented
- [ ] Empty state implemented
- [ ] Error state implemented

### D7. Layout & Alignment
- [ ] Alignment (left / center / right) matches
- [ ] Flex / grid direction matches the Figma auto layout
- [ ] Component stretch / hug behavior matches
- [ ] Overflow behavior matches (clip / scroll / visible)

---

## Audit Output Template

```
DesignOps Audit Report
======================
Date: [YYYY-MM-DD]
Auditor: DesignOps Loop Skill
Scope: [component names / file paths]
Figma Reference: [URL or "not provided"]

SUMMARY SCORECARD
-----------------
A. Token Compliance:      [🔴 FAIL / 🟡 WARN / 🟢 PASS]  — X violations
B. A11y / WCAG:           [🔴 FAIL / 🟡 WARN / 🟢 PASS]  — X violations
C. Component Quality:     [🔴 FAIL / 🟡 WARN / 🟢 PASS]  — X issues
D. Figma Consistency:     [🔴 FAIL / 🟡 WARN / 🟢 PASS]  — X drift items
   (or "⚪ SKIPPED — no Figma reference")

CRITICAL — fix before merge/ship
--------------------------------
[A1] components/Button.tsx:24 — hardcoded bg-[#0066FF] → var(--color-brand-primary)
[B1] components/Badge.tsx — text contrast 2.1:1, needs 4.5:1 (WCAG AA fail)

HIGH — fix this sprint
----------------------
[C4] components/PatientCard.tsx — 280 lines, suggest splitting into PatientCard + PatientCardActions
[B3] components/IconButton.tsx — no visible focus ring

MEDIUM — backlog
----------------
[A2] components/Grid.tsx:8 — p-[18px], suggest p-[var(--spacing-4)]
[D6] components/StatusBadge.tsx — Hover state in Figma but missing in code

PASSED CHECKS
-------------
✅ Token: colors/Typography — CSS variables used correctly
✅ A11y: Keyboard navigation on every component
✅ Component: Naming convention correct across the folder

RECOMMENDED NEXT STEPS
----------------------
1. Fix CRITICAL items first — 2 spots, roughly 30 minutes
2. Run the contrast checker on the whole Badge component set
3. Split PatientCard next sprint
```
