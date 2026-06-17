# Roadmap

## v0.1 MVP

- [x] Pydantic report IR
- [x] Claim-level citations
- [x] HTML renderer
- [x] Real PDF renderer via ReportLab
- [x] Quality gates
- [x] CLI build/validate
- [x] Example report
- [x] Ollama Cloud evidence-pack newsletter with designed HTML/PDF output

## v0.2 Evidence packs

- [x] first evidence-pack sidecar for Ollama Cloud newsletter
- [ ] formal `manifest.json` schema
- [ ] content-addressed source cache
- [ ] source hashing and access timestamps
- [ ] provenance sidecar export
- [ ] link checker

## v0.3 Visual system

- [x] first deterministic newsletter layout with model cards and benchmark bars
- [ ] reusable theme tokens
- [ ] section divider components
- [ ] Plotly/Vega chart adapters
- [ ] Mermaid diagram adapter
- [ ] cover page variants
- [ ] visual screenshot QA

## v0.4 Serious PDF backends

- [ ] WeasyPrint adapter
- [ ] PrinceXML adapter
- [ ] Typst adapter
- [ ] PDF/A and PDF/UA validation hooks

## v0.5 AI-native receipts

- [ ] claim extraction
- [ ] citation entailment verifier
- [ ] evidence graph
- [ ] source appendix generator
- [ ] Discord publisher

## v0.6 Analyst factory gates

- [x] first `factory` schema for departments, run manifest, case rubric, page metrics, and gate results
- [x] deterministic seed rubrics for SpaceX IPO and European banking examples
- [x] route-back gates for missing research dimensions, vague claims, underfilled pages, and missing source appendix
- [x] source-plan artifact with primary/trusted source quotas per required dimension
- [x] visual-plan artifact with chart/map/diagram/image provenance requirements
- [x] `reportfoundry plan-run` CLI that persists manifest, rubric, source plan, visual plan, and initial gate result
- [x] `reportfoundry research-run` CLI that normalizes local marked source files into evidence packs and research gate results
- [x] fail-closed research extraction: missing `DIMENSION:` markers route back to Research
- [ ] final AI reviewer rubric that reads/looks at generated PDF screenshots and scores against the initial case rubric
- [ ] iterative department retry loop: failed gate returns the artifact to the responsible department with repair instructions

## v0.7 Enterprise/MCP deployment

- [ ] MCP server exposing topic intake, source ingestion, evidence validation, render, QA, and artifact retrieval tools
- [ ] connector interface for company databases, document stores, APIs, and internal MCP tools
- [ ] server/queue runner for department workers and audit logs
- [ ] per-tenant source trust policy and connector allowlist
- [ ] artifact package export: PDF, HTML, source appendix, evidence JSON, QA report, and run manifest
