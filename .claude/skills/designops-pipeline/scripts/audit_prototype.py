#!/usr/bin/env python3
"""
audit_prototype.py — the Step 4.7 audit GATE, as a real runnable check (not agent judgment).

Four objective, deterministic gates over the BUILT prototype:
  1. Token compliance — runs lint_hardcodes.py over the generated screens; any raw hex / px /
     ms / raw Tailwind palette utility (bg-gray-500 …) that isn't a token = a violation.
  2. WCAG contrast — parses the prototype's globals.css :root + .dark token blocks, converts
     each oklch value to sRGB itself, and checks the essential foreground/background pairs at
     the a11y target (AA 4.5:1 / AAA 7:1 normal text; 3:1 for UI borders). Light AND dark.
  3. UX copy — runs check_no_emoji.py: no emoji / em-dash in product UI (ux-writing).
  4. Component contracts — runs lint_component_contracts.py: enforces the Button/Dialog/Field
     usage contracts (icon-button accessible name, DialogTitle present, Input↔FieldLabel).
Gates 3 and 4 skip cleanly (—) if their checker script is missing.

By default it audits the GENERATED surface only — `components/ui` (vendored shadcn primitives),
any `docs/` dir (DS demos + these reports), and node_modules/.next/out are auto-excluded, so you
can point it at the whole prototype without it tripping over vendored code. Use --include-vendored
to audit everything.

Usage:
  python3 audit_prototype.py <prototype_dir> [--a11y AA|AAA] [--scan app,components,lib]
                             [--include-vendored] [--report path.md]
Exit 0 = PASS, 1 = BLOCKED. Zero-dependency (imports vendored contrast.py + lint_hardcodes.py).
"""

import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "references" / "aesthetics" / "scripts"))
import contrast as _contrast  # vendored WCAG checker (ratio from hex)

# ux-writing emoji/dash checker (vendored under references/ux-writing/scripts)
_EMOJI_CHECK = HERE.parent / "references" / "ux-writing" / "scripts" / "check_no_emoji.py"

# component-usage contract checker (Button/Dialog/Field — references/component-contracts.md)
_CONTRACT_CHECK = HERE / "lint_component_contracts.py"

# Required pairs FAIL the gate; advisory pairs are reported only. shadcn/ui token names.
REQUIRED_PAIRS = [
    ("foreground", "background", "body text on page"),
    ("card-foreground", "card", "text on card"),
    ("primary-foreground", "primary", "text on primary action"),
    ("secondary-foreground", "secondary", "text on secondary"),
    ("destructive-foreground", "destructive", "text on destructive"),
]
ADVISORY_PAIRS = [
    ("muted-foreground", "background", "muted/secondary text", 4.5),
    ("accent-foreground", "accent", "text on accent", 4.5),
    ("border", "background", "control border (WCAG 1.4.11)", 3.0),
    ("ring", "background", "focus ring", 3.0),
]
WCAG_NORMAL = {"A": 4.5, "AA": 4.5, "AAA": 7.0}


