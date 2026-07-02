#!/usr/bin/env python3
"""
audit_prototype.py — the Step 4.7 audit GATE, as a real runnable check (not agent judgment).

Ten gates over the BUILT prototype (1-9 static + deterministic; 10 optional render). Gate 6 is a
FIDELITY FAMILY — theme colours + font + non-colour axes (formerly separate gates 6/10/11), folded
since they answer one question: did the committed Step 2.6 direction actually get applied?
  1. Token compliance — runs lint_hardcodes.py over the generated screens; any raw hex / px /
     ms / raw Tailwind palette utility (bg-gray-500 …) that isn't a token = a violation.
  2. WCAG contrast — parses the prototype's globals.css :root + .dark token blocks, converts
     each oklch value to sRGB itself, and checks the essential foreground/background pairs at
     the a11y target (AA 4.5:1 / AAA 7:1 normal text; 3:1 for UI borders). Light AND dark.
  3. UX copy — runs check_no_emoji.py: no emoji / em-dash in product UI (ux-writing).
  4. Component contracts — runs lint_component_contracts.py: enforces the Button/Dialog/Field
     usage contracts (icon-button accessible name, DialogTitle present, Input↔FieldLabel).
  5. Font loading — runs lint_font_imports.py: no remote-font @import in CSS (a Turbopack dev
     500 trap; load fonts with next/font instead).
  6. Fidelity family — did the committed Step 2.6 direction actually get applied? ONE gate over three
     sub-checks (each keeps its own linter): theme colours (lint_theme_fidelity.py — no "brand colour
     on a neutral skeleton" regression), font (lint_font_fidelity.py — the committed font_sans is
     wired, not left at the scaffold default), and the NON-colour axes (lint_axis_fidelity.py —
     type line-height/weight, pill shape, motion easing, layout tokens in @theme). Family FAILs if any
     sub fails. (Formerly three separate gates 6/10/11 — folded, since they answer one question.)
  7. Directive fidelity — runs lint_directive_fidelity.py: the build must honor design_directives
     (Step 2.5) — destructive actions guarded when safeguard_level is on, an empty-state when
     guidance_level is guided (density/nav are advisory). Reads intelligence.json.
  8. Screen coverage — runs lint_screen_coverage.py: every Must screen in screen-inventory.json
     (Step 3.5) was actually built as an app route, rendering its declared loading/empty/error states.
  9. Edge-case coverage — runs lint_edge_coverage.py: every Must edge case in edge-cases.json
     (Step 3.7) is actually handled in the screen it maps to (empty/error/loading/partial state,
     inline validation, or a destructive confirm). The back end of the edge-case spine.
Gates 3-9 skip cleanly (—) if their checker / source artifact is missing. With --strict
a skipped gate counts as a FAILURE (block) — use it only on a complete full-pipeline build
where every artifact (brand.config / intelligence / aesthetic / screen-inventory / edge-cases)
sits beside the prototype; on a partial run --strict will block on the legitimately-absent ones.
 10. Render structure (track E, RENDER-OPTIONAL) — renders the built page (out/, Playwright) at
     mobile+desktop and checks control-height parity / surface consistency / phone-lock. Needs a
     build + a browser, so it is ALWAYS evaluated outside --strict: a skip never blocks (even in
     strict mode), only a real render failure blocks. Pass --desktop-role to make phone-lock a block.

By default it audits the GENERATED surface only — `components/ui` (vendored shadcn primitives),
any `docs/` dir (DS demos + these reports), and node_modules/.next/out are auto-excluded, so you
can point it at the whole prototype without it tripping over vendored code. Use --include-vendored
to audit everything.

Usage:
  python3 audit_prototype.py <prototype_dir> [--a11y AA|AAA] [--scan app,components,lib]
                             [--include-vendored] [--strict] [--report path.md]
                             [--theme brand.config.json] [--intel intelligence.json]
                             [--screens screen-inventory.json] [--edges edge-cases.json]
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

# remote-font @import checker (Turbopack dev 500 trap)
_FONT_CHECK = HERE / "lint_font_imports.py"

# theme-fidelity checker (did the committed Step 2.6 identity theme actually get applied?)
_FIDELITY_CHECK = HERE / "lint_theme_fidelity.py"

# font-fidelity checker (did the committed Step 2.6 font_sans actually get applied?)
_FONT_FIDELITY_CHECK = HERE / "lint_font_fidelity.py"

# axis-fidelity checker (did the non-colour axes — type/shape/motion — actually get applied?)
_AXIS_FIDELITY_CHECK = HERE / "lint_axis_fidelity.py"

# directive-fidelity (gate 7) + screen-coverage (gate 8) + edge-coverage (gate 9) —
# did the build honor the upstream intent?
_DIRECTIVE_CHECK = HERE / "lint_directive_fidelity.py"
_SCREEN_CHECK = HERE / "lint_screen_coverage.py"
_EDGE_CHECK = HERE / "lint_edge_coverage.py"

# gate 10 (render structure, track E) — the ONE runtime gate folded into the report. It renders the
# built page (Playwright) and checks control-height parity / surface consistency / phone-lock. Unlike
# gates 1-9 it needs a build (out/) + Playwright, so it is RENDER-OPTIONAL: it is evaluated OUTSIDE
# --strict (a skip never blocks, even in strict mode — decision D0 in the first-draft-quality proposal),
# so a machine without a browser is never blocked, but a real render failure still blocks.
_RENDER_ORCH = HERE.parent / "references" / "runtime-audit" / "scripts" / "audit_runtime.mjs"

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


_IMPORT = re.compile(r"""@import\s+["']([^"']+)["']\s*;?""")


def _read_css_with_imports(css_path, _depth=0):
    """globals.css text with LOCAL `@import "./x.css"` replaced INLINE by the imported file's
    content, so a generated brand.css carries the :root/.dark tokens the gates verify. Inline (not
    appended) preserves cascade order, so a later neutral :root in globals still wins → a regression
    is still caught. Package specifiers (@scope/…, bare names) are LEFT AS-IS — the DS neutral base
    is never pulled in, so a prototype that never applied the theme still fails. One level, depth-guarded."""
    css_path = Path(css_path)
    try:
        text = css_path.read_text(errors="ignore")
    except OSError:
        return ""
    if _depth > 3:
        return text

    def _sub(m):
        spec = m.group(1)
        if not spec.startswith("."):   # local relative import only (never node_modules/DS package)
            return m.group(0)
        p = (css_path.parent / spec).resolve()
        return _read_css_with_imports(p, _depth + 1) if p.is_file() else m.group(0)

    return _IMPORT.sub(_sub, text)


def _parse_blocks(css_text):
    """Return {block_name: {token: hex}} for :root and .dark. MERGES every matching block (a theme
    may split tokens across globals.css + a generated brand.css); later definitions win (cascade)."""
    blocks = {}
    for name, sel in (("light", r":root"), ("dark", r"\.dark")):
        toks = {}
        for m in re.finditer(sel + r"\s*\{(.*?)\}", css_text, re.S):
            for d in _DEF.finditer(m.group(1)):
                hexv = _to_hex(d.group(2))
                if hexv:
                    toks[d.group(1).lower()] = hexv
        if toks:
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


# ── gate 5: font loading — no remote-font @import (Turbopack dev 500 trap) ──────
def font_gate(proto, scan_dirs, include_vendored):
    targets = _collect_targets(proto, scan_dirs, include_vendored)
    if not targets or not _FONT_CHECK.is_file():
        return None, "skipped (no targets or checker missing)"
    proc = subprocess.run([sys.executable, str(_FONT_CHECK), *targets],
                          capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout.strip()


# ── gate 6: theme fidelity — committed Step 2.6 theme must be applied in globals.css ──
def _find_theme(proto, explicit=None):
    """The committed theme json. Explicit --theme wins; else the canonical brand.config.json
    written by Step 2.6 right beside the prototype (output/brand.config.json → proto.parent).
    Deliberately narrow (brand.config.json only, no cwd walk) so an unrelated theme file in a
    sibling/temp dir can't bind to the wrong prototype."""
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for base in (proto.parent, proto):
        c = base / "brand.config.json"
        if c.is_file():
            return c
    return None


