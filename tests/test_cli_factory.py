"""CLI contract tests for factory planning and fixture research.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from report_foundry.cli import app

runner = CliRunner()


def write_cli_sources(source_dir):
    source_dir.mkdir()
    (source_dir / "spacex.md").write_text(
        "\n".join(
            [
                "DIMENSION: valuation_and_ipo_mechanics",
                "Valuation depends on liquidity because 2026 private marks set the IPO baseline; listing pressure matters.",
                "DIMENSION: starlink_economics",
                "Starlink economics depends on subscribers because recurring revenue creates cash-flow evidence; 2026 scale matters.",
                "DIMENSION: government_and_defense_revenue",
                "Government revenue depends on NASA contracts because defense demand reduces cyclicality; 2026 backlog matters.",
                "DIMENSION: launch_cadence_and_payload_proof",
                "Launch cadence depends on payload delivery because repeat missions prove capacity; 2026 cadence matters.",
                "DIMENSION: listing_and_regulatory_mechanics",
                "Listing mechanics depends on securities approvals because rules can delay liquidity; 2026 filings matter.",
                "DIMENSION: bull_bear_market_structure",
                "Market structure depends on bull and bear cases because comparable multiples create spread; 2026 sentiment matters.",
            ]
        ),
        encoding="utf-8",
    )


def test_plan_run_cli_writes_factory_run_package(tmp_path) -> None:
    out_dir = tmp_path / "run"

    result = runner.invoke(
        app,
        [
            "plan-run",
            "current SpaceX IPO launch newsletter",
            "--audience",
            "executive readers",
            "--out-dir",
            str(out_dir),
            "--integration-mode",
            "mcp",
            "--source",
            "company-db",
            "--source",
            "web",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "factory run package" in result.output
    assert "mode=fixture" in result.output
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "source_plan.json").exists()
    assert (out_dir / "visual_plan.json").exists()
    assert (out_dir / "worker_plan.json").exists()

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    source_plan = json.loads((out_dir / "source_plan.json").read_text(encoding="utf-8"))
    visual_plan = json.loads((out_dir / "visual_plan.json").read_text(encoding="utf-8"))
    worker_plan = json.loads((out_dir / "worker_plan.json").read_text(encoding="utf-8"))

    assert manifest["integration_mode"] == "mcp"
    assert manifest["run_mode"] == "fixture"
    assert "company-db" in manifest["connected_sources"]
    assert any(item["dimension"] == "starlink_economics" for item in source_plan["items"])
    assert any(item["visual_id"] == "business_segment_map" for item in visual_plan["items"])
    assert any(task["worker_id"] == "research-starlink-economics" for task in worker_plan["tasks"])
    assert any(task["worker_id"] == "qa-final-gates" for task in worker_plan["tasks"])


def test_plan_run_cli_persists_product_run_mode(tmp_path) -> None:
    out_dir = tmp_path / "product-run"

    result = runner.invoke(app, ["plan-run", "current SpaceX IPO launch newsletter", "--out-dir", str(out_dir), "--run-mode", "product"])

    assert result.exit_code == 0, result.output
    assert "mode=product" in result.output
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    initial_gate = json.loads((out_dir / "initial_gate_result.json").read_text(encoding="utf-8"))
    assert manifest["run_mode"] == "product"
    assert any(check["code"] == "insufficient_source_tier" and check["severity"] == "error" for check in initial_gate["checks"])


def test_research_run_cli_writes_evidence_pack_and_gate_result(tmp_path, monkeypatch) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    write_cli_sources(source_dir)

    plan_result = runner.invoke(app, ["plan-run", "current SpaceX IPO launch newsletter", "--out-dir", str(run_dir)])
    assert plan_result.exit_code == 0, plan_result.output

    monkeypatch.chdir(tmp_path)
    research_result = runner.invoke(app, ["research-run", str(run_dir), "--source-dir", "sources"])

    assert research_result.exit_code == 0, research_result.output
    assert "research evidence" in research_result.output
    assert "mode=fixture" in research_result.output
    assert (run_dir / "evidence_pack.json").exists()
    assert (run_dir / "research_gate_result.json").exists()
    gate = json.loads((run_dir / "research_gate_result.json").read_text(encoding="utf-8"))
    evidence = json.loads((run_dir / "evidence_pack.json").read_text(encoding="utf-8"))
    run_log = json.loads((run_dir / "research_run_log.json").read_text(encoding="utf-8"))
    assert gate["ok"] is True
    assert evidence["scope"]["run_mode"] == "fixture"
    assert evidence["scope"]["artifact_status"] == "fixture"
    assert run_log["run_mode"] == "fixture"
    assert len(evidence["sources"]) == 1
    assert len(evidence["facts"]) == 6


def test_product_mode_rejects_local_fixture_research_without_explicit_override(tmp_path) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    write_cli_sources(source_dir)

    plan_result = runner.invoke(app, ["plan-run", "current SpaceX IPO launch newsletter", "--out-dir", str(run_dir), "--run-mode", "product"])
    assert plan_result.exit_code == 0, plan_result.output

    blocked = runner.invoke(app, ["research-run", str(run_dir), "--source-dir", str(source_dir)])
    assert blocked.exit_code == 1
    assert "product mode requires a connector" in blocked.output

    allowed = runner.invoke(app, ["research-run", str(run_dir), "--source-dir", str(source_dir), "--allow-fixture-sources"])
    assert allowed.exit_code == 1
    assert "route_back=Department.RESEARCH" in allowed.output
    evidence = json.loads((run_dir / "evidence_pack.json").read_text(encoding="utf-8"))
    gate = json.loads((run_dir / "research_gate_result.json").read_text(encoding="utf-8"))
    run_log = json.loads((run_dir / "research_run_log.json").read_text(encoding="utf-8"))
    assert evidence["scope"]["run_mode"] == "product"
    assert evidence["scope"]["artifact_status"] == "product"
    assert evidence["scope"]["fixture_source_override"] is True
    assert any(check["code"] == "insufficient_source_tier" and check["severity"] == "error" for check in gate["checks"])
    assert run_log["run_mode"] == "product"
