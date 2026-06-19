# Report Foundry

Report Foundry is a software toolkit for turning structured research into governed report artifacts.

Canonical product loop:

```text
user enters a keyword/topic
human or external report author searches, reads, and reasons over sources
author returns ResearchIntake JSON: sources, facts, claims, sections, exhibits
Foundry validates the contract and provenance links
Foundry builds the report package: evidence graph, visuals, layout, QA, export
```

Architecture law: the report author owns research behavior; Foundry owns evidence contracts, validation, rendering, logs, QA, and packaging. Foundry does not pretend to browse/search or require a model runtime to operate.

The governing doctrine lives in [`docs/PRINCIPLE_LATTICE.md`](docs/PRINCIPLE_LATTICE.md). Python source, scripts, and tests declare their local doctrine with a `Lattice:` notation in the file description; the test suite fails if new Python files omit or misname it.

## What exists now

- Top-level foundry intake contract: keyword/topic plus user-connected resource provider references.
- Pydantic report IR: sections, text, claims, citations, figures, metric cards, tables.
- Quality gates: unsupported claims, missing alt text warnings, ragged tables.
- HTML renderer for preview/share.
- Legacy PDF renderer via ReportLab for basic IR builds.
- Software-backed PDF renderer via Playwright/Chromium for strict ReportSpec compilation.
- CLI: `reportfoundry validate`, `reportfoundry build`, `reportfoundry plan-run`, and fixture adapter `reportfoundry research-run`.
- Example report fixture.
- Analyst-factory contracts: case rubric, source plan, visual plan, execution plan, gate routing.
- ResearchIntake contract: schema-only authoring prompt, structured full-report intake JSON, validation, and conversion to EvidencePack.

## Quick start

```bash
uv run --extra dev pytest -q
uv run reportfoundry validate examples/daily_systems_brief.json
uv run reportfoundry build examples/daily_systems_brief.json --out-dir .output
```

Outputs:

```text
.output/daily_systems_brief.html
.output/daily_systems_brief.pdf
```

## One-command research-intake smoke loop

Use `intake-run` for end-to-end Foundry verification. It creates a research gate
package, loads a supplied `ResearchIntake`, validates it, compiles artifacts,
runs artifact QA, and ends with a clean user handoff. This is a contract/render
loop, not a web-search crawler or authoring-runtime runner.

```bash
uv run reportfoundry intake-run \
  --topic "nvidia company history" \
  --intake-json path/to/research_intake.json \
  --out-dir .foundry_runs/nvidia-history
```

Successful output is intentionally sanitized:

```text
Here is your PDF
research intake: compiled
pdf: .foundry_runs/nvidia-history/compiled/research_intake.pdf
html: .foundry_runs/nvidia-history/compiled/research_intake.html
package manifest: .foundry_runs/nvidia-history/compiled/research_intake.package_manifest.json
run log: .foundry_runs/nvidia-history/run_log.json
```

Each run writes structured logs with step names, timings, statuses, adequacy
warnings, artifact QA checks, and artifact paths. Foundry does not call a model
or provide source-acquisition tools. Humans, external or tool-assisted authoring sessions, or external research systems
write the `ResearchIntake`; Foundry validates and renders it.

Scratch run directories are ignored by git via `.foundry_runs/`, `.foundry_*/`,
`.verify_tmp/`, and `foundry_verify_*/`.

## Foundry run shape

The real product run starts when a user supplies a topic and a ResearchIntake authored by a human, model-assisted authoring session, or external research system. Raw secrets are not stored in run manifests.

```text
FoundryRunRequest
  keyword: "current SpaceX IPO launch newsletter"
  source_namespaces: ["company-db", "public-web"]
```

Execution target:

```text
keyword/topic
  -> human or external report author observes sources outside Foundry
  -> ResearchIntake JSON: observed sources, facts, claims, report text, exhibits
  -> Foundry validates IDs, citations, provenance, adequacy, and schema
  -> Foundry compiles EvidencePack -> ReportSpec -> HTML/PDF/package
  -> Foundry logs QA and returns "Here is your PDF"
```

Responsibility split:

- Report author: search, read, quote, compare, reason, choose relevant facts, draft report text inside the schema.
- Foundry: prompt/schema law, strict validation, claim/source link checks, adequacy warnings, renderer routing, PDF/HTML/package generation, run logs, artifact QA.
- Not Foundry: general web crawling, source browsing, authoring-runtime orchestration, provider secret orchestration, or deciding facts without supplied evidence.


## Strict ResearchIntake for report authors

The report author is allowed to decide what sources, facts, claims, sections, contradictions, uncertainty notes, and exhibit proposals matter for the operator-provided keyword. The author may be human or external. They are not allowed to free-write an unstructured report or invent their own output shape.

Generate the schema-only prompt for the report author:

```bash
uv run reportfoundry research-intake-prompt --output prompts/research_intake_system.md
```

