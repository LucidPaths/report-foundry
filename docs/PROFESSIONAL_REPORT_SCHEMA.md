# Professional Report Content Schema

Report Foundry must not render schema debris as a report. The authoring/research layer writes into a reader-facing professional report contract; the foundry validates that contract, preserves evidence links, and renders it through software.

## Observed public patterns

Fetched public examples during schema derivation:

- Deloitte Insights — TMT Predictions / industry outlook pattern
- PwC — Global CEO Survey pattern
- a16z crypto — State of Crypto report pattern
- Bessemer Venture Partners — State of the Cloud report pattern
- CB Insights — State of Venture / market-intelligence pattern
- J.P. Morgan Asset Management — Guide to the Markets pattern

McKinsey and Goldman pages were attempted but blocked from this runtime, so they were not treated as observed evidence for this schema pass.

## Structural invariant

Professional reports are answer-first and evidence-backed:

1. **Front matter** — title, subtitle, date, institution/author, audience, one-sentence thesis.
2. **Executive brief** — concise answer, 3–5 key takeaways, confidence/boundary, decision relevance.
3. **Conclusion-led sections** — headings state the finding, not generic labels.
4. **Evidence body** — each section has lede, evidence, interpretation / “so what,” limitations, citations.
5. **Exhibits** — charts/diagrams/tables are first-class evidence objects with a stated insight.
6. **Decision layer** — implications, risks/unknowns, what to watch, recommendations or next research.
7. **Back matter** — methodology and source appendix with human-visible URLs.

## EvidencePack professional contract

Use `professional_report` when the output is meant to be a real report:

```json
{
  "professional_report": {
    "one_sentence_thesis": "...",
    "executive_summary": ["..."],
    "key_takeaways": [
      {
        "takeaway": "Conclusion first.",
        "fact_ids": ["fact_..."],
        "implication": "Decision relevance."
      }
    ],
    "sections": [
      {
        "section_id": "...",
        "role": "financial_analysis",
        "headline": "Conclusion-led section headline",
        "lede": "Reader-facing setup.",
        "paragraphs": ["Evidence-backed prose."],
        "fact_ids": ["fact_..."],
        "so_what": "Why the section matters.",
        "limitations": ["What the evidence cannot prove yet."],
        "exhibit_refs": ["optional_exhibit_id"]
      }
    ],
    "what_to_watch": ["Next observable signal."],
    "methodology": "How the report was constructed."
  }
}
```

## Hard rules

- Do not print internal scope/fact-table plumbing in the reader-facing report.
- Do not use source IDs as citations unless paired with human-visible source titles and URLs.
- Do not let a report make a conclusion that no `fact_id` supports.
- Do not hide limitations. Professional reports name evidence boundaries explicitly.
- The foundry renders; it does not invent missing prose after schema validation.
