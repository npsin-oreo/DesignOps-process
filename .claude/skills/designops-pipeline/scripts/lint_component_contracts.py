#!/usr/bin/env python3
"""lint_component_contracts.py — gate 4 of the Step 4.7 audit.

Enforces the component USAGE CONTRACTS documented for the design system
(Button / Dialog / Field & Input) as runnable checks, not agent judgment.
Mirrors the Storybook "Docs/*" pages — see references/component-contracts.md.

It splits findings into:
  • HARD violations  — high-precision a11y/usage breaks → counted, exit 1.
  • ADVISORY notices — fuzzier heuristics → printed, never fail the gate.

Rules (HARD):
  - Button: an icon-only button (`size="icon"`) must carry an accessible name
    (aria-label / aria-labelledby / title / an sr-only child).
  - Dialog: every <DialogContent> / <AlertDialogContent> must contain a
    <DialogTitle> / <AlertDialogTitle> (backs aria-labelledby; Radix a11y).
  - Field: an <Input id="x"> with no aria-label* must have a matching
    <FieldLabel htmlFor="x"> / <Label htmlFor="x"> (programmatic label).

Rules (ADVISORY):
  - Dialog without a <DialogDescription>.
  - More than one primary (default-variant) <Button> in a file (one per view).
  - Delete/remove-style button not using variant="destructive".
  - <Field> containing <FieldError> but no aria-invalid on its input.
  - <Input> with neither id nor aria-label (possibly unlabeled / label-wrapped).
  - A <Dialog> nested inside another <Dialog>.

Escape hatch: put `ds-allow-contract` on the element's opening line to skip it.

Usage:
  python3 lint_component_contracts.py app components        # dirs
  python3 lint_component_contracts.py Login.tsx             # files
Exit 0 = clean (advisories allowed), 1 = HARD violation(s) found.
"""
import re
import sys
from pathlib import Path

CODE_EXT = {".tsx", ".jsx"}
ALLOW = "ds-allow-contract"

