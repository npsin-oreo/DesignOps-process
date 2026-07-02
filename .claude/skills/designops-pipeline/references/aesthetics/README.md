# Aesthetics — the "taste" layer (Step 2.6)

Vendored from `shadcn-skills-design-starter` — these are **local reference files** (the 138
design-system specs, taste guides, and scripts). Note: only this reference content is vendored;
under **Model A** the design system itself is **imported** as `@npsin-oreo/design-system`, not
vendored — so the pipeline is **not standalone** (it needs a `GITHUB_TOKEN`).

`design_directives` (Step 2.5) decides the *functional* shape — density, a11y, navigation,
safeguards. It says nothing about how the product should **look**. Step 2.6 fills that gap:
it commits a visual direction and resolves it into concrete, contrast-checked tokens, so the
prototype earns a real aesthetic instead of falling back to the neutral shadcn default
("design slop").

## What's here

| Path | Role |
|------|------|
| `design-systems/library/<name>/DESIGN.md` | **138 named design systems** — prose specs (atmosphere, color roles, typography, characteristics) for apple, linear-app, stripe, vercel, notion, resend, brutalism, glassmorphism, luxury… |
| `design-systems/crosswalk.md` · `interop-protocol.md` | map a system's colors to our semantic token roles |
| `taste/design-taste.md` | Brief Inference + the **Banned Defaults** anti-slop checklist |
| `taste/aesthetic-systems.md` · `motion-choreography.md` | archetype recipes + motion guidance |
| `scripts/design_systems.py` | browse the library — `list` / `search <term>` / `show <name>` / `categories` |
| `scripts/contrast.py` | WCAG contrast checker (`validate_aesthetic.py` imports `ratio()` to verify pairs) |
| `CATALOG.txt` | static dump of `design_systems.py list` (138 systems by category) |

## How Step 2.6 uses it

