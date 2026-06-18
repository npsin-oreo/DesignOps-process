# Step 5 · Recipe 01 — Variables

Build the token layers from §1 of [output-spec](output-spec.md). Order: **library primitives →
trim brand-color → Theme semantic (live-alias) → font default/override**. Prereq: load
`figma-use` + `figma-generate-library` skills; MCP tools = `mcp__figma__*`.

## 0. Prep (deterministic, no Figma)
Run `python3 scripts/figma_prep.py --tokens <DS>/tokens.json --aesthetic <out>/aesthetic.json
--intel <out>/intelligence.json --screens <out>/screen-inventory.json --flows <out>/flows.json
--out /tmp/figbuild`. It writes:
- `/tmp/figbuild/vars_<NN>_<collection>.json` — compact `[name, kind('c'|'f'|'s'), value]` per
  collection (aliases already resolved; hex strings `rrggbbaa`; opacity already 0–1).
- `/tmp/figbuild/theme.json` — the Theme semantic map `{ token: {light:<ref>, dark:<ref>, scope} }`
  where `<ref>` = `collection/name` to alias into.
- `/tmp/figbuild/manifest.json` — device size, component list, screen list, flow steps.

## 1. Import library collections (batches ≤ ~400 vars/call)
Read each `vars_*.json`, embed the array, create the collection + variables. Derive **scope** in JS
by collection+kind (don't embed scopes — saves blob size):

```js
function scopeFor(coll,name,k){
  if(k==='c')return["FRAME_FILL","SHAPE_FILL","TEXT_FILL","STROKE_COLOR"];
  if(k==='s')return (coll==='font'&&name.indexOf('style')===0)?["FONT_STYLE"]:["FONT_FAMILY"];
  if(coll==='font'){if(name.indexOf('size')===0)return["FONT_SIZE"];if(name.indexOf('weight')===0)return["FONT_WEIGHT"];if(name.indexOf('leading')===0)return["LINE_HEIGHT"];if(name.indexOf('tracking')===0)return["LETTER_SPACING"];return["WIDTH_HEIGHT"];}
  if(coll==='border-radius')return["CORNER_RADIUS"];
  if(coll==='gap')return["GAP"];
  if(coll==='padding'||coll==='margin'||coll==='space')return["GAP","WIDTH_HEIGHT"];
  if(coll==='height'||coll==='max-height'||coll==='max-width')return["WIDTH_HEIGHT"];
  if(coll==='stroke-width'||coll==='border-width')return["STROKE_FLOAT"];
  if(coll==='opacity')return["OPACITY"];
  return["GAP","WIDTH_HEIGHT","CORNER_RADIUS"]; // tokens ladder, shadcn-ui floats
}
function hex(h){return {r:parseInt(h.slice(0,2),16)/255,g:parseInt(h.slice(2,4),16)/255,b:parseInt(h.slice(4,6),16)/255,a:parseInt(h.slice(6,8),16)/255};}
// per collection C = {collection, mode, items:[[name,k,val],...]}
const col=figma.variables.createVariableCollection(C.collection);
col.renameMode(col.modes[0].modeId, C.mode);
const mode=col.modes[0].modeId;
for(const [name,k,val] of C.items){
  const v=figma.variables.createVariable(name,col, k==='c'?'COLOR':(k==='s'?'STRING':'FLOAT'));
  v.setValueForMode(mode, k==='c'?hex(val):val);
  v.scopes=scopeFor(C.collection,name,k);
  v.setVariableCodeSyntax('WEB','var(--'+(C.collection+'-'+name).replace(/\//g,'-').replace(/,/g,'_')+')');
}
return {collection:C.collection, id:col.id};
```
Validate counts with a read-only `getLocalVariableCollectionsAsync()` after each batch.

## 2. Trim `brand-color`
Keep `primary/*` + `secondary/*`; delete the rest (`cerulean-blue/*`, `coral/*`):
```js
const vars=await figma.variables.getLocalVariablesAsync();
const cols=await figma.variables.getLocalVariableCollectionsAsync();
const bc=cols.find(c=>c.name==='brand-color');
for(const id of bc.variableIds){const v=await figma.variables.getVariableByIdAsync(id);
  if(!/^(primary|secondary)\//.test(v.name)) v.remove();}
```

## 3. Theme semantic collection (Light/Dark, live-alias)
```js
const all=await figma.variables.getLocalVariablesAsync();
const cn={}; for(const c of await figma.variables.getLocalVariableCollectionsAsync())cn[c.id]=c.name;
const ref=(r)=>{const [coll,...rest]=r.split('/');const nm=rest.join('/');return all.find(v=>v.name===nm&&cn[v.variableCollectionId]===coll);};
const theme=figma.variables.createVariableCollection('Theme');
const light=theme.modes[0].modeId; theme.renameMode(light,'Light');
const dark=theme.addMode('Dark');
const TEXT=["TEXT_FILL"],BG=["FRAME_FILL","SHAPE_FILL"],STROKE=["STROKE_COLOR"];
// THEME from /tmp/figbuild/theme.json: [name, lightRef, darkRef, scopeKind]
for(const [name,lr,dr,sk] of THEME){
  const v=figma.variables.createVariable(name,theme,'COLOR');
  v.setValueForMode(light,{type:'VARIABLE_ALIAS',id:ref(lr).id});
  v.setValueForMode(dark,{type:'VARIABLE_ALIAS',id:ref(dr).id});
  v.scopes = sk==='text'?TEXT:sk==='stroke'?STROKE:BG;
  v.setVariableCodeSyntax('WEB','var(--'+name+')');
}
```
Screens + components bind to **Theme** (not the raw library). Editing a library primitive cascades.

## 4. Font: default + brand override
- Default already imported: `font/family/sans`. **Set its value to `"Noto Sans Thai"`** (override the
  library's value) so it's the global default.
- If `aesthetic.json.brand_config.font_sans` ≠ Noto Sans Thai: create collection `brand-font`
  (1 mode), var `sans` STRING = that family, scope `["FONT_FAMILY"]`. The project's screens bind
  `fontFamily` to `brand-font/sans`; everything else falls back to Noto Sans Thai.
- Load the family before any text binds it: `await figma.loadFontAsync({family, style})` for every
  weight used (Regular/SemiBold/Bold/ExtraBold).

## Exit criteria
All library collections present; `brand-color` = primary+secondary only; `Theme` (Light/Dark) all
aliased + scoped; font default = Noto Sans Thai (+ brand-font if overridden). Then → components.
