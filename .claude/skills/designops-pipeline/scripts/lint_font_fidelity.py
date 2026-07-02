#!/usr/bin/env python3
"""
lint_font_fidelity.py — Step 4.7 gate 6 fidelity family (font sub): did the prototype APPLY the committed font?

Step 2.6 commits a `font_sans` in brand.config.json / aesthetic.json, but the bridge only ever
carried colours into the build. The font directive could silently no-op — the scaffold keeps its
default loader (e.g. Geist) and the committed family (e.g. Inter / Noto Sans Thai) never reaches the
page. Nothing caught it: gate 5 only forbids a remote @import, gate 6 only checks colours. For a
Thai TOR that commits "Noto Sans Thai", that is a real regression rendered in the wrong typeface.

This gate re-reads the BUILT app/layout.* + app/globals.css and FAILS when the committed primary
family is nowhere in them (so the build is still on the default font). It is deterministic: the
family name must appear, as a next/font import (spaces → underscores) or in a --font-sans CSS value.

Usage:
  lint_font_fidelity.py <prototype_dir> <theme.json>
    theme.json = brand.config.json or aesthetic.json (reads font_sans / brand_config.font_sans / tokens.font_sans)
Exit 0 = PASS / nothing to check, 1 = BLOCKED. Zero-dependency.
"""

import json
import re
import sys
from pathlib import Path

GENERIC = {"system-ui", "sans-serif", "serif", "monospace", "ui-sans-serif", "ui-monospace",
           "ui-serif", "cursive", "fantasy", "inherit", "initial"}


def _font_sans(theme):
    """Pull the committed font_sans from brand.config.json or aesthetic.json (nested or flat)."""
    if not isinstance(theme, dict):
        return None
    if theme.get("font_sans"):
        return theme["font_sans"]
    for key in ("brand_config", "tokens"):
        node = theme.get(key) or {}
        if isinstance(node, dict) and node.get("font_sans"):
            return node["font_sans"]
    return None


def _primary_family(font_sans):
    """First real (non-generic) family in a CSS font stack. '"Inter", "Noto Sans Thai", sans-serif' → 'Inter'."""
    for raw in str(font_sans).split(","):
        fam = raw.strip().strip("'\"").strip()
        if fam and fam.lower() not in GENERIC:
            return fam
    return None


def _present(family, text):
    """Family appears in the build text — as-is, or in next/font underscore form (spaces → '_')."""
    low = text.lower()
    if family.lower() in low:
        return True
    underscored = re.sub(r"\s+", "_", family).lower()
    return underscored in low


def check(proto, theme_path):
    proto, theme_path = Path(proto), Path(theme_path)
    try:
        theme = json.loads(theme_path.read_text())
    except Exception as e:  # noqa: BLE001
        return [], [f"theme not read ({theme_path}): {e} — font check skipped"]

    font_sans = _font_sans(theme)
    if not font_sans:
        return [], ["no font_sans committed in theme — nothing to verify"]
    family = _primary_family(font_sans)
    if not family:
        return [], [f"font_sans '{font_sans}' has only generic families — nothing to verify"]

    # the build surface where a font is wired: the root layout + the theme CSS
    blob = []
    appdir = proto / "app"
    for name in ("layout.tsx", "layout.jsx", "layout.ts", "layout.js", "globals.css"):
        f = appdir / name
        if f.is_file():
            try:
                blob.append(f.read_text(errors="ignore"))
            except Exception:  # noqa: BLE001
                pass
    if not blob:
        return [], ["no app/layout.* or app/globals.css found — font check skipped"]
    text = "\n".join(blob)

    if _present(family, text):
        return [], [f"committed font '{family}' is applied in the build"]
    return [f"brand committed font_sans '{font_sans}' (primary '{family}') but neither app/layout.* "
            f"nor globals.css references it — the build is still on its default font. Load '{family}' "
            "via next/font and wire --font-sans (the font directive silently no-opped)."], []


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    errors, notes = check(argv[0], argv[1])
    if errors:
        print(f"[font_fidelity] ✗ {len(errors)} font directive not applied:")
        for e in errors:
            print(f"  • {e}")
        return 1
    print("[font_fidelity] ✓ committed font is applied")
    for n in notes:
        print(f"  ℹ {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
