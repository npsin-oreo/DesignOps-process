# Competitive Analysis Layer — Reference (Step 2.4)

Read this when generating `competitive.json`. It sits **after User Research (2.3), before
Product Intelligence (2.5)** and benchmarks the product against its market — competitors,
feature table-stakes, UX pattern conventions, differentiation — feeding both the intelligence
layer (what density/patterns users will expect) and the aesthetic layer (2.6).

**Hybrid by design** — same three modes as the research layer (`meta.evidence_mode`):
`inferred` (no real competitor data → market hypotheses, capped at `medium`), `hybrid`,
`evidence_backed`. **A competitive analysis with no real competitor inputs is a hypothesis, not
a teardown** — the gate enforces that distinction so nobody ships strategy built on imagined rivals.

**Three rules:**
1. **Never fabricate evidence.** No competitor claim is `source:"evidence"` unless its ref is in `meta.inputs_provided` (a URL you were given, a teardown doc, a screenshot set).
2. **Conventions are defaults; breaking one needs a reason.** `convention:"break"` without a `reason` is a hard fail — deviating from an established pattern is a usability cost you must justify.
3. **Table-stakes are not optional silently.** Skipping a `table_stakes` capability requires a `rationale` (the gate warns and surfaces it as risk).

> Validated by `scripts/validate_competitive.py`. Feeds `intelligence.json` (density/pattern hints) + `aesthetic.json` (positioning).

---

## `competitive.json` shape

```jsonc
{
  "meta": { "source_brief": "output/brief.json", "generated_at": "ISO-8601", "schema_version": "1.0",
            "evidence_mode": "inferred|hybrid|evidence_backed",
            "inputs_provided": [],            // e.g. ["competitor:https://acme.com","teardown:rival-notes.md"]; [] = inference
            "overall_confidence": "high|medium|low", "human_reviewed": false },

  "competitors": [{ "id": "CMP01", "name": "", "type": "direct|indirect|aspirational",
    "positioning": "", "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "feature_benchmark": [{ "id": "FB01", "capability": "", "competitor_refs": ["CMP01"],
    "prevalence": "table_stakes|common|differentiator|rare",
    "our_stance": "match|exceed|skip|defer", "rationale": "",
    "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "ux_pattern_conventions": [{ "id": "PC01", "pattern": "", "surface": "",
    "convention": "follow|break", "reason": "",
    "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "differentiation": [{ "id": "D01", "axis": "", "our_position": "",
    "defensibility": "low|med|high", "source": "inferred|evidence", "evidence": [], "confidence": "high|medium|low" }],

  "table_stakes": ["<capability you must have to be credible>"],

  "feeds": { "intelligence_density_hint": "", "aesthetic_hint": "" }
}
```

---

## Honesty + domain invariants (hard fails unless noted)

| Invariant |
|---|
| `meta.inputs_provided == []` ⇒ every item `source == "inferred"` **and** `evidence_mode == "inferred"` |
| `source == "evidence"` ⇒ `evidence` non-empty **and** every ref ∈ `meta.inputs_provided` |
| `source == "inferred"` ⇒ `confidence != "high"` |
| ≥1 competitor; all ids unique; every `competitor_refs` resolves to a competitor id |
| `ux_pattern_conventions[].convention == "break"` ⇒ non-empty `reason` |
| `feature_benchmark` with `prevalence == "table_stakes"` and `our_stance == "skip"` ⇒ non-empty `rationale` (**warn** → risk) |
| `overall_confidence == "low"` ⇒ `constrain_downstream=true` |

---

## Generation prompt (agent reads `brief.json` [+ research.json + provided competitor inputs] → writes `competitive.json`)

```text
You are a Product Strategist building the Competitive Analysis Layer.
INPUT: brief.json (+ research.json, + any competitor URLs/teardowns). OUTPUT: competitive.json.

1. DECLARE THE MODE FIRST. Real competitor inputs → list in meta.inputs_provided. None →
   evidence_mode="inferred": you are reasoning about a LIKELY market, every item source:"inferred", confidence ≤ medium.
2. NEVER FABRICATE. Only source:"evidence" when the ref is in inputs_provided. Do not invent competitor feature lists as fact.
3. CONVENTIONS ARE DEFAULTS — mark "follow" unless you can justify "break" with a concrete reason.
4. NAME THE TABLE STAKES — capabilities the product must have to be credible; if our_stance="skip" on one, write the rationale.
5. Fill feeds so Step 2.5/2.6 can consume density + positioning hints.

Process: competitors (typed) → feature_benchmark (prevalence + our stance) → ux_pattern_conventions
(follow/break + reason) → differentiation (defensibility) → table_stakes → feeds rollup.
```
