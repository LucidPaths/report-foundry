# Report Foundry Principle Lattice

**A factory for claims that can survive inspection.**

---

## What This Is

These are Report Foundry's axiomatic principles. They are doctrine, not decoration. Every durable code path should be traceable to one or more principles using a `Lattice:` notation in the file description.

A principle without an instantiation is a wish. Report Foundry does not ship wishes; it ships artifacts with receipts.

The foundry serves two readers at once:

- **The operator** who wants to type a topic and get a credible report package without hand-building scope, citations, visuals, and QA.
- **The analyst/power user** who wants inspectable source law, explicit gates, replaceable providers, and artifacts that can be challenged line-by-line.

Low floor. High ceiling. Hard receipts.

---

## Notation

Every Python source/test/script file should declare its local doctrine in a file description:

```python
"""Evidence contracts for observed sources, facts, and supported claims.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed.
"""
```

Use the smallest accurate set. The notation is a checksum: if a change violates the named principle, the change is wrong even if tests pass.

---

## The Eight Principles

### RF-P1. Source Sovereignty

> *The source observation is the root of truth. Models are witnesses, not authorities.*

Every shipped fact, claim, chart, and layout decision must originate from an observed source payload with an ID, timestamp, locator/URL when available, extractor, and content fingerprint. The PDF is never the source of truth; the evidence package is.

**Instantiations:**

- `SourceObservation` carries source ID, title, URL, observed timestamp, SHA-256, extractor, and locator.
- Evidence packs store source observations separately from facts and claims.
- Observed payload fixtures are hashed before claims enter the report.
- Local marked-source research is labeled as a fixture adapter, not a truth oracle.

**Demands:**

- New connectors must emit source observations before extraction.
- No direct model prose may bypass source observation.
- External assets require cached hashes, licenses, alt text, and attribution before shipping.

---

### RF-P2. Claim Traceability

> *No orphan claims. Every assertion has a chain of custody.*

A claim is admissible only when it resolves through fact IDs to extracted facts and from there to observed sources. Uncited or weakly cited claims are defects, not style choices.

**Instantiations:**

- `EvidenceClaim.fact_ids` is validated against known facts.
- `build_report_from_evidence()` converts fact/source lineage into block-level citations.
- `run_quality_gates()` rejects report claims without citations.
- Research fixture claims cite their generated dimension facts.

**Demands:**

- Claim extraction must preserve fact IDs, confidence, quote, and locator.
- Citation checks should become stricter over time: quote presence, entailment, source tier, and freshness.
- Renderers must preserve provenance visibility, not hide it in sidecars only.

---

### RF-P3. Provider and Renderer Agnosticism

> *Interfaces are permanent. Providers and renderers are replaceable.*

Report Foundry is the invariant system. Research providers, internal databases, source tools, renderers, and PDF engines are adapters. Swapping one should not rewrite report law.

**Instantiations:**

- `FoundryRunRequest` stores provider/key references, not raw secrets or provider-specific payloads.
- Pipeline stages are named independently of any vendor.
- Report IR is renderer-neutral; HTML and ReportLab consume the same structure.
- Roadmap adapters include WeasyPrint, PrinceXML, Typst, Playwright, Vega/Plotly/Mermaid.

**Demands:**

- New research provider = connector adapter, not factory rewrite.
- New renderer = renderer adapter, not evidence/QA rewrite.
- Core logic must avoid hardcoded model/provider assumptions.

---

### RF-P4. Gates Fail Closed

> *Missing proof routes backward. It never silently ships forward.*

When required scope, source coverage, evidence, visual provenance, layout, or QA conditions are missing, the pipeline stops and names the responsible department. A partial artifact can be useful internally, but it must be labeled as incomplete.

**Instantiations:**

- Initial `plan-run` creates an empty evidence pack and routes back to Research.
- Factory gates detect missing dimensions, weak claim density, missing source appendix, underfilled pages, overlap, and clipping.
- Evidence validation rejects unknown source/fact references.
- CLI exits non-zero when research gates fail.

