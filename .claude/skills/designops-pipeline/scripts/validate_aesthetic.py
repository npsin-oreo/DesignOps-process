#!/usr/bin/env python3
"""
validate_aesthetic.py — gate for Step 2.6 (Aesthetic Direction).

Usage: validate_aesthetic.py <aesthetic.json> [intelligence.json]
Exit 0 = valid, Exit 1 = invalid. Zero-dependency (imports the vendored contrast.py).

aesthetic.json picks a visual direction (a named system from the 138-brand library, or an
archetype) and resolves it into concrete tokens. This gate checks that:
  • the chosen named_system actually exists in references/aesthetics/design-systems/library/
  • a mood adjective was committed (anti-slop: generating before deciding = slop)
  • the FULL identity color set (surfaces, text hierarchy, accent, border) is resolved for
    light AND dark — not just primary/background/foreground. The old narrow contract let the
    prototype's card/secondary/muted/border stay at the shadcn-neutral default ("just slap the
    brand color on" → plain). brand_config must carry that whole theme, faithfully.
  • EVERY contrast pair is independently re-computed from hex and meets the a11y target;
    text-on-surface pairs (card, secondary, …) are required, not just primary.
  • constraints echo intelligence.design_directives (a11y_target, density_target)
"""

import json
import sys
from pathlib import Path

# vendored alongside the brand library — recompute contrast ourselves, never trust the agent
AESTHETICS = Path(__file__).resolve().parent.parent / "references" / "aesthetics"
LIBRARY = AESTHETICS / "design-systems" / "library"
sys.path.insert(0, str(AESTHETICS / "scripts"))
try:
    import contrast as _contrast  # vendored WCAG checker
except Exception:  # pragma: no cover
    _contrast = None

REQUIRED_TOP_KEYS = ["meta", "brief_inference", "direction", "tokens", "contrast_checks",
                     "constraints", "brand_config"]
DIRECTION_TYPES = {"named_system", "archetype"}
MOTION_DEPTH = {"none", "subtle", "expressive"}

# ── decision axes (optional `axes` block) ──────────────────────────────────────
# Each DESIGN.md carries far more than a palette. The `axes` block records which system each
# facet was resolved from, so a build can be a coherent WHOLE — usually one primary system, with a
# *justified* per-axis override from at most one secondary (free-mixing many systems is incoherent).
# Mirrors the interop-protocol crosswalk (Color · Type · Spacing · Radius · Elevation · Motion).
AXES = ("color", "typography", "shape", "elevation", "spacing", "motion")
MAX_AXIS_SOURCES = 2          # coherence cap: a composition may span at most 2 design systems
AXIS_NON_SYSTEM = {"intelligence"}  # a directive-derived axis source (e.g. spacing from data_density)

# ── the identity token contract (what makes a theme not-"plain") ───────────────
# These are the DS's own semantic color tokens. The bridge USED to carry only
# primary/background/foreground → the prototype's card/secondary/muted/accent/border
# stayed at the shadcn-neutral default ("just slap the brand color on"). 2.6 must now
# resolve the full identity set, light AND dark, so the look actually flows through.
IDENTITY_REQUIRED = [
    "background", "foreground", "card", "card-foreground",
    "primary", "primary-foreground", "secondary", "secondary-foreground",
    "muted", "muted-foreground", "accent", "accent-foreground", "border",
]
IDENTITY_RECOMMENDED = ["popover", "popover-foreground", "destructive", "input", "ring"]
IDENTITY_ALL = IDENTITY_REQUIRED + IDENTITY_RECOMMENDED
SCALAR_REQUIRED = ["radius", "font_sans"]
REQUIRED_BRAND_CONFIG = ["project_name", "radius", "font_sans"]  # + must carry the colors block

