# Step 5 · Recipe 04 — Flows (screens as nodes)

One flow diagram per Action in `flows.json`, reference style: **screen = node**, decision diamonds,
**green happy path / red error branch → error-state screen** (§5 of [output-spec](output-spec.md)).
Build per action; screenshot after.

## Node = a screen (clone the page-03 screen)
```js
const src=figma.currentPage.findOne(n=>n.getSharedPluginData('tor','screen')===screenId);
const node=src.clone(); node.x=X; node.y=Y;   // clones keep token bindings + Theme mode
```
Above each node, a **label chip** (annotation, literal colors — not tokens):
orange `#f59e0b` = normal step · green `#16a34a` = success/end · red `#dc2626` = error-state.

## Decision = diamond (4-point polygon — no rotation math)
```js
const d=figma.createPolygon(); d.pointCount=4; d.resize(84,84); d.x=cx-42; d.y=cy-42;
d.fills=[{type:'SOLID',color:{r:1,g:1,b:1}}]; d.strokes=[{type:'SOLID',color:{r:.6,g:.6,b:.64}}]; d.strokeWeight=2;
// label text above the diamond: the check, e.g. "Amount valid?"
```

## Arrows
- **Happy (green), horizontal:** `figma.createLine()` → `resize(len,0)`, `strokeCap='ARROW_LINES'`,
  green stroke. Place at a shared vertical center across the row.
- **Error (red), vertical down:** avoid rotating lines — use a **stem rect + triangle head**:
  ```js
  const stem=figma.createRectangle(); stem.x=cx-1.5; stem.y=yTop; stem.resize(3,(yBot-12)-yTop); stem.fills=[RED];
  const head=figma.createPolygon(); head.pointCount=3; head.resize(14,12); head.x=cx-7; head.y=yBot-12; head.rotation=180; head.fills=[RED];
  ```
- Label arrows `Yes` (green) near the happy branch, `No`/`Cancel` (red) near the error branch.

## Logic to encode (from `flows.json` + `intelligence.json`)
- Each `flows.json` step → a screen node or a decision.
- `design_directives.safeguard_level` confirm steps → a decision diamond before the destructive
  action (e.g. settle-up "User confirms?").
- `mandatory_flows` (privacy notice, settle confirmation) → their own nodes.
- **Error/edge branches** (red) → an **error-state screen** = a clone whose Input/field uses the
  component **`error` variant** (recipe 02), e.g. "Invalid amount", "Save failed", "Empty name".
- Cover at minimum: input-validation error, a save/network failure, and one domain edge case
  (empty household, already-settled, amount > balance, etc.).

## Layout
Orthogonal only (horizontal happy row + vertical red drops) so endpoints are predictable. Error
screens sit directly under their diamond. Title each flow `Flow · <Action>`.

## Exit criteria
One flow per action; screens as nodes; every decision has a green Yes + a red No→error-state;
screenshot reads top-to-bottom / left-to-right cleanly.
