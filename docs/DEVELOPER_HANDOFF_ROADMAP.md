# Developer Handoff Roadmap: Make Existing Deep-Research Tools Safe, Inspectable, and Publishable

## Purpose

Report Foundry should not become another deep-research agent. Existing open-source systems already perform retrieval, query decomposition, multi-agent research, RAG over documents, citation display, and Markdown/PDF report export.

Report Foundry should become the governed artifact layer around those systems:

```text
existing research / RAG / document tools
  -> ConnectorAdapter
  -> SourceObservation[]
  -> EvidenceFact[]
  -> EvidenceClaim[]
  -> EvidencePack
  -> fail-closed gates
  -> ReportSpec / CitationRecord / ExhibitSpec
  -> renderer adapters
  -> artifact package + QA
```

The product value is making research outputs **safe, inspectable, and publishable**:

- **Safe:** unsupported claims, missing source tiers, orphan visuals, stale links, and raw secrets cannot silently ship.
- **Inspectable:** every handoff is an artifact: manifest, source plan, run log, evidence pack, report spec, citation records, exhibit specs, renderer IR, QA result.
- **Publishable:** mature software handles citations, charts, typesetting, PDF rendering, screenshots, and package export.

## Current repo reality

Verified current state from repo docs and implementation:

- `FoundryRunRequest`, `ReportRunManifest`, `ReportRubric`, `SourcePlan`, `VisualPlan`, `WorkerTask`, and `FactoryGateResult` exist.
- `reportfoundry plan-run` persists a planning package.
- `reportfoundry research-run` is a deterministic local fixture path, not product search.
- `ResearchRunLog` now exists for fixture research and records selected sources, extraction steps, and evidence gaps.
- `SourceObservation` now carries initial metadata depth: `source_tier`, `publisher`, `published_at`, and `citation_metadata`.
- `insufficient_source_tier` exists as a Research gate warning.
- Strict ReportSpec compilation and Playwright/Chromium HTML-to-PDF exist.
- ReportLab legacy PDF exists but should not be the main professional path.
- Typst, Pandoc, Quarto, WeasyPrint, CSL/citeproc, Vega-Lite, Plotly/Kaleido, and Citation.js are researched but mostly not wired as adapters.

## Prior art reality

### Deep-research / report agents already exist

These systems cover research execution, RAG, citations, and report/article generation. Report Foundry should adapter-wrap them rather than duplicate them.

