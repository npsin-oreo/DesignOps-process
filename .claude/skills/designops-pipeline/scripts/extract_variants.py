#!/usr/bin/env python3
"""extract_variants.py — read the REAL variant vocabulary out of a shadcn/cva design system.

Component contracts (references/component-contracts.md) are hand-authored only for the few
high-a11y controls. For every other component, the machine-usable part of the contract — the
variant/size/state vocabulary — is **derivable from source**, not something to invent: it's the
`variants: { … }` object in each component's `class-variance-authority` (cva) call.

This parses those blocks and emits the vocab as a Markdown table (default) or JSON, so Step 4
(which variant exists) and Step 5 Figma (variant matrices) build against the truth, and a new
component-contract starts from real values instead of guesses.

Usage:
  python3 extract_variants.py <dir-or-files...>            # Markdown table
  python3 extract_variants.py design-system/components/ui --json
Zero-dependency. Skips files without cva. Default value (from defaultVariants) is marked •.
"""
import json
import re
import sys
from pathlib import Path

CODE_EXT = {".tsx", ".jsx", ".ts", ".js"}


def destring(text):
    """Blank the CONTENTS of every VALUE string/template literal (keep delimiters + length), so
    structural scanning never trips on `:` or `,` inside a className (e.g. "hover:bg-muted",
    "[color-mix(in_oklch,…)]"). Strings used as object KEYS — a string immediately followed by
    `:`, e.g. "icon-xs": — are preserved so hyphenated variant keys survive."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            si = i
            i += 1
            while i < n and text[i] != c:
                i += 2 if text[i] == "\\" else 1
            ei = i  # closing quote (or n)
            j = ei + 1
            while j < n and text[j] in " \t\n":
                j += 1
            is_key = j < n and text[j] == ":"
            if not is_key:
                for k in range(si + 1, min(ei, n)):
                    out[k] = " "
            i = ei + 1
        else:
            i += 1
    return "".join(out)


def match_brace(s, open_idx):
    """Index just past the `}` matching the `{` at open_idx (s already destrung)."""
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(s) - 1


KEY = re.compile(r"""["']?([A-Za-z_][\w-]*)["']?\s*:""")
GROUP = re.compile(r"""([A-Za-z_]\w*)\s*:\s*\{""")


def parse_groups(block):
    """{group_name: [keys…]} from a destrung `variants:` object body."""
    groups = {}
    for gm in GROUP.finditer(block):
        gname = gm.group(1)
        ob = block.index("{", gm.start())
        cb = match_brace(block, ob)
        inner = block[ob + 1:cb]
        # keys are the `word:` pairs at the top level of this group (values are now blank strings)
        keys, depth = [], 0
        for km in re.finditer(r"[{}]|" + KEY.pattern, inner):
            tok = km.group(0)
            if tok == "{":
                depth += 1
            elif tok == "}":
                depth -= 1
            elif depth == 0 and km.group(1):
                keys.append(km.group(1))
        if keys:
            groups[gname] = keys
    return groups


def parse_defaults(scan):
    out = {}
    m = re.search(r"defaultVariants\s*:\s*\{", scan)
    if m:
        ob = scan.index("{", m.start())
        body = scan[ob + 1:match_brace(scan, ob)]
        for dm in re.finditer(r"([A-Za-z_]\w*)\s*:\s*([\w-]+)", body):
            out[dm.group(1)] = dm.group(2)
    return out


def parse_file(path):
    try:
        text = Path(path).read_text()
    except (UnicodeDecodeError, OSError):
        return None
    if "cva(" not in text:
        return None
    scan = destring(text)
    result = {}
    for vm in re.finditer(r"variants\s*:\s*\{", scan):
        ob = scan.index("{", vm.start())
        body = scan[ob + 1:match_brace(scan, ob)]
        for g, keys in parse_groups(body).items():
            result.setdefault(g, [])
            for k in keys:
                if k not in result[g]:
                    result[g].append(k)
    if not result:
        return None
    return {"variants": result, "defaults": parse_defaults(scan)}


def iter_files(paths):
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in sorted(pp.rglob("*")):
                if f.suffix in CODE_EXT and "node_modules" not in f.parts:
                    yield f
        elif pp.is_file() and pp.suffix in CODE_EXT:
            yield pp


def comp_name(path):
    return "".join(w.capitalize() for w in Path(path).stem.split("-"))


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 0

    data = {}
    for f in iter_files(args):
        parsed = parse_file(f)
        if parsed:
            data[comp_name(f)] = parsed

    if as_json:
        print(json.dumps(data, indent=2))
        return 0

    print("# Component variant vocabulary (generated)\n")
    print(f"> Auto-extracted from cva `variants:` blocks by `scripts/extract_variants.py`. "
          f"{len(data)} component(s). `•` marks the default value. Do not hand-edit — regenerate.\n")
    print("| Component | Group | Values |")
    print("|-----------|-------|--------|")
    for name in sorted(data):
        for group, keys in data[name]["variants"].items():
            dflt = data[name]["defaults"].get(group)
            vals = ", ".join((f"{k} •" if k == dflt else k) for k in keys)
            print(f"| {name} | `{group}` | {vals} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