Compile strict author output into the Foundry pipeline:

```bash
uv run reportfoundry compile-intake research_intake.json --out-dir .output_intake
```

`ResearchIntake` is a structured full-report proposal. Foundry validates references before trust:

```text
operator keyword/request
  -> report author returns ResearchIntake JSON only
  -> Foundry validates sources/facts/claims/sections/exhibits
  -> EvidencePack
  -> ReportSpec
  -> package manifest
  -> renderer + QA gates
```

The prompt/schema intentionally contain no prefilled topic, URL, source ID, fact ID, claim ID, or example source. Runtime inputs fill those blanks.

## Factory run planning

Create the first executable factory package from a keyword/topic before source acquisition starts:

```bash
uv run reportfoundry plan-run "current SpaceX IPO launch newsletter" \
  --audience "executive readers" \
  --integration-mode adapter \
  --source company-db \
  --source web \
  --out-dir .factory-run/spacex-ipo
```

Outputs:

- `manifest.json` — topic, audience, integration mode, connected source namespaces, and rubric.
- `rubric.json` — case-specific report law created before research/rendering.
- `source_plan.json` — required source coverage per inferred dimension.
- `visual_plan.json` — provenance-required chart/map/matrix/timeline contracts.
- `execution_plan.json` — neutral pipeline topology: research, synthesis, visual, and QA tasks with dependency edges, expected outputs, completion signals, and health checks.
- `initial_gate_result.json` — fail-closed route-back result. A new run with no observed evidence should route to Research.

This is a planning package, not a completed deep-research report. Research/connectors must satisfy the source plan before synthesis/rendering can ship.

### Fixture adapter: local marked sources

`research-run` is a development/test adapter, not the product search path. It exists so the foundry can be tested without calling any external resource provider. It creates an evidence pack from local `.md`/`.txt` files whose claims are explicitly marked against the source plan:

```bash
uv run reportfoundry research-run .factory-run/spacex-ipo \
  --source-dir ./marked-sources
```

Marked source format:

```text
DIMENSION: starlink_economics
Starlink economics depends on subscriber and revenue scale because recurring broadband cash flow creates the strongest public-market proof point; 2026 disclosures matter.
```

Outputs:

- `evidence_pack.json` — observed local source records with SHA-256 hashes, extracted dimension facts, and source-bound claims.
- `research_gate_result.json` — factory gate result after research coverage. Missing dimension markers route back to Research.
- `research_run_log.json` — source-selection, extraction-step, and evidence-gap audit trail for the fixture run.

This mode is deterministic and local. It does not discover web sources or claim live facts by itself; it only normalizes marked source files into the evidence contract.

## Strict ReportSpec compilation

Compile an `evidence_pack.json` into the machine-checkable tool-feed layer and real artifacts:

```bash
uv run reportfoundry compile-spec .factory-run/spacex-ipo/evidence_pack.json \
  --out-dir .output_spec/spacex-ipo
```

Outputs:

- `*.evidence.json` — copied evidence input used by the renderer package.
- `*.spec.json` — strict ReportSpec: sections, claim fact IDs, visual provenance, source appendix, and renderer/tool routes.
- `*.json` — renderer-neutral Report IR compiled from the spec.
- `*.html` — HTML/CSS preview artifact.
- `*.pdf` — Playwright/Chromium print-to-PDF artifact from the generated HTML/CSS package.
- `*.layout.json` and `*.pages/` — PDF layout metrics and page previews for QA.
- `*.citations.json`, `*.citations.csl.json`, `*.citations.bib`, and `*.source_appendix.md` — citation/source appendix sidecars.
- `exhibits.json` plus `exhibits/*.vega.json` when formal Vega-Lite exhibits are present.
- `render_gate_result.json` and `*.render_artifact.json` — renderer route result and renderer artifact manifest.
- `*.package_manifest.json` — canonical package manifest listing package artifacts, gates, source paths, route, run mode, and success/failure status. The manifest indexes the package; it is returned by the CLI but not listed inside its own `artifacts` map.

This is the first practical version of the foundry toolkit model: a report author fills a strict plain-text+structured spec, Foundry routes that spec into software tools, and gates reject missing source/claim/visual provenance. The PDF route uses Chromium as the layout engine; the author does not hand-edit PDF geometry.

## Strategy truth

The PDF is not the source of truth. The canonical artifact is the semantic report package and its `*.package_manifest.json`, with claim-level provenance. Existing research, citation, exhibit, and rendering tools are adapters around Foundry's evidence law.

The single roadmap and developer handoff is [`docs/DEVELOPER_HANDOFF_ROADMAP.md`](docs/DEVELOPER_HANDOFF_ROADMAP.md). Work from that document first; older roadmap/backlog notes were removed to keep one design north.

See also `docs/ARCHITECTURE.md` for the current architecture and `docs/PRINCIPLE_LATTICE.md` for governing doctrine.