def fidelity_gate(proto, theme_path=None):
    css = proto / "app" / "globals.css"
    theme = _find_theme(proto, theme_path)
    if not theme or not css.is_file() or not _FIDELITY_CHECK.is_file():
        return None, "skipped (no brand.config.json beside prototype, or checker missing)"
    proc = subprocess.run([sys.executable, str(_FIDELITY_CHECK), str(css), str(theme)],
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout.strip() or proc.stderr.strip())


# ── gates 7 + 8: did the build honor the upstream intent? (auto-discover the artifact) ──
def _find_artifact(proto, names, explicit=None):
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for base in (proto.parent, proto):
        for name in names:
            c = base / name
            if c.is_file():
                return c
    return None


def directive_gate(proto, intel_path=None):
    intel = _find_artifact(proto, ("intelligence.json",), intel_path)
    if not intel or not _DIRECTIVE_CHECK.is_file():
        return None, "skipped (no intelligence.json beside prototype, or checker missing)"
    proc = subprocess.run([sys.executable, str(_DIRECTIVE_CHECK), str(proto), str(intel)],
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout.strip() or proc.stderr.strip())


def screen_gate(proto, screens_path=None):
    inv = _find_artifact(proto, ("screen-inventory.json",), screens_path)
    if not inv or not _SCREEN_CHECK.is_file():
        return None, "skipped (no screen-inventory.json beside prototype, or checker missing)"
    proc = subprocess.run([sys.executable, str(_SCREEN_CHECK), str(proto), str(inv)],
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout.strip() or proc.stderr.strip())