# optional signature block — non-color identity expressed via existing Tailwind utilities
SIGNATURE_ENUMS = {
    "border_style": {"solid", "translucent", "none"},
    "elevation": {"flat", "soft", "layered"},
    "type_weight": {"regular", "medium", "semibold"},
    "tracking": {"tighter", "tight", "normal", "wide"},
}
# contrast pairs the gate insists on (recomputed from hex below). text-on-surface = error.
REQUIRED_CONTRAST_PAIRS = {
    "foreground/background", "primary-foreground/primary",
    "card-foreground/card", "secondary-foreground/secondary",
}
# note: border/background is deliberately NOT here — a subtle aesthetic border legitimately
# sits below the 3:1 UI floor (audit_prototype.py treats it as advisory too).
RECOMMENDED_CONTRAST_PAIRS = {
    "muted-foreground/background", "accent-foreground/accent",
}
# WCAG normal-text thresholds by target
WCAG_MIN = {"A": 4.5, "AA": 4.5, "AAA": 7.0}


def _colors(node):
    """Light/dark color dicts from a tokens|brand_config node — supports nested + flat.

    Nested (new):  node.colors = {light:{...}, dark:{...}}
    Flat (legacy): identity colors live directly on the node (dark is then unknown → None).
    """
    if not isinstance(node, dict):
        return {}, None
    colors = node.get("colors")
    if isinstance(colors, dict):
        return (colors.get("light") or {}), colors.get("dark")
    flat = {k: node[k] for k in IDENTITY_ALL if k in node}
    return flat, None


