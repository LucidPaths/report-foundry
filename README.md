# Report Foundry

AI-native evidence-to-PDF report compiler.

Report Foundry turns structured evidence packs into beautiful, grounded reports with claim-level citations, visual assets, QA gates, and Discord-ready PDF delivery.

## What exists now

- Pydantic report IR: sections, text, claims, citations, figures, metric cards, tables
- Quality gates: unsupported claims, missing alt text warnings, ragged tables
- HTML renderer for preview/share
- Real PDF renderer via ReportLab
- CLI: `reportfoundry validate` and `reportfoundry build`
- Example report fixture

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

## Ollama Cloud newsletter path

Generate a live model brief from Ollama Cloud, then render it through Report Foundry:

```bash
python scripts/ollama_daily_newsletter.py \
  --out .output/ollama_cloud_field_brief.json \
  --discord-md .output/ollama_cloud_field_brief.discord.md
uv run reportfoundry validate .output/ollama_cloud_field_brief.json
uv run reportfoundry build .output/ollama_cloud_field_brief.json --out-dir .output
```

The script expects `OLLAMA_API_KEY` in the environment or in the local Hermes `.env`. It does not print the key.

## Design direction

The PDF is not the source of truth. The canonical artifact is a semantic report IR with claim-level provenance. Renderers are adapters.

Planned backends:

- WeasyPrint for open-source HTML/CSS paged media
- PrinceXML for premium PDF/A and PDF/UA publishing
- Playwright for web-dashboard reports and visual QA
- Typst for deterministic technical reports
- Plotly/Vega/Mermaid for chart and diagram assets

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.