def font_fidelity_gate(proto, theme_path=None):
    theme = _find_theme(proto, theme_path)
    if not theme or not _FONT_FIDELITY_CHECK.is_file():
        return None, "skipped (no brand.config.json/aesthetic.json beside prototype, or checker missing)"
    proc = subprocess.run([sys.executable, str(_FONT_FIDELITY_CHECK), str(proto), str(theme)],
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout.strip() or proc.stderr.strip())


def axis_fidelity_gate(proto, aes_path=None):
    aes = _find_artifact(proto, ("aesthetic.json",), aes_path)
    css = proto / "app" / "globals.css"
    if not aes or not css.is_file() or not _AXIS_FIDELITY_CHECK.is_file():
        return None, "skipped (no aesthetic.json beside prototype / no globals.css, or checker missing)"
    proc = subprocess.run([sys.executable, str(_AXIS_FIDELITY_CHECK), str(css), str(aes)],
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout.strip() or proc.stderr.strip())


def edge_gate(proto, edges_path=None, screens_path=None):
    ec = _find_artifact(proto, ("edge-cases.json",), edges_path)
    if not ec or not _EDGE_CHECK.is_file():
        return None, "skipped (no edge-cases.json beside prototype, or checker missing)"
    inv = _find_artifact(proto, ("screen-inventory.json",), screens_path)
    cmd = [sys.executable, str(_EDGE_CHECK), str(proto), str(ec)]
    if inv:  # lets each edge resolve to its screen's route; without it the check is whole-app
        cmd.append(str(inv))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout.strip() or proc.stderr.strip())


# ── gate 10: render structure (track E) — RENDER-OPTIONAL, always outside --strict (D0) ──
def _find_built_html(proto):
    """A built, renderable entry beside the prototype (Next static export → out/index.html), or None.
    The render gate needs a build; without one there's nothing to render, so it skips (never a failure)."""
    for cand in (proto / "out" / "index.html", proto / "out" / "index.htm"):
        if cand.is_file():
            return cand
    # any exported route (out/<page>/index.html) as a fallback entry
    out = proto / "out"
    if out.is_dir():
        for p in sorted(out.rglob("index.html")):
            return p
    return None


def _find_render_orch(proto):
    """The runtime orchestrator to run. PREFER the copy inside the prototype (proto/scripts/runtime/…):
    ESM `import('playwright')` resolves from the SCRIPT's own location, so only a copy that sits beside
    the prototype's node_modules can load Playwright (this is the README's enable step). The vendored
    skill copy is a last resort — it self-skips when Playwright isn't up-tree, which is the honest result."""
    local = proto / "scripts" / "runtime" / "audit_runtime.mjs"
    if local.is_file():
        return local
    return _RENDER_ORCH if _RENDER_ORCH.is_file() else None


def render_gate(proto, desktop_role=False):
    """Spawn the runtime orchestrator on the built page (cwd=proto). Returns None (skipped) when there's
    no build, no node, no in-prototype orchestrator, or Playwright is absent — the orchestrator prints
    SKIPPED and exits 0, which we map to skipped, not a pass. Only a real render failure returns False."""
    import shutil
    html = _find_built_html(proto)
    orch = _find_render_orch(proto)
    if not html or not orch or not shutil.which("node"):
        return None, ("skipped (needs a build + the runtime scripts in the prototype: `npm run build`, "
                      "then copy references/runtime-audit/scripts/*.mjs → prototype/scripts/runtime/)")
    cmd = ["node", str(orch), str(html)]
    if desktop_role:
        cmd.append("--desktop-role")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(proto))
    out = f"{proc.stdout}{proc.stderr}".strip()
    # every runtime sub-gate SKIPPED (Playwright not installed) → treat as skipped, not a pass
    if "all gates SKIPPED" in out or ("SKIPPED" in out and "PASS" not in out and "FAIL" not in out):
        return None, "skipped (Playwright not installed — npm i -D playwright && npx playwright install chromium)"
    return proc.returncode == 0, out


