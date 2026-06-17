# Report Foundry Architecture

Report Foundry is an AI-native publication compiler. Deterministic code owns sourcing, evidence validation, rendering, verification, and publishing. The model may contribute bounded prose only after the source/evidence boundary is fixed.

## Pipeline

```text
observed source payloads -> source hashes -> extracted facts -> supported claims -> semantic IR -> assets/charts -> HTML/PDF renderers -> QA -> delivery
```

The Ollama Cloud newsletter path implements the contract explicitly:

```text
Ollama /v1/models + benchmark/model-card sources
  -> source observations (ID, URL, observed_at, SHA-256, extractor)
  -> extracted facts (subject, predicate, value, source_id, quote)
  -> supported claims (fact_ids required; unsupported claims fail closed)
  -> semantic IR for QA/rendering
  -> bounded LLM commentary (short notes only; never source of truth)
  -> deterministic designed HTML/PDF renderers
  -> sanitized Discord message
```

## Principles

- PDF is an artifact, not the source of truth.
- Claims carry citations at span/block level.
- A claim is invalid unless every backing fact resolves to an observed source.
- Extractors fail closed when expected facts cannot be found in the observed payload.
- LLMs may write bounded prose, but must not own scope, source selection, citations, charts, or layout.
- Renderers are adapters: ReportLab now, WeasyPrint/PrinceXML/Typst/Playwright later.
- Charts and diagrams should be SVG/vector-first.
- External assets require cached hashes, license metadata, alt text, and attribution.
- Every report should ship with optional provenance JSON.

## Planned adapters

- WeasyPrint: open-source paged-media HTML/CSS backend.
- PrinceXML: premium accessibility/archive publishing backend.
- Playwright: web-dashboard and screenshot backend.
- Typst: deterministic technical/whitepaper backend.
- Vega/Plotly/Mermaid: chart and diagram asset builders.

## QA gates

- unsupported claims
- missing alt text
- ragged tables
- broken links
- oversized Discord attachments
- clipped visual layout via page screenshots
- PDF/A/PDF/UA validation via veraPDF where available
