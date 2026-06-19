# Report Foundry Architecture

Report Foundry is an evidence-contract and artifact factory. A research-capable LLM/session searches, reads, and reasons over the topic, then returns structured `ResearchIntake` JSON. Foundry validates that contract and turns it into governed HTML/PDF/package artifacts. Deterministic code owns schema law, evidence validation, gate routing, rendering, verification, logs, and publishing. The LLM owns research behavior.

## Product loop

```text
keyword/topic -> LLM research session -> ResearchIntake JSON -> Foundry validation -> evidence graph -> report package
```

The foundry is not the AI provider, not the search provider, and not a crawler. Those are upstream capabilities. Foundry owns the invariant: every shipped claim/visual/layout decision must trace back to admissible source observations supplied in the contract or fail closed.

## Pipeline

```text
keyword/topic -> research-capable LLM/session -> observed sources/facts/claims/report text -> ResearchIntake JSON -> Foundry validation -> semantic IR/ReportSpec -> assets/charts -> HTML/PDF renderers -> QA score -> delivery
```

## Responsibility law

```text
LLM/session responsibilities:
  - use web/search/tools available in that session
  - observe and quote sources
  - choose relevant facts and claims
  - write report prose inside ResearchIntake
  - surface contradictions, uncertainty, and gaps

Foundry responsibilities:
  - provide prompt/schema law
  - validate IDs, links, citations, and source/fact/claim contracts
  - normalize valid intakes into EvidencePack/ReportSpec
  - route renderer/tool adapters fail-closed
  - produce HTML/PDF/package artifacts
  - write run logs and QA evidence

Not Foundry responsibilities:
  - autonomous web browsing without an explicit connector runtime
  - pretending a plain model endpoint has web_search tools
  - deciding facts without supplied source observations
  - hand-rolling PDF geometry with the LLM
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

## Principle lattice

The Report Foundry doctrine is [`docs/PRINCIPLE_LATTICE.md`](PRINCIPLE_LATTICE.md). Each Python source/script/test file carries `Lattice:` notation in its file description so code can be reviewed against the principle it claims to instantiate.

The eight principles are:

1. **RF-P1 Source Sovereignty** — source observations are the root of truth.
2. **RF-P2 Claim Traceability** — no orphan claims; every assertion has chain of custody.
3. **RF-P3 Provider and Renderer Agnosticism** — interfaces survive adapter swaps.
4. **RF-P4 Gates Fail Closed** — missing proof routes backward instead of shipping forward.
5. **RF-P5 Case Law Before Generation** — rubric/scope exist before prose.
6. **RF-P6 Visuals Are Claims** — charts/maps/matrices/timelines need provenance.
7. **RF-P7 Secrets Stay Handles** — keys connect capabilities but never become artifacts.
8. **RF-P8 Low Floor, High Ceiling** — simple commands, inspectable internals.

## Principles

- PDF is an artifact, not the source of truth.
- User keys are connection inputs, not artifacts: manifests reference provider/key handles or environment variable names, never raw API keys.
- Topic input is not scope input: the factory must infer what a serious analyst would be negligent to omit, then prove or drop those dimensions.
- The case-specific rubric is created before research/rendering and becomes the acceptance contract for the run.
- Claims carry citations at span/block level.
- A claim is invalid unless every backing fact resolves to an observed source.
- Extractors fail closed when expected facts cannot be found in the observed payload.
- LLMs may propose scope, sources, code, visuals, and prose, but deterministic gates decide what is admissible and shippable.
- Renderers are adapters: Playwright/Chromium is the strict ReportSpec PDF backend; ReportLab remains a legacy/basic renderer; WeasyPrint/PrinceXML/Typst are future adapters.
- Charts and diagrams should be SVG/vector-first.
- External assets require cached hashes, license metadata, alt text, and attribution.
- Every report should ship with optional provenance JSON.

## Enterprise integration shape

The same core should run as:

- CLI/library for local report runs.
- MCP server for Claude, ChatGPT, Ollama-backed agents, Hermes, and other tool-using clients.
- Server/queue deployment where companies connect databases, document stores, APIs, and internal MCP tools.

External and internal information enter through connectors, but the connector does not bypass source law: every ingested item must become a source observation with ID, timestamp, hash/fingerprint, trust tier, and extraction provenance.

## Renderer and asset adapters

- Playwright/Chromium: current strict ReportSpec HTML/CSS -> PDF backend.
- WeasyPrint: open-source paged-media HTML/CSS backend.
- PrinceXML: premium accessibility/archive publishing backend.
- Playwright screenshots: web-dashboard and visual QA backend.
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
