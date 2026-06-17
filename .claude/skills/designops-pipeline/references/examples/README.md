# UX layer examples (validated)

Reference artifacts for the three UX layers — each passes its gate. Use them as the shape to
generate against.

| File | Layer / Step | evidence_mode shown |
|------|--------------|---------------------|
| `research.example.json` | User Research · 2.3 | **hybrid** — 2 personas/JTBD are `evidence` (cite `inputs_provided`), the rest `inferred` |
| `competitive.example.json` | Competitive Analysis · 2.4 | **inferred** — no competitor data given → market hypotheses; one `convention:"break"` with a reason |
| `usability.example.json` | Usability Test · 4.8 | simulated — `not_real_user_testing:true`, automated finding cites an axe rule, persona walkthrough `simulated:true` |

Validate:

```bash
S=.claude/skills/designops-pipeline/scripts ; E=.claude/skills/designops-pipeline/references/examples
python3 $S/validate_research.py    $E/research.example.json
python3 $S/validate_competitive.py $E/competitive.example.json
python3 $S/validate_usability.py   $E/usability.example.json $E/research.example.json
```

## inferred → hybrid → evidence_backed (ingest)

The mode is set by what you put in `meta.inputs_provided`:

- **inferred** — `inputs_provided: []`. Every item is `source:"inferred"`, confidence ≤ medium. The
  gate **rejects** any item marked `evidence`. This is an honest hypothesis layer, not research.
- **hybrid** — list the real inputs you have (`"interview:notes.md"`, `"analytics:ga4-export"`,
  `"competitor:https://…"`, `"session:rec-03"`). Items grounded in one of those refs become
  `source:"evidence"` and may claim `high`; everything else stays `inferred`. See `research.example.json`.
- **evidence_backed** — every item cites a ref in `inputs_provided`.

The gate's anti-fabrication rule: an item is `evidence` **only if** every entry in its `evidence`
array appears in `meta.inputs_provided`. You cannot cite a source you didn't declare.
