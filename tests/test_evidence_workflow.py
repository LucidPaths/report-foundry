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
        title="Mechanical model brief",
        scope={
            "question": "Which models are live and what can we truthfully claim?",
            "audience": "agent workflow test",
        },
        sources=[
            SourceObservation(
                source_id="ollama-models",
                title="Ollama /v1/models fixture",
                url="https://ollama.com/v1/models",
                observed_at="2026-06-17T00:00:00Z",
                content_sha256="a" * 64,
                extractor="fixture",
            )
        ],
        facts=[
            EvidenceFact(
                fact_id="fact:model-live:glm-5.2",
                subject="glm-5.2",
                predicate="is_live_model_id",
                value="true",
                source_id="ollama-models",
                quote="glm-5.2",
            )
        ],
        claims=[
            EvidenceClaim(
                text="glm-5.2 is a live Ollama Cloud model ID.",
                fact_ids=["fact:model-live:glm-5.2"],
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
                    text="kimi-k2.7-code is faster than glm-5.2.",
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

    assert report.title == "Mechanical model brief"
    assert qa.ok
    [claim] = report.claims()
    assert claim.text == "glm-5.2 is a live Ollama Cloud model ID."
    assert claim.verification_status == "supported"
    assert claim.citations[0].source_id == "ollama-models"
    assert claim.citations[0].quote == "glm-5.2"


def test_build_report_from_evidence_refuses_invalid_pack() -> None:
    pack = make_pack().model_copy(update={"facts": []})

    with pytest.raises(ValueError, match="missing_fact"):
        build_report_from_evidence(pack)
