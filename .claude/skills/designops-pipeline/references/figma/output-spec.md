# Step 5 · Figma Output Spec

The canonical definition of what Step 5 produces in Figma, generated **from pipeline artifacts**
(repeatable, every project — not a manual one-off). Code → Figma, one direction.

> Companion recipes: [01-variables](01-variables.md) · [02-components](02-components.md) ·
> [03-screens](03-screens.md) · [04-flows](04-flows.md) · pitfalls: [mcp-gotchas](mcp-gotchas.md).
> Deterministic prep: `scripts/figma_prep.py`.

## Inputs (from the pipeline)
| Artifact | Used for |
|----------|----------|
| `aesthetic.json` + `brand.config.json` | brand direction, semantic theme values, font, radius |
| DS `tokens.json` (library) | primitive/scale token layer (the full library) |
| `intelligence.json` | `design_directives` (a11y target, density) + **platform → device frame size** |
| `flows.json` | one flow diagram per Action (+ mandatory/injected flows, safeguards) |
| `screen-inventory.json` | the screen list + components per screen + states/gaps |

## Output: one Figma file, 5 pages
```
00 Cover        project name · aesthetic (named_system + mood) · device · date · source TOR
01 Foundations  token swatches/specimens (color ramps, type scale, spacing, radius) + the variables
02 Components   DS components as component-sets with variants, bound to Theme tokens
03 Screens      every screen (screen-inventory.json), composed from component instances, at device size
04 Flows        one flow per Action (flows.json): screens as nodes + decision + error/edge branches
```

Build order is strict: **variables → components → screens → flows** (each layer binds the previous).

---

## 1. Token architecture (library + brand, two layers)

**Layer A — Library (primitives/scales):** import the DS `tokens.json` in full (~1.8k vars) as the
foundation collections (`tw-colors`, `rdx-colors`, `tokens`, `gap`, `padding`, `border-radius`,
`font`, …). Aliases resolved per `figma_prep.py`. Designers can reach any of these. Scope + WEB
`var(--…)` code syntax on every var. (See [01-variables](01-variables.md).)

**`brand-color` trim:** keep only the **`primary`** and **`secondary`** ramps. **Delete
`cerulean-blue` and `coral`** (and any other speculative brand hues) — a project has one primary +
one secondary, not a palette of unused brand hues.

**Layer B — Theme (semantic, the one screens/components bind to):** a `Theme` collection with
**Light + Dark** modes, ~50 semantic tokens (`background, foreground, card, card-foreground,
popover, popover-foreground, primary, primary-foreground, secondary, secondary-foreground, muted,
muted-foreground, accent, accent-foreground, destructive, destructive-foreground, border, input,
ring`). Each is a **live alias into Layer A** (`VARIABLE_ALIAS`) so editing a primitive cascades.
Alias targets come from `aesthetic.json` (e.g. `primary → brand-color/primary/<step>` or the closest
`tw-colors` ramp step that equals `brand.config.primary`).

**Font (default + override):**
- Default `font/family/sans = "Noto Sans Thai"` (Thai-first projects).
- If `aesthetic.json.brand_config.font_sans` names another family (e.g. Nunito), create a
  `brand-font/sans` STRING var = that family and bind the project's screens/components to it.
  Noto Sans Thai stays the library default; the brand var overrides per project.

---

## 2. Device frame sizes (from `intelligence.platform`)
| Platform signal | Frame preset |
|-----------------|--------------|
| mobile / mobile-first | **390 × 844** |
| tablet | **834 × 1194** |
| desktop / web app | **1440 × 1024** |
| responsive | build the primary (mobile) + note breakpoints from the `breakpoints`/`max-width` tokens |

All Screens (page 03) and the screen-nodes in Flows (page 04) use the chosen device width.

---

## 3. Components (page 02) — variants, token-bound
Build the DS `components/ui` set the screens actually use, as Figma component-sets:

| Component | Variant axes |
|-----------|--------------|
| Button | `variant` = default / secondary / outline / ghost / destructive / link · `size` = sm / default / lg / icon · `state` = default / hover / focus / disabled / loading |
| Input | `state` = default / focus / **error** |
| Card | (base) |
| Avatar | `size` (+ fallback) |
| Badge | `variant` = primary / secondary |
| Select / Radio / Checkbox | base + state |
| AlertDialog | base (used by Settle confirm + flow error frames) |

Rules: every fill/stroke/radius/gap/padding/fontSize **bound to a Theme/library variable**
(no raw values); cap any variant matrix > 30 (split or use INSTANCE_SWAP for icons); name variants
`Prop=Value, …`. The **Input `error` variant** (destructive border + error text) is reused by Flow
error-state nodes. **Variant/state vocab, anatomy slots, and token mapping come from
[`../component-contracts.md`](../component-contracts.md); prop names/values mirror the code props
(Code-Connect-ready) — `variant=default`, not `primary`.**

---

## 4. Screens (page 03) — composed from component instances
Each entry in `screen-inventory.json` → one frame at the device size, `Theme` mode = Light,
built from **instances** of page-02 components (not flat shapes), in the layout the draft implies.
Cover the screen's declared `states` where useful (e.g. an empty + a loaded variant).

---

## 5. Flows (page 04) — screens as nodes (reference style)
One flow per Action in `flows.json`. Convention:
- **Node = a screen** (clone/instance of the page-03 screen) with a colored **label chip** above:
  orange = normal, green = success/end, red = error-state.
- **Decision = a diamond** (4-point polygon) labelled with the check (`Amount valid?`).
- **Happy path = green arrows** left→right; **error/edge = red arrows** down to an **error-state
  screen** (uses the component `error` variants).
- Inject the `flows.json` mandatory/safeguard steps (e.g. settle-up confirmation, privacy notice)
  as their own nodes; map each `design_directives.safeguard_level` confirm into a decision.

---

## 6. Automation contract
`figma_prep.py` turns the artifacts into: (a) **compact token blobs** (`[name,kind,value]`, hex
strings — keeps each `use_figma` under the 50 KB code limit), (b) a **build manifest** (collections,
device size, component list, screen list, flow steps). The agent then runs `use_figma` in the strict
order above, validating with `get_screenshot` after each layer. Pitfalls are in
[mcp-gotchas](mcp-gotchas.md). This makes Step 5 reproducible for any project, not hand-built.
