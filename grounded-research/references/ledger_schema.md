# Claims Ledger schema (v1)

The shared JSON record that carries results through all five stages. Stage 1
creates it; Stages 2–4 only UPDATE fields; Stage 5 reads it to produce the
report. Never delete or renumber claims mid-pipeline — IDs are stable references.

```json
{
  "ledger_version": "1.0",
  "source_text": "<filename or 'pasted text'>",
  "created": "<ISO date>",
  "pipeline_stage": "decomposed | grounded | citations_audited | contradictions_checked | reported",
  "claims": [
    {
      "id": "C1",
      "claim": "One atomic assertion, self-contained, no pronouns",
      "type": "factual | numeric | causal | attributed | definitional | normative",
      "location": "paragraph 2, sentence 1",
      "cites": "Smith et al. 2021 | null",

      "grounding": {
        "status": "UNCHECKED | SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED | CONTRADICTED | NOT_APPLICABLE",
        "evidence": "verbatim span (<=25 words) | null",
        "evidence_location": "source_A.pdf, p.4 | null",
        "note": "e.g. 'Direction supported; figure 30% not in any source.'"
      },

      "citation": {
        "status": "UNCHECKED | VERIFIED | METADATA_MISMATCH | MISATTRIBUTED | NOT_FOUND | UNVERIFIED",
        "resolved_title": "... | null",
        "mismatches": ["year: cited 2022, actual 2023"],
        "support_note": "Source confirms the claim. | Source does not mention X."
      },

      "cross_source": {
        "status": "UNCHECKED | CONSISTENT | CONFLICT | UNRESOLVED_CONFLICT | APPARENT_ONLY",
        "conflict_with": ["C9", "source_B.pdf"],
        "detail": "C2 states 30% (A, p.3); B p.7 reports 18% for the same metric.",
        "reconciling_dimension": "null | 'A measures 2021, B measures 2024'"
      },

      "final_label": "null until Stage 5 | VERIFIED | PARTIALLY VERIFIED | UNVERIFIED | DISPUTED | FAILED | OPINION"
    }
  ]
}
```

## Field lifecycle

| Stage | Sets / updates |
|-------|----------------|
| 1 Decompose | creates everything; all statuses = UNCHECKED, final_label = null |
| 2 Ground | `grounding` |
| 3 Audit citations | `citation` |
| 4 Contradict | `cross_source` |
| 5 Report | `final_label`, `pipeline_stage` = "reported" |

## final_label decision rule (Stage 5)

```
citation NOT_FOUND or MISATTRIBUTED  → FAILED
grounding CONTRADICTED               → FAILED
cross_source UNRESOLVED_CONFLICT     → DISPUTED
grounding UNSUPPORTED                → UNVERIFIED
grounding PARTIALLY_SUPPORTED        → PARTIALLY VERIFIED
citation METADATA_MISMATCH (else ok) → PARTIALLY VERIFIED
type normative                       → OPINION (excluded from score)
grounding SUPPORTED, nothing above   → VERIFIED
```
