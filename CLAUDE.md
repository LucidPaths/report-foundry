# Report Foundry Agent Instructions

Report Foundry is an evidence-contract and artifact factory: a research-capable LLM/session searches, reads, reasons, and returns structured `ResearchIntake`; Foundry validates that contract and renders the governed package. Foundry is not the AI provider, search provider, crawler, or autonomous browser. Schema law, evidence gates, rendering, run logs, and QA are the product.

## Principle Lattice

Report Foundry has 8 axiomatic principles. Read [`docs/PRINCIPLE_LATTICE.md`](docs/PRINCIPLE_LATTICE.md) for the full lattice with instantiations. Summary:

| # | Principle | Axiom |
|---|-----------|-------|
| RF-P1 | **Source Sovereignty** | The source observation is the root of truth. Models are witnesses, not authorities. |
| RF-P2 | **Claim Traceability** | No orphan claims. Every assertion has a chain of custody. |
| RF-P3 | **Provider and Renderer Agnosticism** | Interfaces are permanent. Providers and renderers are replaceable. |
| RF-P4 | **Gates Fail Closed** | Missing proof routes backward. It never silently ships forward. |
| RF-P5 | **Case Law Before Generation** | Scope is inferred before prose. The rubric is the contract. |
| RF-P6 | **Visuals Are Claims** | A chart, map, matrix, or timeline asserts structure. It needs provenance too. |
| RF-P7 | **Secrets Stay Handles** | Keys connect capabilities. They do not become artifacts. |
| RF-P8 | **Low Floor, High Ceiling** | One command for beginners. Full inspection for operators. |

When making design decisions, check against these principles. If a choice violates one, reconsider. If two choices both violate something, find a third path.

## Doctrine Notation

Every Python source, script, and test file must carry a module docstring with canonical `Lattice:` notation:

```python
"""Evidence contracts for observed sources, extracted facts, and supported claims.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed.
"""
```

The test suite rejects missing, empty, duplicate, unknown, or misnamed declarations. Keep the set small and accurate.

## Product Invariants

- The PDF is an artifact, not the source of truth.
- Raw model prose is never a source observation.
- A report claim is invalid unless it resolves to extracted facts and observed sources.
- A visual is a claim about numbers, relationships, geography, sequence, or risk.
- A topic is not scope. The rubric/source plan/visual plan define scope before generation.
- AI/search providers, renderers, MCP tools, and company data stores are replaceable adapters.
- LLM/session owns research behavior; Foundry owns contract validation and artifact generation.
- Run manifests reference key handles or environment variable names only; never raw secrets.
- Partial artifacts are allowed internally only when gate results clearly route backward.

## Development Guidelines

1. **Use `uv`, not ad-hoc pip.** Project commands should run through `uv run`.
2. **Do not treat fixture research as product search.** `research-run` is local deterministic scaffolding only.
3. **Do not make Foundry pretend to browse.** Web/search belongs to the upstream LLM/tool session or an explicit connector runtime.
4. **Do not let LLM output choose report law.** Models may propose; deterministic code gates admissibility.
5. **Do not hand-roll layout engines prematurely.** Prefer typed IR plus established renderers/adapters.
6. **Do not add provider-specific logic to core contracts.** Add connectors/adapters instead.
7. **Do not store raw keys in schemas, manifests, fixtures, tests, or docs.** Store handles/env var names only.
8. **When adding a new Python file, add canonical `Lattice:` notation immediately.**

## Common Tasks

### Run Tests

```bash
uv run --extra dev pytest -q
```

### Plan a Factory Run

```bash
uv run reportfoundry plan-run "current SpaceX IPO launch newsletter" \
  --audience "executive readers" \
  --integration-mode mcp \
  --source company-db \
  --source web \
  --out-dir .factory-run/spacex-ipo
```

### Fixture Research Run

```bash
uv run reportfoundry research-run .factory-run/spacex-ipo \
  --source-dir ./marked-sources
```

This path does not discover web sources. It only normalizes marked local files into the evidence contract.

### Build and Validate Example Report

```bash
uv run reportfoundry validate examples/daily_systems_brief.json
uv run reportfoundry build examples/daily_systems_brief.json --out-dir .output
```

## Things to Avoid

- Do not frame Report Foundry as “a PDF generator.” It is an evidence/governance factory; PDF is one renderer. (RF-P1, RF-P3)
- Do not call generated prose “researched” unless it passes source-observation and claim-traceability gates. (RF-P1, RF-P2, RF-P4)
- Do not let a beautiful chart ship without source-backed data, alt text, and transform/provenance notes. (RF-P6)
- Do not let missing sources degrade into “best effort” prose. Route back to Research. (RF-P4)
- Do not add raw `api_key`, `token`, `password`, or `secret` fields to public typed models. (RF-P7)
- Do not add a new renderer by changing evidence or QA contracts. Renderers are adapters. (RF-P3)
- Do not add a domain rubric unless its required dimensions differ meaningfully from the generic rubric. (RF-P5)

## Pre-Commit Verification

Do all of these before claiming completion:

1. **Run the full suite.** `uv run --extra dev pytest -q`; test count must not decrease.
2. **Trace the actual flow.** If the change affects topic intake, verify topic → rubric/source plan/visual plan/gate result. If it affects evidence, verify source → fact → claim → citation.
3. **Grep for the pattern (RF-P4 / RF-P5).** Every bug fix gets a codebase-wide search for the same class of mistake.
4. **Check all 8 Principle Lattice items explicitly:**
   - RF-P1 Source Sovereignty: Does every fact/visual/layout decision trace to an observed source?
   - RF-P2 Claim Traceability: Can every claim resolve to fact IDs and citations?
   - RF-P3 Provider and Renderer Agnosticism: Did this avoid coupling core contracts to a provider or renderer?
   - RF-P4 Gates Fail Closed: Does missing proof stop or route backward instead of shipping forward?
   - RF-P5 Case Law Before Generation: Is rubric/source/visual law established before generation?
   - RF-P6 Visuals Are Claims: Are charts/maps/timelines treated as provenance-bearing claims?
   - RF-P7 Secrets Stay Handles: Are credentials represented only by handles/env var names and omitted from outputs?
   - RF-P8 Low Floor High Ceiling: Is there a simple CLI/default path plus inspectable artifacts for operators?
5. **No dead code.** New public functions need production callers or explicit roadmap/test-fixture framing.
6. **Check external-surface safety.** Before posting to Discord/Telegram or writing share artifacts, scan/sanitize for credentials and private payloads.
7. **Inspect the diff.** Confirm only requested files changed; leave `.output_*` scratch directories untracked unless explicitly asked.

## Lessons Learned

| Risk | Failure Mode | Defense |
|------|--------------|---------|
| Weak doctrine enforcement | `Lattice: vibes` passes while principles rot | Parse canonical RF-P declarations in tests |
| Fixture/product confusion | Local marked-source worker gets mistaken for real search | Keep fixture language in docs, CLI help, and file docstrings |
| Provider leakage | Core models grow raw key/provider-specific fields | Store connector handles/env var names only |
| Pretty artifact bias | Renderer output looks good but lacks evidence chain | QA source/fact/claim gates before rendering |
| Visual laundering | Charts imply unsupported relationships | Treat visuals as claims with provenance and alt text |