SIZE_ICON = re.compile(r"""size\s*=\s*\{?\s*["']icon["']""")
HAS_NAME = re.compile(r"aria-label\b|aria-labelledby\b|\btitle\s*=|sr-only")
VARIANT = re.compile(r"""variant\s*=\s*\{?\s*["']([a-z]+)["']""")
ID_ATTR = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""")
ARIA_NAME_ATTR = re.compile(r"aria-label\b|aria-labelledby\b")
HTMLFOR = re.compile(r"""htmlFor\s*=\s*["']([^"']+)["']""")
DELETEISH = re.compile(r"\b(delete|remove|discard|trash)\b", re.I)


def neutralize(text):
    """Blank out JSX operators that contain < or > so tag scanning is reliable.
    Length-preserving (2 chars → 2 spaces), so indices/line numbers are unchanged."""
    for op in ("=>", ">=", "<=", "&&"):
        text = text.replace(op, "  ")
    return text


def element_text(scan, start):
    """Full source of the JSX element opening at `start` (incl. children), and its open tag."""
    gt = scan.find(">", start)
    if gt == -1:
        return scan[start:start + 200], scan[start:start + 200]
    open_tag = scan[start:gt + 1]
    if open_tag.rstrip().endswith("/>"):
        return open_tag, open_tag
    name = re.match(r"<(\w+)", open_tag)
    if not name:
        return open_tag, open_tag
    name = name.group(1)
    open_re = re.compile(rf"<{name}\b")
    close_re = re.compile(rf"</{name}>")
    depth, pos = 1, gt + 1
    while pos < len(scan):
        no = open_re.search(scan, pos)
        nc = close_re.search(scan, pos)
        if nc is None:
            break
        if no and no.start() < nc.start():
            depth += 1
            pos = no.end()
        else:
            depth -= 1
            pos = nc.end()
            if depth == 0:
                return scan[start:pos], open_tag
    return open_tag, open_tag


def line_of(scan, idx):
    return scan.count("\n", 0, idx) + 1


def line_text(scan, idx):
    """The source line containing idx (for the allow-comment check)."""
    s = scan.rfind("\n", 0, idx) + 1
    e = scan.find("\n", idx)
    return scan[s:e if e != -1 else len(scan)]


def lint_file(path):
    """Return (hard, advisory) lists of (lineno, message)."""
    try:
        text = Path(path).read_text()
    except (UnicodeDecodeError, OSError):
        return [], []
    scan = neutralize(text)
    hard, adv = [], []

    def skipped(start):
        return ALLOW in line_text(scan, start)

    # ── Button ────────────────────────────────────────────────────────────────
    primary_count = 0
    for m in re.finditer(r"<Button\b", scan):
        if skipped(m.start()):
            continue
        el, open_tag = element_text(scan, m.start())
        ln = line_of(scan, m.start())
        if SIZE_ICON.search(open_tag) and not HAS_NAME.search(el):
            hard.append((ln, "icon-only <Button size=\"icon\"> has no accessible name "
                             "(add aria-label / an sr-only child)"))
        var = VARIANT.search(open_tag)
        variant = var.group(1) if var else "default"
        if variant == "default":
            primary_count += 1
        if DELETEISH.search(el) and variant != "destructive":
            adv.append((ln, f"destructive-looking <Button> uses variant=\"{variant}\" "
                            "— irreversible actions should use variant=\"destructive\""))
    if primary_count > 1:
        adv.append((1, f"{primary_count} primary (default-variant) <Button>s in this file "
                       "— keep one primary action per view, step the rest down"))

    # ── Dialog / AlertDialog ────────────────────────────────────────────────────
    for content, title, desc in (
        ("DialogContent", "DialogTitle", "DialogDescription"),
        ("AlertDialogContent", "AlertDialogTitle", "AlertDialogDescription"),
    ):
        for m in re.finditer(rf"<{content}\b", scan):
            if skipped(m.start()):
                continue
            el, _ = element_text(scan, m.start())
            ln = line_of(scan, m.start())
            if title not in el:
                hard.append((ln, f"<{content}> is missing <{title}> "
                                f"(required for aria-labelledby / screen-reader title)"))
            if desc not in el:
                adv.append((ln, f"<{content}> has no <{desc}> "
                               "(recommended for aria-describedby)"))

    # nested <Dialog> inside <Dialog>
    for m in re.finditer(r"<Dialog\b", scan):
        if skipped(m.start()):
            continue
        el, _ = element_text(scan, m.start())
        if re.search(r"<Dialog\b", el[1:]):
            adv.append((line_of(scan, m.start()),
                        "nested <Dialog> detected — don't stack modals"))

    # ── DS gotchas (track D — see references/component-notes.json) ───────────────
    # NativeSelect: className routes to the WRAPPER (data-slot=native-select-wrapper); the inner
    # <select data-slot=native-select> is hardcoded h-8, so a height utility here silently no-ops.
    for m in re.finditer(r"<NativeSelect\b", scan):
        if skipped(m.start()):
            continue
        _, open_tag = element_text(scan, m.start())
        if re.search(r"""className\s*=\s*["'][^"']*(?<![\w-])(?:h-\S+|min-h-\S+|size-\S+)""", open_tag):
            hard.append((line_of(scan, m.start()),
                         "<NativeSelect> className sets a height (h-*/min-h-*/size-*) but it routes to the "
                         "WRAPPER — the inner <select> stays h-8 and the height no-ops. Set control height via "
                         "the [data-slot=native-select] rule in globals.css (the scaffold ships one), not here"))

    # A disabled control inside a modal trigger → the trigger can't be clicked, so the dialog never
    # opens. Guard the ACTION inside the dialog (or conditionally render), don't disable the trigger.
    for trig in ("AlertDialogTrigger", "DialogTrigger"):
        for m in re.finditer(rf"<{trig}\b", scan):
            if skipped(m.start()):
                continue
            el, _ = element_text(scan, m.start())
            if re.search(r"(?<![\w-])disabled\b(?!\s*=\s*\{?\s*false)", el):
                adv.append((line_of(scan, m.start()),
                            f"<{trig}> wraps a disabled control — a disabled trigger can't be clicked, so the "
                            "dialog may never open; guard the action inside the dialog instead"))

    # ── Field & Input ──────────────────────────────────────────────────────────
    htmlfors = set(HTMLFOR.findall(scan))
    for m in re.finditer(r"<Input\b", scan):
        if skipped(m.start()):
            continue
        _, open_tag = element_text(scan, m.start())
        ln = line_of(scan, m.start())
        has_aria = ARIA_NAME_ATTR.search(open_tag)
        idm = ID_ATTR.search(open_tag)
        if idm:
            if not has_aria and idm.group(1) not in htmlfors:
                hard.append((ln, f"<Input id=\"{idm.group(1)}\"> has no matching "
                                "<FieldLabel htmlFor> / <Label htmlFor> and no aria-label"))
        elif not has_aria:
            adv.append((ln, "<Input> has neither id nor aria-label — confirm it is labelled "
                           "(FieldLabel htmlFor / label-wrapped)"))

    # FieldError present but no aria-invalid in the same Field
    for m in re.finditer(r"<Field\b", scan):
        if skipped(m.start()):
            continue
        el, _ = element_text(scan, m.start())
        if "FieldError" in el and "aria-invalid" not in el:
            adv.append((line_of(scan, m.start()),
                        "<Field> renders <FieldError> but no aria-invalid on its input "
                        "(error not announced)"))

    return hard, adv


def iter_files(paths):
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in pp.rglob("*"):
                if f.suffix in CODE_EXT and "node_modules" not in f.parts:
                    yield f
        elif pp.is_file() and pp.suffix in CODE_EXT:
            yield pp


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    files = list(iter_files(argv))
    hard_total = adv_total = 0
    for f in files:
        hard, adv = lint_file(f)
        for ln, msg in sorted(hard):
            print(f"{f}:{ln}: [contract] {msg}")
            hard_total += 1
        for ln, msg in sorted(adv):
            print(f"{f}:{ln}: [advisory] {msg}")
            adv_total += 1

    print(f"\nScanned {len(files)} file(s). {hard_total} contract violation(s), "
          f"{adv_total} advisory note(s).")
    if hard_total:
        print(f"FAIL: {hard_total} component-contract violation(s). Fix each, "
              f"or add a '{ALLOW}' comment on the element for a justified exception.")
        return 1
    print("OK: no component-contract violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
