"""Research run log tests for source selection, extraction steps, and evidence gaps.

Lattice: RF-P1 Source Sovereignty; RF-P4 Gates Fail Closed; RF-P5 Case Law Before Generation.
"""

from __future__ import annotations

import json

from report_foundry.factory import write_run_package
from report_foundry.research import build_research_evidence, write_research_artifacts


def test_research_run_log_records_selected_sources_extractions_and_gaps(tmp_path) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    write_run_package(topic="current SpaceX IPO launch newsletter", audience="executive readers", out_dir=run_dir)
    (source_dir / "partial.md").write_text(
        "\n".join(
            [
                "DIMENSION: starlink_economics",
                "Starlink economics depends on subscriber scale because recurring revenue creates cash-flow evidence; 2026 scale matters.",
            ]
        ),
        encoding="utf-8",
    )

    result = build_research_evidence(run_dir=run_dir, source_dir=source_dir)

    assert result.run_log.run_dir == str(run_dir)
    assert result.run_log.source_dir == str(source_dir)
    assert result.run_log.candidates[0].decision == "selected"
    assert result.run_log.candidates[0].reason == "local marked source file matched fixture adapter extension"
    assert result.run_log.extraction_steps[0].source_id == "local:partial.md"
    assert result.run_log.extraction_steps[0].dimension == "starlink_economics"
    assert result.run_log.extraction_steps[0].fact_id == "fact:starlink_economics:1"
    assert any(gap.dimension == "valuation_and_ipo_mechanics" for gap in result.run_log.evidence_gaps)
    assert result.gate_result.route_back_department == "research"


def test_write_research_artifacts_persists_research_run_log(tmp_path) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    write_run_package(topic="mechanism newsletter", audience="executive readers", out_dir=run_dir)
    (source_dir / "source.txt").write_text(
        "DIMENSION: mechanism\nMechanism depends on source law because claims need observed evidence; 2026 proof matters.",
        encoding="utf-8",
    )

    write_research_artifacts(run_dir=run_dir, source_dir=source_dir)

    path = run_dir / "research_run_log.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source_plan_dimensions"]
    assert data["candidates"][0]["decision"] == "selected"
    assert data["extraction_steps"][0]["extractor"] == "local_marked_source_v1"
    assert "research_run_log" in data["artifact_role"]
