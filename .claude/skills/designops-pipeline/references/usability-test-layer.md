# Usability Test Layer — Reference (Step 4.8)

Read this when generating `usability.json`. It runs **after the audit gate (4.7), on the built
prototype**, and produces a usability assessment from three *simulated* methods — it does **not**
recruit real participants, and the schema forces that admission so findings are never mistaken
for empirical data.

**Methods (all simulated):**
- `heuristic` — expert evaluation against Nielsen's 10 heuristics (extends the 4.6 critique).
- `automated` — machine signals from 4.7/4.7b (axe-core, contrast, focus-trap) restated as usability findings with evidence.
- `persona_walkthrough` — an AI persona (from `research.json`) is walked through a task flow; friction is flagged step by step.

**Three rules:**
1. **Tell the truth about the method.** `meta.not_real_user_testing` MUST be `true`; every persona walkthrough is `simulated:true`; `meta.methods_used` may only contain the three methods above (no `moderated`/`unmoderated`/`real_user`). `limitations` must be non-empty.
2. **Severe means actionable.** Use Nielsen's 0–4 severity. Any finding ≥3 needs a `recommendation` and must appear in `top_issues`.
3. **Automated findings cite their signal.** `method:"automated"` requires `evidence` (the axe rule id, selector, or contrast pair) — no unsourced "machine said so".

> Validated by `scripts/validate_usability.py`. Advisory by default; the gate **fails** only on integrity violations (a fake "real test", an un-actionable severe finding), not on the findings themselves.

---

## Severity scale (Nielsen)

`0` not a problem · `1` cosmetic · `2` minor · `3` major · `4` catastrophe

---

## `usability.json` shape

```jsonc
{
  "meta": { "source_prototype": "output/prototype", "generated_at": "ISO-8601", "schema_version": "1.0",
            "not_real_user_testing": true,                 // REQUIRED true — no real participants
            "methods_used": ["heuristic", "automated", "persona_walkthrough"],
            "research_ref": "output/research.json",         // optional — lets persona_ref resolve
            "overall_confidence": "high|medium|low", "human_validation_required": true },

  "heuristic_findings": [{ "id": "H01", "heuristic": "Visibility of system status",
    "screen": "", "severity": 3, "issue": "", "recommendation": "",
    "method": "heuristic|automated", "evidence": "", "confidence": "high|medium|low" }],

  "persona_walkthroughs": [{ "persona_ref": "P01", "task": "", "simulated": true, "completed": true,
    "friction_points": [{ "step": "", "problem": "", "severity": 2 }] }],

  "severity_summary": { "0": 0, "1": 0, "2": 0, "3": 0, "4": 0 },

  "top_issues": [{ "ref": "H01", "severity": 3, "fix_priority": "now|next|later" }],

  "limitations": ["no real participants — findings are expert/simulated and need validation with users"]
}
```

---

## Integrity invariants (hard fails)

| Invariant |
|---|
| `meta.not_real_user_testing` is **exactly** `true` (false/missing ⇒ fail — cannot claim a real test) |
| `meta.methods_used` ⊆ {`heuristic`,`automated`,`persona_walkthrough`} |
| every `persona_walkthroughs[].simulated` is `true` |
| `severity` ∈ integers 0..4 everywhere |
| any finding `severity >= 3` ⇒ non-empty `recommendation` **and** its id ∈ `top_issues` |
| `method == "automated"` ⇒ non-empty `evidence` |
| `limitations` non-empty |
| if `research_ref` resolves, every `persona_ref` ∈ that file's persona ids |

---

## Generation prompt (agent reads the built prototype + 4.6/4.7 output [+ research.json] → writes `usability.json`)

```text
You are a Usability Specialist running a SIMULATED evaluation (no real users).
INPUT: the built prototype, the 4.6 critique, the 4.7/4.7b audit, research.json (personas).
OUTPUT: usability.json per the shape above.

1. BE HONEST ABOUT METHOD. not_real_user_testing:true, simulated:true on every walkthrough,
   methods_used only from {heuristic,automated,persona_walkthrough}, fill limitations.
2. HEURISTIC PASS. Evaluate each screen against Nielsen's 10; rate severity 0–4.
3. RESTATE AUTOMATED SIGNALS. Pull axe/contrast/focus-trap findings from 4.7/4.7b as method:"automated" with evidence.
4. PERSONA WALKTHROUGHS. For each primary persona's must-do task, walk the flow and flag friction per step.
5. SEVERE ⇒ ACTIONABLE. Every severity≥3 gets a recommendation and goes into top_issues with a fix_priority.
6. Roll up severity_summary; list limitations frankly.
```
