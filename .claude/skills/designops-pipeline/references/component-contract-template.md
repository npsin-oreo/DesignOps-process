# Component Contract — `<ComponentName>` (template)

> Copy this to author a **deep contract** for a component, the way Button / Dialog / Field & Input
> are documented in [`component-contracts.md`](component-contracts.md). Only the high-traffic / high-a11y
> controls need one; for everything else the variant vocabulary in
> [`component-variants.generated.md`](component-variants.generated.md) (auto-extracted) is the contract.
>
> **Start from real values.** Run `python3 scripts/extract_variants.py
> design-system/components/ui/<file>.tsx --json` and paste the actual variant/size keys — never
> invent them. Pull the token names from the component's source classNames.
>
> **Mark gate-enforceable rules** with 🔴 (a hard, mechanically-checkable a11y/usage break) or 🟡
> (advisory). If a 🔴 rule is genuinely checkable by regex, add it to
> `scripts/lint_component_contracts.py` (gate 4) — a contract rule with no gate is just a suggestion.

---

## `<ComponentName>` — `components/ui/<file>.tsx`

One sentence: what it's for and where it sits in the system.

**Anatomy:** the slot tree — root + named child slots (e.g. `Header › Title / Description`, `Footer`).
For Figma/Code-Connect these slot names must match the code.

**Variants / sizes / states:** (from `extract_variants.py` — real keys)

| Axis | Values | Use each for |
|---|---|---|
| `variant` | … | one job per variant |
| `size` | … | … |
| state | default · hover · focus · disabled · … | how it's driven (attribute vs. utility) |

**Wiring rules:**
- 🔴 <hard a11y/usage invariant — also add to gate 4 if regex-checkable>
- 🟡 <advisory best-practice>
- **Do** …  **Don't** …

**Token mapping:** `--<comp>-*` → semantic token (`--primary`, `--ring`, `--radius-lg`, …). Never hardcode.

**Accessibility (WCAG 2.2 AA):** label association · visible focus ring · color-not-the-only-signal ·
contrast ≥ 4.5:1 light + dark · keyboard semantics from the primitive.

```tsx
// minimal correct usage — the shape Step 4 should generate
```
