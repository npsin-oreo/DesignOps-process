#!/usr/bin/env python3
"""
validate_intelligence.py — gate for the Product Intelligence Layer (Step 2.5).

Usage: validate_intelligence.py <path/to/intelligence.json> [path/to/brief.json]
Exit 0 = valid, Exit 1 = invalid (with errors). Warnings + confidence gating are
printed but do not fail the gate.

Validates 4 layers: (A) structural enums/bands/ids, (B) referential integrity into
brief.json ids, (C) cross-dimension invariants, plus confidence gating + contradiction
warnings. Zero-dependency, mirrors validate_brief.py.
"""

import json
import sys

REQUIRED_TOP_KEYS = [
    "meta", "user_types", "user_goals", "core_tasks", "workflow_complexity",
    "data_density", "error_tolerance", "accessibility_needs",
    "compliance_requirements", "decision_criticality", "design_directives",
]

# ── enums ──────────────────────────────────────────────────────────────────────
CONFIDENCE   = {"high", "medium", "low"}
ROLE_CAT     = {"operator", "admin", "end_user", "approver", "auditor", "system"}
RELATIONSHIP = {"primary", "secondary", "occasional"}
EXPERTISE    = {"novice", "intermediate", "expert"}
FREQUENCY_U  = {"first_time", "occasional", "daily", "power"}
TRAINING     = {"yes", "no", "unknown"}
JOB_TYPE     = {"functional", "emotional", "social"}
GOAL_PRIO    = {"must", "should", "could"}
TASK_FREQ    = {"rare", "occasional", "frequent", "constant"}
TRIGGER      = {"user", "scheduled", "event", "system"}
LINEARITY    = {"linear", "branching", "parallel"}
STATE_PERSIST= {"none", "draft", "long_running"}
TOLERANCE    = {"high", "medium", "low", "zero"}
REVERSIBILITY= {"reversible", "recoverable", "irreversible"}
WCAG         = {"AA", "AA_plus", "AAA"}
COMPLIANCE_SCOPE = {"data_privacy", "financial", "medical", "accessibility", "sector", "other"}
CRITICALITY  = {"low", "medium", "high", "safety_critical"}
COMPLETENESS = {"low", "med", "high"}
GUIDANCE     = {"guided", "balanced", "expert"}
SAFEGUARD    = {"minimal", "standard", "strict", "maximal"}
NAV_MODEL    = {"single", "wizard", "hub_spoke", "workspace"}
TRUST        = {"low", "medium", "high"}
IMPACT       = {"blocker", "important", "nice_to_know"}

# brief signals that imply regulatory exposure / dense data
SENSITIVE_DATA_HINTS = ("health", "medical", "patient", "financial", "payment", "bank",
                        "biometric", "national id", "minor", "child", "pdpa", "gdpr", "hipaa", "pci")
PUBLIC_SECTOR_HINTS  = ("government", "public service", "public sector", "citizen", "accessibility law", "wcag")
ANALYTICS_HINTS      = ("dashboard", "report", "analytics", "statistic", "metric")


def _enum(val, allowed, path, errors):
    if val not in allowed:
        errors.append(f"{path} must be one of {sorted(allowed)} (got: {val!r})")


