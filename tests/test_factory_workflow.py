from __future__ import annotations

from report_foundry.evidence import EvidenceClaim, EvidenceFact, EvidencePack, SourceObservation
from report_foundry.factory import (
    Department,
    PageMetrics,
    ReportRunManifest,
    build_case_rubric,
    evaluate_factory_gates,
)


def source(source_id: str = "spacex-10k-source") -> SourceObservation:
    return SourceObservation(
        source_id=source_id,
        title="Primary source fixture",
        url="https://example.test/source",
        observed_at="2026-06-17T00:00:00Z",
        content_sha256="b" * 64,
        extractor="fixture",
    )


def fact(fact_id: str, subject: str, predicate: str, value: str, quote: str) -> EvidenceFact:
    return EvidenceFact(
        fact_id=fact_id,
        subject=subject,
        predicate=predicate,
        value=value,
        source_id="spacex-10k-source",
        quote=quote,
    )


def pack_with_dimensions(dimensions: list[str]) -> EvidencePack:
    facts = [
        fact(
            fact_id=f"fact:{dimension}",
            subject="SpaceX IPO",
            predicate=f"dimension:{dimension}",
            value="covered",
            quote=f"Source-backed coverage for {dimension}",
        )
        for dimension in dimensions
    ]
    return EvidencePack(
        title="SpaceX IPO launch newsletter",
        sources=[source()],
        facts=facts,
        claims=[
            EvidenceClaim(
                text="SpaceX IPO readiness depends on Starlink economics, government contracts, launch cadence, and listing mechanics.",
                fact_ids=[item.fact_id for item in facts],
                confidence="high",
            )
        ],
    )


def test_spacex_ipo_topic_expands_into_non_obvious_required_dimensions() -> None:
    rubric = build_case_rubric("current SpaceX IPO launch newsletter", audience="executive readers")

    names = {dimension.name for dimension in rubric.required_dimensions}

    assert "starlink_economics" in names
    assert "government_and_defense_revenue" in names
    assert "launch_cadence_and_payload_proof" in names
    assert "listing_and_regulatory_mechanics" in names
    assert rubric.required_source_tiers["primary"] >= 4
    assert rubric.required_visuals >= {"business_segment_map", "numbers_chart", "bull_bear_matrix"}
    assert rubric.final_score_minimum >= 85


def test_missing_required_dimension_routes_back_to_research_department() -> None:
    rubric = build_case_rubric("current SpaceX IPO launch newsletter", audience="executive readers")
    incomplete_pack = pack_with_dimensions(["launch_cadence_and_payload_proof", "government_and_defense_revenue"])
    manifest = ReportRunManifest(topic="current SpaceX IPO launch newsletter", rubric=rubric)

    result = evaluate_factory_gates(manifest, incomplete_pack, pages=[PageMetrics(page_number=1, fill_ratio=0.72, has_source_appendix=False)])

    assert not result.ok
    research_failures = [check for check in result.checks if check.department == Department.RESEARCH]
    assert research_failures
    assert any("starlink_economics" in check.message for check in research_failures)
    assert result.route_back_department == Department.RESEARCH


def test_vague_claim_routes_back_to_synthesis_department() -> None:
    rubric = build_case_rubric("current SpaceX IPO launch newsletter", audience="executive readers")
    covered_dimensions = [dimension.name for dimension in rubric.required_dimensions]
    dimension_facts = [
        fact(
            fact_id=f"fact:{dimension}",
            subject="SpaceX IPO",
            predicate=f"dimension:{dimension}",
            value="covered",
            quote=f"Source-backed coverage for {dimension}",
        )
        for dimension in covered_dimensions
    ]
    vague_pack = EvidencePack(
        title="SpaceX IPO launch newsletter",
        sources=[source()],
        facts=[*dimension_facts, fact("fact:hype", "SpaceX IPO", "market_sentiment", "hype", "Some investors are excited.")],
        claims=[EvidenceClaim(text="SpaceX could be huge.", fact_ids=["fact:hype"], confidence="medium")],
    )
    manifest = ReportRunManifest(topic="current SpaceX IPO launch newsletter", rubric=rubric)

    result = evaluate_factory_gates(manifest, vague_pack, pages=[PageMetrics(page_number=1, fill_ratio=0.75, has_source_appendix=True)])

    assert not result.ok
    synthesis_failures = [check for check in result.checks if check.department == Department.SYNTHESIS]
    assert synthesis_failures
    assert any("hard-hitting claim" in check.message for check in synthesis_failures)
    assert result.route_back_department == Department.SYNTHESIS


def test_layout_gate_requires_source_appendix_and_useful_page_fill_without_dense_boxes() -> None:
    rubric = build_case_rubric("european banking situation newsletter", audience="executive readers")
    dimensions = [dimension.name for dimension in rubric.required_dimensions]
    pack = pack_with_dimensions(dimensions)
    manifest = ReportRunManifest(topic="european banking situation newsletter", rubric=rubric)

    result = evaluate_factory_gates(
        manifest,
        pack,
        pages=[
            PageMetrics(page_number=1, fill_ratio=0.18, has_source_appendix=False),
            PageMetrics(page_number=2, fill_ratio=0.64, has_source_appendix=False),
        ],
    )

    assert not result.ok
    layout_failures = [check for check in result.checks if check.department == Department.LAYOUT]
    assert any("source appendix" in check.message for check in layout_failures)
    assert any("underfilled" in check.message for check in layout_failures)
    assert result.route_back_department == Department.LAYOUT
