# Report Foundry Architecture

Report Foundry is an AI-native publication compiler. The model produces structured report intent; deterministic code renders, verifies, and publishes.

## Pipeline

```text
sources -> evidence pack -> semantic IR -> assets/charts -> HTML/PDF renderers -> QA -> delivery
```

## Principles

- PDF is an artifact, not the source of truth.
- Claims carry citations at span/block level.
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