# ── gate 2: WCAG contrast over the actual theme ───────────────────────────────
def contrast_gate(css_path, a11y):
    text = _read_css_with_imports(css_path)   # follow a local @import "./brand.css" (DS-native theming)
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


# ── gate-result helpers (a gate is True=pass / False=fail / None=skipped) ──────
def _ok(v, strict):
    """Does a gate result count as passing? A skipped gate (None) passes unless --strict."""
    if v is None:
        return not strict
    return v is True


def _badge(v, strict):
    """Verdict glyph for a gate result, honoring --strict for skipped gates."""
    if v is None:
        return "🔴" if strict else "—"
    return "🟢" if v else "🔴"


def _word(v, strict):
    """Console word for a gate result, honoring --strict for skipped gates."""
    if v is None:
        return "FAIL" if strict else "—"
    return "PASS" if v else "FAIL"


# ── gate 6: FIDELITY FAMILY — did the committed Step 2.6 direction actually get applied? ──
# theme colours + font + non-colour axes are one concern ("is the chosen aesthetic in the build, or
# did it regress to the scaffold default?"), so they report as ONE gate with three sub-checks. Each
# sub keeps its own linter (lint_theme_fidelity / lint_font_fidelity / lint_axis_fidelity) — this only
# combines their verdicts. Family = FAIL if any sub fails; PASS if any ran and none failed; — if all skip.
def fidelity_family_gate(proto, theme_path, aes_path):
    subs = [
        ("theme", *fidelity_gate(proto, theme_path)),
        ("font", *font_fidelity_gate(proto, theme_path)),
        ("axis", *axis_fidelity_gate(proto, aes_path)),
    ]
    if any(v is False for _, v, _ in subs):
        fam = False
    elif all(v is None for _, v, _ in subs):
        fam = None
    else:
        fam = True
    lines = []
    for name, v, o in subs:
        tag = "—" if v is None else ("PASS" if v else "FAIL")
        detail = (o or "").strip().replace("\n", " ")
        lines.append(f"[{name:5}] {tag} — {detail}" if detail else f"[{name:5}] {tag}")
    return fam, "\n".join(lines)


