# Component Usage Contracts — Button · Dialog · Field & Input

> Read this when assembling screens in **Step 4**. These are the *usage contracts* for the
> three highest-traffic controls — what to compose, which variant/size/state to reach for, how
> to wire accessibility, and which tokens carry the styling. Distilled from the design system's
> Storybook **Docs/** pages (`stories/docs/{Button,Dialog,Field}.mdx`).
>
> **Gate-enforced.** The marked rules are checked by `scripts/lint_component_contracts.py`
> (Step 4.7 audit, **gate 4**). Build to them up front so the gate passes first try.
> 🔴 = hard rule (blocks the audit, exit 1) · 🟡 = advisory (printed, never blocks).
> Escape a justified case with a `ds-allow-contract` comment on the element's opening line.

---

## Button — `components/ui/button.tsx`

The highest-traffic control. Triggers an action; anchors forms, dialogs, toolbars.

**Anatomy:** `[leading icon?] · Label (children) · [spinner when loading]` — native `<button>`
(or any element via `asChild` + Radix `Slot`). Icons auto-size via `[&_svg]`.

**Variants — one job each:**

| Variant | Use it for |
|---|---|
| `default` | THE primary action on a surface (Apple action blue). **One per view.** |
| `secondary` | Secondary action sitting next to a primary. |
| `outline` | Low-emphasis actions, toolbars, segmented groups. |
| `ghost` | Tertiary / icon actions where chrome should stay quiet. |
| `destructive` | Irreversible actions (delete, remove) — soft red. |
| `link` | Inline navigation styled as a link. |

**Sizes:** `sm · default · lg · icon`. States: `default · hover · focus · active · disabled · loading · error`.

**Wiring rules:**
- 🔴 **Icon-only buttons (`size="icon"`) need an accessible name** — `aria-label="…"` (or an
  `sr-only` child). Without it screen readers announce nothing.
- 🟡 **One primary (`default`) button per view.** Everything else steps down (`secondary`→`outline`→`ghost`).
- 🟡 **Irreversible actions use `variant="destructive"`** — not `default`/`outline`.
- **Do** use `loading` for async submits — it shows a spinner, sets `aria-busy`, blocks repeat clicks.
- **Don't** disable the primary action silently — prefer inline validation explaining why.

**Tokens:** `--button-default-bg`→`--primary` · `--button-default-fg`→`--primary-foreground` ·
`--button-focus-ring`→`--ring` · `--button-radius`→`--radius-lg`. Never hardcode colors.

```tsx
<Button onClick={save}>Save changes</Button>            {/* one primary per view */}
<Button variant="outline">Cancel</Button>
<Button variant="destructive" onClick={remove}>Delete</Button>
<Button size="icon" variant="ghost" aria-label="Close"><X /></Button>
<Button loading disabled={pending}>Submit</Button>
```

---

## Dialog — `components/ui/dialog.tsx` (Radix)

A modal overlay that interrupts the user for a focused task or confirmation. Focus-trap,
scroll-lock, `Esc`-to-close, `aria-modal` come from the primitive — don't reimplement them.

**Anatomy:**
```
Dialog (open state)
 ├─ DialogTrigger (asChild → Button)
 └─ DialogContent
     ├─ DialogHeader
     │   ├─ DialogTitle        ← labels the dialog (aria-labelledby)
     │   └─ DialogDescription  ← describes it  (aria-describedby)
     ├─ (body / form)
     ├─ DialogFooter → actions (primary action LAST)
     └─ DialogClose  → ✕ (sr-only "Close")
