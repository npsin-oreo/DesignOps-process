# User Research Layer — Reference (Step 2.3)

Read this when generating `research.json`. It sits **after the brief, before Product Intelligence
(2.5)** and turns the brief's stated audience into structured research artifacts — personas,
jobs-to-be-done, pain points, behavioral assumptions — that become *evidence* for the
intelligence layer instead of raw guesses.

**Hybrid by design.** An AI pipeline cannot run real interviews. So this layer operates in one
of three modes, declared in `meta.evidence_mode`:
- `inferred` — no real inputs; everything is a **hypothesis** derived from the TOR. Caps confidence at `medium`.
- `hybrid` — some real inputs provided (interview notes, analytics, surveys); those items are `evidence`, the rest stay `inferred`.
- `evidence_backed` — all items grounded in provided inputs.

**Three rules:**
1. **Never fabricate evidence.** If `meta.inputs_provided` is empty, every item is `source:"inferred"`. You may not mark anything `evidence` without a matching ref in `inputs_provided`.
2. **Inferred ≠ confident.** `source:"inferred"` may never claim `confidence:"high"` — an unvalidated guess is medium at best, and every high-risk assumption needs a `research_question`.
3. **Outcomes, not features.** JTBD are situations + motivations ("when I…, I want…, so that…"), never UI.

> Validated by `scripts/validate_research.py` — schema + ref resolution + the **honesty invariants** below. Feeds `intelligence.json` via `feeds_intelligence`.

---

## `research.json` shape

```jsonc
{
  "meta": { "source_brief": "output/brief.json", "generated_at": "ISO-8601", "schema_version": "1.0",
            "evidence_mode": "inferred|hybrid|evidence_backed",
            "inputs_provided": [],            // e.g. ["interview:notes-2026-06.md","analytics:ga4-export"]; [] = pure inference
            "overall_confidence": "high|medium|low", "human_reviewed": false },

  "personas": [{ "id": "P01", "name": "", "archetype": "", "primary": true,
    "context": "", "tech_proficiency": "novice|intermediate|expert", "environment": "",
    "goals_ref": ["JTBD01"], "frustrations": [],
    "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "jobs_to_be_done": [{ "id": "JTBD01", "persona_ref": "P01",
    "when": "<situation>", "want": "<motivation>", "so_that": "<outcome>",
    "priority": "must|should|could", "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "pain_points": [{ "id": "PP01", "persona_ref": "P01", "statement": "",
    "severity": "low|med|high", "frequency": "rare|occasional|frequent",
    "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "behavioral_assumptions": [{ "id": "A01", "statement": "", "risk_if_wrong": "low|med|high",
    "validation_method": "interview|survey|analytics|usability_test",
    "status": "unvalidated|validated|invalidated",
    "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "research_questions": [{ "id": "RQ01", "question": "", "tied_to": "A01",
    "method": "interview|survey|analytics|usability_test", "priority": "blocker|important|nice_to_know" }],

  "feeds_intelligence": { "user_types_hint": [], "user_goals_hint": [], "error_tolerance_hint": "" }
}
```

`feeds_intelligence` is the **seam** Step 2.5 reads: personas → `user_types`, JTBD → `user_goals`,
pain points + assumptions → `error_tolerance` / `open_questions`. Evidence-backed hints let the
intelligence layer raise its own confidence; inferred hints stay hypotheses.

---

## Honesty invariants (hard fails)

| Invariant |
|---|
| `meta.inputs_provided == []` ⇒ every item `source == "inferred"` **and** `evidence_mode == "inferred"` |
| `source == "evidence"` ⇒ `evidence` non-empty **and** every ref ∈ `meta.inputs_provided` |
| `source == "inferred"` ⇒ `confidence != "high"` |
| `behavioral_assumptions[].status == "validated"` ⇒ `source == "evidence"` |
| every `risk_if_wrong == "high"` assumption ⇒ ≥1 `research_questions` with `tied_to` = its id |
| ≥1 persona with `primary == true`; all ids unique; every `*_ref` resolves |
| `overall_confidence == "low"` ⇒ emits `constrain_downstream=true` (Step 2.5 treats hints as low-confidence) |

---

## Generation prompt (agent reads `brief.json` [+ any provided inputs] → writes `research.json`)

```text
You are a UX Researcher building the User Research Layer.
INPUT: brief.json (facts) + any provided research inputs. OUTPUT: research.json per the shape above.

1. DECLARE THE MODE FIRST. List every real input in meta.inputs_provided. If there are none,
   evidence_mode="inferred" and EVERYTHING is source:"inferred" — you are writing hypotheses, label them so.
2. NEVER FABRICATE EVIDENCE. Only mark source:"evidence" when you can cite a ref that is in inputs_provided.
3. INFERRED CAPS AT MEDIUM. Any inferred item is confidence ≤ medium; every high-risk assumption gets a research_question.
4. JTBD ARE SITUATIONS, not features ("when I…, I want…, so that…").
5. Fill feeds_intelligence so Step 2.5 can consume personas/JTBD/pains as evidence.

Process: personas → JTBD (per persona) → pain_points → behavioral_assumptions (+ risk) →
research_questions (cover every high-risk assumption) → feeds_intelligence rollup.
```
