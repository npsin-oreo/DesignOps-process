# Step 5 · Recipe 03 — Screens

Build every screen in `screen-inventory.json` as a frame at the **device size** (manifest), `Theme`
mode = Light, composed from **instances of page-02 components** (§4 of [output-spec](output-spec.md)).
One screen per `use_figma` call; screenshot after each.

## Frame setup
```js
const W = manifest.device.w, H = manifest.device.h;   // e.g. 390 × 844 (mobile)
const scr=figma.createAutoLayout('VERTICAL',{name: screen.id+' '+screen.name});
scr.resize(W, scr.height); scr.layoutSizingHorizontal='FIXED';
const theme=await figma.variables.getVariableCollectionByIdAsync(THEME_COLLECTION_ID);
scr.setExplicitVariableModeForCollection(theme, LIGHT_MODE_ID);   // resolve aliases to Light
await fill(scr,'background'); await bn(scr,'itemSpacing','space-lg'); await pad(scr,'space-xl');
```
Position top-level screens away from (0,0); lay them left→right with a gap.

## Compose from component instances
For each component the screen declares (`screen.components`):
```js
const set = figma.currentPage.findOne(n=>n.type==='COMPONENT_SET' && n.name==='Button');
const inst = set.defaultVariant.createInstance();        // or pick a variant
inst.setProperties({ variant:'primary', size:'lg' });    // variant props
scr.appendChild(inst); inst.layoutSizingHorizontal='FILL';
// set instance text via its text node (load font first)
```
- Prefer instances over redrawing. Only drop to raw nodes for one-off layout glue.
- Set `layoutSizing*='FILL'` **after** `appendChild`.
- Render the declared `states` that matter (e.g. an empty state + a loaded state) as separate frames
  or a labelled variant.
- Mobile: keep tap targets ≥ 44px, thumb-reachable primary action (mobile-usability ref).

## Naming + traceability
Frame name `= screen.id + ' ' + screen.name`; tag `setSharedPluginData('tor','screen',screen.id)`
so Flows (recipe 04) can find/clone the right screen by id.

## Exit criteria
One frame per screen-inventory entry, device-sized, built from instances, Theme=Light, screenshot
matches the draft. Then → flows.
