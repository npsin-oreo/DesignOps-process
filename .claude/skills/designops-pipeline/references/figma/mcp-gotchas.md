# Step 5 · Figma MCP — gotchas (learned the hard way)

Pitfalls hit while building the SplitMate file. Read before running any recipe.

## Setup
- Load skills **`figma-use` + `figma-generate-library`** before `use_figma`. The MCP tools are
  deferred as **`mcp__figma__*`** — fetch with `ToolSearch query="select:mcp__figma__use_figma,
  mcp__figma__get_metadata,mcp__figma__get_screenshot,mcp__figma__get_variable_defs"`.
- File must be a design file (`figma.com/design/...`). `fileKey` = the URL segment after `/design/`.

## Variables
- **Compact the token blob.** Full-precision float JSON (e.g. `0.9725490196…`) blew past the
  50 KB `code` limit on a 244-var collection. Emit `[name, kind, value]` with **hex strings**
  (`"be185dff"`) for colors and parse in JS. `figma_prep.py` does this.
- **Derive scopes in JS** (by collection+kind) instead of embedding them per var — smaller blob.
- **Never `ALL_SCOPES`.** color→fill/text/stroke, gap→`GAP`, radius→`CORNER_RADIUS`,
  opacity→`OPACITY`, font size→`FONT_SIZE`, family→`FONT_FAMILY`.
- **Opacity scale:** library opacity tokens are 0–100 (Tailwind) — divide by 100 for Figma's 0–1
  `OPACITY`.
- **Aliases:** create the target first, or set alias values in a second pass that looks vars up live
  by name. `figma_prep.py` pre-resolves cross-set refs so order doesn't matter for primitives.
- **Code syntax WEB must wrap:** `var(--name)`, not `--name`. Sanitize `/`→`-`, `,`→`_` in the name.
- ~400 vars per `use_figma` call is a safe batch.

## Binding (the #1 source of confusion)
- Color is bound via a **paint**, not a property:
  `node.fills=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:0,g:0,b:0}},'color',v)]`
  — it returns a **new** paint; you must reassign the array.
- **Corner radius** binds the 4 corner fields (`topLeftRadius`…), there's no single `cornerRadius`
  bindable.
- **Spacing/padding/fontSize**: `node.setBoundVariable('itemSpacing'|'paddingLeft'|'fontSize', v)`.
  Scope only filters the picker UI — the **API binds any FLOAT var to any FLOAT field** regardless
  of scope.
- **`setExplicitVariableModeForCollection(themeCollection, lightModeId)`** on a screen frame so its
  aliased Theme colors resolve to Light. Pass the collection **object** (fetch it async first).

## Layout / text
- `layoutSizingHorizontal/Vertical='FILL'` only **after** `appendChild` (and only inside an
  auto-layout parent). Set `'FIXED'` + `resize()` otherwise.
- **Load the font before any text write/bind:** `await figma.loadFontAsync({family,style})` for every
  weight (Regular/SemiBold/Bold/ExtraBold). Binding `fontFamily` to a var needs the value family
  loaded too.
- Wrapping text: set `textAutoResize='HEIGHT'` + `layoutSizingHorizontal='FILL'`.

## Shapes (flow diagrams)
- **Diamond** = `createPolygon(); pointCount=4` (no rotation). **Arrowhead** = `createPolygon();
  pointCount=3; rotation=180` for down. **Avoid rotating LINE nodes** for vertical arrows
  (center-pivot makes endpoints unpredictable) — use a stem rect + triangle head.
- Horizontal arrows: `createLine()` + `strokeCap='ARROW_LINES'` works cleanly.

## General
- `use_figma` is **atomic** — on error nothing is applied; read the error, fix, retry (don't blind
  retry). Common: an undefined id in a map (e.g. `R.full` missing) → `getVariableByIdAsync` fails
  validation.
- **Return every created/mutated node id**; you'll need them for the next call.
- **Clones are independent** of their source — deleting the original keeps the clone (used to drop
  the screen strip but keep the flow nodes).
- Deleting a variable that's bound **detaches** the property to its last raw value (screen keeps its
  look, loses the link) — rebind by value-mapping to surviving tokens if needed.
- Validate each layer with `get_screenshot` before building the next.
