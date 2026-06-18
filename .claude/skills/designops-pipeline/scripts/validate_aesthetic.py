#!/usr/bin/env python3
"""
validate_aesthetic.py — gate for Step 2.6 (Aesthetic Direction).

Usage: validate_aesthetic.py <aesthetic.json> [intelligence.json]
Exit 0 = valid, Exit 1 = invalid. Zero-dependency (imports the vendored contrast.py).

aesthetic.json picks a visual direction (a named system from the 138-brand library, or an
archetype) and resolves it into concrete tokens. This gate checks that:
  • the chosen named_system actually exists in references/aesthetics/design-systems/library/
  • a mood adjective was committed (anti-slop: generating before deciding = slop)
  • the token set is complete + emits a ready-to-drop brand.config
  • EVERY contrast pair is independently re-computed from hex and meets the a11y target
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
REQUIRED_TOKENS = ["primary", "background", "foreground", "radius", "font_sans"]
REQUIRED_BRAND_CONFIG = ["project_name", "primary", "radius", "font_sans"]
# WCAG normal-text thresholds by target
WCAG_MIN = {"A": 4.5, "AA": 4.5, "AAA": 7.0}


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

    # ── tokens (complete enough to render + theme) ────────────────────────────────
    tok = d["tokens"]
    for t in REQUIRED_TOKENS:
        if not tok.get(t):
            errors.append(f"tokens.{t} is required")

    # ── brand_config (ready to drop as brand.config.json) ─────────────────────────
    bc = d["brand_config"]
    for t in REQUIRED_BRAND_CONFIG:
        if not bc.get(t):
            errors.append(f"brand_config.{t} is required (this becomes brand.config.json)")
    # brand_config must agree with the resolved tokens
    for field in ("primary", "radius", "font_sans"):
        if bc.get(field) and tok.get(field) and bc[field] != tok[field]:
            errors.append(f"brand_config.{field} ({bc[field]!r}) must equal tokens.{field} ({tok[field]!r})")

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
        need = {"foreground/background", "primary-foreground/primary"}
        missing = need - pairs_seen
        if missing:
            warnings.append(f"contrast_checks is missing recommended pairs: {sorted(missing)}")

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
                NON_TOKEN = {"project_name"}  # brand_config metadata, not a themeable token
                pkg = contract.get("package", "the DS")
                for src in ("tokens", "brand_config"):
                    for k in (d.get(src) or {}):
                        if k in NON_TOKEN:
                            continue
                        if k not in allowed:
                            errors.append(f"{src}.{k!r} is not in {pkg}'s token contract — "
                                          "2.6 may only theme tokens the design system exposes")

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
    print("[validate_aesthetic] ✓ Valid")
    print(f"  Direction  : {dir_.get('type')} · {dir_.get('name')}  [{dir_.get('category', '—')}]")
    print(f"  Mood       : {bi.get('mood_adjective')} · motion={bi.get('motion_depth', '—')}")
    print(f"  a11y target: {d.get('constraints', {}).get('a11y_target')} · "
          f"contrast pairs verified: {len(d.get('contrast_checks', []))}")
    for w in warnings:
        print(f"  ⚠ {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
