"""ReportSpec compiler tests for strict research-to-tool payload routing.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.evidence import (
    EvidenceClaim,
    EvidenceFact,
    EvidencePack,
    ProfessionalKeyTakeaway,
    ProfessionalReportContent,
    ProfessionalReportSection,
    ReportNarrativeSection,
    SourceObservation,
)
from report_foundry.report_spec import compile_report_spec, compile_spec_to_report, write_spec_artifacts, _assert_pdf_layout_quality

runner = CliRunner()


def make_evidence_pack() -> EvidencePack:
    source = SourceObservation(
        source_id="src_spacex_registry",
        title="SpaceX launch registry fixture",
        url="https://example.test/spacex-registry",
        observed_at="2026-06-17T00:00:00Z",
        content_sha256="c" * 64,
        extractor="fixture",
        locator="fixture://spacex-registry",
    )
    facts = [
        EvidenceFact(
            fact_id="fact_starlink",
            subject="SpaceX IPO",
            predicate="dimension:starlink_economics",
            value="covered",
            source_id=source.source_id,
            quote="Starlink economics depends on subscriber scale because recurring broadband revenue creates IPO-ready cash-flow evidence; 2026 watch item.",
            locator="DIMENSION: starlink_economics",
        ),
        EvidenceFact(
            fact_id="fact_launch",
            subject="SpaceX IPO",
            predicate="dimension:launch_cadence_and_payload_proof",
            value="covered",
            source_id=source.source_id,
            quote="Launch cadence depends on repeat payload delivery because frequent missions prove operational capacity; 2026 cadence is the bottleneck.",
            locator="DIMENSION: launch_cadence_and_payload_proof",
        ),
    ]
    claims = [
        EvidenceClaim(
            text="SpaceX IPO readiness depends on Starlink economics because recurring broadband revenue creates cash-flow evidence; 2026 scale is the watch item.",
            fact_ids=["fact_starlink"],
            confidence="high",
        ),
        EvidenceClaim(
            text="SpaceX IPO readiness depends on launch cadence because repeated payload delivery proves operational capacity; 2026 cadence is the bottleneck.",
            fact_ids=["fact_launch"],
            confidence="medium",
        ),
    ]
    return EvidencePack(
        title="SpaceX IPO readiness brief",
        subtitle="Strict ReportSpec fixture",
        scope={"audience": "executive readers", "format": "analyst newsletter"},
        sources=[source],
        facts=facts,
        claims=claims,
        report_sections=[
            ReportNarrativeSection(
                section_id="analyst_context",
                title="Analyst context",
                kicker="Plain report prose authored upstream.",
                paragraphs=[
                    "This is a full narrative paragraph, not schema debris. It explains why Starlink economics and launch cadence are separate IPO-readiness gates.",
                    "The foundry must render this prose as report content while keeping citations, source links, and evidence maps attached as supporting material.",
                ],
                fact_ids=["fact_starlink", "fact_launch"],
            )
        ],
        tags=["spec-fixture"],
    )


def make_professional_evidence_pack() -> EvidencePack:
    pack = make_evidence_pack()
    pack.professional_report = ProfessionalReportContent(
        one_sentence_thesis="SpaceX IPO readiness should be evaluated as separate execution, recurring-revenue, and disclosure gates rather than a single hype narrative.",
        executive_summary=[
            "Professional reports lead with the answer, then show the evidence path. This brief therefore starts with a thesis, key takeaways, and decision relevance before showing claims or appendices.",
            "The available evidence supports an IPO-readiness map, not an IPO-ready verdict, because source-observed financial and control evidence is missing from the pack.",
        ],
        key_takeaways=[
            ProfessionalKeyTakeaway(
                takeaway="Starlink economics is the commercial hinge of the IPO story.",
                fact_ids=["fact_starlink"],
                implication="Recurring broadband revenue is the difference between launch-company and infrastructure-platform framing.",
            ),
            ProfessionalKeyTakeaway(
                takeaway="Launch cadence is execution evidence, not financial-readiness evidence.",
                fact_ids=["fact_launch"],
                implication="Operations can be strong while valuation evidence remains incomplete.",
            ),
        ],
        sections=[
            ProfessionalReportSection(
                section_id="starlink_hinge",
                role="financial_analysis",
                headline="Starlink economics is the hinge, but the financial proof is still absent",
                lede="Investor-style reports separate the commercial engine from the operating narrative. For SpaceX, that means Starlink cannot be treated as a footnote.",
                paragraphs=[
                    "If Starlink demonstrates durable subscriber economics, SpaceX can be framed partly as a recurring infrastructure platform. If those economics are weak or unobserved, the public-market story falls back toward launch cadence and project revenue.",
                ],
                fact_ids=["fact_starlink"],
                so_what="The next research cycle must prioritize Starlink ARPU, churn, margin, capex, and subscriber trend evidence before any valuation section is credible.",
                limitations=["The fixture does not include audited Starlink financials or unit economics."],
            ),
            ProfessionalReportSection(
                section_id="launch_repeatability",
                role="operating_analysis",
                headline="Launch cadence supports execution credibility but cannot carry the IPO thesis alone",
                lede="Consulting-style reports turn operational facts into decision implications instead of treating them as trivia.",
                paragraphs=[
                    "Repeated payload delivery and launch cadence matter because public investors price repeatability. The same evidence does not prove margins, backlog quality, customer concentration, or reporting readiness.",
                ],
                fact_ids=["fact_launch"],
                so_what="A professional report should make launch cadence one readiness gate, not the whole conclusion.",
                limitations=["The fixture does not include year-by-year launch cadence, payload mix, or reliability data."],
            ),
        ],
        what_to_watch=[
            "Starlink subscriber economics and capex intensity",
            "Launch cadence by customer and payload class",
            "Public-company controls, ownership, and disclosure readiness",
        ],
        methodology="Schema derived from observed public consulting, venture, market-intelligence, and investor report structures: answer first, conclusion-led sections, exhibits near evidence, explicit limitations, and source appendix.",
    )
    return pack


def test_professional_report_schema_renders_answer_first_sections() -> None:
    spec = compile_report_spec(make_professional_evidence_pack())

    assert spec.sections[0].section_id == "executive_brief"
    assert "one single hype narrative" not in spec.sections[0].blocks[0].content
    assert "single hype narrative" in spec.sections[0].blocks[0].content
    assert any(section.title.startswith("Starlink economics is the hinge") for section in spec.sections)
    report = compile_spec_to_report(spec)
    assert report.sections[0].title == "Executive brief"
    first_page_text = "\n".join(block.text for block in report.sections[0].blocks if block.type == "text")
    assert "Key takeaways:" in first_page_text
    html = __import__("report_foundry.render", fromlist=["render_html"]).render_html(report)
    assert "<ul>" in html and "<li>Starlink economics is the commercial hinge" in html
    assert "So what:" in "\n".join(block.text for section in report.sections for block in section.blocks if block.type == "text")


def test_compile_report_spec_is_strict_tool_feed() -> None:
    spec = compile_report_spec(make_evidence_pack())

    assert spec.title == "SpaceX IPO readiness brief"
    assert spec.render_targets == ["html", "pdf"]
    assert spec.tool_routes["pdf"] == "playwright_chromium"
    assert spec.tool_routes["html"] == "html_css"
    assert spec.generation_metadata["run_mode"] == "fixture"
    assert spec.generation_metadata["artifact_status"] == "fixture"
    assert len(spec.sections) >= 4
    assert spec.sections[0].role == "report"
    assert spec.sections[0].blocks[0].role == "paragraph"

    assert all(section.blocks for section in spec.sections)
    assert all(claim.fact_ids for section in spec.sections for claim in section.claims)
    assert spec.visuals[0].provenance_fact_ids == ["fact_starlink", "fact_launch"]
    assert spec.source_appendix.rows[0][0] == "src_spacex_registry"


def test_compile_spec_to_report_preserves_claim_citations_and_visual_claim() -> None:
    spec = compile_report_spec(make_evidence_pack())

    report = compile_spec_to_report(spec)

    claims = report.claims()
    assert len(claims) == 2
    assert claims[0].citations[0].source_id == "src_spacex_registry"
    assert claims[0].citations[0].url == "https://example.test/spacex-registry"
    assert "Starlink economics depends" in (claims[0].citations[0].quote or "")
    assert report.sections[0].title == "Analyst context"
    assert any("full narrative paragraph" in block.text for block in report.sections[0].blocks if block.type == "text")
    assert any(block.type == "figure" and "source-backed" in (block.caption or "") for section in report.sections for block in section.blocks)


def test_write_spec_artifacts_creates_report_spec_ir_html_and_pdf(tmp_path: Path) -> None:
    paths = write_spec_artifacts(make_evidence_pack(), tmp_path)

    assert set(paths) == {"spec", "ir", "html", "pdf", "evidence_trace_map", "layout_metrics", "page_previews"}
    for key, path in paths.items():
        assert path.exists(), (key, path)
        if path.is_file():
            assert path.stat().st_size > 0, path
    assert paths["evidence_trace_map"].suffix == ".svg"
    assert "<svg" in paths["evidence_trace_map"].read_text(encoding="utf-8")
    assert paths["pdf"].read_bytes().startswith(b"%PDF")
    assert b"Chromium" in paths["pdf"].read_bytes()
    assert b"Skia/PDF" in paths["pdf"].read_bytes()
    layout = json.loads(paths["layout_metrics"].read_text(encoding="utf-8"))
    assert layout["page_count"] >= 1
    assert layout["visual_object_count"] >= 1
    assert layout["producer"] == "Skia/PDF"
    assert layout["average_words_per_page"] > 0
    assert (paths["page_previews"] / "page_001.png").exists()
    spec = json.loads(paths["spec"].read_text(encoding="utf-8"))
    assert spec["tool_routes"]["pdf"] == "playwright_chromium"
    assert spec["source_appendix"]["headers"] == ["Source", "Title", "URL", "Observed", "SHA-256", "Extractor"]
    assert spec["source_appendix"]["rows"][0][2] == "https://example.test/spacex-registry"


def test_pdf_layout_density_gate_rejects_multi_page_sparse_reports() -> None:
    try:
        _assert_pdf_layout_quality({"page_count": 8, "average_words_per_page": 120})
    except ValueError as exc:
        assert "layout density gate" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("Sparse multi-page PDFs must fail closed")


def test_compile_spec_command_builds_pdf_from_evidence_pack(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence_pack.json"
    out_dir = tmp_path / "compiled"
    evidence_path.write_text(make_evidence_pack().model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-spec", str(evidence_path), "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "report spec" in result.output
    assert (out_dir / "evidence_pack.spec.json").exists()
    assert (out_dir / "evidence_pack.pdf").exists()
    assert (out_dir / "evidence_pack.layout.json").exists()
    assert (out_dir / "evidence_pack.pdf").read_bytes().startswith(b"%PDF")


def test_oss_strategy_command_codes_the_full_sample_workflow(tmp_path: Path) -> None:
    out_dir = tmp_path / "oss_strategy"

    result = runner.invoke(app, ["oss-strategy-report", "--out-dir", str(out_dir), "--offline"])

    assert result.exit_code == 0, result.output
    assert "evidence pack" in result.output
    assert "layout metrics" in result.output
    assert (out_dir / "oss_strategy_evidence_pack.json").exists()
    assert (out_dir / "oss_strategy_evidence_pack.spec.json").exists()
    assert (out_dir / "oss_strategy_evidence_pack.html").exists()
    assert (out_dir / "oss_strategy_evidence_pack.pdf").exists()
    assert (out_dir / "oss_strategy_evidence_pack.layout.json").exists()
    assert (out_dir / "oss_strategy_evidence_pack.pages" / "page_001.png").exists()
    layout = json.loads((out_dir / "oss_strategy_evidence_pack.layout.json").read_text(encoding="utf-8"))
    assert layout["producer"] == "Skia/PDF"
    assert layout["average_words_per_page"] >= 180