# ── oklch → sRGB hex (Björn Ottosson's OKLab matrices) ────────────────────────
def _srgb_gamma(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def oklch_to_hex(L, C, h_deg):
    h = math.radians(h_deg)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bl = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return "#" + "".join(f"{round(_srgb_gamma(x) * 255):02x}" for x in (r, g, bl))


_OKLCH = re.compile(r"oklch\(\s*([0-9.]+%?)\s+([0-9.]+%?)\s+([0-9.]+)", re.I)
_DEF = re.compile(r"--([a-z0-9-]+)\s*:\s*(oklch\([^)]*\)|#[0-9a-fA-F]{3,8})", re.I)


def _num(tok):
    return float(tok[:-1]) / 100 if tok.endswith("%") else float(tok)


def _to_hex(value):
    """A token value (oklch(...) or #hex) → #rrggbb, or None if unparseable."""
    value = value.strip()
    if value.startswith("#"):
        return value
    m = _OKLCH.search(value)
    if not m:
        return None
    L, C, h = _num(m.group(1)), _num(m.group(2)), float(m.group(3))
    if L > 1:  # tolerate 0..100 lightness
        L /= 100
    return oklch_to_hex(L, C, h)


def _parse_blocks(css_text):
    """Return {block_name: {token: hex}} for :root and .dark."""
    blocks = {}
    for name, sel in (("light", r":root"), ("dark", r"\.dark")):
        m = re.search(sel + r"\s*\{(.*?)\}", css_text, re.S)
        if not m:
            continue
        toks = {}
        for d in _DEF.finditer(m.group(1)):
            hexv = _to_hex(d.group(2))
            if hexv:
                toks[d.group(1).lower()] = hexv
        blocks[name] = toks
    return blocks


# Vendored / non-UI paths the audit should not blame on the generated screens.
_SKIP_SEGMENTS = {"node_modules", ".next", "out", "docs"}


def _is_vendored(rel_posix):
    """True if a prototype-relative path is vendored DS / build / report (not generated)."""
    if "components/ui/" in rel_posix + "/":
        return True
    return any(seg in rel_posix.split("/") for seg in _SKIP_SEGMENTS)


def _collect_targets(proto, scan_dirs, include_vendored):
    """Files under the scan dirs, minus vendored DS internals (unless include_vendored)."""
    files = []
    for d in scan_dirs:
        base = proto / d
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(proto).as_posix()
            if not include_vendored and _is_vendored(rel):
                continue
            files.append(str(f))
    return files


# ── gate 1: token compliance (hardcoded values) ───────────────────────────────
def lint_gate(proto, scan_dirs, include_vendored):
    targets = _collect_targets(proto, scan_dirs, include_vendored)
    if not targets:
        return None, "no scan targets found"
    proc = subprocess.run([sys.executable, str(HERE / "lint_hardcodes.py"), *targets],
                          capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout.strip()


# ── gate 3: UX copy — no emoji / no em-dash in product UI (ux-writing) ─────────
def emoji_gate(proto, scan_dirs, include_vendored):
    targets = _collect_targets(proto, scan_dirs, include_vendored)
    if not targets or not _EMOJI_CHECK.is_file():
        return None, "skipped (no targets or checker missing)"
    proc = subprocess.run([sys.executable, str(_EMOJI_CHECK), *targets],
                          capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout.strip()


# ── gate 4: component usage contracts (Button/Dialog/Field a11y) ───────────────
def contract_gate(proto, scan_dirs, include_vendored):
    targets = _collect_targets(proto, scan_dirs, include_vendored)
    if not targets or not _CONTRACT_CHECK.is_file():
        return None, "skipped (no targets or checker missing)"
    proc = subprocess.run([sys.executable, str(_CONTRACT_CHECK), *targets],
                          capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout.strip()


# ── gate 2: WCAG contrast over the actual theme ───────────────────────────────
def contrast_gate(css_path, a11y):
    text = css_path.read_text(errors="ignore")
    blocks = _parse_blocks(text)
    threshold = WCAG_NORMAL.get(a11y, 4.5)
    failures, lines = [], []
    if not blocks:
        return False, ["no :root/.dark token block parsed from globals.css"]
    for mode, toks in blocks.items():
        for fg, bg, label in REQUIRED_PAIRS:
            if fg not in toks or bg not in toks:
                continue  # token not in theme (e.g. no destructive-foreground) — skip
            r = _contrast.ratio(toks[fg], toks[bg])
            ok = r + 1e-9 >= threshold
            lines.append(f"  [{mode}] {label:28} {toks[fg]} on {toks[bg]} = {r:.2f}:1  {'PASS' if ok else 'FAIL'} (≥{threshold})")
            if not ok:
                failures.append(f"[{mode}] {label}: {r:.2f}:1 < {threshold}:1 — adjust the token")
        for fg, bg, label, req in ADVISORY_PAIRS:
            if fg in toks and bg in toks:
                r = _contrast.ratio(toks[fg], toks[bg])
                lines.append(f"  [{mode}] {label:28} {toks[fg]} on {toks[bg]} = {r:.2f}:1  {'ok' if r >= req else 'advisory<'+str(req)}")
    return len(failures) == 0, lines, failures


def main(argv):
    args, a11y, scan, report, include_vendored = [], "AA", ["app", "components", "lib"], None, False
    i = 0
    while i < len(argv):
        if argv[i] == "--a11y" and i + 1 < len(argv):
            a11y = argv[i + 1].replace("AA_plus", "AAA").upper(); i += 2
        elif argv[i] == "--scan" and i + 1 < len(argv):
            scan = argv[i + 1].split(","); i += 2
        elif argv[i] == "--include-vendored":
            include_vendored = True; i += 1
        elif argv[i] == "--report" and i + 1 < len(argv):
            report = argv[i + 1]; i += 2
        else:
            args.append(argv[i]); i += 1
    if not args:
        print(__doc__); return 2
    proto = Path(args[0])
    if not proto.is_dir():
        print(f"[audit_prototype] ✗ prototype dir not found: {proto}", file=sys.stderr); return 1

    out = [f"# Audit Report — Step 4.7 (a11y target: {a11y})", ""]

    # gate 1
    lint_ok, lint_out = lint_gate(proto, scan, include_vendored)
    out += ["## 1. Token compliance (no hardcoded values)",
            "```", lint_out or "(nothing scanned)", "```", ""]

    # gate 3 (UX copy: no emoji / em-dash in product UI)
    emoji_ok, emoji_out = emoji_gate(proto, scan, include_vendored)
    out += ["## 3. UX copy — no emoji / em-dash in UI (ux-writing)",
            "```", emoji_out or "(skipped)", "```", ""]

    # gate 4 (component usage contracts: Button/Dialog/Field a11y)
    contract_ok, contract_out = contract_gate(proto, scan, include_vendored)
    out += ["## 4. Component contracts (Button/Dialog/Field usage)",
            "```", contract_out or "(skipped)", "```", ""]

    # gate 2
    css = proto / "app" / "globals.css"
    if css.is_file():
        cg = contrast_gate(css, a11y)
        contrast_ok, clines = cg[0], cg[1]
        cfails = cg[2] if len(cg) > 2 else []
        out += [f"## 2. WCAG contrast — {a11y} (from globals.css, light + dark)", "```", *clines, "```", ""]
    else:
        contrast_ok, cfails = False, [f"globals.css not found at {css}"]
        out += ["## 2. WCAG contrast", "globals.css not found — cannot verify.", ""]

    # emoji_ok / contract_ok may be None (skipped) — only fail the gate when explicitly False
    blocked = not (lint_ok and contrast_ok and emoji_ok is not False and contract_ok is not False)
    verdict = "🔴 BLOCKED" if blocked else "🟢 PASS"
    out += ["## Verdict", f"- Token compliance: {'🟢' if lint_ok else '🔴'}",
            f"- WCAG {a11y} contrast: {'🟢' if contrast_ok else '🔴'}",
            f"- UX copy (no emoji/dash): {'🟢' if emoji_ok else ('—' if emoji_ok is None else '🔴')}",
            f"- Component contracts: {'🟢' if contract_ok else ('—' if contract_ok is None else '🔴')}",
            "", f"**{verdict}**"]
    if cfails:
        out += ["", "### Contrast failures", *[f"- {f}" for f in cfails]]

    report_text = "\n".join(out)
    if report:
        Path(report).parent.mkdir(parents=True, exist_ok=True)
        Path(report).write_text(report_text + "\n")

    # console summary
    print(f"[audit_prototype] {verdict} — token={'PASS' if lint_ok else 'FAIL'} · "
          f"WCAG {a11y}={'PASS' if contrast_ok else 'FAIL'} · "
          f"copy={'PASS' if emoji_ok else ('—' if emoji_ok is None else 'FAIL')} · "
          f"contracts={'PASS' if contract_ok else ('—' if contract_ok is None else 'FAIL')}")
    if report:
        print(f"  → {report}")
    for f in cfails:
        print(f"  • {f}", file=sys.stderr)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
