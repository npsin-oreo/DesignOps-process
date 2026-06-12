#!/usr/bin/env python3
"""
validate_flows.py — gate for Step C (User Flows).

Usage: validate_flows.py <flows.json> [intelligence.json] [brief.json]
Exit 0 = valid, Exit 1 = invalid. Zero-dependency, mirrors validate_brief.py.

flows.json refines the brief's raw user_flows using design_directives (navigation_model,
safeguard_level, mandatory_flows). This gate checks structure + that the refinement is
consistent with intelligence.json and the brief.
"""

import json
import sys

REQUIRED_TOP_KEYS = ["meta", "navigation_model", "flows"]
NAV_MODEL = {"single", "wizard", "hub_spoke", "workspace"}


def _load(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error in {path}: {e}"
    except FileNotFoundError:
        return None, f"file not found: {path}"


def validate(flows_path, intel_path=None, brief_path=None):
    errors, warnings = [], []
    d, err = _load(flows_path)
    if err:
        return [err], []

    intel = brief = None
    if intel_path:
        intel, e = _load(intel_path)
        if e:
            warnings.append(e + " — skipping intelligence checks")
    if brief_path:
        brief, e = _load(brief_path)
        if e:
            warnings.append(e + " — skipping brief checks")

    for k in REQUIRED_TOP_KEYS:
        if k not in d:
            errors.append(f"missing top-level key: '{k}'")
    if errors:
        return errors, warnings

    if d["navigation_model"] not in NAV_MODEL:
        errors.append(f"navigation_model must be one of {sorted(NAV_MODEL)} (got: {d['navigation_model']!r})")

    flows = d["flows"]
    if not isinstance(flows, list) or not flows:
        errors.append("flows must have at least 1 entry")
        return errors, warnings

    # reference sets from upstream artifacts
    ut_ids = {u.get("id") for u in (intel or {}).get("user_types", [])} if intel else None
    goal_ids = {g.get("id") for g in (intel or {}).get("user_goals", [])} if intel else None
    brief_flow_ids = {fl.get("id") for fl in (brief or {}).get("user_flows", [])} if brief else None

    flow_ids = set()
    for i, fl in enumerate(flows):
        fid = fl.get("id", "")
        if not fid or fid in flow_ids:
            errors.append(f"flows[{i}].id missing or duplicate ('{fid}')")
        else:
            flow_ids.add(fid)
        if not fl.get("name"):
            errors.append(f"flows[{i}].name must not be empty")
        steps = fl.get("steps", [])
        if not isinstance(steps, list) or not steps:
            errors.append(f"flows[{i}].steps must be a non-empty array")
        else:
            for j, s in enumerate(steps):
                if not s.get("action"):
                    errors.append(f"flows[{i}].steps[{j}].action must not be empty")
        if ut_ids is not None and fl.get("user_type_ref") not in ut_ids:
            errors.append(f"flows[{i}].user_type_ref '{fl.get('user_type_ref')}' not in intelligence.user_types")
        if goal_ids is not None and fl.get("goal_ref") not in goal_ids:
            errors.append(f"flows[{i}].goal_ref '{fl.get('goal_ref')}' not in intelligence.user_goals")
        # source_flow_ref may be null for injected (mandatory) flows
        src = fl.get("source_flow_ref")
        if brief_flow_ids is not None and src and src not in brief_flow_ids:
            errors.append(f"flows[{i}].source_flow_ref '{src}' not in brief.user_flows")

    # navigation_model must echo the directive
    if intel is not None:
        dz = intel.get("design_directives", {})
        if dz.get("navigation_model") and d["navigation_model"] != dz["navigation_model"]:
            errors.append(f"navigation_model ({d['navigation_model']}) must equal design_directives.navigation_model ({dz['navigation_model']})")
        # every mandatory_flow directive must appear as an injected flow
        directed = set(dz.get("mandatory_flows", []))
        present = {m.get("name") for m in d.get("mandatory_flows", [])}
        present_names = present | {fl.get("name", "").lower() for fl in flows}
        for mf in directed:
            if mf not in present and not any(mf in str(p).lower() for p in present_names):
                errors.append(f"design_directives mandatory_flow '{mf}' has no corresponding flow (must be injected)")

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_flows.py <flows.json> [intelligence.json] [brief.json]", file=sys.stderr)
        sys.exit(1)
    errors, warnings = validate(*sys.argv[1:4])
    if errors:
        print(f"[validate_flows] ✗ Invalid — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        d = json.load(f)
    print("[validate_flows] ✓ Valid")
    print(f"  Navigation : {d.get('navigation_model')}")
    print(f"  Flows      : {len(d.get('flows', []))} · mandatory/injected: {len(d.get('mandatory_flows', []))}")
    for w in warnings:
        print(f"  ⚠ {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
