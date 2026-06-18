"""RendererAdapter contract tests.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.evidence import EvidenceClaim, EvidenceFact, EvidencePack, ReportNarrativeSection, SourceObservation
from report_foundry.factory import RunMode
from report_foundry.renderers import (
    PlaywrightChromiumRendererAdapter,
    RenderRequest,
    RendererRouteError,
    TypstRendererAdapter,
    render_with_route,
)

runner = CliRunner()


def make_evidence_pack() -> EvidencePack:
    source = SourceObservation(
        source_id="src_renderer",
        title="Renderer fixture source",
        url="https://example.test/renderer",
        observed_at="2026-06-18T00:00:00Z",
        content_sha256="e" * 64,
        extractor="fixture",
        locator="fixture://renderer",
    )
    fact = EvidenceFact(
        fact_id="fact_renderer",
        subject="Renderer route",
        predicate="emits",
        value="artifacts",
        source_id=source.source_id,
        quote="The renderer route emits HTML, PDF, previews, metrics, and a gate result.",
        locator="line 1",
    )
    return EvidencePack(
        title="Renderer route brief",
        scope={"run_mode": "product"},
        sources=[source],
        facts=[fact],
        claims=[EvidenceClaim(text="Renderer routes emit artifacts without changing evidence.", fact_ids=[fact.fact_id], confidence="high")],
        report_sections=[ReportNarrativeSection(section_id="renderer", title="Renderer", paragraphs=["Renderer routes are adapters around immutable evidence."], fact_ids=[fact.fact_id])],
    )


def write_render_inputs(tmp_path: Path, *, run_mode: RunMode = RunMode.PRODUCT) -> RenderRequest:
    evidence_path = tmp_path / "evidence_pack.json"
    spec_path = tmp_path / "report.spec.json"
    citations_path = tmp_path / "report.citations.json"
    exhibits_path = tmp_path / "exhibits.json"
    html_path = tmp_path / "report.html"
    evidence_path.write_text(make_evidence_pack().model_dump_json(indent=2), encoding="utf-8")
    spec_path.write_text(json.dumps({"title": "Renderer smoke"}, indent=2), encoding="utf-8")
    citations_path.write_text(json.dumps({"records": []}, indent=2), encoding="utf-8")
    exhibits_path.write_text(json.dumps({"artifacts": []}, indent=2), encoding="utf-8")
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Renderer smoke</title></head>"
        "<body><h1>Renderer smoke</h1><p>Report title visible. Source appendix visible. "
        "Citation visible. Exhibit alt text visible.</p></body></html>",
        encoding="utf-8",
    )
    return RenderRequest(
        report_spec_path=spec_path,
        evidence_pack_path=evidence_path,
        citation_records_path=citations_path,
        exhibit_specs_path=exhibits_path,
        html_path=html_path,
        pdf_path=tmp_path / "report.pdf",
        route="playwright_chromium",
        out_dir=tmp_path,
        run_mode=run_mode,
    )


def test_playwright_renderer_emits_artifact_without_mutating_evidence_contract(tmp_path: Path) -> None:
    request = write_render_inputs(tmp_path)
    before = request.evidence_pack_path.read_text(encoding="utf-8")

    artifact = PlaywrightChromiumRendererAdapter().render(request)

    assert artifact.route == "playwright_chromium"
    assert artifact.html_path == str(request.html_path)
    assert artifact.pdf_path and Path(artifact.pdf_path).read_bytes().startswith(b"%PDF")
    assert artifact.metrics_path and json.loads(Path(artifact.metrics_path).read_text(encoding="utf-8"))["page_count"] >= 1
    assert artifact.preview_paths and Path(artifact.preview_paths[0]).exists()
    assert artifact.gate_result_path and json.loads(Path(artifact.gate_result_path).read_text(encoding="utf-8"))["ok"] is True
    assert request.evidence_pack_path.read_text(encoding="utf-8") == before


def test_unknown_renderer_route_fails_closed_with_gate_file(tmp_path: Path) -> None:
    request = write_render_inputs(tmp_path)
    request.route = "unknown_renderer"

    try:
        render_with_route(request)
    except RendererRouteError as exc:
        gate = exc.gate_result
    else:  # pragma: no cover - assertion branch
        raise AssertionError("Unknown renderer route must fail closed")

    gate_path = tmp_path / "render_gate_result.json"
    assert gate.ok is False
    assert gate_path.exists()
    assert any(check.code == "unknown_renderer_route" for check in gate.checks)


def test_typst_unavailable_records_real_gate_reason(tmp_path: Path, monkeypatch) -> None:
    request = write_render_inputs(tmp_path)
    request.route = "typst"
    monkeypatch.setattr("report_foundry.renderers.shutil.which", lambda _: None)

    try:
        TypstRendererAdapter().render(request)
    except RendererRouteError as exc:
        gate = exc.gate_result
    else:  # pragma: no cover - assertion branch
        raise AssertionError("Unavailable typst must fail closed")

    assert any(check.code == "renderer_unavailable" and "typst" in check.message for check in gate.checks)
    assert (tmp_path / "render_gate_result.json").exists()


def test_compile_spec_cli_accepts_explicit_playwright_route(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence_pack.json"
    out_dir = tmp_path / "compiled"
    evidence_path.write_text(make_evidence_pack().model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-spec", str(evidence_path), "--route", "playwright_chromium", "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "route=playwright_chromium" in result.output
    assert (out_dir / "render_gate_result.json").exists()
    assert json.loads((out_dir / "render_gate_result.json").read_text(encoding="utf-8"))["ok"] is True