def validate(intel_path, brief_path=None):
    errors, warnings = [], []

    try:
        with open(intel_path) as f:
            d = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"], []
    except FileNotFoundError:
        return [f"file not found: {intel_path}"], []

    brief = None
    if brief_path:
        try:
            with open(brief_path) as f:
                brief = json.load(f)
        except Exception:
            warnings.append(f"could not read brief.json at {brief_path} — skipping referential checks")

    for k in REQUIRED_TOP_KEYS:
        if k not in d:
            errors.append(f"missing top-level key: '{k}'")
    if errors:
        return errors, warnings

    # ── meta ───────────────────────────────────────────────────────────────────
    meta = d["meta"]
    oc = meta.get("overall_confidence", "")
    _enum(oc, CONFIDENCE, "meta.overall_confidence", errors)

    # ── A. user_types (+ nested expertise) ──────────────────────────────────────
    ut_ids, novice_domains, has_power_novice = set(), [], False
    uts = d["user_types"]
    if not isinstance(uts, list) or not uts:
        errors.append("user_types must have at least 1 entry")
    else:
        if not any(u.get("relationship") == "primary" for u in uts):
            errors.append("user_types must include at least 1 'primary' type")
        for i, u in enumerate(uts):
            uid = u.get("id", "")
            if not uid:
                errors.append(f"user_types[{i}].id must not be empty")
            elif uid in ut_ids:
                errors.append(f"user_types: duplicate id '{uid}'")
            else:
                ut_ids.add(uid)
            _enum(u.get("role_category"), ROLE_CAT, f"user_types[{i}].role_category", errors)
            _enum(u.get("relationship"), RELATIONSHIP, f"user_types[{i}].relationship", errors)
            if not u.get("evidence"):
                errors.append(f"user_types[{i}].evidence must not be empty")
            ex = u.get("expertise") or {}
            _enum(ex.get("domain"), EXPERTISE, f"user_types[{i}].expertise.domain", errors)
            _enum(ex.get("tool"), EXPERTISE, f"user_types[{i}].expertise.tool", errors)
            _enum(ex.get("usage_frequency"), FREQUENCY_U, f"user_types[{i}].expertise.usage_frequency", errors)
            if ex.get("training_provided") not in TRAINING:
                errors.append(f"user_types[{i}].expertise.training_provided must be one of {sorted(TRAINING)}")
            novice_domains.append(ex.get("domain") == "novice")
            if ex.get("usage_frequency") == "power" and ex.get("domain") == "novice":
                has_power_novice = True

    # ── user_goals ──────────────────────────────────────────────────────────────
    goal_ids = set()
    goals = d["user_goals"]
    if not isinstance(goals, list) or not goals:
        errors.append("user_goals must have at least 1 entry")
    else:
        if not any(g.get("priority") == "must" for g in goals):
            errors.append("user_goals must include at least 1 'must' goal")
        for i, g in enumerate(goals):
            gid = g.get("id", "")
            if not gid or gid in goal_ids:
                errors.append(f"user_goals[{i}].id missing or duplicate ('{gid}')")
            else:
                goal_ids.add(gid)
            _enum(g.get("job_type"), JOB_TYPE, f"user_goals[{i}].job_type", errors)
            _enum(g.get("priority"), GOAL_PRIO, f"user_goals[{i}].priority", errors)
            if g.get("user_type_ref") not in ut_ids:
                errors.append(f"user_goals[{i}].user_type_ref '{g.get('user_type_ref')}' not in user_types")
            stmt = (g.get("statement") or "").lower()
            if any(n in stmt for n in ("button", "screen", "page", "click", "tab ", "modal")):
                warnings.append(f"user_goals[{i}].statement reads like a feature, not an outcome: {g.get('statement')!r}")

    # ── core_tasks ──────────────────────────────────────────────────────────────
    task_ids = set()
    tasks = d["core_tasks"]
    if not isinstance(tasks, list) or not tasks:
        errors.append("core_tasks must have at least 1 entry")
    else:
        for i, t in enumerate(tasks):
            tid = t.get("id", "")
            if not tid or tid in task_ids:
                errors.append(f"core_tasks[{i}].id missing or duplicate ('{tid}')")
            else:
                task_ids.add(tid)
            _enum(t.get("frequency"), TASK_FREQ, f"core_tasks[{i}].frequency", errors)
            _enum(t.get("trigger"), TRIGGER, f"core_tasks[{i}].trigger", errors)
            if t.get("user_type_ref") not in ut_ids:
                errors.append(f"core_tasks[{i}].user_type_ref '{t.get('user_type_ref')}' not in user_types")
            if t.get("goal_ref") not in goal_ids:
                errors.append(f"core_tasks[{i}].goal_ref '{t.get('goal_ref')}' not in user_goals")

    # ── workflow_complexity ─────────────────────────────────────────────────────
    wc = d["workflow_complexity"]
    if not isinstance(wc.get("overall_score"), int) or not (1 <= wc.get("overall_score", 0) <= 5):
        errors.append("workflow_complexity.overall_score must be an integer 1..5")
    flow_ids = {fl.get("id") for fl in (brief or {}).get("user_flows", [])} if brief else None
    for i, w in enumerate(wc.get("per_workflow", [])):
        _enum(w.get("linearity"), LINEARITY, f"workflow_complexity.per_workflow[{i}].linearity", errors)
        _enum(w.get("state_persistence"), STATE_PERSIST, f"workflow_complexity.per_workflow[{i}].state_persistence", errors)
        if flow_ids is not None and w.get("flow_ref") not in flow_ids:
            errors.append(f"workflow_complexity.per_workflow[{i}].flow_ref '{w.get('flow_ref')}' not in brief.user_flows")

    # ── data_density ────────────────────────────────────────────────────────────
    dd = d["data_density"]
    band = dd.get("overall_band")
    if not isinstance(band, int) or not (1 <= band <= 5):
        errors.append("data_density.overall_band must be an integer 1..5")

    # ── error_tolerance ─────────────────────────────────────────────────────────
    et = d["error_tolerance"]
    _enum(et.get("overall"), TOLERANCE, "error_tolerance.overall", errors)
    _enum(et.get("reversibility"), REVERSIBILITY, "error_tolerance.reversibility", errors)
    crit_actions = et.get("critical_actions", [])
    for i, a in enumerate(crit_actions):
        if task_ids and a.get("task_ref") not in task_ids:
            errors.append(f"error_tolerance.critical_actions[{i}].task_ref '{a.get('task_ref')}' not in core_tasks")

    # ── accessibility_needs ─────────────────────────────────────────────────────
    an = d["accessibility_needs"]
    _enum(an.get("wcag_target"), WCAG, "accessibility_needs.wcag_target", errors)  # enum is the AA floor

    # ── compliance_requirements ─────────────────────────────────────────────────
    comp = d["compliance_requirements"]
    comp_ids = set()
    if not isinstance(comp, list):
        errors.append("compliance_requirements must be an array")
    else:
        for i, c in enumerate(comp):
            cid = c.get("id", "")
            if not cid or cid in comp_ids:
                errors.append(f"compliance_requirements[{i}].id missing or duplicate ('{cid}')")
            else:
                comp_ids.add(cid)
            _enum(c.get("scope"), COMPLIANCE_SCOPE, f"compliance_requirements[{i}].scope", errors)
            if c.get("mandatory") and not c.get("ui_implications"):
                errors.append(f"compliance_requirements[{i}] is mandatory but has empty ui_implications")

    # ── decision_criticality ────────────────────────────────────────────────────
    dc = d["decision_criticality"]
    _enum(dc.get("overall"), CRITICALITY, "decision_criticality.overall", errors)
    for i, p in enumerate(dc.get("decision_points", [])):
        _enum(p.get("info_completeness_need"), COMPLETENESS, f"decision_criticality.decision_points[{i}].info_completeness_need", errors)
        if task_ids and p.get("task_ref") not in task_ids:
            errors.append(f"decision_criticality.decision_points[{i}].task_ref '{p.get('task_ref')}' not in core_tasks")

    # ── design_directives ───────────────────────────────────────────────────────
    dz = d["design_directives"]
    if not isinstance(dz.get("density_target"), int) or not (1 <= dz.get("density_target", 0) <= 5):
        errors.append("design_directives.density_target must be an integer 1..5")
    _enum(dz.get("guidance_level"), GUIDANCE, "design_directives.guidance_level", errors)
    _enum(dz.get("safeguard_level"), SAFEGUARD, "design_directives.safeguard_level", errors)
    _enum(dz.get("a11y_target"), WCAG, "design_directives.a11y_target", errors)
    _enum(dz.get("navigation_model"), NAV_MODEL, "design_directives.navigation_model", errors)
    _enum(dz.get("trust_emphasis"), TRUST, "design_directives.trust_emphasis", errors)

    # reasoning trace — makes the strategy auditable ("Reasoning System", not generator).
    # rationale = why these directives follow from the dimensions; trade_offs = decisions made.
    if not isinstance(dz.get("rationale"), str) or not dz.get("rationale", "").strip():
        errors.append("design_directives.rationale required — a short why, grounded in the dimensions")
    tos = dz.get("trade_offs", [])
    if not isinstance(tos, list):
        errors.append("design_directives.trade_offs must be a list")
    else:
        for i, t in enumerate(tos):
            if not isinstance(t, dict):
                errors.append(f"design_directives.trade_offs[{i}] must be an object")
                continue
            for k in ("decision", "chose", "over", "because"):
                if not t.get(k):
                    errors.append(f"design_directives.trade_offs[{i}].{k} required (decision/chose/over/because)")
        if not tos:
            warnings.append("design_directives.trade_offs is empty — state at least the central trade-off so the strategy is auditable")

    # ── C. cross-dimension invariants (hard fails) ──────────────────────────────
    # rollup must agree with its source dimension
    if dz.get("a11y_target") != an.get("wcag_target"):
        errors.append(f"design_directives.a11y_target ({dz.get('a11y_target')}) must equal accessibility_needs.wcag_target ({an.get('wcag_target')})")

    # public-sector / accessibility-law ⇒ AAA
    a11y_text = " ".join(str(x) for x in an.get("drivers", [])).lower()
    comp_text = " ".join(str(c.get("name", "")) + " " + str(c.get("scope", "")) for c in comp).lower()
    if any(h in (a11y_text + " " + comp_text) for h in PUBLIC_SECTOR_HINTS):
        if an.get("wcag_target") != "AAA":
            errors.append("public-sector / accessibility-law signal present ⇒ accessibility_needs.wcag_target must be AAA")

    # safety-critical ⇒ low/zero tolerance
    if dc.get("overall") == "safety_critical" and et.get("overall") not in {"low", "zero"}:
        errors.append("decision_criticality=safety_critical ⇒ error_tolerance.overall must be low or zero")

    # low/zero tolerance ⇒ enumerate critical_actions, each with safeguards
    if et.get("overall") in {"low", "zero"}:
        if not crit_actions:
            errors.append("error_tolerance is low/zero but no critical_actions are enumerated")
        for i, a in enumerate(crit_actions):
            if not a.get("recommended_safeguards"):
                errors.append(f"error_tolerance.critical_actions[{i}] needs recommended_safeguards (tolerance is low/zero)")

    # high/safety-critical decisions ⇒ recommended_patterns present
    if dc.get("overall") in {"high", "safety_critical"}:
        if not any(p.get("recommended_patterns") for p in dc.get("decision_points", [])):
            errors.append("decision_criticality is high/safety_critical but no decision_point lists recommended_patterns")

    # sensitive data in brief ⇒ ≥1 compliance entry
    if brief is not None:
        brief_text = json.dumps(brief, ensure_ascii=False).lower()
        if any(h in brief_text for h in SENSITIVE_DATA_HINTS) and not comp:
            errors.append("brief references sensitive data (health/financial/biometric/minor) but compliance_requirements is empty")
        # coverage: features exist but no tasks/goals derived
        if brief.get("core_features") and (not goals or not tasks):
            errors.append("brief has core_features but intelligence has no user_goals/core_tasks (coverage gap)")
        # analytics features but minimal density
        if any(h in brief_text for h in ANALYTICS_HINTS) and isinstance(band, int) and band <= 2:
            warnings.append("brief mentions analytics/report/dashboard but data_density.overall_band ≤ 2 — verify")

    # ── E. contradiction warnings ───────────────────────────────────────────────
    if has_power_novice:
        warnings.append("a user_type is usage_frequency=power but domain=novice — verify")
    if isinstance(band, int) and band >= 4 and novice_domains and all(novice_domains):
        warnings.append("data_density ≥ 4 (dense) but all user_types are domain novices — ensure onboarding/guidance")
    if et.get("reversibility") == "irreversible" and et.get("overall") == "high":
        warnings.append("error_tolerance.reversibility=irreversible but overall=high — verify")

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_intelligence.py <intelligence.json> [brief.json]", file=sys.stderr)
        sys.exit(1)

    intel_path = sys.argv[1]
    brief_path = sys.argv[2] if len(sys.argv) > 2 else None
    errors, warnings = validate(intel_path, brief_path)

    if errors:
        print(f"[validate_intelligence] ✗ Invalid — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        sys.exit(1)

    with open(intel_path) as f:
        d = json.load(f)
    dz = d.get("design_directives", {})
    oc = d.get("meta", {}).get("overall_confidence", "-")
    constrain = "true" if oc == "low" else "false"

    print("[validate_intelligence] ✓ Valid")
    print(f"  Confidence : {oc}   (constrain_downstream={constrain})")
    print(f"  User types : {len(d.get('user_types', []))} · Goals: {len(d.get('user_goals', []))} · Tasks: {len(d.get('core_tasks', []))}")
    print(f"  Compliance : {len(d.get('compliance_requirements', []))} · Criticality: {d.get('decision_criticality', {}).get('overall', '-')} · Error tol: {d.get('error_tolerance', {}).get('overall', '-')}")
    print("  Directives :")
    print(f"    density={dz.get('density_target')} · guidance={dz.get('guidance_level')} · safeguards={dz.get('safeguard_level')}")
    print(f"    a11y={dz.get('a11y_target')} · nav={dz.get('navigation_model')} · trust={dz.get('trust_emphasis')}")
    print(f"    mandatory_flows={dz.get('mandatory_flows')}")
    for w in warnings:
        print(f"  ⚠ {w}")
    if constrain == "true":
        print("  ⚠ overall_confidence=low → downstream should produce wireframe-level output + human gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
