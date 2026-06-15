# Aesthetics — the "taste" layer (Step 2.6)

Vendored from `shadcn-skills-design-starter` so the pipeline stays **standalone**.

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
2. **Pick a direction** — a `named_system` from the library (read its `DESIGN.md`) or an archetype.
3. **Resolve tokens** (oklch) + give `fg_hex`/`bg_hex` for every contrast pair.
4. **Obey constraints** — `a11y_target` + `density_target` must echo `design_directives`; any brand
   color failing the WCAG floor is adjusted (taste never overrides POUR).
5. Emit `brand_config` → written to `output/brand.config.json` for `/generate-prototype`.

Output: `output/aesthetic.json`, gated by `scripts/validate_aesthetic.py` (recomputes contrast
from hex — the agent never self-certifies; named systems must resolve in this library).

## Browse

```bash
python3 .claude/skills/tor-to-brief/references/aesthetics/scripts/design_systems.py categories
python3 .claude/skills/tor-to-brief/references/aesthetics/scripts/design_systems.py search dark
python3 .claude/skills/tor-to-brief/references/aesthetics/scripts/design_systems.py show linear-app
```