def main(argv):
    args, a11y, scan, report, include_vendored, theme = [], "AA", ["app", "components", "lib"], None, False, None
    strict = False
    intel, screens_path, edges_path, aes_path = None, None, None, None
    desktop_role = False
    i = 0
    while i < len(argv):
        if argv[i] == "--a11y" and i + 1 < len(argv):
            a11y = argv[i + 1].replace("AA_plus", "AAA").upper(); i += 2
        elif argv[i] == "--scan" and i + 1 < len(argv):
            scan = argv[i + 1].split(","); i += 2
        elif argv[i] == "--include-vendored":
            include_vendored = True; i += 1
        elif argv[i] == "--strict":
            strict = True; i += 1
        elif argv[i] == "--report" and i + 1 < len(argv):
            report = argv[i + 1]; i += 2
        elif argv[i] == "--theme" and i + 1 < len(argv):
            theme = argv[i + 1]; i += 2
        elif argv[i] == "--intel" and i + 1 < len(argv):
            intel = argv[i + 1]; i += 2
        elif argv[i] == "--screens" and i + 1 < len(argv):
            screens_path = argv[i + 1]; i += 2
        elif argv[i] == "--edges" and i + 1 < len(argv):
            edges_path = argv[i + 1]; i += 2
        elif argv[i] == "--aesthetic" and i + 1 < len(argv):
            aes_path = argv[i + 1]; i += 2
        elif argv[i] == "--desktop-role":
            desktop_role = True; i += 1
        else:
            args.append(argv[i]); i += 1
    if not args:
        print(__doc__); return 2
    proto = Path(args[0])
    if not proto.is_dir():
        print(f"[audit_prototype] ✗ prototype dir not found: {proto}", file=sys.stderr); return 1

    out = [f"# Audit Report — Step 4.7 (a11y target: {a11y}{', strict' if strict else ''})", ""]

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

    # gate 5 (font loading: no remote-font @import — Turbopack dev 500 trap)
    font_ok, font_out = font_gate(proto, scan, include_vendored)
    out += ["## 5. Font loading (Turbopack-safe — no remote @import)",
            "```", font_out or "(skipped)", "```", ""]

    # gate 6 (FIDELITY FAMILY: committed Step 2.6 theme + font + non-colour axes all applied)
    fidelity_ok, fidelity_out = fidelity_family_gate(proto, theme, aes_path)
    out += ["## 6. Fidelity family (Step 2.6 applied: theme colours + font + non-colour axes)",
            "```", fidelity_out or "(skipped)", "```", ""]

    # gate 7 (directive fidelity: build honors design_directives — safeguard/guidance)
    directive_ok, directive_out = directive_gate(proto, intel)
    out += ["## 7. Directive fidelity (design_directives honored: safeguards, guidance)",
            "```", directive_out or "(skipped)", "```", ""]

    # gate 8 (screen coverage: every Must screen in the inventory was actually built)
    screen_ok, screen_out = screen_gate(proto, screens_path)
    out += ["## 8. Screen coverage (every Must screen built with its declared states)",
            "```", screen_out or "(skipped)", "```", ""]

    # gate 9 (edge-case coverage: every Must edge case is handled in the build)
    edge_ok, edge_out = edge_gate(proto, edges_path, screens_path)
    out += ["## 9. Edge-case coverage (every Must edge case handled in its screen)",
            "```", edge_out or "(skipped)", "```", ""]

    # gate 10 (render structure, track E) — RENDER-OPTIONAL: evaluated outside --strict (D0).
    # Auto-derive --desktop-role from intelligence.json's responsive rollup (track A → E): a build
    # that serves a desktop role must not be phone-locked, so phone-lock becomes a hard failure.
    if not desktop_role:
        intel_art = _find_artifact(proto, ("intelligence.json",), intel)
        if intel_art:
            try:
                import json as _json
                _resp = (_json.loads(intel_art.read_text()).get("design_directives", {}) or {}).get("responsive", {})
                if (_resp or {}).get("target") in ("desktop", "both"):
                    desktop_role = True
            except (OSError, ValueError):
                pass
    render_ok, render_out = render_gate(proto, desktop_role)
    out += ["## 10. Render structure (control parity / surface / phone-lock — needs a build + Playwright)",
            "```", render_out or "(skipped)", "```", ""]

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

    # gates that may be None (skipped) pass unless --strict; lint_ok/contrast_ok are never None.
    # fidelity_ok is the FAMILY verdict (theme+font+axis combined); font/axis are no longer separate.
    skippable = (emoji_ok, contract_ok, font_ok, fidelity_ok, directive_ok,
                 screen_ok, edge_ok)
    # gate 10 (render) is RENDER-OPTIONAL: always evaluated with strict=False, so a skip never blocks
    # even under --strict (needs a build + Playwright); only a real render failure blocks. (D0)
    blocked = not (lint_ok and contrast_ok and all(_ok(v, strict) for v in skippable)
                   and _ok(render_ok, False))
    verdict = "🔴 BLOCKED" if blocked else "🟢 PASS"
    if strict:
        verdict += " (strict — skipped gates count as failures)"
    out += ["## Verdict", f"- Token compliance: {'🟢' if lint_ok else '🔴'}",
            f"- WCAG {a11y} contrast: {'🟢' if contrast_ok else '🔴'}",
            f"- UX copy (no emoji/dash): {_badge(emoji_ok, strict)}",
            f"- Component contracts: {_badge(contract_ok, strict)}",
            f"- Font loading (no remote @import): {_badge(font_ok, strict)}",
            f"- Fidelity family (theme + font + axes applied): {_badge(fidelity_ok, strict)}",
            f"- Directive fidelity (safeguards/guidance): {_badge(directive_ok, strict)}",
            f"- Screen coverage (Must screens built): {_badge(screen_ok, strict)}",
            f"- Edge-case coverage (Must edges handled): {_badge(edge_ok, strict)}",
            f"- Render structure (control parity/surface/phone-lock): {_badge(render_ok, False)}",
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
          f"copy={_word(emoji_ok, strict)} · "
          f"contracts={_word(contract_ok, strict)} · "
          f"font={_word(font_ok, strict)} · "
          f"fidelity={_word(fidelity_ok, strict)} · "
          f"directive={_word(directive_ok, strict)} · "
          f"screens={_word(screen_ok, strict)} · "
          f"edges={_word(edge_ok, strict)} · "
          f"render={_word(render_ok, False)}")
    if report:
        print(f"  → {report}")
    for f in cfails:
        print(f"  • {f}", file=sys.stderr)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
