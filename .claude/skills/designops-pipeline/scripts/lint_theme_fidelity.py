#!/usr/bin/env python3
"""
lint_theme_fidelity.py — Step 4.7 gate 6: did the prototype actually APPLY the committed theme?

Step 2.6 resolves a full identity theme (surfaces, text hierarchy, accent, border + dark) into
aesthetic.json / brand.config.json. The bridge USED to carry only `--primary`, so the prototype's
card / secondary / muted / accent / border stayed at the shadcn-neutral default — "plain, the brand
colour slapped on a neutral skeleton". This gate re-reads the BUILT globals.css and FAILS when an
identity token the theme committed is missing, or was left at a value that doesn't match (i.e. it
regressed to neutral). Deterministic — it compares the committed hex to the rendered token, it does
not ask the agent whether the theme "looks applied".

Usage:
  lint_theme_fidelity.py <globals.css> <theme.json>
    theme.json = brand.config.json (colors at top) or aesthetic.json (tokens.colors / brand_config.colors)
Exit 0 = PASS / nothing to check, 1 = BLOCKED. Zero-dependency (reuses audit_prototype's parser).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_prototype import _parse_blocks, _to_hex  # oklch/hex → #hex (same math as the audit)

# the identity tokens that carry a system's character (must survive the bridge)
IDENTITY = [
    "background", "foreground", "card", "card-foreground",
    "primary", "primary-foreground", "secondary", "secondary-foreground",
    "muted", "muted-foreground", "accent", "accent-foreground", "border",
]
# extended semantics — checked ONLY when the theme commits them (Phase 3). A theme that adds
# warning/info/success then leaves them out of globals.css is the same silent no-op as a missing
# identity token, so verify them too; absent from the theme → skipped (back-compat).
EXTENDED = [
    "warning", "warning-foreground", "info", "info-foreground", "success", "success-foreground",
]
TOL = 8  # per-channel sRGB tolerance — absorbs oklch↔hex rounding, not a neutral regression


def _rgb(h):
    if not isinstance(h, str) or not h.startswith("#"):
        return None
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) >= 6:
        try:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return None
    return None


def _close(a, b):
    ra, rb = _rgb(a), _rgb(b)
    if ra is None or rb is None:
        return a == b
    return all(abs(x - y) <= TOL for x, y in zip(ra, rb))


def _committed(theme):
    """Pull {light:{...}, dark:{...}} from brand.config.json OR aesthetic.json, nested OR flat."""
    def colors_of(node):
        if not isinstance(node, dict):
            return {}, None
        c = node.get("colors")
        if isinstance(c, dict):
            return (c.get("light") or {}), c.get("dark")
        flat = {k: node[k] for k in IDENTITY if k in node}
        return flat, None

    # brand.config.json: colors/flat at the top level
    light, dark = colors_of(theme)
    if light:
        return light, dark
    # aesthetic.json: try tokens, then brand_config
    for key in ("tokens", "brand_config"):
        light, dark = colors_of(theme.get(key, {}))
        if light:
            return light, dark
    return {}, None


def check(css_path, theme_path):
    errors, notes = [], []
    css_path, theme_path = Path(css_path), Path(theme_path)
    if not css_path.is_file():
        return [f"globals.css not found: {css_path}"], notes
    try:
        theme = json.loads(Path(theme_path).read_text())
    except Exception as e:  # noqa: BLE001
        return [], [f"theme not read ({theme_path}): {e} — fidelity check skipped"]

    light, dark = _committed(theme)
    if not light:
        return [], ["no identity colors committed in theme — nothing to verify"]

    blocks = _parse_blocks(css_path.read_text(errors="ignore"))
    if not blocks:
        return ["no :root/.dark token block parsed from globals.css"], notes

    committed = {"light": light}
    if dark:
        committed["dark"] = dark

    applied = 0
    for mode, want in committed.items():
        have = blocks.get(mode, {})
        if not have:
            errors.append(f"globals.css has no '{mode}' token block but the theme commits {mode} colors")
            continue
        for tok in IDENTITY + EXTENDED:
            if tok not in want:   # EXTENDED tokens skip unless the theme committed them
                continue
            target = want[tok]
            # normalise BOTH sides through the same oklch→hex math the audit uses, so an
            # oklch brand.config and a hex-rendered token (or vice-versa) compare correctly.
            target_hex = _to_hex(str(target)) or target
            actual = have.get(tok)  # already #hex (from _parse_blocks)
            if actual is None:
                errors.append(f"[{mode}] --{tok} missing from globals.css "
                              f"(theme committed {target}) — identity token not applied")
            elif not _close(actual, target_hex):
                errors.append(f"[{mode}] --{tok} = {actual} but theme committed {target} "
                              f"— regressed/drifted from the chosen system (neutral default?)")
            else:
                applied += 1

    # signature is advisory — it lives in component utilities, not globals.css
    sig = theme.get("signature") or (theme.get("brief_inference") or {}).get("signature")
    if sig:
        notes.append(f"signature to express via utilities (not checked here): {sig}")
    if not errors:
        notes.append(f"{applied} identity tokens applied faithfully across {len(committed)} mode(s)")
    return errors, notes


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    errors, notes = check(argv[0], argv[1])
    if errors:
        print(f"[theme_fidelity] ✗ {len(errors)} identity token(s) not applied:")
        for e in errors:
            print(f"  • {e}")
        for n in notes:
            print(f"  ℹ {n}")
        return 1
    print("[theme_fidelity] ✓ committed theme is faithfully applied")
    for n in notes:
        print(f"  ℹ {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