1. **Brief Inference** (anti-slop): name domain, audience/tone, the one `mood_adjective`, motion depth.
2. **Pick a direction** — a `named_system` from the library (read its `DESIGN.md`) or, only if nothing
   fits, an archetype. **Search the library first, by *mood / visual adjective*, NOT by industry.**
   The 178 systems are indexed by visual character (calm, clean, minimal, trust, mono, warm…), not by
   vertical — searching `medical` / `fintech` / `gov` returns nothing and falsely concludes "no fit",
   so you fall back to an archetype and throw away a documented design language. Run
   `design_systems.py search <mood>` for the `mood_adjective` and 2-3 neighbours (e.g. a calm clinical
   portal → `search calm` → **openai** "calm teal-black"; `search clean` → **clean**/**cal**). Prefer a
   `named_system` whenever one is close; reach for an archetype only when the search genuinely turns up
   nothing, and **record the terms you tried in `direction.library_search`** (the gate nudges if it is
   missing on an archetype).
3. **Resolve on six axes, not just colour** (optional `axes` block — the composition layer). A
   DESIGN.md carries far more than a palette; resolve each facet and record where it came from:

   | Axis | Pull from the DESIGN.md | Scored against (intelligence) |
   |------|-------------------------|-------------------------------|
   | `color` | palette + accent strategy | `trust_emphasis`, `decision_criticality`, mood |
   | `typography` | font + type scale + weight principles + tracking | `guidance_level`, `data_density`, `a11y_target` |
   | `shape` | radii, pill usage, corner language | mood, audience |
   | `elevation` | flat / soft / layered, shadow language, border strategy | `data_density`, `decision_criticality` |
   | `spacing` | base unit, section rhythm, grid | `data_density`, platform |
   | `motion` | duration, easing, restraint | `trust_emphasis`, `error_tolerance` |
   | `layout` *(optional, directive-derived)* | grid columns, gutter, container widths, control-height scale, touch target | `density_target`, `responsive` (device), platform |

   **Composition is principled, not free-mixing.** Pick ONE *primary* system (the coherent backbone —
   it owns `color` + usually `typography`/`shape`). Override a single axis from a *secondary* system
   only when the primary genuinely doesn't fit the product on that axis, **with a rationale**. The gate
   caps a composition at **2 systems** (`MAX_AXIS_SOURCES`) — design languages are coherent wholes, and
   stitching many together reads worse than any one. A directive-derived axis (e.g. `spacing` set from
   `data_density`) uses `source: "intelligence"`. Record the trade-offs in an `axis_scores` matrix so the
   choice is auditable. `axes.color.source` must equal `direction.name` (the contrast-checked tokens come
   from the resolved palette). The build must then APPLY the non-colour axes too (type scale/weights,
   motion easing, spacing) — not just the colours — or the DESIGN.md is ~20% used.
4. **Resolve tokens** (oklch) + give `fg_hex`/`bg_hex` for every contrast pair.
5. **Obey constraints** — `a11y_target` + `density_target` must echo `design_directives`; any brand
   color failing the WCAG floor is adjusted (taste never overrides POUR).
6. Emit `brand_config` → written to `output/brand.config.json` for `/generate-prototype`.

Output: `output/aesthetic.json`, gated by `scripts/validate_aesthetic.py` (recomputes contrast
from hex — the agent never self-certifies; named systems must resolve in this library).

## The `layout` axis (optional 7th axis) — gives structure a real token

The six axes above stop at colour / type / radius / motion, so **layout** (grid, gutter, container
widths, control-height scale, touch target) was left to ad-hoc per-screen decisions → cramped
mobile-only columns, mismatched control heights, no grid. The `layout` axis makes structure a
*resolved token* the build can apply from screen 1 and gate 11 can verify — the same "declared →
applied" discipline as the other axes.

It is **directive-derived**, not pulled from a DESIGN.md: `source: "intelligence"`, resolved from
`design_directives.density_target` (spacing rhythm + control size) and `design_directives.responsive`
(which roles are desktop vs mobile → container widths + which control-height scale is the default).
It is **optional** and outside the coherence source-count, so it never disturbs the primary/secondary
system composition.

```jsonc
"layout": {
  "source": "intelligence",
  "rationale": "density_target=3 + a mixed desk/mobile audience → 12/8/4 responsive grid, comfortable gutter, and ≥44px controls sized for gloved hands.",
  "resolved": {
    "grid_cols":     { "sm": 4, "md": 8, "lg": 12 },   // columns per breakpoint (consumed by the <Grid> primitive)
    "gutter":        "1.5rem",                          // grid/gap rhythm            → --spacing-gutter
    "container_max": { "content": "80rem", "prose": "48rem" }, // page + reading widths → --container-content / --container-prose
    "control_h":     { "mobile": "3rem", "desktop": "2.5rem" }, // input/select/button height → --control-h-mobile / --control-h-desktop
    "touch_min":     "2.75rem",                         // minimum tap target (44px)  → --touch-min
    "radius":        "0.5rem"                           // echoes tokens.radius (single source)
  }
}
```

**Units are no-hardcode-safe** (`rem`/unitless, never raw `px`/`ms`) so the values land in `@theme`
without tripping gate 1 — e.g. the 44px touch floor is expressed as `2.75rem`.

### `@theme` token contract (what fix C scaffolds, what gate 11 checks)

The build applies `layout.resolved` by re-pointing Tailwind's `@theme` in `globals.css` (so existing
utilities inherit it) — never by editing components:

| `resolved` key | `@theme` token in `globals.css` | Consumed by |
|----------------|--------------------------------|-------------|
| `gutter` | `--spacing-gutter` | `<Grid>`/`<Stack>` gap, page padding |
| `container_max.content` / `.prose` | `--container-content` / `--container-prose` | page/`<main>` max-width |
| `control_h.mobile` / `.desktop` | `--control-h-mobile` / `--control-h-desktop` | `[data-slot]` control-parity overrides (fix C2) |
| `touch_min` | `--touch-min` | min-height/-width on interactive slots |
| `grid_cols.{sm,md,lg}` | *(component prop, not a token)* | `<Grid>` → `grid-cols-4 md:grid-cols-8 lg:grid-cols-12` |

**Consistency invariant** (enforced by `validate_aesthetic.py`, fix B2, later task):
`touch_min ≤ control_h.mobile` (a tap target can't exceed the control it lives on) and
`grid_cols.sm ≤ grid_cols.md ≤ grid_cols.lg`. Gate 11 (fix B3, later task) fails the build when a
declared token above is absent from `globals.css` — the same no-op guard it already applies to
type/shape/motion.

## Browse

```bash
python3 .claude/skills/designops-pipeline/references/aesthetics/scripts/design_systems.py categories
python3 .claude/skills/designops-pipeline/references/aesthetics/scripts/design_systems.py search dark
python3 .claude/skills/designops-pipeline/references/aesthetics/scripts/design_systems.py show linear-app
```
