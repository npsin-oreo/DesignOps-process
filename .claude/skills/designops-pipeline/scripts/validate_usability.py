#!/usr/bin/env python3
"""Gate for usability.json (Step 4.8 — Usability Test Layer).

Integrity-first: the gate exists to stop a SIMULATED evaluation from being
dressed up as a real user test, and to keep severe findings actionable.

Usage:  validate_usability.py <usability.json> [research.json]
"""
import json
import sys

CONFIDENCE = {"high", "medium", "low"}
METHODS = {"heuristic", "automated", "persona_walkthrough"}
FINDING_METHOD = {"heuristic", "automated"}
FIX_PRIORITY = {"now", "next", "later"}


def _enum(val, allowed, path, errors):
    if val not in allowed:
        errors.append(f"{path}: {val!r} not in {sorted(allowed)}")


def _sev(val, path, errors):
    if not isinstance(val, int) or isinstance(val, bool) or not (0 <= val <= 4):
        errors.append(f"{path}: severity must be an int 0..4 (Nielsen), got {val!r}")
        return None
    return val


def validate(path, research_path=None):
    errors, warnings = [], []
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"cannot read {path}: {e}"], [], {}

    meta = data.get("meta", {})
    # honesty: cannot claim a real test
    if meta.get("not_real_user_testing") is not True:
        errors.append("meta.not_real_user_testing must be exactly true "
                      "(this layer is simulated — it cannot claim a real user test)")
    methods = meta.get("methods_used", [])
    if not isinstance(methods, list) or not methods:
        errors.append("meta.methods_used must be a non-empty list")
    else:
        for m in methods:
            if m not in METHODS:
                errors.append(f"meta.methods_used: {m!r} not allowed (only {sorted(METHODS)} — "
                              "no real-participant methods)")
    _enum(meta.get("overall_confidence"), CONFIDENCE, "meta.overall_confidence", errors)

    top_ids = {t.get("ref") for t in data.get("top_issues", [])}

    for i, h in enumerate(data.get("heuristic_findings", [])):
        path = f"heuristic_findings[{i}]"
        sev = _sev(h.get("severity"), path, errors)
        _enum(h.get("method"), FINDING_METHOD, f"{path}.method", errors)
        _enum(h.get("confidence"), CONFIDENCE, f"{path}.confidence", errors)
        if h.get("method") == "automated" and not h.get("evidence"):
            errors.append(f"{path}: method 'automated' requires evidence (axe rule / selector / contrast pair)")
        if sev is not None and sev >= 3:
            if not h.get("recommendation"):
                errors.append(f"{path}: severity {sev} requires a recommendation")
            if h.get("id") not in top_ids:
                errors.append(f"{path}: severity {sev} finding {h.get('id')!r} missing from top_issues")

    for i, w in enumerate(data.get("persona_walkthroughs", [])):
        path = f"persona_walkthroughs[{i}]"
        if w.get("simulated") is not True:
            errors.append(f"{path}.simulated must be true (no real participant)")
        for j, fp in enumerate(w.get("friction_points", [])):
            _sev(fp.get("severity"), f"{path}.friction_points[{j}]", errors)

    for i, t in enumerate(data.get("top_issues", [])):
        path = f"top_issues[{i}]"
        _sev(t.get("severity"), path, errors)
        _enum(t.get("fix_priority"), FIX_PRIORITY, f"{path}.fix_priority", errors)

    if not data.get("limitations"):
        errors.append("limitations must be non-empty (state that no real users were involved)")

    # optional persona ref resolution
    rref = research_path or meta.get("research_ref")
    if rref:
        try:
            with open(rref) as f:
                personas = {p.get("id") for p in json.load(f).get("personas", [])}
            for i, w in enumerate(data.get("persona_walkthroughs", [])):
                pr = w.get("persona_ref")
                if pr and pr not in personas:
                    errors.append(f"persona_walkthroughs[{i}].persona_ref {pr!r} not in {rref}")
        except (OSError, json.JSONDecodeError):
            warnings.append(f"research_ref {rref} not readable — skipped persona resolution")

    flags = {}
    if meta.get("human_validation_required") is not False:
        flags["human_validation_required"] = True
    return errors, warnings, flags


def main():
    if len(sys.argv) < 2:
        print("usage: validate_usability.py <usability.json> [research.json]")
        sys.exit(2)
    errors, warnings, flags = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for w in warnings:
        print(f"  ⚠ {w}")
    if errors:
        print(f"\n✗ usability.json INVALID — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print(f"✓ usability.json valid{' (flags: ' + ','.join(flags) + ')' if flags else ''}")
    sys.exit(0)


if __name__ == "__main__":
    main()