```
> Same contract applies to `AlertDialog` (`AlertDialogContent` needs `AlertDialogTitle`).

**Wiring rules:**
- 🔴 **Every `DialogContent`/`AlertDialogContent` must contain a `DialogTitle`/`AlertDialogTitle`.**
  Required for `aria-labelledby`; Radix also warns at runtime without it.
- 🟡 **Include a `DialogDescription`** (backs `aria-describedby`).
- **Do** keep dialogs short, single-purpose; put the primary action last in the footer; use
  `variant="destructive"` + a clear Cancel for irreversible confirmations.
- **Don't** 🟡 nest dialogs / stack modals. **Don't** suppress the close affordance / `Esc`.

**Tokens:** `--dialog-overlay` (black 50% + `backdrop-blur`) · `--dialog-bg`→`--popover`/`--background` ·
`--dialog-border`→`--border` · `--dialog-radius`→`--radius-xl`.

```tsx
<Dialog>
  <DialogTrigger asChild><Button variant="outline">Edit</Button></DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Edit profile</DialogTitle>
      <DialogDescription>Update your details. Changes save immediately.</DialogDescription>
    </DialogHeader>
    {/* form */}
    <DialogFooter>
      <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
      <Button onClick={save}>Save</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## Field & Input — `components/ui/field.tsx` + `input.tsx`

**Input** is the control; **Field** is the composition that wires a label, description, and
error message to it accessibly. A bare input should rarely ship without a Field around it.

**Anatomy:**
```
Field
 ├─ FieldLabel        → htmlFor ↔ input id
 ├─ Input             → the control (aria-invalid on error)
 ├─ FieldDescription  → helper text
 └─ FieldError        → error message (aria-describedby ↔ input)
```

**Input states:** `default · focus · filled · disabled · error`. Sizes: `sm · md · xl`.

**Wiring rules:**
- 🔴 **Every `Input` with an `id` needs a matching `FieldLabel htmlFor`** (or `Label htmlFor`),
  unless it carries an `aria-label`/`aria-labelledby`. Placeholders are **not** labels.
- 🟡 **On error, set `aria-invalid` on the Input** and put the message in `FieldError`
  (linked via `aria-describedby`). 🟡 An `Input` with neither `id` nor `aria-label` is flagged.
- **Don't** rely on red color alone for errors — always include text.
- **Don't** use `disabled` to hide actions the user may need; explain why instead.

**Tokens:** `--field-bg`→`--background` · `--field-border`→`--input` · `--field-border-focus`→`--ring` ·
`--field-border-error`→`--destructive` · `--field-placeholder`→`--muted-foreground` · `--field-radius`→`--radius-lg`.

```tsx
<Field>
  <FieldLabel htmlFor="email">Email</FieldLabel>
  <Input id="email" type="email" aria-invalid={!!error} aria-describedby="email-err" />
  <FieldDescription>We'll never share it.</FieldDescription>
  {error && <FieldError id="email-err">{error}</FieldError>}
</Field>
```

---

## A11y invariants (all three, WCAG 2.2 AA)

- Native `<button>` / Radix primitives give keyboard + focus semantics for free — don't strip them.
- Visible focus ring (`focus-visible:ring-*`) on every control — never `outline-none` without a replacement.
- Programmatic label association (`htmlFor`/`id`, or `aria-label*`) on every interactive control.
- Color is never the only signal (destructive uses a distinct label; errors include text).
- Foreground/background contrast ≥ 4.5:1 in **both** light and dark (gate 2 verifies the theme tokens).

---

## Extending to other components

Two tiers of contract — don't hand-author what you can extract:

| Tier | What | For which components |
|---|---|---|
| **Deep contract** (this file) | Full prose: anatomy, Do/Don't, token mapping, a11y invariants, gate-4 rules | The high-traffic / high-a11y controls only — **Button · Dialog · Field & Input** so far |
| **Extracted vocab** | Real `variant`/`size` keys auto-pulled from each cva component | **Everything else** — see [`component-variants.generated.md`](component-variants.generated.md) |

- **Extracted vocab is the contract for the rest.** Regenerate it from source (never invent variant names):
  ```bash
  python3 .claude/skills/designops-pipeline/scripts/extract_variants.py \
    design-system/components/ui > \
    .claude/skills/designops-pipeline/references/component-variants.generated.md
  ```
  Step 4 reads it to know which variants exist; Step 5 (recipe 02) builds Figma matrices from it.
- **To promote a component to a deep contract**, copy [`component-contract-template.md`](component-contract-template.md),
  paste its real keys from `extract_variants.py --json`, and — if it has a regex-checkable 🔴 a11y
  rule — add that rule to `scripts/lint_component_contracts.py` (gate 4). A contract rule with no gate
  is only a suggestion.
