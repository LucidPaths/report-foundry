"""Run package manifest tests.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.evidence import EvidenceClaim, EvidenceFact, EvidencePack, ReportNarrativeSection, SourceObservation
from report_foundry.factory import RunMode
from report_foundry.package import build_package_manifest
from report_foundry.report_spec import write_spec_artifacts

runner = CliRunner()


def make_manifest_pack() -> EvidencePack:
    source = SourceObservation(
        source_id="src_manifest_fixture",
        title="Package manifest fixture source",
        url="https://example.test/package-manifest",
        observed_at="2026-06-18T00:00:00Z",
        content_sha256="d" * 64,
        extractor="fixture",
        locator="fixture://package-manifest",
        publisher="Example Publisher",
    )
    fact = EvidenceFact(
        fact_id="fact_manifest_fixture",
        subject="Report package",
        predicate="records",
        value="artifact truth",
        source_id=source.source_id,
        quote="The package manifest records artifact truth.",
        locator="line 1",
    )
    claim = EvidenceClaim(
        text="The report package has a machine-readable artifact manifest.",
        fact_ids=[fact.fact_id],
        confidence="high",
    )
    section = ReportNarrativeSection(
        section_id="manifest_contract",
        title="Manifest contract",
        paragraphs=["The package manifest is the source of truth for generated artifacts."],
        fact_ids=[fact.fact_id],
    )
    return EvidencePack(
        title="Package manifest fixture",
        subtitle="Manifest test",
        author="Report Foundry",
        sources=[source],
        facts=[fact],
        claims=[claim],
        report_sections=[section],
        scope={"run_mode": "fixture"},
    )


def test_write_spec_artifacts_emits_package_manifest_as_truth_source(tmp_path: Path) -> None:
    paths = write_spec_artifacts(make_manifest_pack(), tmp_path)

    assert "package_manifest" in paths
    manifest = json.loads(paths["package_manifest"].read_text(encoding="utf-8"))
    assert manifest["status"] == "success"
    assert manifest["route"] == "playwright_chromium"
    assert manifest["run_mode"] == "fixture"
    assert manifest["artifacts"]["spec"]["path"].endswith("package_manifest_fixture.spec.json")
    assert manifest["artifacts"]["evidence_pack"]["exists"] is True
    assert manifest["artifacts"]["render_artifact"]["exists"] is True
    assert manifest["gates"]["render"] == "render_gate_result.json"
    assert "package_manifest_fixture.evidence.json" in manifest["source_paths"]
    assert set(paths).issubset(set(manifest["artifacts"]) | {"package_manifest"})


def test_compile_spec_unknown_route_writes_failed_package_manifest(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence_pack.json"
    out_dir = tmp_path / "compiled"
    evidence_path.write_text(make_manifest_pack().model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-spec", str(evidence_path), "--route", "bogus", "--out-dir", str(out_dir)])

    assert result.exit_code == 1
    assert "Unknown renderer route: bogus" in result.output
    manifest_path = out_dir / "evidence_pack.package_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["route"] == "bogus"
    assert manifest["gates"]["render"] == "render_gate_result.json"
    assert manifest["errors"] == ["Unknown renderer route: bogus"]
    assert manifest["artifacts"]["html"]["exists"] is True
    assert manifest["artifacts"]["pdf"]["exists"] is False


def test_compile_spec_cli_reports_package_manifest_path(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence_pack.json"
    out_dir = tmp_path / "compiled"
    evidence_path.write_text(make_manifest_pack().model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-spec", str(evidence_path), "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "package manifest" in result.output
    assert (out_dir / "evidence_pack.package_manifest.json").exists()


def test_package_manifest_normalizes_internal_paths_and_preserves_external_paths(tmp_path: Path) -> None:
    inside = tmp_path / "report.spec.json"
    inside.write_text("{}", encoding="utf-8")
    outside = tmp_path.parent / "external-source.json"
    outside.write_text("{}", encoding="utf-8")

    manifest = build_package_manifest(
        package_id="path_check",
        route="playwright_chromium",
        run_mode=RunMode.FIXTURE,
        status="success",
        out_dir=tmp_path,
        artifact_paths={"spec": inside, "external": outside},
        gates={},
        source_paths=[inside, outside],
    )

    assert manifest.artifacts["spec"].path == "report.spec.json"
    assert manifest.artifacts["spec"].exists is True
    assert manifest.artifacts["external"].path.endswith("external-source.json")
    assert "report.spec.json" in manifest.source_paths
    assert any(path.endswith("external-source.json") for path in manifest.source_paths)
