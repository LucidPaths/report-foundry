"""Research intake contract tests.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.evidence import validate_evidence_pack
from report_foundry.research_intake import (
    IntakeValidationError,
    ResearchIntake,
    build_research_intake_system_prompt,
    research_intake_to_evidence_pack,
)

runner = CliRunner()


def valid_intake_payload() -> dict[str, object]:
    return {
        "schema_version": "research_intake.v1",
        "request": {
            "keyword": "operator supplied keyword",
            "audience": "operator supplied audience",
            "task": "deep_research_report",
        },
        "sources_observed": [
            {
                "source_id": "src_a",
                "title": "Observed source title",
                "url": "https://source.test/a",
                "observed_at": "2026-06-18T12:00:00Z",
                "content_sha256": "a" * 64,
                "extractor": "research_intake_llm",
                "locator": "paragraph 2",
                "publisher": "Source Publisher",
                "source_tier": "trusted_secondary",
            }
        ],
        "extracted_facts": [
            {
                "fact_id": "fact_a",
                "subject": "Observed subject",
                "predicate": "has_property",
                "value": "observed value",
                "source_id": "src_a",
                "quote": "The observed source states the observed value.",
                "locator": "paragraph 2",
            }
        ],
        "proposed_claims": [
            {
                "claim_id": "claim_a",
                "text": "The report claim is fully backed by the observed fact.",
                "fact_ids": ["fact_a"],
                "confidence": "high",
            }
        ],
        "report": {
            "title": "Operator keyword report",
            "subtitle": "Source-backed full report",
            "summary": ["The full report is represented as structured report sections."],
            "sections": [
                {
                    "section_id": "section_a",
                    "title": "Findings",
                    "paragraphs": ["The report claim is fully backed by the observed fact."],
                    "claim_ids": ["claim_a"],
                    "fact_ids": ["fact_a"],
                }
            ],
        },
        "proposed_exhibits": [],
        "contradictions": [],
        "uncertainty_notes": [],
        "omitted_or_failed_sources": [],
    }


def test_research_intake_prompt_is_schema_only_without_topic_drift() -> None:
    prompt = build_research_intake_system_prompt()
    lowered = prompt.lower()

    assert "return only valid json" in lowered
    assert "full report" in lowered
    assert "do not write prose outside" in lowered
    assert "research_intake.v1" in prompt
    assert "ResearchIntake" in prompt
    assert "json_schema" in prompt
    for forbidden in ["spacex", "ipo", "example.com", "src_001", "fact_001", "claim_001", "current as of run date"]:
        assert forbidden not in lowered


def test_valid_research_intake_converts_to_evidence_pack() -> None:
    intake = ResearchIntake.model_validate(valid_intake_payload())

    pack = research_intake_to_evidence_pack(intake, author="Research Intake LLM")
    gate = validate_evidence_pack(pack)

    assert gate.ok, [check.code for check in gate.checks]
    assert pack.title == "Operator keyword report"
    assert pack.author == "Research Intake LLM"
    assert pack.scope["keyword"] == "operator supplied keyword"
    assert pack.sources[0].source_id == "src_a"
    assert pack.facts[0].source_id == "src_a"
    assert pack.claims[0].fact_ids == ["fact_a"]
    assert pack.report_sections[0].section_id == "executive_summary"
    assert pack.report_sections[0].paragraphs == ["The full report is represented as structured report sections."]
    assert pack.report_sections[1].paragraphs == ["The report claim is fully backed by the observed fact."]


def test_research_intake_rejects_claim_referencing_unknown_fact() -> None:
    payload = valid_intake_payload()
    payload["proposed_claims"][0]["fact_ids"] = ["missing_fact"]  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="claim_references_unknown_fact"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_fact_referencing_unknown_source() -> None:
    payload = valid_intake_payload()
    payload["extracted_facts"][0]["source_id"] = "missing_source"  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="fact_references_unknown_source"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_section_without_claim_support() -> None:
    payload = valid_intake_payload()
    payload["report"]["sections"][0]["claim_ids"] = []  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="section_requires_claim_support"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_schema_has_no_value_examples_or_prefilled_topics() -> None:
    schema = ResearchIntake.model_json_schema()
    serialized = json.dumps(schema).lower()

    for forbidden in ["spacex", "ipo", "example.com", "src_001", "fact_001", "claim_001"]:
        assert forbidden not in serialized
    assert "keyword" in serialized
    assert "sources_observed" in serialized
    assert "proposed_claims" in serialized


def test_compile_intake_cli_turns_structured_llm_output_into_package(tmp_path: Path) -> None:
    intake_path = tmp_path / "research_intake.json"
    out_dir = tmp_path / "compiled"
    intake_path.write_text(json.dumps(valid_intake_payload(), indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-intake", str(intake_path), "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "research intake" in result.output
    assert (out_dir / "research_intake.evidence.json").exists()
    assert (out_dir / "research_intake.package_manifest.json").exists()


def test_research_intake_prompt_cli_writes_schema_law_without_topic_drift(tmp_path: Path) -> None:
    prompt_path = tmp_path / "research_intake_system.md"

    result = runner.invoke(app, ["research-intake-prompt", "--output", str(prompt_path)])

    assert result.exit_code == 0, result.output
    prompt = prompt_path.read_text(encoding="utf-8").lower()
    assert "json_schema" in prompt
    for forbidden in ["spacex", "ipo", "example.com", "src_001", "fact_001", "claim_001"]:
        assert forbidden not in prompt


def test_research_intake_rejects_extra_fields_at_top_level_and_nested() -> None:
    payload = valid_intake_payload()
    payload["invented_shape"] = True
    with pytest.raises(ValueError):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    payload["sources_observed"][0]["invented_source_field"] = True  # type: ignore[index]
    with pytest.raises(ValueError):
        ResearchIntake.model_validate(payload)


def test_research_intake_rejects_path_shaped_exhibit_id() -> None:
    payload = valid_intake_payload()
    payload["proposed_exhibits"] = [
        {
            "visual_id": "../escape",
            "visual_type": "diagram",
            "title": "Bad exhibit",
            "purpose": "Demonstrate unsafe path-shaped ID rejection.",
            "preferred_tool": "mermaid",
            "provenance_fact_ids": ["fact_a"],
            "plain_text_payload": "flowchart LR\n  A-->B",
        }
    ]

    with pytest.raises(ValueError):
        ResearchIntake.model_validate(payload)


def test_research_intake_rejects_duplicate_section_and_exhibit_ids() -> None:
    payload = valid_intake_payload()
    payload["report"]["sections"].append(dict(payload["report"]["sections"][0]))  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="duplicate_section_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))

    payload = valid_intake_payload()
    exhibit = {
        "visual_id": "safe_visual",
        "visual_type": "diagram",
        "title": "Safe exhibit",
        "purpose": "Demonstrate duplicate visual ID rejection.",
        "preferred_tool": "mermaid",
        "provenance_fact_ids": ["fact_a"],
        "plain_text_payload": "flowchart LR\n  A-->B",
    }
    payload["proposed_exhibits"] = [dict(exhibit), dict(exhibit)]

    with pytest.raises(IntakeValidationError, match="duplicate_exhibit_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_section_facts_not_covered_by_referenced_claims() -> None:
    payload = valid_intake_payload()
    payload["extracted_facts"].append(  # type: ignore[index]
        {
            "fact_id": "fact_b",
            "subject": "Another subject",
            "predicate": "has_property",
            "value": "another value",
            "source_id": "src_a",
            "quote": "The observed source states another value.",
            "locator": "paragraph 3",
        }
    )
    payload["report"]["sections"][0]["fact_ids"] = ["fact_b"]  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="section_fact_not_covered_by_claim"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_compile_intake_cli_reports_malformed_json_cleanly(tmp_path: Path) -> None:
    intake_path = tmp_path / "bad_intake.json"
    intake_path.write_text('{"schema_version":"research_intake.v1", "unexpected": true}', encoding="utf-8")

    result = runner.invoke(app, ["compile-intake", str(intake_path), "--out-dir", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "invalid research intake" in result.output.lower()
    assert "traceback" not in result.output.lower()


def test_research_intake_rejects_reserved_generated_section_id_when_summary_present() -> None:
    payload = valid_intake_payload()
    payload["report"]["sections"][0]["section_id"] = "executive_summary"  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="reserved_section_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_reserved_generated_visual_id() -> None:
    payload = valid_intake_payload()
    payload["proposed_exhibits"] = [
        {
            "visual_id": "evidence_trace_map",
            "visual_type": "diagram",
            "title": "Reserved visual",
            "purpose": "Demonstrate reserved generated visual ID rejection.",
            "preferred_tool": "mermaid",
            "provenance_fact_ids": ["fact_a"],
            "plain_text_payload": "flowchart LR\n  A-->B",
        }
    ]

    with pytest.raises(IntakeValidationError, match="reserved_visual_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


@pytest.mark.parametrize("reserved_id", ["scope", "evidence_claims", "fact_table"])
def test_research_intake_rejects_downstream_generated_section_ids(reserved_id: str) -> None:
    payload = valid_intake_payload()
    payload["report"]["sections"][0]["section_id"] = reserved_id  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="reserved_section_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))
