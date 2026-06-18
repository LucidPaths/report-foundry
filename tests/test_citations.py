"""Citation seam tests for reader-facing source metadata.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed.
"""

from __future__ import annotations

from report_foundry.citations import (
    citation_gate_checks,
    citation_records_from_evidence,
    export_bibtex,
    export_csl_json,
    render_source_appendix_markdown,
)
from report_foundry.evidence import EvidenceClaim, EvidenceFact, EvidencePack, SourceObservation


def make_citation_pack() -> EvidencePack:
    source = SourceObservation(
        source_id="src_reader_source",
        title="SpaceX public launch registry",
        url="https://example.test/spacex-launch-registry",
        observed_at="2026-06-18T10:00:00Z",
        content_sha256="a" * 64,
        extractor="fixture",
        locator="table 2",
        source_tier="primary",
        publisher="Example Registry",
        published_at="2026-06-01",
        citation_metadata={"author": "Example Registry Team", "type": "webpage"},
    )
    fact = EvidenceFact(
        fact_id="fact_launch_registry",
        subject="SpaceX IPO",
        predicate="dimension:launch_cadence_and_payload_proof",
        value="covered",
        source_id=source.source_id,
        quote="Launch cadence depends on repeat payload delivery because frequent missions prove operational capacity; 2026 cadence is the bottleneck.",
        locator="row 4",
    )
    claim = EvidenceClaim(
        text="SpaceX IPO readiness depends on launch cadence because repeat payload delivery proves operating capacity; 2026 cadence is the bottleneck.",
        fact_ids=[fact.fact_id],
        confidence="high",
    )
    return EvidencePack(title="Citation fixture", sources=[source], facts=[fact], claims=[claim])


def test_citation_record_preserves_hash_but_reader_appendix_prioritizes_human_locator() -> None:
    records = citation_records_from_evidence(make_citation_pack())

    assert records[0].content_sha256 == "a" * 64
    appendix = render_source_appendix_markdown(records)
    assert "SpaceX public launch registry" in appendix
    assert "https://example.test/spacex-launch-registry" in appendix
    assert "accessed 2026-06-18T10:00:00Z" in appendix
    assert "row 4" in appendix
    assert "aaaaaaaa" not in appendix


def test_csl_json_export_includes_reader_fields_for_citeproc_tools() -> None:
    records = citation_records_from_evidence(make_citation_pack())
    csl = export_csl_json(records)

    assert csl == [
        {
            "id": "cite_src_reader_source",
            "type": "webpage",
            "title": "SpaceX public launch registry",
            "URL": "https://example.test/spacex-launch-registry",
            "author": [{"literal": "Example Registry Team"}],
            "publisher": "Example Registry",
            "issued": {"literal": "2026-06-01"},
            "accessed": {"literal": "2026-06-18T10:00:00Z"},
        }
    ]


def test_bibtex_export_is_stable_enough_for_pandoc_ingestion() -> None:
    records = citation_records_from_evidence(make_citation_pack())
    bibtex = export_bibtex(records)

    assert "@online{cite_src_reader_source," in bibtex
    assert "title = {SpaceX public launch registry}" in bibtex
    assert "url = {https://example.test/spacex-launch-registry}" in bibtex
    assert "urldate = {2026-06-18T10:00:00Z}" in bibtex
    assert "note = {table 2; row 4}" in bibtex


def test_product_citation_gate_rejects_claim_source_without_reader_locator() -> None:
    pack = make_citation_pack()
    pack.sources[0].url = None
    pack.sources[0].locator = None
    pack.facts[0].locator = None

    checks = citation_gate_checks(pack, product_mode=True)

    assert any(check.code == "citation_missing_reader_locator" and check.severity == "error" for check in checks)


def test_duplicate_citation_ids_fail_gate() -> None:
    pack = make_citation_pack()
    duplicate = pack.sources[0].model_copy(update={"source_id": "src reader source"})
    pack.sources.append(duplicate)

    checks = citation_gate_checks(pack, product_mode=False)

    assert any(check.code == "duplicate_citation_id" for check in checks)
