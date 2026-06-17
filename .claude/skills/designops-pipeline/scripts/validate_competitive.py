#!/usr/bin/env python3
"""Gate for competitive.json (Step 2.4 — Competitive Analysis Layer).

Schema + ref resolution + honesty invariants (no fabricated competitor evidence)
+ domain rules (justify breaking conventions / skipping table-stakes).

Usage:  validate_competitive.py <competitive.json> [brief.json]
"""
import json
import sys

EVIDENCE_MODE = {"inferred", "hybrid", "evidence_backed"}
CONFIDENCE = {"high", "medium", "low"}
SOURCE = {"inferred", "evidence"}
CTYPE = {"direct", "indirect", "aspirational"}
PREVALENCE = {"table_stakes", "common", "differentiator", "rare"}
STANCE = {"match", "exceed", "skip", "defer"}
CONVENTION = {"follow", "break"}
DEFENSIBILITY = {"low", "med", "high"}


def _enum(val, allowed, path, errors):
    if val not in allowed:
        errors.append(f"{path}: {val!r} not in {sorted(allowed)}")


def validate(path, brief_path=None):
    errors, warnings = [], []
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"cannot read {path}: {e}"], [], {}

    meta = data.get("meta", {})
    mode = meta.get("evidence_mode")
    _enum(mode, EVIDENCE_MODE, "meta.evidence_mode", errors)
    inputs = meta.get("inputs_provided", [])
    if not isinstance(inputs, list):
        errors.append("meta.inputs_provided must be a list")
        inputs = []
    inputs_set = set(inputs)
    _enum(meta.get("overall_confidence"), CONFIDENCE, "meta.overall_confidence", errors)
    no_inputs = len(inputs_set) == 0
    if no_inputs and mode != "inferred":
        errors.append("meta.inputs_provided is empty but evidence_mode != 'inferred'")

    def honesty(item, path):
        src = item.get("source")
        _enum(src, SOURCE, f"{path}.source", errors)
        conf = item.get("confidence")
        _enum(conf, CONFIDENCE, f"{path}.confidence", errors)
        for ref in item.get("evidence", []):
            if src == "evidence" and ref not in inputs_set:
                errors.append(f"{path}: evidence {ref!r} not in meta.inputs_provided (fabricated)")
        if src == "evidence" and not item.get("evidence"):
            errors.append(f"{path}: source 'evidence' but evidence is empty")
        if src == "inferred" and conf == "high":
            errors.append(f"{path}: inferred items may not claim confidence 'high'")
        if no_inputs and src and src != "inferred":
            errors.append(f"{path}: no inputs provided, source must be 'inferred' (not {src!r})")

    competitors = data.get("competitors", [])
    if not competitors:
        errors.append("competitors: need ≥1")
    cmp_ids = set()
    for i, c in enumerate(competitors):
        path = f"competitors[{i}]"
        cid = c.get("id")
        if cid in cmp_ids:
            errors.append(f"{path}: duplicate id {cid!r}")
        cmp_ids.add(cid)
        _enum(c.get("type"), CTYPE, f"{path}.type", errors)
        honesty(c, path)

    for i, fb in enumerate(data.get("feature_benchmark", [])):
        path = f"feature_benchmark[{i}]"
        _enum(fb.get("prevalence"), PREVALENCE, f"{path}.prevalence", errors)
        _enum(fb.get("our_stance"), STANCE, f"{path}.our_stance", errors)
        for ref in fb.get("competitor_refs", []):
            if ref not in cmp_ids:
                errors.append(f"{path}.competitor_refs: {ref!r} does not resolve")
        honesty(fb, path)
        if fb.get("prevalence") == "table_stakes" and fb.get("our_stance") == "skip" and not fb.get("rationale"):
            warnings.append(f"{path}: skipping a TABLE-STAKES capability with no rationale — credibility risk")

    for i, pc in enumerate(data.get("ux_pattern_conventions", [])):
        path = f"ux_pattern_conventions[{i}]"
        _enum(pc.get("convention"), CONVENTION, f"{path}.convention", errors)
        honesty(pc, path)
        if pc.get("convention") == "break" and not pc.get("reason"):
            errors.append(f"{path}: convention 'break' requires a reason (deviating costs usability)")

    for i, d in enumerate(data.get("differentiation", [])):
        path = f"differentiation[{i}]"
        _enum(d.get("defensibility"), DEFENSIBILITY, f"{path}.defensibility", errors)
        honesty(d, path)

    flags = {}
    if meta.get("overall_confidence") == "low":
        flags["constrain_downstream"] = True
        warnings.append("overall_confidence=low → constrain_downstream")
    if mode == "inferred":
        warnings.append("evidence_mode=inferred → market hypotheses, NOT a verified teardown")
    return errors, warnings, flags


def main():
    if len(sys.argv) < 2:
        print("usage: validate_competitive.py <competitive.json> [brief.json]")
        sys.exit(2)
    errors, warnings, flags = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for w in warnings:
        print(f"  ⚠ {w}")
    if errors:
        print(f"\n✗ competitive.json INVALID — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print(f"✓ competitive.json valid{' (flags: ' + ','.join(flags) + ')' if flags else ''}")
    sys.exit(0)


if __name__ == "__main__":
    main()
