#!/usr/bin/env python3
"""
validate_screens.py — gate for Step D (Screen Inventory).

Usage: validate_screens.py <screen-inventory.json> [flows.json]
Exit 0 = valid, Exit 1 = invalid. Zero-dependency, mirrors validate_brief.py.

Enforces flow→screen coverage (every flow has at least one screen) and screen→flow
traceability, plus structural enums.
"""

import json
import sys

REQUIRED_TOP_KEYS = ["meta", "screens"]
PRIORITY = {"Must", "Should", "Could"}
LAYOUT = {"card", "table", "dashboard", "form", "wizard_step", "list", "detail", "hub"}
GAP_STATUS = {"missing", "partial"}


def _load(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error in {path}: {e}"
    except FileNotFoundError:
        return None, f"file not found: {path}"


def validate(screens_path, flows_path=None):
    errors, warnings = [], []
    d, err = _load(screens_path)
    if err:
        return [err], []

    flows = None
    if flows_path:
        flows, e = _load(flows_path)
        if e:
            warnings.append(e + " — skipping coverage checks")

    for k in REQUIRED_TOP_KEYS:
        if k not in d:
            errors.append(f"missing top-level key: '{k}'")
    if errors:
        return errors, warnings

    screens = d["screens"]
    if not isinstance(screens, list) or not screens:
        errors.append("screens must have at least 1 entry")
        return errors, warnings

    flow_ids = {fl.get("id") for fl in (flows or {}).get("flows", [])} if flows else None
    covered = set()
    sc_ids = set()

    for i, s in enumerate(screens):
        sid = s.get("id", "")
        if not sid or sid in sc_ids:
            errors.append(f"screens[{i}].id missing or duplicate ('{sid}')")
        else:
            sc_ids.add(sid)
        if not s.get("name"):
            errors.append(f"screens[{i}].name must not be empty")
        if s.get("priority") not in PRIORITY:
            errors.append(f"screens[{i}].priority must be one of {sorted(PRIORITY)} (got: {s.get('priority')!r})")
        if s.get("layout_primitive") not in LAYOUT:
            errors.append(f"screens[{i}].layout_primitive must be one of {sorted(LAYOUT)} (got: {s.get('layout_primitive')!r})")
        refs = s.get("flow_refs", [])
        if not isinstance(refs, list) or not refs:
            errors.append(f"screens[{i}].flow_refs must be a non-empty array")
        else:
            for r in refs:
                if flow_ids is not None and r not in flow_ids:
                    errors.append(f"screens[{i}].flow_refs '{r}' not in flows.json")
                covered.add(r)
        # a screen must declare components OR explicit gaps (not be empty)
        if not s.get("components") and not s.get("gaps"):
            errors.append(f"screens[{i}] has neither components nor gaps (empty screen)")
        for j, g in enumerate(s.get("gaps", [])):
            if g.get("status") not in GAP_STATUS:
                errors.append(f"screens[{i}].gaps[{j}].status must be one of {sorted(GAP_STATUS)} (got: {g.get('status')!r})")

    # coverage: every flow must have at least one screen
    if flow_ids is not None:
        uncovered = sorted(flow_ids - covered)
        if uncovered:
            errors.append(f"flows with no screen (coverage gap): {uncovered}")

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_screens.py <screen-inventory.json> [flows.json]", file=sys.stderr)
        sys.exit(1)
    errors, warnings = validate(*sys.argv[1:3])
    if errors:
        print(f"[validate_screens] ✗ Invalid — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        d = json.load(f)
    screens = d.get("screens", [])
    gaps = sum(len(s.get("gaps", [])) for s in screens)
    by_prio = {p: sum(1 for s in screens if s.get("priority") == p) for p in PRIORITY}
    print("[validate_screens] ✓ Valid")
    print(f"  Screens    : {len(screens)} ({by_prio['Must']} Must / {by_prio['Should']} Should / {by_prio['Could']} Could)")
    print(f"  Gaps       : {gaps}")
    for w in warnings:
        print(f"  ⚠ {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
