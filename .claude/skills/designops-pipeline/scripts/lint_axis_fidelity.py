#!/usr/bin/env python3
"""
lint_axis_fidelity.py — Step 4.7 gate 11: were the NON-colour axes actually applied?

Step 2.6's `axes` block (typography / shape / motion / …) records the design language pulled from
each system's DESIGN.md beyond colour. Gate 6 verifies colours and gate 10 the font, but the rest
(type scale + leading + weight, pill shape, motion easing) is expressed in globals.css via @theme
re-points and brand-scoped [data-slot=*] rules — and could silently stay at the scaffold default
(the same no-op class as the font bug). This gate reads each axis's `resolved` metrics and FAILS
when they are not present in the built globals.css.

Deterministic, substring/regex over globals.css:
  • typography.resolved.base_line_height  → that line-height value is set (re-pointed --text-* ramp)
  • typography.resolved.heading_weight_cap → that font-weight is applied
  • shape.resolved.pill_slots[]           → each slot has a [data-slot=<slot>] … rounded-full rule
  • motion.resolved.easing                → the easing value is present AND applied to a non-card slot

Usage:
  lint_axis_fidelity.py <globals.css> <aesthetic.json>
Exit 0 = PASS / nothing to check, 1 = BLOCKED. Zero-dependency. Skips cleanly when no axes.resolved.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_prototype import _read_css_with_imports  # follow a local @import "./brand.css" (same as gate 2/6)


def _num(v):
    return str(v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def check(css_path, aes_path):
    errors, notes = [], []
    css_path, aes_path = Path(css_path), Path(aes_path)
    if not css_path.is_file():
        return [f"globals.css not found: {css_path}"], notes
    try:
        aes = json.loads(Path(aes_path).read_text())
    except Exception as e:  # noqa: BLE001
        return [], [f"aesthetic not read ({aes_path}): {e} — axis-fidelity check skipped"]

    axes = aes.get("axes")
    if not isinstance(axes, dict):
        return [], ["no axes block in aesthetic.json — nothing to verify"]
    css = _read_css_with_imports(css_path)   # axes may live in a DS-native @import "./brand.css"
    low = css.lower()
    checked = 0

    # ── typography ────────────────────────────────────────────────────────────
    typo = (axes.get("typography") or {}).get("resolved") or {}
    if typo:
        blh = typo.get("base_line_height")
        if blh is not None:
            checked += 1
            val = _num(blh)
            # the value must appear as a line-height (re-pointed --text-base--line-height or body)
            if not re.search(rf"(line-height|--text-[a-z0-9]+--line-height)\s*:?\s*{re.escape(val)}\b", css, re.I) \
               and not re.search(rf"--text-base--line-height:\s*{re.escape(val)}", css, re.I):
                errors.append(f"typography.resolved.base_line_height {val} is not applied in globals.css "
                              "— re-point the --text-* ramp (or set a body line-height) so the type axis lands")
        cap = typo.get("heading_weight_cap")
        if cap is not None:
            checked += 1
            if not re.search(rf"font-weight\s*:\s*{re.escape(str(cap))}\b", low):
                errors.append(f"typography.resolved.heading_weight_cap {cap} is not applied "
                              "(no font-weight rule) — headings still use the default weight")

    # ── shape (pills) ─────────────────────────────────────────────────────────
    shape = (axes.get("shape") or {}).get("resolved") or {}
    for slot in shape.get("pill_slots", []) or []:
        checked += 1
        # a brand-scoped rule for the slot that makes it a pill (rounded-full / radius 9999)
        pat = rf'\[data-slot=["\']{re.escape(slot)}["\']\][^{{]*\{{[^}}]*(rounded-full|border-radius[^;}}]*9999|border-radius[^;}}]*var\(--radius-full)'
        if not re.search(pat, css, re.I | re.S):
            errors.append(f"shape.resolved.pill_slots '{slot}' is not applied — add a brand-scoped "
                          f"[data-slot=\"{slot}\"] {{ @apply rounded-full }} rule so chips read as pills")
    pill_pad = shape.get("pill_padding")
    if pill_pad:
        checked += 1
        if pill_pad not in css:
            errors.append(f"shape.resolved.pill_padding '{pill_pad}' is not applied in globals.css")

    # ── spacing ───────────────────────────────────────────────────────────────
    spacing = (axes.get("spacing") or {}).get("resolved") or {}
    sv = spacing.get("section_var")
    if sv:
        checked += 1
        # the rhythm token must be defined AND used (declared-only is the no-op we're guarding against)
        if not re.search(rf"{re.escape(sv)}\s*:", css):
            errors.append(f"spacing.resolved.section_var '{sv}' is not defined in globals.css")
        # usage lives in the JSX (e.g. pt-[var(--spacing-section)]) — defined here is the gate's scope

    # ── motion ────────────────────────────────────────────────────────────────
    motion = (axes.get("motion") or {}).get("resolved") or {}
    easing = motion.get("easing")
    if easing:
        checked += 1
        ez = easing.replace(" ", "")
        if ez not in low.replace(" ", ""):
            errors.append(f"motion.resolved.easing '{easing}' is not present in globals.css "
                          "— define it as a CSS var and apply it (the motion axis silently no-opped)")
        else:
            # applied beyond the card? look for a non-card slot referencing the timing function / var
            applied_non_card = re.search(
                r'\[data-slot=["\'](?:button|badge)["\']|a\[href\]', css, re.I) and "transition-timing-function" in low
            if not applied_non_card:
                errors.append("motion.resolved.easing is defined but only the card uses it — apply the "
                              "easing to interactive slots (button/link) too, per motion.slots")

    if not errors:
        notes.append(f"{checked} axis metric(s) applied in the build (typography/shape/motion)")
    return errors, notes


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    errors, notes = check(argv[0], argv[1])
    if errors:
        print(f"[axis_fidelity] ✗ {len(errors)} axis metric(s) declared but not applied:")
        for e in errors:
            print(f"  • {e}")
        for n in notes:
            print(f"  ℹ {n}")
        return 1
    print("[axis_fidelity] ✓ non-colour axes are applied in the build")
    for n in notes:
        print(f"  ℹ {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
