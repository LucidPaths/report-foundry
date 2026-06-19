"""Evidence workflow tests proving source-to-claim lineage.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed.
"""

from __future__ import annotations

import pytest

from report_foundry.evidence import (
    EvidenceClaim,
    EvidenceFact,
    EvidencePack,
    SourceObservation,
    build_report_from_evidence,
    validate_evidence_pack,
)
from report_foundry.qa import run_quality_gates


def make_pack() -> EvidencePack:
    return EvidencePack(
        title="Mechanical market brief",
        scope={
            "question": "Which suppliers are qualified and what can we truthfully claim?",
            "audience": "report workflow test",
        },
        sources=[
            SourceObservation(
                source_id="supplier-registry",
                title="Supplier registry fixture",
                url="https://example.com/supplier-registry",
                observed_at="2026-06-17T00:00:00Z",
                content_sha256="a" * 64,
                extractor="fixture",
            )
        ],
        facts=[
            EvidenceFact(
                fact_id="fact:supplier-qualified:acme",
                subject="acme-supply",
                predicate="is_qualified_supplier_id",
                value="true",
                source_id="supplier-registry",
                quote="acme-supply",
            )
        ],
        claims=[
            EvidenceClaim(
                text="acme-supply is a qualified supplier ID.",
                fact_ids=["fact:supplier-qualified:acme"],
                confidence="high",
            )
        ],
    )


def test_evidence_pack_validates_source_fact_claim_chain() -> None:
    pack = make_pack()

    result = validate_evidence_pack(pack)

    assert result.ok
    assert result.checks == []


def test_evidence_pack_fails_closed_on_unsupported_claim() -> None:
    pack = make_pack().model_copy(
        update={
            "claims": [
                EvidenceClaim(
                    text="kimi-k2.7-code is faster than acme-supply.",
                    fact_ids=["missing:fact"],
                    confidence="high",
                )
            ]
        }
    )

    result = validate_evidence_pack(pack)

    assert not result.ok
    assert result.checks[0].code == "missing_fact"


def test_build_report_from_evidence_preserves_claim_citations() -> None:
    pack = make_pack()

    report = build_report_from_evidence(pack)
    qa = run_quality_gates(report)

    assert report.title == "Mechanical market brief"
    assert qa.ok
    [claim] = report.claims()
    assert claim.text == "acme-supply is a qualified supplier ID."
    assert claim.verification_status == "supported"
    assert claim.citations[0].source_id == "supplier-registry"
    assert claim.citations[0].quote == "acme-supply"


def test_build_report_from_evidence_refuses_invalid_pack() -> None:
    pack = make_pack().model_copy(update={"facts": []})

    with pytest.raises(ValueError, match="missing_fact"):
        build_report_from_evidence(pack)
