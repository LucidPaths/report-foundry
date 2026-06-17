"""ReportSpec compiler tests for strict research-to-tool payload routing.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.evidence import EvidenceClaim, EvidenceFact, EvidencePack, ReportNarrativeSection, SourceObservation
from report_foundry.report_spec import compile_report_spec, compile_spec_to_report, write_spec_artifacts

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


def test_compile_report_spec_is_strict_tool_feed() -> None:
    spec = compile_report_spec(make_evidence_pack())

    assert spec.title == "SpaceX IPO readiness brief"
    assert spec.render_targets == ["html", "pdf"]
    assert spec.tool_routes["pdf"] == "playwright_chromium"
    assert spec.tool_routes["html"] == "html_css"
    assert len(spec.sections) >= 4
    assert spec.sections[0].role == "report"
    assert spec.sections[0].blocks[0].role == "paragraph"
    assert "full narrative paragraph" in spec.sections[0].blocks[0].content
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

    assert set(paths) == {"spec", "ir", "html", "pdf", "evidence_trace_map"}
    for path in paths.values():
        assert path.exists(), path
        assert path.stat().st_size > 0, path
    assert paths["evidence_trace_map"].suffix == ".svg"
    assert "<svg" in paths["evidence_trace_map"].read_text(encoding="utf-8")
    assert paths["pdf"].read_bytes().startswith(b"%PDF")
    assert b"Chromium" in paths["pdf"].read_bytes()
    assert b"Skia/PDF" in paths["pdf"].read_bytes()
    spec = json.loads(paths["spec"].read_text(encoding="utf-8"))
    assert spec["tool_routes"]["pdf"] == "playwright_chromium"
    assert spec["source_appendix"]["headers"] == ["Source", "Title", "URL", "Observed", "SHA-256", "Extractor"]
    assert spec["source_appendix"]["rows"][0][2] == "https://example.test/spacex-registry"


def test_compile_spec_command_builds_pdf_from_evidence_pack(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence_pack.json"
    out_dir = tmp_path / "compiled"
    evidence_path.write_text(make_evidence_pack().model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-spec", str(evidence_path), "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "report spec" in result.output
    assert (out_dir / "evidence_pack.spec.json").exists()
    assert (out_dir / "evidence_pack.pdf").exists()
    assert (out_dir / "evidence_pack.pdf").read_bytes().startswith(b"%PDF")
