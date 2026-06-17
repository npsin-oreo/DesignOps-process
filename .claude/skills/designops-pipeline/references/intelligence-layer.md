# Product Intelligence Layer — Reference (Step 2.5)

Read this when generating `intelligence.json`. It sits between the brief (facts) and
Component Mapping (UI). It infers **10 measurable product dimensions** from `brief.json`,
each with evidence + confidence, and rolls them up into `design_directives` that Step 3/4
consume — so UI decisions come from *what the product needs*, not from a feature list.

**Three rules:**
1. **Fact vs interpretation are separate.** `brief.json` = stated facts. `intelligence.json` = inference. Never restate; infer what the brief *implies*.
2. **Evidence or silence.** Every value needs `evidence` (feature/flow/persona ids or `TOR:<section>`) + `confidence`. If you can't ground it → `confidence:"low"` + an `open_question`. Never invent a fact.
3. **Scales, not prose.** Resolve each dimension to its enum/band so downstream can branch deterministically.

> Validated by `scripts/validate_intelligence.py` — structural + referential (resolves brief ids) + **cross-dimension invariants** + confidence gating. Violations of the invariants are hard fails.

---

## The 10 categories

| # | Category | Purpose | Generation method | Validation |
|---|----------|---------|-------------------|------------|
| 1 | **User Types** | distinct roles → multi-surface IA, role views | extract `target_users` + **infer implicit roles from verbs/permissions** in features | ≥1 `primary`; ids unique; evidence required |
| 2 | **User Expertise** (per type) | guidance vs speed; onboarding vs density | infer `domain` + `tool` axes from role/training/frequency | enums; `power`+`novice` → warn |
| 3 | **User Goals** | outcomes (the why), not features | from objective + pain_points + flows, as JTBD outcome statements | outcome (no UI nouns); `user_type_ref` valid; ≥1 `must` |
| 4 | **Core Tasks** | repeatable units that achieve goals | decompose goals+flows into verb-object tasks | verb-object; `goal_ref`+`user_type_ref` valid |
| 5 | **Workflow Complexity** | nav model, save/resume, wizard vs form | score flows by steps/branches/actors/async/handoffs | `overall_score` 1..5; `flow_ref`→brief flows |
| 6 | **Data Density** | layout (cards/table/dashboard), virtualization | infer entities-per-view + fields-per-entity | band 1..5; analytics+low band → warn |
| 7 | **Error Tolerance** | confirms, undo, autosave, preview | infer from consequence/reversibility of actions | low/zero ⇒ critical_actions w/ safeguards |
| 8 | **Accessibility Needs** | WCAG target, AT support, motion/lang | infer from audience breadth + explicit a11y/compliance | ≥ AA floor; public-sector ⇒ AAA |
| 9 | **Compliance Requirements** | mandatory flows/copy/data rules | extract named regs + infer from data types | mandatory ⇒ ui_implications; sensitive data ⇒ ≥1 entry |
| 10 | **Decision Criticality** | info completeness, explainability, review | infer from stakes + who bears consequence | high/safety ⇒ recommended_patterns; safety ⇒ tolerance low/zero |

---

## `intelligence.json` shape

```jsonc
{
  "meta": { "source_brief": "output/brief.json", "generated_at": "ISO-8601",
            "schema_version": "1.0", "overall_confidence": "high|medium|low", "human_reviewed": false },

  "user_types": [{ "id": "UT01", "name": "", "role_category": "operator|admin|end_user|approver|auditor|system",
    "relationship": "primary|secondary|occasional", "primary_surface": "",
    "expertise": { "domain": "novice|intermediate|expert", "tool": "novice|intermediate|expert",
                   "usage_frequency": "first_time|occasional|daily|power", "training_provided": "yes|no|unknown" },
    "source": "stated|inferred", "evidence": ["personas[0]","F03"], "confidence": "high|medium|low" }],

  "user_goals": [{ "id": "G01", "user_type_ref": "UT01", "statement": "<outcome, no UI nouns>",
    "job_type": "functional|emotional|social", "priority": "must|should|could", "success_signal": "", "evidence": [] }],

  "core_tasks": [{ "id": "T01", "name": "verb_object", "user_type_ref": "UT01", "goal_ref": "G01",
    "frequency": "rare|occasional|frequent|constant", "trigger": "user|scheduled|event|system",
    "steps_estimate": 0, "evidence": [] }],

  "workflow_complexity": { "overall_score": 3, "per_workflow": [{ "flow_ref": "UF01",
    "linearity": "linear|branching|parallel", "actor_count": 1, "step_band": "1-3|4-7|8+",
    "has_async_wait": false, "has_handoffs": false, "state_persistence": "none|draft|long_running",
    "score": 2, "drivers": [] }] },

  "data_density": { "overall_band": 3, "per_surface": [{ "surface": "",
    "entity_count_band": "1|2-20|20-200|200+", "fields_per_entity_band": "1-3|4-8|9+",
    "realtime": false, "comparison_need": false, "drivers": [] }] },

  "error_tolerance": { "overall": "high|medium|low|zero", "reversibility": "reversible|recoverable|irreversible",
    "critical_actions": [{ "task_ref": "T01", "consequence": "", "recommended_safeguards": [] }] },

  "accessibility_needs": { "wcag_target": "AA|AA_plus|AAA", "default_floor": "WCAG 2.2 AA",
    "specific_needs": [], "motion_sensitivity": false, "drivers": [] },

  "compliance_requirements": [{ "id": "C01", "name": "", "scope": "data_privacy|financial|medical|accessibility|sector|other",
    "source": "stated|inferred", "mandatory": true, "ui_implications": [], "confidence": "high|medium|low" }],

  "decision_criticality": { "overall": "low|medium|high|safety_critical", "decision_points": [{ "task_ref": "T01",
    "stakes": "", "who_bears_consequence": "", "info_completeness_need": "low|med|high", "recommended_patterns": [] }] },

  "design_directives": { "density_target": 3, "guidance_level": "guided|balanced|expert",
    "safeguard_level": "minimal|standard|strict|maximal", "a11y_target": "AA|AA_plus|AAA",
    "mandatory_flows": [], "navigation_model": "single|wizard|hub_spoke|workspace",
    "trust_emphasis": "low|medium|high",
    "rationale": "<short why: how these directives follow from the dimensions + research/competitive evidence>",
    "trade_offs": [{ "decision": "", "chose": "", "over": "", "because": "" }] },

  "open_questions": [{ "dimension": "compliance", "question": "", "impact": "blocker|important|nice_to_know" }]
}
```

