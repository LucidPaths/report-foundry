# Report Foundry Architecture

Report Foundry is an AI-operated analyst factory. Deterministic code owns sourcing law, evidence validation, gate routing, rendering, verification, and publishing. Models and connected agents may research, draft, code, and critique, but every output moves through typed handoffs and quality gates.

## Pipeline

```text
topic/keywords -> case rubric -> source plan -> observed source payloads -> source hashes -> extracted facts -> supported claims -> visual plan -> semantic IR -> assets/charts -> HTML/PDF renderers -> QA score -> delivery
```

The factory layer is department-oriented:

```text
editorial: infer report promise, audience, scope, and case-specific rubric
research: discover primary/trusted sources and required dimensions
analysis: extract numbers, actors, mechanisms, timelines, and contradictions
synthesis: convert evidence into hard-hitting claims
visuals: choose sourced charts, maps, diagrams, and generated assets
layout: compose a lightweight report/newsletter and source appendix
qa: read/look at the final artifact, score it against the initial rubric, and route failures back
```

Each department consumes a typed artifact and emits the next artifact. Gate failures name a route-back department rather than letting the pipeline continue with weak output.

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
- Topic input is not scope input: the factory must infer what a serious analyst would be negligent to omit, then prove or drop those dimensions.
- The case-specific rubric is created before research/rendering and becomes the acceptance contract for the run.
- Claims carry citations at span/block level.
- A claim is invalid unless every backing fact resolves to an observed source.
- Extractors fail closed when expected facts cannot be found in the observed payload.
- LLMs may propose scope, sources, code, visuals, and prose, but deterministic gates decide what is admissible and shippable.
- Renderers are adapters: ReportLab now, WeasyPrint/PrinceXML/Typst/Playwright later.
- Charts and diagrams should be SVG/vector-first.
- External assets require cached hashes, license metadata, alt text, and attribution.
- Every report should ship with optional provenance JSON.

## Enterprise integration shape

The same core should run as:

- CLI/library for local report runs.
- MCP server for Claude, ChatGPT, Ollama-backed agents, Hermes, and other tool-using clients.
- Server/queue deployment where companies connect databases, document stores, APIs, and internal MCP tools.

External and internal information enter through connectors, but the connector does not bypass source law: every ingested item must become a source observation with ID, timestamp, hash/fingerprint, trust tier, and extraction provenance.

## Planned adapters

- WeasyPrint: open-source paged-media HTML/CSS backend.
- PrinceXML: premium accessibility/archive publishing backend.
- Playwright: web-dashboard and screenshot backend.
- Typst: deterministic technical/whitepaper backend.
- Vega/Plotly/Mermaid: chart and diagram asset builders.

## QA gates

- missing required research dimension
- unsupported claims
- vague claims without actor + mechanism + implication
- missing numeric support for quantitative claims
- missing source appendix
- missing alt text
- ragged tables
- broken links
- underfilled pages
- overlapping or clipped visual elements
- oversized Discord attachments
- clipped visual layout via page screenshots
- PDF/A/PDF/UA validation via veraPDF where available
