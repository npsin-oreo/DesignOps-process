# Step 5 · Recipe 02 — Components

Build the DS components the screens use as Figma **component-sets with variants**, every visual
property **bound to a Theme variable** (§3 of [output-spec](output-spec.md)). One component per
`use_figma` call; validate with `get_screenshot`. Prereq: variables (recipe 01) exist.

> **Source of truth = [`../component-contracts.md`](../component-contracts.md).** It owns the
> canonical *anatomy* (slot layers), the full *variant/size/state vocabulary*, and the
> *token mapping* (`--button-*` / `--field-*` / `--dialog-*` → semantic tokens) for Button /
> Dialog / Field & Input. Mirror it 1:1 so the Figma component is **Code-Connect-ready** (the
> optional Code Connect mapping step): variant **prop names + values must equal the code props** — use `variant=default` (NOT
> `primary`), `secondary`, `outline`, `ghost`, `destructive`, `link`; `size` = `sm/default/lg/icon`.
> (Earlier builds used `variant=primary` for `default` — reconcile to the code value on rebuild.)

## Binding helpers (reuse in every call)
```js
const vid=async(id)=>await figma.variables.getVariableByIdAsync(id);
const sb =(v)=>figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:0,g:0,b:0}},'color',v);
async function fill(n,V){n.fills=[sb(await vid(V))];}            // V = Theme var id
async function strk(n,V){n.strokes=[sb(await vid(V))];n.strokeWeight=1;}
async function rad(n,V){const v=await vid(V);for(const c of['topLeftRadius','topRightRadius','bottomLeftRadius','bottomRightRadius'])n.setBoundVariable(c,v);}
async function bn(n,f,V){n.setBoundVariable(f,await vid(V));}    // f='itemSpacing'|'paddingLeft'|'fontSize'…
```
Resolve Theme var ids once (read `getLocalVariablesAsync`, filter collection `Theme`).

## Variant build pattern
1. Build each variant as an auto-layout COMPONENT (`figma.createComponent()` → set layoutMode), bind
   tokens, set text (load font first — recipe 01 §4).
2. `figma.combineAsVariants(components, page)` → component-set.
3. **Position variants in a grid AFTER combining** (they stack at 0,0): set x/y per cell + resize.
4. Name each `Prop=Value, Prop=Value` (e.g. `variant=primary, size=md, state=default`).

## Anatomy → Figma slot layers
Composed components carry the **same named slots as the contract/code**, so instances map cleanly
and Code Connect reads them:
- **Dialog / AlertDialog** → `DialogTitle` + `DialogDescription` (header) · body · `DialogFooter`
  (actions, primary LAST) · `DialogClose` (✕). Title slot is **required**.
- **Field** → `FieldLabel` · `Input` instance · `FieldDescription` · `FieldError`. Field is a
  *composition* (frame of slots), not a variant set — build it from the Input component-set.

## Components + variant matrices (§3 table)
Names mirror code (see source-of-truth note above). Cap the build at a **representative grid**, not
the full Cartesian product (Button alone is 6×4×5).

| Component | Variants (vocab from contract) | Token bindings |
|-----------|--------------------------------|----------------|
| Button | `variant` {default,secondary,outline,ghost,destructive,link} × `size` {sm,default,lg,icon} × `state` {default,hover,focus,disabled,loading} | fill `--button-*`→`primary`/`secondary`/`bg`/`destructive`; text=`*-foreground`; radius `--radius-lg`; padding from spacing; fontSize; **focus** = `ring` stroke; **loading** = spinner |
| Input | `state` {default,focus,filled,disabled,**error**} × `size` {sm,md,xl} | fill `--field-bg`→`background`; stroke `--field-border`→`input` / focus→`ring` / **error**→`destructive`; placeholder=`muted-foreground` |
| Card | base | fill=`card`; stroke=`border`; radius; card-foreground text |
| Avatar | `size` {sm,md,lg} | fill=`accent`; text=`accent-foreground`; radius=full |
| Badge | `variant` {primary,secondary} | fill + matching `-foreground`; radius=full |
| Select / Radio / Checkbox | base + state | border=`input`/`ring`; selected dot/check fill=`primary` |
| Dialog / AlertDialog | base (+ slots above) | fill `--dialog-bg`→`popover`/`background`; overlay `--dialog-overlay`; border=`border`; radius `--radius-xl`; drop-shadow effect |

Cap matrices > 30 combinations (split, or INSTANCE_SWAP for icon slots — never a variant per icon).
The **Input `error` variant** is the one Flow error-state nodes (recipe 04) reuse.

> For components **not** in the table above, take the real variant/size axes from
> [`../component-variants.generated.md`](../component-variants.generated.md) (auto-extracted from the
> DS cva source by `scripts/extract_variants.py`) — don't invent variant names.

## Exit criteria
Each component-set has the expected variant count, grid-laid, screenshot looks right, **no raw
fills/strokes/radii/spacing** (everything bound). Then → screens.