`design_directives` is the **seam** Component Mapping consumes:
`density_target → layout primitive` · `safeguard_level → confirm/undo/preview` · `guidance_level → onboarding/copy` ·
`a11y_target → component variants + audit target` · `navigation_model → app shell` · `mandatory_flows → injected screens` · `trust_emphasis → evidence/transparency`.

---

## Cross-dimension invariants (hard fails)

| Invariant |
|---|
| `accessibility_needs.wcag_target` ∈ {AA, AA_plus, AAA} — AA is the floor, always |
| public-sector / accessibility-law signal ⇒ `wcag_target = AAA` |
| `design_directives.a11y_target` = `accessibility_needs.wcag_target` (rollup agrees with source) |
| `decision_criticality.overall = safety_critical` ⇒ `error_tolerance.overall ∈ {low, zero}` |
| `error_tolerance.overall ∈ {low, zero}` ⇒ critical_actions enumerated, each with `recommended_safeguards` |
| `decision_criticality ∈ {high, safety_critical}` ⇒ ≥1 decision_point with `recommended_patterns` |
| sensitive data in brief (health/financial/biometric/minor) ⇒ ≥1 `compliance_requirements` |
| `compliance.mandatory = true` ⇒ non-empty `ui_implications` |
| every goal/task `*_ref` resolves; every `flow_ref` → `brief.user_flows` |

**Confidence gating:** if `meta.overall_confidence = low`, the validator emits
`constrain_downstream=true` → Step 3/4 should produce wireframe-level output + force a human gate
(don't mint an authoritative prototype from a guessed brief).

---

## Generation prompt (agent reads `brief.json` → writes `intelligence.json`)

```text
You are a Staff Product Designer building the Product Intelligence Layer.
INPUT: brief.json (facts). OUTPUT: intelligence.json (interpretation) per the shape above.

Rules:
1. INFER, don't restate — derive roles/stakes/constraints the brief implies but doesn't state;
   mark them source:"inferred" with evidence + confidence.
2. EVIDENCE OR SILENCE — every value needs evidence refs (feature/flow/persona ids or "TOR:<x>").
   Ungrounded → confidence:"low" + an open_question. Never invent a fact.
3. SCALES, NOT PROSE — resolve each dimension to its enum/band.
4. GOALS ARE OUTCOMES — no UI nouns (button/screen/page).
5. RESPECT THE INVARIANTS above (the validator rejects violations).
6. Synthesize design_directives by combining dimensions — these drive the next stage, make them decisive.
   Write `rationale` (a short why, grounded in the dimensions + any research/competitive evidence) and at
   least the central `trade_offs` entry (decision / chose / over / because) so the strategy is auditable,
   not just emitted — this is what makes the pipeline a reasoning system, not a generator.

Process: user_types (+inferred roles) → expertise → goals → tasks → workflow_complexity + data_density →
error_tolerance + decision_criticality (together) → accessibility + compliance → design_directives rollup →
open_questions for every low-confidence inference.
```

**Self-critique sub-prompt (run before writing the file):**
```text
Re-read the draft against brief.json:
- Any feature with no user_type/goal/task covering it? (coverage gap)
- Any directive contradicting another dimension? (invariant check)
- Any inference mislabeled as fact, or vice versa? (provenance check)
Fix, or move the uncertainty into open_questions, and lower overall_confidence if gaps remain.
```
