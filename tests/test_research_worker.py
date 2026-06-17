from __future__ import annotations

import json

from report_foundry.evidence import validate_evidence_pack
from report_foundry.factory import Department, write_run_package
from report_foundry.research import build_research_evidence, write_research_artifacts


def write_source_set(source_dir):
    source_dir.mkdir()
    (source_dir / "spacex_primary.md").write_text(
        "\n".join(
            [
                "# SpaceX source notes",
                "DIMENSION: valuation_and_ipo_mechanics",
                "Valuation depends on private-share liquidity because observed transactions show multiple price marks; 2026 timing remains conditional.",
                "DIMENSION: starlink_economics",
                "Starlink economics depends on subscriber scale because recurring broadband revenue creates IPO-ready cash-flow evidence; 2026 watch item.",
                "DIMENSION: government_and_defense_revenue",
                "Government revenue depends on NASA and defense contracts because contracted missions reduce demand volatility; 2026 backlog matters.",
            ]
        ),
        encoding="utf-8",
    )
    (source_dir / "spacex_registry.txt").write_text(
        "\n".join(
            [
                "DIMENSION: launch_cadence_and_payload_proof",
                "Launch cadence depends on repeat payload delivery because frequent missions prove operational capacity; 2026 cadence is the bottleneck.",
                "DIMENSION: listing_and_regulatory_mechanics",
                "Listing mechanics depends on exchange and securities approvals because rule timing can delay liquidity; 2026 path needs documented filings.",
                "DIMENSION: bull_bear_market_structure",
                "Market structure depends on bull and bear cases because comparable multiples create valuation spread; 2026 risk is sentiment compression.",
            ]
        ),
        encoding="utf-8",
    )


def test_build_research_evidence_extracts_marked_dimensions_with_hashes(tmp_path) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    write_run_package(topic="current SpaceX IPO launch newsletter", audience="executive readers", out_dir=run_dir)
    write_source_set(source_dir)

    result = build_research_evidence(run_dir=run_dir, source_dir=source_dir)

    assert result.gate_result.ok
    assert result.gate_result.route_back_department is None
    assert len(result.evidence.sources) == 2
    assert all(len(source.content_sha256) == 64 for source in result.evidence.sources)
    assert validate_evidence_pack(result.evidence).ok

    predicates = {fact.predicate for fact in result.evidence.facts}
    assert "dimension:starlink_economics" in predicates
    assert "dimension:listing_and_regulatory_mechanics" in predicates
    assert len(result.evidence.claims) >= result.manifest.rubric.min_hard_claims
    assert all(claim.fact_ids for claim in result.evidence.claims)


def test_build_research_evidence_fails_closed_when_dimension_marker_missing(tmp_path) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    write_run_package(topic="current SpaceX IPO launch newsletter", audience="executive readers", out_dir=run_dir)
    write_source_set(source_dir)
    (source_dir / "spacex_registry.txt").write_text("DIMENSION: launch_cadence_and_payload_proof\nOnly one late dimension is covered; 2026.", encoding="utf-8")

    result = build_research_evidence(run_dir=run_dir, source_dir=source_dir)

    assert not result.gate_result.ok
    assert result.gate_result.route_back_department == Department.RESEARCH
    messages = [check.message for check in result.gate_result.checks]
    assert any("listing_and_regulatory_mechanics" in message for message in messages)
    assert any("bull_bear_market_structure" in message for message in messages)


def test_write_research_artifacts_persists_evidence_and_gate_result(tmp_path) -> None:
    run_dir = tmp_path / "run"
    source_dir = tmp_path / "sources"
    write_run_package(topic="current SpaceX IPO launch newsletter", audience="executive readers", out_dir=run_dir)
    write_source_set(source_dir)

    result = write_research_artifacts(run_dir=run_dir, source_dir=source_dir)

    assert (run_dir / "evidence_pack.json").exists()
    assert (run_dir / "research_gate_result.json").exists()
    evidence = json.loads((run_dir / "evidence_pack.json").read_text(encoding="utf-8"))
    gate = json.loads((run_dir / "research_gate_result.json").read_text(encoding="utf-8"))
    assert evidence["scope"]["research_mode"] == "local_marked_sources"
    assert gate["ok"] is True
    assert result.gate_result.ok
