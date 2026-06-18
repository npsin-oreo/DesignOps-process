# Step 5 · Recipe 02 — Components

Build the DS components the screens use as Figma **component-sets with variants**, every visual
property **bound to a Theme variable** (§3 of [output-spec](output-spec.md)). One component per
`use_figma` call; validate with `get_screenshot`. Prereq: variables (recipe 01) exist.

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

## Components + variant matrices (§3 table)
| Component | Variants | Token bindings |
|-----------|----------|----------------|
| Button | variant {primary,secondary,outline,destructive} × size {sm,md,lg} × state {default,hover,disabled} | fill=`primary`/`secondary`/`bg`/`destructive`; text=`*-foreground`; radius; padding from spacing; fontSize |
| Input | state {default,focus,**error**} | fill=`background`; stroke = `input` / `ring` / `destructive`; **error** adds destructive helper text |
| Card | base | fill=`card`; stroke=`border`; radius; card-foreground text |
| Avatar | size {sm,md,lg} | fill=`accent`; text=`accent-foreground`; radius=full |
| Badge | variant {primary,secondary} | fill + matching `-foreground`; radius=full |
| Select / Radio / Checkbox | base + state | border=`input`/`ring`; selected dot/check fill=`primary` |
| AlertDialog | base | fill=`popover`; text=`popover-foreground`; border; drop-shadow effect |

Cap matrices > 30 combinations (split, or INSTANCE_SWAP for icon slots — never a variant per icon).
The **Input `error` variant** is the one Flow error-state nodes (recipe 04) reuse.

## Exit criteria
Each component-set has the expected variant count, grid-laid, screenshot looks right, **no raw
fills/strokes/radii/spacing** (everything bound). Then → screens.
