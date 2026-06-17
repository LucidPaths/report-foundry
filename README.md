# Report Foundry

AI-native report foundry: user-connected AI/search turns a keyword into a grounded report package.

Canonical product loop:

```text
user connects their own AI/search key
user enters a keyword/topic
AI searches and gathers sources
foundry normalizes sources into evidence
foundry builds the report package: rubric, facts, claims, visuals, layout, QA, export
```

Report Foundry is the system that owns source law, evidence validation, gate routing, rendering, verification, and publishing. AI/search providers are connected capabilities; they are not the foundry.

The governing doctrine lives in [`docs/PRINCIPLE_LATTICE.md`](docs/PRINCIPLE_LATTICE.md). Python source, scripts, and tests declare their local doctrine with a `Lattice:` notation in the file description; the test suite fails if new Python files omit it.

## What exists now

- Top-level foundry intake contract: keyword/topic plus user-connected AI/search provider references.
- Pydantic report IR: sections, text, claims, citations, figures, metric cards, tables.
- Quality gates: unsupported claims, missing alt text warnings, ragged tables.
- HTML renderer for preview/share.
- Real PDF renderer via ReportLab.
- CLI: `reportfoundry validate`, `reportfoundry build`, `reportfoundry plan-run`, and fixture adapter `reportfoundry research-run`.
- Example report fixture.
- Analyst-factory contracts: case rubric, source plan, visual plan, gate routing.

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

## Foundry run shape

The real product run starts when a user connects their own AI/search provider key and submits a keyword/topic. The key is referenced through environment/config; raw secrets are not stored in run manifests.

```text
FoundryRunRequest
  keyword: "current SpaceX IPO launch newsletter"
  ai: provider + api_key_env_var
  search: provider + api_key_env_var
```

Execution target:

```text
keyword/topic
  -> AI search over web/user-connected sources
  -> observed source payloads with hashes
  -> extracted facts
  -> supported claims
  -> visual/layout plan
  -> QA gates
  -> export package
```

## Factory run planning

Create the first executable factory package from a keyword/topic before source acquisition starts:

```bash
uv run reportfoundry plan-run "current SpaceX IPO launch newsletter" \
  --audience "executive readers" \
  --integration-mode mcp \
  --source company-db \
  --source web \
  --out-dir .factory-run/spacex-ipo
```

Outputs:

- `manifest.json` — topic, audience, integration mode, connected source namespaces, and rubric.
- `rubric.json` — case-specific report law created before research/rendering.
- `source_plan.json` — required source coverage per inferred dimension.
- `visual_plan.json` — provenance-required chart/map/matrix/timeline contracts.
- `initial_gate_result.json` — fail-closed route-back result. A new run with no observed evidence should route to Research.

This is a planning package, not a completed deep-research report. Research/connectors must satisfy the source plan before synthesis/rendering can ship.

### Fixture adapter: local marked sources

`research-run` is a development/test adapter, not the product search path. It exists so the foundry can be tested without calling an AI/search provider. It creates an evidence pack from local `.md`/`.txt` files whose claims are explicitly marked against the source plan:

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

This mode is deterministic and local. It does not discover web sources or claim live facts by itself; it only normalizes marked source files into the evidence contract.

## Ollama Cloud newsletter path

Generate a live model brief from Ollama Cloud. The script now writes a mechanically sourced evidence pack, semantic IR, designed HTML preview, deterministic PDF, and Discord-ready attachment message:

```bash
uv run python scripts/ollama_daily_newsletter.py --out-dir .output
uv run reportfoundry validate .output/ollama_cloud_field_brief.json
```

The script expects `OLLAMA_API_KEY` in the environment or in the local Hermes `.env`. It does not print the key.

Outputs:

- `.output/ollama_cloud_field_brief.evidence.json` — scope, live checks, observed sources with hashes, extracted facts, supported claims, benchmark metrics, toolchain, layout contract.
- `.output/ollama_cloud_field_brief.json` — Report Foundry IR for generic validation/rendering.
- `.output/ollama_cloud_field_brief_designed.html` — newsletter preview.
- `.output/ollama_cloud_field_brief_designed.pdf` — polished PDF artifact with scope, pipeline, model cards, benchmark bars, and source footer.
- `.output/ollama_cloud_field_brief_designed.discord.md` — sanitized Discord message with PDF attachment path.

Mechanical contract:

```text
observed source payload -> SHA-256 source record -> extracted fact -> supported claim -> Report Foundry IR -> PDF
```

The workflow fails closed when required source data is missing or a claim references an unknown fact. The LLM is allowed to generate bounded commentary only. It does not choose report scope, sources, layout, charts, citations, or PDF structure.

## Design direction

The PDF is not the source of truth. The canonical artifact is a semantic report IR with claim-level provenance. Renderers are adapters.

Planned backends:

- WeasyPrint for open-source HTML/CSS paged media
- PrinceXML for premium PDF/A and PDF/UA publishing
- Playwright for web-dashboard reports and visual QA
- Typst for deterministic technical reports
- Plotly/Vega/Mermaid for chart and diagram assets

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.