def _load(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error in {path}: {e}"
    except FileNotFoundError:
        return None, f"file not found: {path}"


def validate(aesthetic_path, intel_path=None, contract_path=None):
    errors, warnings = [], []
    d, err = _load(aesthetic_path)
    if err:
        return [err], []

    intel = None
    if intel_path:
        intel, e = _load(intel_path)
        if e:
            warnings.append(e + " — skipping intelligence cross-checks")

    for k in REQUIRED_TOP_KEYS:
        if k not in d:
            errors.append(f"missing top-level key: '{k}'")
    if errors:
        return errors, warnings

    # ── brief_inference (anti-slop: a direction must be *named* before tokens) ─────
    bi = d["brief_inference"]
    if not bi.get("mood_adjective"):
        errors.append("brief_inference.mood_adjective is required — name the one mood the result must earn (anti-slop)")
    if not bi.get("rationale"):
        errors.append("brief_inference.rationale is required — tie the choice to the product intelligence")
    if bi.get("motion_depth") and bi["motion_depth"] not in MOTION_DEPTH:
        errors.append(f"brief_inference.motion_depth must be one of {sorted(MOTION_DEPTH)} (got {bi.get('motion_depth')!r})")

    # ── direction (must resolve into the vendored library when named_system) ───────
    dir_ = d["direction"]
    dtype = dir_.get("type")
    if dtype not in DIRECTION_TYPES:
        errors.append(f"direction.type must be one of {sorted(DIRECTION_TYPES)} (got {dtype!r})")
    if not dir_.get("why_fit"):
        errors.append("direction.why_fit is required — justify the fit against intelligence dimensions")
    if dtype == "named_system":
        name = dir_.get("name", "")
        spec = LIBRARY / name / "DESIGN.md"
        if not name:
            errors.append("direction.name is required for a named_system")
        elif not spec.is_file():
            errors.append(f"direction.name '{name}' is not in the brand library "
                          f"(no {spec}) — run design_systems.py search <term>")
        else:
            ref = dir_.get("spec_ref", "")
            if name not in ref:
                warnings.append(f"direction.spec_ref should point at library/{name}/DESIGN.md")
    elif dtype == "archetype":
        # An archetype throws away the library's documented design language, and the library is indexed
        # by visual character (not industry) — so an industry search ("medical") falsely returns nothing.
        # Nudge: an archetype must record the mood/visual terms searched, proving the library was checked.
        searched = dir_.get("library_search")
        if not searched or (isinstance(searched, (list, str)) and not searched):
            warnings.append("direction.type=archetype but direction.library_search is empty — search the "
                            "library by mood/visual adjective (calm/clean/minimal/trust…), NOT by industry, "
                            "before falling back to an archetype; record the terms tried so the skip is a "
                            "decision, not a default (a close named_system keeps its DESIGN.md guidance).")

    # ── axes (optional): per-facet composition, coherence-gated ───────────────────
    # Resolve a system on more than just colour — record the source + rationale for each of the 6
    # axes. Coherence is enforced: a composition spans ≤2 systems, the colour axis comes from the
    # resolved palette (direction.name), and any override (axis sourced from a non-primary system)
    # must be justified.
    axes = d.get("axes")
    if axes is not None:
        if not isinstance(axes, dict):
            errors.append("axes must be an object mapping each axis to {source, rationale}")
        else:
            primary = d.get("primary_system") or dir_.get("name")
            if not primary:
                errors.append("axes present but no primary_system (or direction.name) to anchor the composition")
            sources = []
            for ax in AXES:
                node = axes.get(ax)
                if not isinstance(node, dict):
                    errors.append(f"axes.{ax} is required when axes is present — give it {{source, rationale}}")
                    continue
                src = node.get("source")
                if not src:
                    errors.append(f"axes.{ax}.source is required (which system this facet is resolved from)")
                else:
                    sources.append(src)
                    # a named source must resolve in the library (a directive-derived source is exempt)
                    if src not in AXIS_NON_SYSTEM and not (LIBRARY / src / "DESIGN.md").is_file():
                        errors.append(f"axes.{ax}.source '{src}' is not a library system "
                                      f"(no library/{src}/DESIGN.md) — or use 'intelligence' for a directive-derived axis")
                    # an override (source != primary) must be justified
                    if primary and src != primary and src not in AXIS_NON_SYSTEM and not node.get("rationale"):
                        errors.append(f"axes.{ax} overrides the primary system with '{src}' but has no rationale "
                                      "— a per-axis override must be justified (else use the primary for coherence)")
                if not node.get("rationale"):
                    warnings.append(f"axes.{ax}.rationale is empty — say why this source fits the axis")
            # the colour axis must come from the resolved palette (direction.name)
            col_src = (axes.get("color") or {}).get("source")
            if col_src and dir_.get("name") and col_src != dir_.get("name"):
                errors.append(f"axes.color.source '{col_src}' must equal direction.name '{dir_.get('name')}' "
                              "— the palette is resolved from the chosen system; theme another system's colour "
                              "and the contrast-checked tokens no longer match")
            # coherence cap: at most MAX_AXIS_SOURCES distinct systems (excluding directive-derived)
            distinct = {s for s in sources if s not in AXIS_NON_SYSTEM}
            if len(distinct) > MAX_AXIS_SOURCES:
                errors.append(f"axes span {len(distinct)} systems {sorted(distinct)} — cap is {MAX_AXIS_SOURCES} "
                              "for coherence (one primary backbone + at most one justified override). "
                              "Design languages are coherent wholes; mixing many produces a Frankenstein.")

    # ── tokens: the full identity color set (light + dark), not just primary ───────
    tok = d["tokens"]
    dark_mode = d.get("constraints", {}).get("dark_mode", True)
    light, dark = _colors(tok)
    for c in IDENTITY_REQUIRED:
        if not light.get(c):
            errors.append(f"tokens.colors.light.{c} is required — resolve the FULL identity set "
                          "from the system's DESIGN.md, not just primary (this is the anti-'plain' fix)")
    for c in IDENTITY_RECOMMENDED:
        if not light.get(c):
            warnings.append(f"tokens.colors.light.{c} not resolved — recommended for fidelity")
    for s in SCALAR_REQUIRED:
        if not tok.get(s):
            errors.append(f"tokens.{s} is required")
    if dark_mode is not False:
        if not dark:
            errors.append("tokens.colors.dark is required when constraints.dark_mode != false — "
                          "a system's dark identity is not a tinted light theme; resolve it explicitly")
        else:
            for c in IDENTITY_REQUIRED:
                if not dark.get(c):
                    errors.append(f"tokens.colors.dark.{c} is required (dark_mode is on)")

    # ── brand_config: ready-to-drop brand.config.json — must CARRY the whole theme ─
    bc = d["brand_config"]
    for t in REQUIRED_BRAND_CONFIG:
        if not bc.get(t):
            errors.append(f"brand_config.{t} is required (this becomes brand.config.json)")
    bc_light, _bc_dark = _colors(bc)
    for c in IDENTITY_REQUIRED:
        if not bc_light.get(c):
            errors.append(f"brand_config.colors.light.{c} is required — brand.config.json must carry "
                          "the full theme, else generate-prototype falls back to the neutral default")
    # brand_config must AGREE with the resolved tokens (the bridge has to be faithful)
    for field in ("radius", "font_sans", "font_mono"):
        if bc.get(field) and tok.get(field) and bc[field] != tok[field]:
            errors.append(f"brand_config.{field} ({bc[field]!r}) must equal tokens.{field} ({tok[field]!r})")
    for c in IDENTITY_REQUIRED:
        if bc_light.get(c) and light.get(c) and bc_light[c] != light[c]:
            errors.append(f"brand_config.colors.light.{c} ({bc_light[c]!r}) must equal "
                          f"tokens.colors.light.{c} ({light[c]!r})")

    # ── signature (optional): non-color identity, validated against enums ─────────
    sig = d.get("signature") or bi.get("signature") or {}
    if isinstance(sig, dict):
        for k, v in sig.items():
            if k in SIGNATURE_ENUMS and v not in SIGNATURE_ENUMS[k]:
                errors.append(f"signature.{k} must be one of {sorted(SIGNATURE_ENUMS[k])} (got {v!r})")

    # ── constraints must echo the upstream directives ─────────────────────────────
    cons = d["constraints"]
    a11y_target = cons.get("a11y_target")
    if a11y_target not in WCAG_MIN:
        errors.append(f"constraints.a11y_target must be one of {sorted(WCAG_MIN)} (got {a11y_target!r})")
    if intel is not None:
        dz = intel.get("design_directives", {})
        if dz.get("a11y_target") and a11y_target != dz["a11y_target"]:
            errors.append(f"constraints.a11y_target ({a11y_target}) must equal "
                          f"design_directives.a11y_target ({dz['a11y_target']})")
        if dz.get("density_target") and cons.get("density_target") != dz["density_target"]:
            errors.append(f"constraints.density_target ({cons.get('density_target')}) must equal "
                          f"design_directives.density_target ({dz['density_target']})")

    # ── contrast: recompute from hex, never trust the self-reported ratio ──────────
    threshold = WCAG_MIN.get(a11y_target, 4.5)
    checks = d["contrast_checks"]
    if not isinstance(checks, list) or not checks:
        errors.append("contrast_checks must list at least the foreground/background and primary pairs")
    else:
        pairs_seen = set()
        for i, c in enumerate(checks):
            fg, bg = c.get("fg_hex"), c.get("bg_hex")
            label = c.get("pair", f"checks[{i}]")
            pairs_seen.add(label)
            if not fg or not bg:
                errors.append(f"contrast_checks[{i}] ('{label}') needs fg_hex + bg_hex (so the gate can verify, not the agent)")
                continue
            if _contrast is None:
                warnings.append("vendored contrast.py not importable — skipping independent contrast verification")
                continue
            try:
                r = _contrast.ratio(fg, bg)
            except ValueError as e:
                errors.append(f"contrast_checks[{i}] ('{label}'): {e}")
                continue
            # large/UI pairs may use the relaxed 3.0 floor when explicitly marked
            req = 3.0 if c.get("large") or c.get("ui") else threshold
            if r + 1e-9 < req:
                errors.append(f"contrast_checks '{label}': {fg} on {bg} = {r:.2f}:1, "
                              f"below {req}:1 required for {a11y_target} — adjust the token (taste never overrides POUR)")
            # flag a self-reported ratio that disagrees with the truth
            claimed = c.get("ratio")
            if isinstance(claimed, (int, float)) and abs(claimed - r) > 0.2:
                warnings.append(f"contrast_checks '{label}' self-reported {claimed}:1 but actual is {r:.2f}:1")
        missing_req = REQUIRED_CONTRAST_PAIRS - pairs_seen
        if missing_req:
            errors.append(f"contrast_checks is missing required text-on-surface pairs: {sorted(missing_req)} "
                          "— every surface that carries text must be contrast-verified, not just primary")
        missing_rec = RECOMMENDED_CONTRAST_PAIRS - pairs_seen
        if missing_rec:
            warnings.append(f"contrast_checks is missing recommended pairs: {sorted(missing_rec)}")

    # ── token contract (optional — only when a DS token-contract.json is given) ───
    # The DS repo owns which tokens are themeable; DesignOps 2.6 may only set those.
    # No contract passed → behaviour unchanged (back-compatible).
    if contract_path:
        contract, cerr = _load(contract_path)
        if cerr or not isinstance(contract, dict):
            warnings.append(f"token contract not read ({contract_path}) — skipped contract check")
        else:
            allowed = set(contract.get("color_tokens", [])) | set(contract.get("scalar_tokens", []))
            if not allowed:
                warnings.append("token contract lists no tokens — skipped contract check")
            else:
                # metadata / structural keys that are not themeable DS tokens
                NON_TOKEN = {"project_name", "colors", "dark_mode", "signature"}
                # additive semantic EXTENSIONS (Phase 3): warning/info/success map to NEW CSS vars
                # (bg-warning, …) — they don't override a DS token, so a strict contract that predates
                # them must still allow them. The build gates verify they're applied (theme fidelity
                # gate 6 EXTENDED), and contrast is re-checked above.
                EXTENSIONS = {"warning", "warning-foreground", "info", "info-foreground",
                              "success", "success-foreground"}
                allowed |= EXTENSIONS
                pkg = contract.get("package", "the DS")
                for src in ("tokens", "brand_config"):
                    node = d.get(src) or {}
                    src_light, src_dark = _colors(node)
                    keys = set(src_light) | set(src_dark or {})           # nested color tokens
                    keys |= {k for k in node if k not in NON_TOKEN}        # flat scalars (radius, font_*)
                    for k in keys:
                        if k not in allowed:
                            errors.append(f"{src}.{k!r} is not in {pkg}'s token contract (nor an allowed "
                                          "semantic extension) — 2.6 may only theme tokens the DS exposes")
    else:
        # No contract → brand_config keys are NOT verified against the DS. Every key here
        # becomes a `--key` CSS-var override in the prototype; a name the DS doesn't define
        # is a silent no-op (the theme just doesn't apply). Surface that so it's a choice,
        # not an accident. Pass the DS token-contract.json (Model A) to make it a hard gate.
        warnings.append("no DS token-contract.json provided — brand_config keys are NOT verified "
                        "against the design system; a mistyped/unknown token silently fails to theme. "
                        "Pass token-contract.json (from @npsin-oreo/design-system) to enforce it.")

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_aesthetic.py <aesthetic.json> [intelligence.json] [token-contract.json]", file=sys.stderr)
        sys.exit(1)
    errors, warnings = validate(*sys.argv[1:4])
    if errors:
        print(f"[validate_aesthetic] ✗ Invalid — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        for w in warnings:
            print(f"  ⚠ {w}", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        d = json.load(f)
    dir_ = d.get("direction", {})
    bi = d.get("brief_inference", {})
    _light, _dark = _colors(d.get("tokens", {}))
    sig = d.get("signature") or bi.get("signature") or {}
    print("[validate_aesthetic] ✓ Valid")
    print(f"  Direction  : {dir_.get('type')} · {dir_.get('name')}  [{dir_.get('category', '—')}]")
    print(f"  Mood       : {bi.get('mood_adjective')} · motion={bi.get('motion_depth', '—')}"
          + (f" · signature={sig}" if sig else ""))
    print(f"  Identity   : {len(_light)} light tokens" + (f" + {len(_dark)} dark" if _dark else " (light only)"))
    axes = d.get("axes")
    if isinstance(axes, dict):
        comp = " · ".join(f"{ax}={(axes.get(ax) or {}).get('source', '?')}" for ax in
                          ("color", "typography", "shape", "elevation", "spacing", "motion") if ax in axes)
        srcs = sorted({(axes.get(ax) or {}).get("source") for ax in axes} - {None})
        print(f"  Axes       : {comp}")
        print(f"  Composition: {len(srcs)} system(s) {srcs} (primary {d.get('primary_system') or dir_.get('name')})")
    print(f"  a11y target: {d.get('constraints', {}).get('a11y_target')} · "
          f"contrast pairs verified: {len(d.get('contrast_checks', []))}")
    for w in warnings:
        print(f"  ⚠ {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
