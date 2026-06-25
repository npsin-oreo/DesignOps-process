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

## Browse

```bash
python3 .claude/skills/designops-pipeline/references/aesthetics/scripts/design_systems.py categories
python3 .claude/skills/designops-pipeline/references/aesthetics/scripts/design_systems.py search dark
python3 .claude/skills/designops-pipeline/references/aesthetics/scripts/design_systems.py show linear-app
```
