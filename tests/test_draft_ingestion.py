"""Authored markdown draft ingestion tests.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.draft import parse_markdown_draft
from report_foundry.report_spec import compile_report_spec

runner = CliRunner()

DRAFT = """# AI Infrastructure Debt Is Becoming a Bank Underwriting Problem

Authored reports should arrive as real prose, not as a tiny coded sample. This opening paragraph is written by the research fixture and must survive into the rendered report body.

:::source
id: src_bis_ai_risk
title: BIS working paper on AI and financial stability
url: https://example.test/bis-ai-risk
quote: Banks adopting AI infrastructure create model, vendor, and operational risk channels that supervisors need to measure.
:::

:::claim
id: claim_underwriting_shift
text: European banks need to underwrite AI infrastructure exposure as a balance-sheet and operational-risk issue, not only a productivity theme.
source: src_bis_ai_risk
confidence: high
:::

:::exhibit
id: ai_risk_flow
type: diagram
renderer: mermaid
source: src_bis_ai_risk
title: AI risk transmission path
purpose: Show how a source-backed risk claim flows from infrastructure spend to supervisory pressure.
payload:
flowchart LR
  A[AI infrastructure spend] --> B[Vendor concentration]
  B --> C[Operational resilience risk]
  C --> D[Supervisor scrutiny]
:::

## Banks need an exposure map before they need another AI strategy memo

The central move in the report is simple: treat AI infrastructure as an exposure class. That means linking capex, vendor dependence, model risk, resilience, and governance into one underwriting view rather than scattering them across innovation decks.

The evidence claim above should become a supported claim in the Foundry output, and the Mermaid exhibit should be rendered by software rather than described as a placeholder.

## The design path is software composition, not PDF handcrafting

The report author writes this report and chooses the graph intent. The Foundry parses the prose, validates the cited source, renders the diagram, lays out the document, emits metrics, and produces page previews for QA.
"""


def test_parse_markdown_draft_preserves_authored_written_report_and_exhibit_contract() -> None:
    pack = parse_markdown_draft(DRAFT, author="Research Author")

    assert pack.title == "AI Infrastructure Debt Is Becoming a Bank Underwriting Problem"
    assert pack.author == "Research Author"
    assert len(pack.report_sections) == 3
    assert "must survive into the rendered report body" in pack.report_sections[0].paragraphs[0]
    assert pack.sources[0].source_id == "src_bis_ai_risk"
    assert pack.sources[0].url == "https://example.test/bis-ai-risk"
    assert pack.facts[0].source_id == "src_bis_ai_risk"
    assert pack.claims[0].fact_ids == [pack.facts[0].fact_id]
    assert pack.exhibits[0].visual_id == "ai_risk_flow"
    assert pack.exhibits[0].preferred_tool == "mermaid"
    assert "flowchart LR" in pack.exhibits[0].plain_text_payload

    spec = compile_report_spec(pack)
    assert any(section.title == "Banks need an exposure map before they need another AI strategy memo" for section in spec.sections)
    visual = next(visual for visual in spec.visuals if visual.visual_id == "ai_risk_flow")
    assert "flowchart LR" in visual.plain_text_payload
    assert "AI infrastructure spend" in visual.plain_text_payload


def test_compile_draft_command_turns_authored_markdown_into_foundry_artifacts(tmp_path: Path) -> None:
    draft_path = tmp_path / "authored_bank_report.md"
    out_dir = tmp_path / "rendered"
    draft_path.write_text(DRAFT, encoding="utf-8")

    result = runner.invoke(app, ["compile-draft", str(draft_path), "--out-dir", str(out_dir), "--author", "Research Author"])

    assert result.exit_code == 0, result.output
    assert (out_dir / "authored_bank_report.evidence.json").exists()
    assert (out_dir / "authored_bank_report.spec.json").exists()
    assert (out_dir / "authored_bank_report.html").exists()
    assert (out_dir / "authored_bank_report.pdf").exists()
    assert (out_dir / "authored_bank_report.ai_risk_flow.svg").exists()
    assert (out_dir / "authored_bank_report.pages" / "page_001.png").exists()

    evidence = json.loads((out_dir / "authored_bank_report.evidence.json").read_text(encoding="utf-8"))
    serialized = json.dumps(evidence).lower()
    assert "report foundry oss strategy brief" not in serialized
    assert evidence["report_sections"][0]["paragraphs"][0].startswith("Authored reports")

    layout = json.loads((out_dir / "authored_bank_report.layout.json").read_text(encoding="utf-8"))
    assert layout["page_count"] >= 1
    assert layout["visual_object_count"] > 0