**Demands:**

- New gates must identify route-back department and actionable failure reason.
- No successful CLI exit for artifacts that violate error-severity gates.
- Warnings must be deliberate and visible; errors must block shipping.

---

### RF-P5. Case Law Before Generation

> *Scope is inferred before prose. The rubric is the contract.*

A topic is not enough. The foundry must infer what a serious analyst would be negligent to omit, write that into a case-specific rubric, then force research, visuals, synthesis, layout, and QA to satisfy it.

**Instantiations:**

- `build_case_rubric()` expands topics into required dimensions, source tiers, visuals, claim density, page limits, and score thresholds.
- SpaceX IPO and European banking topics produce domain-specific dimensions.
- `source_plan.json`, `visual_plan.json`, and `rubric.json` are persisted before research/rendering.

**Demands:**

- New domains should add rubrics only when the required dimensions are meaningfully different.
- The rubric must be written before connectors run or prose is generated.
- QA evaluates against the original rubric, not against whatever the artifact happened to become.

---

### RF-P6. Visuals Are Claims

> *A chart, map, matrix, or timeline asserts structure. It needs provenance too.*

Visuals are not decoration. Every visual encodes a claim about numbers, relationships, geography, sequence, or risk. Therefore visuals need source-backed inputs, acceptance rules, alt text, and layout QA.

**Instantiations:**

- `VisualPlanItem` requires provenance by default.
- Factory visual plans assign purpose, type, and acceptance rule per required visual.
- Report QA warns on missing alt text.
- Layout gates track fill, source appendix presence, overlap, and clipped text.

**Demands:**

- Decorative generated images must be explicitly marked decorative or rejected.
- Chart adapters must record source IDs and data transforms.
- Screenshot/visual QA should become part of final artifact verification.

---

### RF-P7. Secrets Stay Handles

> *Keys connect capabilities. They do not become artifacts.*

User API keys and internal credentials may enable connectors, but raw secrets must never appear in run manifests, evidence packs, reports, logs, commits, Discord messages, or docs.

**Instantiations:**

- Core run requests store topic and optional source namespaces, not provider credentials or raw keys.
- Intake models forbid extra raw key fields.
- Discord-ready output is sanitized before external delivery.

**Demands:**

- Every external post must be scanned/sanitized first.
- New config files store key names, vault references, or connector IDs only.
- Tests should reject credential-shaped fields in typed public artifacts.

---

### RF-P8. Low Floor, High Ceiling

> *One command for beginners. Full inspection for operators.*

The simple path should work with a topic and sane defaults. The advanced path should expose the run manifest, source plan, visual plan, evidence pack, QA result, renderer outputs, and provenance sidecars.

**Instantiations:**

- `reportfoundry plan-run "topic"` creates a readable run package.
- `reportfoundry validate` and `reportfoundry build` are small CLI surfaces over typed internals.
- Deterministic local fixture mode allows testing without provider setup.
- Outputs are plain JSON/HTML/PDF, inspectable outside the program.

**Demands:**

- Zero-config paths must remain useful.
- Advanced controls should be explicit flags/artifacts, not hidden magic.
- Every artifact should be understandable by a human and consumable by another tool.

---

## Using The Lattice

### Design Decisions

When choosing between approaches, score them against the lattice. If a design violates any principle, look for a third path.

Examples:

- Direct model-to-PDF generation violates RF-P1, RF-P2, RF-P4, and RF-P6.
- Provider-specific source logic in UI/CLI violates RF-P3.
- A beautiful chart with no source data violates RF-P6.
- A manifest containing raw API keys violates RF-P7.

### Code Review

Every change should answer:

- Which principles does this instantiate?
- Which principle could this accidentally violate?
- Is the `Lattice:` notation still true after the change?
- Did tests exercise the named gate or contract?

### New Files

New Python files must include `Lattice:` in the file description. The test suite enforces this so the doctrine does not become wallpaper.
