# OSS Report Generation Landscape

Report Foundry should be an evidence/orchestration layer, not a hand-rolled PDF/layout engine. This landscape maps public open-source equivalents and adjacent systems into concrete architecture choices.

## Source collection

Collected with GitHub public repository metadata and public scholarly metadata APIs during implementation. Generated raw files live under `.output_oss_landscape/` and are intentionally untracked.

### Canonical open-source systems

#### Formatting / PDF / publishing engines

- [typst/typst](https://github.com/typst/typst) — Apache-2.0 — markup-based typesetting system.
- [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli) — scientific/technical publishing CLI.
- [jgm/pandoc](https://github.com/jgm/pandoc) — universal document converter; strong citation/filter ecosystem.
- [sile-typesetter/sile](https://github.com/sile-typesetter/sile) — programmable typesetting engine.
- [Kozea/WeasyPrint](https://github.com/Kozea/WeasyPrint) — HTML/CSS to PDF in Python.
- [vivliostyle/vivliostyle.js](https://github.com/vivliostyle/vivliostyle.js) — browser/CSS paged media publishing.
- [pagedjs/pagedjs](https://github.com/pagedjs/pagedjs) — CSS paged media/polyfill for print layouts.
- [microsoft/playwright](https://github.com/microsoft/playwright) / [puppeteer/puppeteer](https://github.com/puppeteer/puppeteer) — Chromium PDF route and browser verification.

#### Scientific / reproducible reports

- [manubot/manubot](https://github.com/manubot/manubot) and [manubot/rootstock](https://github.com/manubot/rootstock) — automated scholarly manuscript pattern.
- [jupyter-book/jupyter-book](https://github.com/jupyter-book/jupyter-book) — publication-quality books/documents from computational content.
- [rstudio/bookdown](https://github.com/rstudio/bookdown) — long-form technical documents from R Markdown.
- [rstudio/distill](https://github.com/rstudio/distill) — scientific/technical article format.

#### Citations / bibliographies / source extraction

- [citation-js/citation-js](https://github.com/citation-js/citation-js) — parse/format citations in JS.
- [Juris-M/citeproc-js](https://github.com/Juris-M/citeproc-js) — CSL citation processor.
- [retorquere/zotero-better-bibtex](https://github.com/retorquere/zotero-better-bibtex) — reproducible BibTeX export from Zotero.
- [zotero/translators](https://github.com/zotero/translators) — source metadata extraction/translators.

#### Exhibits / charts / diagrams

- [vega/vega-lite](https://github.com/vega/vega-lite) and [vega/vega](https://github.com/vega/vega) — declarative charts.
- [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid) — diagrams as code.
- [plotly/Kaleido](https://github.com/plotly/Kaleido) — static Plotly export.
- [observablehq/framework](https://github.com/observablehq/framework) — data app/static report patterns.

#### Evidence pipeline orchestration

- [ploomber/ploomber](https://github.com/ploomber/ploomber) — notebook/data pipelines.
- [dagster-io/dagster](https://github.com/dagster-io/dagster) — asset graph/orchestration.
- [snakemake/snakemake](https://github.com/snakemake/snakemake) — reproducible workflow DAGs.
- [nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) — scalable reproducible pipelines.

### Conceptual/reporting patterns from scholarly metadata

The metadata search was noisy, but three durable concepts are directly relevant:

- **PRISMA / systematic review reporting** — evidence selection, inclusion/exclusion, transparent methodology, source audit trail.
- **Data-to-text / NLG report generation** — separate content planning from surface realization; do not collapse evidence selection, prose writing, and rendering into one prompt.
- **RAG citation/provenance work** — every generated claim must remain attributable to retrievable evidence; source URLs and quotes belong in the reader surface, not just internal JSON.

## Architecture implication

Report Foundry should use a layered contract:

```text
research retrieval / source harvest
  -> evidence extraction + citation metadata
  -> content planning schema
  -> professional report schema
  -> exhibit specifications
  -> renderer adapters
  -> PDF/HTML/package QA
```

The foundry owns validation, orchestration, provenance, and QA. It should delegate formatting and rendering to established engines.

## Recommended implementation direction

### 1. Keep `EvidencePack`; add source metadata depth

`EvidencePack` should preserve:

- URL
- title
- author/publisher when available
- published/updated date when available
- observed timestamp
- hash
- extracted quote/snippet
- locator
- citation metadata candidate

Do **not** show hashes as primary citations in the reader PDF. Hashes are audit metadata; URLs/titles/publishers are reader metadata.

### 2. Split report generation into two schemas

- `ProfessionalReportContent`: answer-first narrative, key takeaways, conclusion-led sections, implications, limitations.
- `ExhibitSpec`: chart/table/diagram intent, data payload, renderer choice, source-backed insight.

This matches data-to-text/content-planning architecture: decide *what to say* before deciding *how to render it*.

### 3. Add renderer adapters instead of one blessed renderer

Renderer routes should be swappable:

- `typst` for high-polish print/PDF templates.
- `quarto` or `pandoc` for markdown/scientific/technical reports.
- `weasyprint` / `pagedjs` / `vivliostyle` for CSS print layouts.
- `playwright_chromium` for pragmatic HTML-to-PDF and visual QA.
- `mermaid`, `vega_lite`, `kaleido` for exhibits.

### 4. Add citation adapter layer

Start with simple URL/title citations, then add:

- CSL JSON export
- BibTeX export
- Citation.js/citeproc integration
- Zotero translator fallback for source metadata extraction

### 5. Borrow PRISMA-style audit trail

For serious reports, store:

- search queries
- source inclusion/exclusion reasons
- retrieval timestamps
- extractor used
- claim-to-fact-to-source matrix
- unresolved evidence gaps

This makes “what evidence did we use, and why?” a first-class artifact.

## Immediate backlog

1. **Typst adapter spike**
   - Input: `ProfessionalReportContent` + `ExhibitSpec` + citation list.
   - Output: `.typ` + PDF.
   - Verify: text extraction, visual raster QA, URL visibility.

2. **CSL/BibTeX citation adapter**
   - Add source metadata fields.
   - Export CSL JSON/BibTeX.
   - Render human citations in PDF and machine bibliography in package.

3. **ExhibitSpec schema**
   - Separate chart/diagram/table specifications from prose sections.
   - Validate every exhibit has an insight and provenance fact IDs.

4. **PRISMA-lite evidence log**
   - Add `ResearchRunLog`: queries, candidates, selected/rejected sources, reasons, gaps.
   - Render methodology appendix from the log.

5. **Professional template suite**
   - Consulting brief template.
   - Investor memo template.
   - Market map template.
   - Scientific/reproducible report template.

## Non-goals

- Hand-rolling a PDF layout engine.
- Treating LLM prose as the only artifact.
- Hiding evidence in JSON while the PDF shows unsupported prose.
- Building citations from source IDs/hashes instead of titles/URLs.
