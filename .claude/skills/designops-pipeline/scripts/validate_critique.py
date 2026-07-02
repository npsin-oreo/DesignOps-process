#!/usr/bin/env python3
"""Gate for critique.json (Step 4.6 — scored critique, judge-separated).

Integrity-first, mirroring the browser-use `qa` skill's judge pattern: the
agent that BUILT the prototype must not be the sole authority on whether it
passes. Step 4.6 now emits a structured critique with an INDEPENDENT judge
verdict, and this gate enforces the one rule that makes the separation real:

    a failed judge verdict CAPS the score — a high self-score cannot rescue
    a build the judge says is broken.

(See references/critique-framework.md "Structured output + judge" for the
schema and why the judge is a separate pass.)

Usage:  validate_critique.py <critique.json>
"""
import json
import sys

# self-score is on the framework's 1-10 scale; judge=false caps it here.
JUDGE_FAIL_CAP = 2.0
# below this the screen is "rework before ship" — a warning, not a block,
# because the agent's fix loop (not the gate) is what raises it.
SHIP_THRESHOLD = 6.0
# 7th dimension `richness` (track J): visual richness / identity usage, scored from what actually
# RENDERS (tinted surfaces, elevation hierarchy, accent placement, a hero moment — the track-H usage
# intent, seen by the track-I anti-plain check). A flat "brand colour on a neutral skeleton" can pass
# every static gate and score high on the other six; requiring an explicit richness score means the
# critique cannot certify a plain build as good just because its tokens exist.
DIMENSIONS = ("hierarchy", "consistency", "a11y", "usability", "responsiveness", "performance", "richness")
SEVERITIES = {"critical", "major", "minor", "enhancement"}


def _num(val, path, errors, lo, hi):
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        errors.append(f"{path}: must be a number {lo}..{hi}, got {val!r}")
        return None
    if not (lo <= val <= hi):
        errors.append(f"{path}: {val} out of range {lo}..{hi}")
        return None
    return val


def validate(path):
    errors, warnings, flags = [], [], {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"cannot read {path}: {e}"], [], {}

    # ── judge verdict — the separation-of-concerns core ───────────────────────
    if "judge_verdict" not in data:
        errors.append("judge_verdict (bool) is required — the critique must be "
                      "signed off by a judge pass separate from the build/self-score")
    judge = data.get("judge_verdict")
    if "judge_verdict" in data and not isinstance(judge, bool):
        errors.append(f"judge_verdict: must be true|false, got {judge!r}")
        judge = None
    # a false verdict must say why (so the cap is actionable, not a black box)
    if judge is False and not data.get("judge_reason"):
        errors.append("judge_verdict is false → judge_reason is required "
                      "(state what the judge saw that the self-score missed)")

    # ── overall score ─────────────────────────────────────────────────────────
    overall = _num(data.get("overall_score"), "overall_score", errors, 1, 10)

    # ── THE CAP RULE: judge=false caps the score, no matter the self-report ───
    if judge is False and overall is not None and overall > JUDGE_FAIL_CAP:
        errors.append(
            f"judge_verdict is false but overall_score is {overall} (> {JUDGE_FAIL_CAP}) — "
            f"a failed judge caps the score at {JUDGE_FAIL_CAP}. Lower it and lead with "
            "judge_reason (the build's own optimism cannot override the judge).")

    # ── per-screen dimension scores ───────────────────────────────────────────
    screens = data.get("screens")
    if not isinstance(screens, list) or not screens:
        errors.append("screens must be a non-empty list (score every main screen)")
    else:
        for i, s in enumerate(screens):
            sp = f"screens[{i}]"
            if not s.get("name"):
                errors.append(f"{sp}.name is required")
            dims = s.get("dimensions", {})
            for d in DIMENSIONS:
                if d not in dims:
                    errors.append(f"{sp}.dimensions.{d} is required (7 weighted dimensions incl. richness)")
                else:
                    _num(dims[d], f"{sp}.dimensions.{d}", errors, 1, 10)
            _num(s.get("score"), f"{sp}.score", errors, 1, 10)

    # ── findings (light schema — severity must be a known band) ───────────────
    for i, fnd in enumerate(data.get("findings", [])):
        sev = fnd.get("severity", "").lower()
        if sev not in SEVERITIES:
            errors.append(f"findings[{i}].severity {fnd.get('severity')!r} "
                          f"not in {sorted(SEVERITIES)}")

    # ── warnings (advisory — never block) ─────────────────────────────────────
    if overall is not None and judge is not False and overall < SHIP_THRESHOLD:
        warnings.append(f"overall_score {overall} < {SHIP_THRESHOLD} — rework before ship "
                        "(the fix loop should raise this; the gate does not block on it)")
    unresolved = [f for f in data.get("findings", [])
                  if f.get("severity", "").lower() == "critical" and not f.get("resolved")]
    if unresolved and judge is True:
        warnings.append(f"{len(unresolved)} unresolved Critical finding(s) but judge_verdict "
                        "is true — confirm the judge accounted for them")
    if not data.get("what_worked"):
        warnings.append("what_worked is empty — a good critique names what works, not only faults")

    if judge is False:
        flags["judge_failed"] = True
    return errors, warnings, flags


def main():
    if len(sys.argv) < 2:
        print("usage: validate_critique.py <critique.json>")
        sys.exit(2)
    errors, warnings, flags = validate(sys.argv[1])
    for w in warnings:
        print(f"  ⚠ {w}")
    if errors:
        print(f"\n✗ critique.json INVALID — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print(f"✓ critique.json valid{' (flags: ' + ','.join(flags) + ')' if flags else ''}")
    sys.exit(0)


if __name__ == "__main__":
    main()