- [GPT Researcher](https://github.com/assafelovic/gpt-researcher)
  - Autonomous web/local research, planner/executor/publisher pattern, reports with citations, PDF/Word export.
  - Gap: no strict source-observation/fact/claim ledger, no fail-closed product gates, no governed renderer/citation/exhibit adapter layer.

- [STORM](https://github.com/stanford-oval/storm) / [STORM research preview](https://storm.genie.stanford.edu/)
  - Paper: [Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models](https://arxiv.org/abs/2402.14207)
  - Pre-writing research, multi-perspective question asking, references, outline, long-form cited article generation.
  - Gap: encyclopedic article workflow, not governed report artifact factory.

- [Co-STORM](https://arxiv.org/abs/2408.15232)
  - Collaborative knowledge curation, human steering, unknown-unknown discovery.
  - Gap: exploration and discourse, not deterministic evidence gates or artifact packaging.

- [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research)
  - LangGraph supervisor/sub-researcher orchestration with search/MCP/model configurability and cited reports.
  - Gap: prompt-enforced citations, not structural claim admissibility.

- [Open Deep Research / dzhng](https://github.com/dzhng/deep-research)
  - Minimal iterative breadth/depth research agent and Markdown report with sources.
  - Gap: useful small implementation, but little governance or publication machinery.

- [PaperQA](https://github.com/Future-House/paper-qa) / PaperQA2
  - Paper: [Language agents achieve superhuman synthesis of scientific knowledge](https://arxiv.org/abs/2409.13740)
  - Strong scientific-paper RAG, cited summaries, contradiction-oriented scientific synthesis.
  - Gap: scientific QA/synthesis substrate, not a general professional report factory.

- [Khoj](https://github.com/khoj-ai/khoj), [DocsGPT](https://github.com/arc53/DocsGPT), [deep-searcher](https://github.com/zilliztech/deep-searcher)
  - Private document search, agents, automations, RAG, enterprise/private-data retrieval.
  - Gap: search/assistant products, not fail-closed evidence-to-report artifact factories.

### Publishing/citation/exhibit tooling already exists

These should become adapters, not rewritten internals.

- [Pandoc](https://pandoc.org/) / [jgm/pandoc](https://github.com/jgm/pandoc)
  - Document AST/conversion, Markdown, citations, filters, many output formats.

- [Typst](https://typst.app/) / [typst/typst](https://github.com/typst/typst)
  - Modern high-quality programmable typesetting and PDF output.

- [Quarto](https://quarto.org/) / [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli)
  - Scientific/technical publishing built on Pandoc, notebooks, citations, crossrefs.

- [CSL](https://citationstyles.org/), [citeproc-js](https://github.com/Juris-M/citeproc-js), [CSL styles](https://github.com/citation-style-language/styles)
  - Citation style language and mature citation processors.

- [Citation.js](https://github.com/citation-js/citation-js)
  - Bibliography parsing/normalization/import-export utility.

- [Vega-Lite](https://vega.github.io/vega-lite/) / [vega/vega-lite](https://github.com/vega/vega-lite)
  - Declarative chart specs.

- [Mermaid](https://mermaid.js.org/) / [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid)
  - Diagrams as code.

- [Kaleido](https://github.com/plotly/Kaleido)
  - Static Plotly export.

- [Playwright](https://playwright.dev/) / [microsoft/playwright](https://github.com/microsoft/playwright)
  - Browser rendering, screenshot QA, pragmatic Chromium PDF route.

## Lattice fit

This roadmap is constrained by the Report Foundry Principle Lattice:

- **RF-P1 Source Sovereignty:** connector outputs must become observed sources with hashes/metadata before claims are admitted.
- **RF-P2 Claim Traceability:** no generated report text becomes valid unless claims resolve to facts and facts resolve to source observations.
- **RF-P3 Provider and Renderer Agnosticism:** GPT Researcher, STORM, PaperQA, Pandoc, Typst, CSL, Vega, and Playwright are adapters, not core law.
- **RF-P4 Gates Fail Closed:** product mode blocks unsupported/missing evidence instead of degrading to best-effort prose.
- **RF-P5 Case Law Before Generation:** rubric/source plan/visual plan are established before research and writing.
- **RF-P6 Visuals Are Claims:** charts, diagrams, maps, timelines, and tables need provenance fact IDs and transform metadata.
- **RF-P7 Secrets Stay Handles:** connector credentials are env var names/key handles only.
- **RF-P8 Low Floor, High Ceiling:** one command should run a product path; operators can inspect every artifact.

---

# Five-point implementation roadmap

## 1. Add `ConnectorAdapter` protocol

### Goal

Turn existing deep-research/RAG/search tools into source-observation producers without letting those tools define Report Foundry law.

### Why this is first

The current repo has `SourcePlan`, `ResearchRunLog`, and `EvidencePack`, but no real connector executing the plan. This is the boundary where Foundry stops being a fixture demo and starts wrapping real tools.

### Prior art to wrap

Initial adapter candidates:

1. **GPT Researcher adapter**
   - Source: https://github.com/assafelovic/gpt-researcher
   - Best for: general web/local-document reports with existing citation/report output.
   - Likely ingest formats: generated Markdown, source/citation lists, JSON/log artifacts if available.
   - Risk: its citations are not claim-law; Foundry must re-normalize.

2. **STORM adapter**
   - Source: https://github.com/stanford-oval/storm
   - Paper: https://arxiv.org/abs/2402.14207
   - Best for: broad topic exploration, perspectives, outline/reference generation.
   - Likely ingest formats: references, outline, generated article sections.
   - Risk: article citations are not enough; Foundry must extract/validate claims.

3. **PaperQA adapter**
   - Source: https://github.com/Future-House/paper-qa
   - PaperQA2: https://arxiv.org/abs/2409.13740
   - Best for: scientific/literature-heavy reports.
   - Likely ingest formats: cited answer, paper metadata, passages, document IDs.
   - Risk: scientific domain assumptions; not generic consulting/investor reports.

4. **MCP / local source adapter**
   - Best for: company docs, internal APIs, user-provided corpora.
   - Risk: tenant trust policy and secrets handling must be explicit.

### New models / files

Create:

- `src/report_foundry/connectors.py`
- `tests/test_connectors.py`

Suggested models:

```python
class ConnectorKind(StrEnum):
    GPT_RESEARCHER = "gpt_researcher"
    STORM = "storm"
    PAPERQA = "paperqa"
    MCP = "mcp"
    LOCAL_FIXTURE = "local_fixture"


class ConnectorRequest(BaseModel):
    run_id: str
    topic: str
    audience: str | None
    source_plan: SourcePlan
    credential_handle: str | None = None
    max_sources: int = 20
    run_mode: RunMode


class ConnectorSourceCandidate(BaseModel):
    candidate_id: str
    title: str
    url: str | None = None
    raw_locator: str | None = None
    source_tier: SourceTier = "unclassified"
    publisher: str | None = None
    published_at: str | None = None
    snippet: str | None = None
    decision: Literal["selected", "rejected", "pending"] = "pending"
    reason: str | None = None


class ConnectorResult(BaseModel):
    connector_name: str
    connector_version: str
    candidates: list[ConnectorSourceCandidate]
    observations: list[SourceObservation]
    raw_artifact_paths: list[str] = []
    warnings: list[str] = []
```

Protocol:

```python
class ConnectorAdapter(Protocol):
    name: str

    def collect(self, request: ConnectorRequest) -> ConnectorResult:
        ...
```

### Artifact handoff

Input:

```text
manifest.json
source_plan.json
connector config / credential handles
```

Output:

```text
connector_result.json
observed_sources/*.json or observed_sources/*.txt
research_run_log.json updated with queries/candidates/selected/rejected/gaps
```

### Gates

Add gates for:

- no selected source for required dimension
- missing source hash
- raw credential-looking payload in connector result
- selected source has no title/URL/path
- product mode selected source has `source_tier = unclassified`
- connector returned generated prose as a source observation without a real source locator

### Tests first

Write failing tests for:

- connector protocol rejects raw secret fields in public models
- connector result converts selected candidate to `SourceObservation` with hash and observed timestamp
- missing required dimension writes `ResearchEvidenceGap`
- product mode treats unclassified source tier as error
- fixture mode allows warning but labels artifact non-product

### Acceptance criteria

- A fake connector fixture can satisfy one required dimension and leave another as a gap.
- `research_run_log.json` records candidates, decisions, and gaps.
- Product mode blocks unclassified/missing source metadata.
- No provider-specific fields leak into `EvidencePack` core models.

### Verified fulfillment — 2026-06-18

Implemented in `src/report_foundry/connectors.py` with tests in `tests/test_connectors.py`:

- `ConnectorAdapter` protocol plus `ConnectorRequest`, `ConnectorResult`, `ConnectorSourceCandidate`, `ConnectorKind`, and initial `RunMode`.
- Public connector models use `extra="forbid"`; raw secret-like fields and raw secret-looking credential handles are rejected.
- `FakeConnectorAdapter` converts selected candidates into hashed `SourceObservation` records with observed timestamps.
- Connector handoff produces a `ResearchRunLog` carrying candidate decisions and `ResearchEvidenceGap` entries for uncovered required dimensions.
- `connector_result_gate_checks()` treats unclassified selected sources as fixture warnings but product/experiment errors.
- Verified by `uv run --extra dev pytest tests/test_connectors.py -q` and full suite `uv run --extra dev pytest -q`.

---

## 2. Add `RunMode` / product-vs-fixture governance

### Goal

Make the system honest about whether an artifact is a local fixture/proof-of-pipeline or a real product research run.

### Why this matters

The repo currently warns that `research-run` is a deterministic local fixture, but gate severity does not fully encode that distinction. Without explicit mode, fixture behavior can get mistaken for product behavior.

### New model

Add to `factory.py` or a shared contract module:

```python
class RunMode(StrEnum):
    FIXTURE = "fixture"
    PRODUCT = "product"
    EXPERIMENT = "experiment"
```

Add fields:

- `ReportRunManifest.run_mode: RunMode = RunMode.FIXTURE`
- `ResearchRunLog.run_mode`
- generated artifact metadata: `artifact_status = fixture | product | experiment`

CLI behavior:

```bash
reportfoundry plan-run "topic" --run-mode product ...
reportfoundry research-run RUN_DIR --source-dir SOURCES
reportfoundry research-run RUN_DIR --source-dir SOURCES --allow-fixture-sources  # explicit product-mode override
```

Default should remain `fixture` until a real connector exists. Product mode should require a connector, not local marked files unless explicitly allowed.

### Gate policy

Fixture mode:

- source-tier deficits: warning
- missing citation metadata: warning
- local fixture source: allowed
- output labeled non-product

Product mode:

- source-tier deficits: error
- missing source hash: error
- missing title/URL/path: error
- unsupported claims: error
- visual without fact IDs: error
- raw model prose as source observation: error
- raw credential in model/artifact: error

Experiment mode:

- like product for secrets and source hashes
- warnings allowed for incomplete source tiers
- output labeled experimental

### Artifact handoff

Every artifact should disclose mode:

```text
manifest.json -> run_mode
research_run_log.json -> run_mode
EvidencePack.scope -> run_mode
ReportSpec.generation_metadata -> run_mode
QA result -> mode-sensitive gate severities; product blockers are represented as error checks
```

### Tests first

Write failing tests for:

- `plan-run --run-mode product` persists product mode.
- product mode promotes `insufficient_source_tier` to error.
- fixture mode keeps the same condition as warning.
- product mode cannot use local fixture research unless `--allow-fixture-sources` or equivalent exists.
- rendered artifact metadata includes run mode.

### Acceptance criteria

- One test proves the same `EvidencePack` gets different severity under fixture vs product mode.
- Product mode cannot silently ship weak source evidence.
- CLI output clearly says when a run is fixture-only.

### Fulfilled in this pass

Verified by `uv run --extra dev pytest -q` -> `52 passed in 14.03s`.

Implemented:

- `RunMode` is centralized in `src/report_foundry/factory.py` and reused by connector contracts.
- `ReportRunManifest.run_mode` defaults to `fixture` and is persisted by `plan-run`.
- `ResearchRunLog.run_mode`, `EvidencePack.scope["run_mode"]`, `EvidencePack.scope["artifact_status"]`, and `ReportSpec.generation_metadata` now disclose mode.
- `plan-run --run-mode product` writes product mode and prints `mode=product`.
- `research-run` rejects product manifests that point at local marked fixture sources unless `--allow-fixture-sources` is explicit.
- Product mode promotes source-tier deficits from warning to error; fixture mode keeps the same deficit as warning.
- Product override still fails closed when local fixtures cannot satisfy product source-tier quotas.

Remaining from the broader gate-policy list:

- Dedicated top-level QA-result `run_mode` / `product_blockers` fields are not yet added; current behavior represents product blockers as mode-sensitive error checks.
- Missing citation metadata, visual fact-ID, and raw prose-as-source policies are partly covered by existing evidence/connector gates but not all are product-mode-specific yet.

---

## 3. Add `CitationRecord` and CSL/BibTeX seam

### Goal

Separate audit provenance from reader-facing citations, then delegate formatting to CSL/citeproc-style tools.

### Why this matters

Hashes and source IDs are audit metadata. Readers need title, author/publisher, URL/path, date, locator, and access date. Existing citation ecosystems already solve style formatting; Foundry should not hand-roll APA/MLA/Chicago/etc.

### Prior art to reuse

- [Citation Style Language](https://citationstyles.org/)
- [CSL styles](https://github.com/citation-style-language/styles)
- [citeproc-js](https://github.com/Juris-M/citeproc-js)
- [Citation.js](https://github.com/citation-js/citation-js)
- [Pandoc citations](https://pandoc.org/MANUAL.html#citations)
- [Zotero translators](https://github.com/zotero/translators)
- [Better BibTeX for Zotero](https://github.com/retorquere/zotero-better-bibtex)

### New models / files

Create:

- `src/report_foundry/citations.py`
- `tests/test_citations.py`

Suggested models:

```python
class CitationRecord(BaseModel):
    citation_id: str
    source_id: str
    title: str
    url: str | None = None
    author: list[str] = Field(default_factory=list)
    publisher: str | None = None
    issued: str | None = None
    accessed: str
    locator: str | None = None
    source_tier: SourceTier = "unclassified"
    content_sha256: str


class CitationExport(BaseModel):
    records: list[CitationRecord]
    csl_json: list[dict[str, object]]
    bibtex: str | None = None
```

Functions:

```python
def citation_records_from_evidence(evidence: EvidencePack) -> list[CitationRecord]:
    ...


def export_csl_json(records: list[CitationRecord]) -> list[dict[str, object]]:
    ...


def export_bibtex(records: list[CitationRecord]) -> str:
    ...
```

### Artifact handoff

Input:

```text
EvidencePack.sources
EvidencePack.facts.locator
EvidenceClaim.fact_ids
```

Output:

```text
citations.json
citations.csl.json
citations.bib
source_appendix.md/json
```

### Gates

Add gates for:

- claim references fact whose source has no citation record
- citation record missing reader title
- citation record missing URL/path
- product citation missing accessed timestamp
- duplicate citation IDs
- rendered source appendix missing visible URL/path

### Renderer integration

Short-term:

- Render simple source appendix from `CitationRecord`.
- Include title + URL/path + accessed date + quote locator.

Medium-term:

- Feed CSL JSON into Pandoc/citeproc or Citation.js/citeproc.
- Keep exact quote locator in Foundry metadata even when style output omits it.

### Tests first

Write failing tests for:

- `CitationRecord` preserves source hash but does not expose hash as primary reader citation.
- CSL JSON export includes title/URL/accessed.
- source appendix renders human-usable URLs.
- claim with missing citation metadata fails product gate.

### Acceptance criteria

- `EvidencePack -> citations.json -> source appendix` works without renderer coupling.
- Rendered report shows human-usable citations, not only hashes/IDs.
- CSL JSON export is valid enough for Pandoc/citeproc integration.

### Fulfilled in this pass

Verified by `uv run --extra dev pytest -q` -> `58 passed in 13.81s`.

Implemented:

- Added `src/report_foundry/citations.py` with `CitationRecord`, `CitationExport`, `citation_records_from_evidence`, `export_csl_json`, `export_bibtex`, and `render_source_appendix_markdown`.
- Added `tests/test_citations.py` covering hash retention, reader-facing appendix output, CSL JSON export, BibTeX export, duplicate citation IDs, and product citation gates.
- `ReportSpec.source_appendix` now uses citation IDs and reader fields (`Citation`, `Title`, `URL/Path`, `Accessed`, `Locator`) instead of raw source hash columns.
- `ReportSpec.citation_source_map` preserves the internal citation-ID -> source-ID bridge so claim citations still resolve to source-backed facts.
- `write_spec_artifacts` now emits `*.citations.json`, `*.citations.csl.json`, `*.citations.bib`, and `*.source_appendix.md` alongside spec/IR/HTML/PDF artifacts.
- Factory gates now include citation contract checks; product mode promotes missing reader URL/path/locator to an error while fixture mode treats it as a warning.
- Source appendix Markdown deliberately keeps full hashes out of the reader-primary citation surface while preserving `content_sha256` in `citations.json`.

Remaining / not claimed:

- No external Pandoc/citeproc/Citation.js process is invoked yet; CSL JSON/BibTeX are handoff artifacts for a later adapter.
- Rendered-source-appendix visibility is covered by emitted Markdown and ReportSpec/IR report citations; a dedicated visual/PDF assertion for the appendix page can be strengthened when renderer adapter contracts are split out.

---

## 4. Add `ExhibitSpec` with Vega-Lite as first chart adapter

### Goal

Treat visuals as source-backed claims, not decoration.

### Why this matters

The current repo has `VisualPlan`, draft exhibits, Mermaid evidence maps, and strict ReportSpec visuals. But charts/tables/diagrams need a formal provenance-bearing spec before renderer adapters produce images/SVG/PDF objects.

### Prior art to reuse

- [Vega-Lite](https://vega.github.io/vega-lite/) / [vega/vega-lite](https://github.com/vega/vega-lite)
- [Vega](https://vega.github.io/vega/) / [vega/vega](https://github.com/vega/vega)
- [Mermaid](https://mermaid.js.org/) / [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid)
- [Kaleido](https://github.com/plotly/Kaleido)
- [Observable Plot](https://observablehq.com/plot/)

### New models / files

Create:

- `src/report_foundry/exhibits.py`
- `src/report_foundry/exhibit_adapters.py`
- `tests/test_exhibits.py`

Suggested models:

```python
class ExhibitKind(StrEnum):
    CHART = "chart"
    TABLE = "table"
    DIAGRAM = "diagram"
    TIMELINE = "timeline"
    MATRIX = "matrix"
    IMAGE = "image"


class ExhibitDataPoint(BaseModel):
    label: str
    value: int | float | str
    unit: str | None = None
    fact_id: str
    transform_note: str | None = None


class ExhibitSpec(BaseModel):
    exhibit_id: str
    title: str
    kind: ExhibitKind
    insight: str
    fact_ids: list[str]
    data: list[ExhibitDataPoint] = Field(default_factory=list)
    renderer_route: Literal["vega_lite", "mermaid", "table", "kaleido", "image"]
    alt_text: str
    transform_provenance: list[str] = Field(default_factory=list)
```

Adapter protocol:

```python
class ExhibitAdapter(Protocol):
    route: str

    def render(self, spec: ExhibitSpec, evidence: EvidencePack, out_dir: Path) -> ExhibitArtifact:
        ...
```

### Artifact handoff

Input:

```text
visual_plan.json
EvidencePack facts
ExhibitSpec[]
```

Output:

```text
exhibits.json
exhibits/<exhibit_id>.vega.json
exhibits/<exhibit_id>.svg/png
exhibit_gate_result.json
```

### Gates

Add gates for:

- exhibit has no `fact_ids`
- exhibit references unknown fact ID
- data point references unknown fact ID
- insight makes a claim not backed by facts
- missing alt text
- missing transform provenance for derived numbers
- renderer route unavailable

### First adapter choice

Implement **Vega-Lite first** because it is:

- declarative JSON
- renderer-independent
- easy to store as artifact
- mature OSS
- compatible with HTML, SVG, PNG/PDF export paths

Mermaid should become a formal adapter too, but Vega-Lite gives charts/tables stronger data provenance leverage.

### Tests first

Write failing tests for:

- exhibit without fact IDs fails.
- exhibit with unknown fact ID fails.
- Vega-Lite adapter emits `.vega.json` with data values tied to facts.
- renderer IR includes exhibit artifact paths and alt text.

### Acceptance criteria

- A simple chart can be generated from facts into `exhibits/*.vega.json`.
- Missing provenance blocks product mode.
- ReportSpec can reference exhibit artifacts without knowing adapter internals.

---

## 5. Add `RendererAdapter` package path with Typst/Pandoc/Playwright split

### Goal

Stop treating rendering as one hardwired path. Make mature renderers swappable while Foundry preserves evidence and QA law.

### Why this matters

The current strict path is HTML/CSS -> Playwright/Chromium PDF. That is pragmatic and useful for QA, but professional reports need cleaner adapter boundaries. Typst/Pandoc/Quarto/WeasyPrint should be routes, not roadmap names.

### Prior art to reuse

- [Typst](https://typst.app/) / [typst/typst](https://github.com/typst/typst) for high-polish PDF/typesetting.
- [Pandoc](https://pandoc.org/) / [jgm/pandoc](https://github.com/jgm/pandoc) for Markdown/AST/conversion/citations.
- [Quarto](https://quarto.org/) / [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli) for scientific/technical documents and notebooks.
- [WeasyPrint](https://github.com/Kozea/WeasyPrint) for Python HTML/CSS-to-PDF.
- [Playwright](https://playwright.dev/) for browser screenshots, HTML inspection, and pragmatic PDF.

### New models / files

Create:

- `src/report_foundry/renderers.py`
- `tests/test_renderer_adapters.py`

Suggested protocol:

```python
class RenderRequest(BaseModel):
    report_spec_path: Path
    evidence_pack_path: Path
    citation_records_path: Path | None = None
    exhibit_specs_path: Path | None = None
    route: str
    out_dir: Path
    run_mode: RunMode


class RenderArtifact(BaseModel):
    route: str
    html_path: str | None = None
    pdf_path: str | None = None
    source_paths: list[str] = Field(default_factory=list)
    preview_paths: list[str] = Field(default_factory=list)
    metrics_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RendererAdapter(Protocol):
    route: str

    def render(self, request: RenderRequest) -> RenderArtifact:
        ...
```

### Route priorities

1. **Keep `playwright_chromium` as baseline**
   - Already exists.
   - Useful for screenshots and visual QA.
   - Do not remove.

2. **Add `typst` spike**
   - Best candidate for professional static PDF.
   - Should consume a renderer-neutral report package, not raw EvidencePack.
   - Output `.typ` source + PDF.

3. **Add `pandoc` citation route**
   - Useful for Markdown + CSL/citeproc pipelines.
   - Can prove CitationRecord -> CSL JSON -> formatted bibliography.

4. **Optional `quarto` route**
   - Use for notebook/scientific report package only if needed.

5. **Optional `weasyprint` route**
   - Use for CSS paged-media comparison if Playwright output becomes limiting.

### Artifact handoff

Input:

```text
ReportSpec
CitationRecord[]
ExhibitSpec[]
RendererRoute
```

Output:

```text
rendered/report.html
rendered/report.pdf
rendered/report.typ or report.md when applicable
rendered/previews/page-*.png
rendered/layout_metrics.json
render_gate_result.json
```

### Gates / QA

Renderer-independent gates:

- source appendix present
- citations visible in rendered text
- report title visible
- required sections visible
- exhibit alt text visible or embedded
- rendered PDF exists and text extracts
- page count within rubric bounds
- no clipped text if detector exists
- screenshot previews generated in product mode

Route-specific checks:

- Typst: `.typ` source saved, PDF produced, text extracted.
- Pandoc: CSL JSON accepted, bibliography rendered.
- Playwright: HTML screenshot and PDF preview generated.

### Tests first

Write failing tests for:

- renderer adapter protocol produces `RenderArtifact` without mutating evidence contracts.
- unknown renderer route fails closed.
- Playwright route emits previews/metrics in product mode.
- Typst route can be skipped with clear unavailable-tool gate if binary missing, not silent success.

### Acceptance criteria

- CLI can select route:

```bash
reportfoundry compile-spec evidence_pack.json --route playwright_chromium --out-dir out
reportfoundry compile-spec evidence_pack.json --route typst --out-dir out
reportfoundry compile-spec evidence_pack.json --route pandoc --out-dir out
```

- If a route is unavailable, the gate records a real failure reason.
- Report Foundry never changes evidence law to satisfy a renderer.

---

# Cross-cutting worker/execution handoff

The five points above need one execution seam:

```text
RunPackage
  -> ConnectorAdapter.collect()
  -> ResearchRunLog + SourceObservation[]
  -> extraction / claim normalization
  -> EvidencePack
  -> CitationRecord[]
  -> ExhibitSpec[]
  -> ReportSpec
  -> RendererAdapter.render()
  -> QA gates
  -> artifact package
```

## Suggested run package structure

```text
.run/<run_id>/
  manifest.json
  rubric.json
  source_plan.json
  visual_plan.json
  worker_plan.json
  connector_result.json
  research_run_log.json
  observed_sources/
  evidence_pack.json
  citations.json
  citations.csl.json
  exhibits.json
  exhibits/
  report.spec.json
  renderer_ir.json
  rendered/
    report.html
    report.pdf
    page-1.png
    layout_metrics.json
  gate_results/
    initial_gate_result.json
    research_gate_result.json
    citation_gate_result.json
    exhibit_gate_result.json
    render_gate_result.json
    final_gate_result.json
```

## Minimum CLI path

Final low-floor command target:

```bash
uv run reportfoundry run "current SpaceX IPO launch newsletter" \
  --audience "executive readers" \
  --run-mode product \
  --connector gpt-researcher \
  --renderer playwright_chromium \
  --out-dir .factory-run/spacex-ipo
```

Operator/high-ceiling path:

```bash
uv run reportfoundry plan-run ...
uv run reportfoundry collect-sources RUN_DIR --connector gpt-researcher
uv run reportfoundry normalize-evidence RUN_DIR
uv run reportfoundry build-citations RUN_DIR
uv run reportfoundry build-exhibits RUN_DIR
uv run reportfoundry compile-spec RUN_DIR --route typst
uv run reportfoundry qa RUN_DIR
uv run reportfoundry package RUN_DIR
```

---

# Recommended implementation order

## Phase 1 — Connector seam and run mode

Build:

1. `RunMode`
2. `ConnectorAdapter` protocol
3. `FakeConnectorAdapter` for tests
4. product-vs-fixture gate severity split
5. `collect-sources` CLI that writes `connector_result.json` and updates `research_run_log.json`

Why first:

- It proves Foundry can wrap external tools without depending on them yet.
- It resolves fixture/product ambiguity.
- It gives a stable target for GPT Researcher/STORM/PaperQA adapters.

## Phase 2 — First real adapter

Pick one:

- **GPT Researcher** if the goal is broad web/deep-research reports.
- **PaperQA** if the goal is scientific/literature report credibility.
- **STORM** if the goal is outline/perspective-rich knowledge curation.

Recommendation: start with **GPT Researcher ingestion**, because it most closely matches general report generation and already has report/source outputs. Keep adapter ingest-only at first; do not embed it as a hard dependency.

Build:

1. Parse GPT Researcher output/source list into `ConnectorResult`.
2. Convert selected sources to `SourceObservation`.
3. Preserve raw output path under run package.
4. Extract claims only through Foundry normalization, not by trusting the report prose.

## Phase 3 — Citation seam

Build:

1. `CitationRecord`
2. `citations.json`
3. `citations.csl.json`
4. simple source appendix renderer
5. product gates for missing citation metadata

Why before renderer polish:

- Reader-visible citations are part of publishability.
- CSL/Pandoc/Typst integration needs a stable citation artifact.

## Phase 4 — ExhibitSpec and Vega-Lite

Build:

1. `ExhibitSpec`
2. `VegaLiteExhibitAdapter`
3. gate that every exhibit references known fact IDs
4. `exhibits.json` and rendered `.vega.json` artifacts

Why now:

- Visuals are claims under RF-P6.
- Charts need source-backed data before professional templates matter.

## Phase 5 — RendererAdapter and package QA

Build:

1. `RendererAdapter` protocol
2. formalize existing Playwright route as adapter
3. add Typst spike route
4. add Pandoc citation proof route
5. final package manifest and QA summary

Why last:

- Renderer polish is downstream of evidence/citation/exhibit truth.
- Mature tools can be swapped once artifact contracts are stable.

---

# Development rules for implementers

## TDD required

Every phase starts with failing tests:

```bash
uv run --extra dev pytest tests/test_<feature>.py -q
```

Then implement minimal code and run:

```bash
uv run --extra dev pytest -q
```

Test count must not decrease.

## No provider leakage

Core contracts must not import GPT Researcher, STORM, PaperQA, Pandoc, Typst, or Playwright-specific objects. Those live behind adapters.

Bad:

```python
class EvidencePack(BaseModel):
    gpt_researcher_sources: list[...]
```

Good:

```python
class ConnectorResult(BaseModel):
    connector_name: str
    observations: list[SourceObservation]
```

## No raw secrets

Never add fields named or shaped like:

```text
api_key
secret
token
password
```

Use:

```text
credential_handle
env_var_name
provider_ref
```

## Artifacts over hidden state

If a step matters, it writes an artifact. Internal agent memory is not an audit trail.

## Gate failures route backward

Do not convert gate errors into warnings just to make a demo pass. If a product path lacks evidence, it routes back to the responsible department.

---

# Open decisions for Lucid

These need operator choice before implementation beyond Phase 1:

1. **First real adapter:** GPT Researcher, STORM, PaperQA, or MCP/internal source?
2. **First product report class:** executive/current-events brief, investor memo, scientific literature review, or internal knowledge report?
3. **Renderer priority:** Typst first, or formalize Playwright and add visual QA first?
4. **Citation engine:** Python-only CSL/BibTeX export first, or Node-based Citation.js/citeproc integration?
5. **Workflow runner:** simple local CLI sequence first, Hermes subagents, or a durable queue/server?

Default recommendation:

```text
Phase 1: RunMode + ConnectorAdapter + FakeConnectorAdapter
Phase 2: GPT Researcher ingest adapter
Phase 3: CitationRecord + CSL JSON
Phase 4: ExhibitSpec + Vega-Lite
Phase 5: RendererAdapter formalization + Typst spike
```

This keeps Foundry focused: not another research agent, but the system that makes research agents safe, inspectable, and publishable.
