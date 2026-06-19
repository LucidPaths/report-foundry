"""Research intake contract tests.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from report_foundry.cli import app
from report_foundry.citations import citation_export_from_evidence
from report_foundry.evidence import validate_evidence_pack
from report_foundry.report_spec import compile_report_spec, compile_spec_to_report, write_spec_artifacts
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
        "intake_id": "operator_keyword_report",
        "request": {
            "user_request": "operator supplied keyword",
            "topic": "operator supplied keyword",
            "core_question": "What does the observed source support?",
            "audience": "operator supplied audience",
            "intended_use": "compile a source-backed report",
            "geographic_scope": None,
            "time_scope": None,
            "depth": "deep_research_report",
            "format_preferences": ["pdf"],
            "explicit_constraints": [],
        },
        "assumptions": [],
        "sources": [
            {
                "id": "source_a",
                "title": "Observed source title",
                "source_type": "provided_document",
                "publisher_or_author": "Source Publisher",
                "locator": "https://source.test/a",
                "publication_date": None,
                "observed_at": "2026-06-18T12:00:00Z",
                "access_method": "research_intake_authored",
                "content_hash": "a" * 64,
                "reliability": "medium",
                "reliability_rationale": "The payload was provided and directly quoted.",
                "relevance": "It directly supports the report claim.",
                "limitations": [],
                "provenance_notes": None,
            }
        ],
        "failed_sources": [],
        "excluded_sources": [],
        "facts": [
            {
                "id": "fact_a",
                "source_id": "source_a",
                "evidence_quote_or_excerpt": "The observed source states the observed value.",
                "paraphrase": "The source reports an observed value.",
                "normalized_statement": "Observed subject has observed value.",
                "date_or_period": None,
                "geography_or_scope": None,
                "units": None,
                "value": "observed value",
                "confidence": "high",
                "supports": ["claim_a"],
                "limitations": [],
            }
        ],
        "proposed_claims": [
            {
                "id": "claim_a",
                "claim": "The report claim is fully backed by the observed fact.",
                "claim_type": "descriptive",
                "supporting_fact_ids": ["fact_a"],
                "opposing_fact_ids": [],
                "confidence": "high",
                "reasoning": "The claim restates the quoted observed fact without broadening it.",
                "caveats": [],
                "implication": "The report may include the claim safely.",
                "suitable_report_section_ids": ["section_a"],
            }
        ],
        "contradictions": [],
        "uncertainties": [],
        "research_gaps": [],
        "report": {
            "title": "Operator keyword report",
            "subtitle": "Source-backed full report",
            "thesis": {
                "text": "The observed evidence supports a bounded descriptive report.",
                "referenced_claim_ids": ["claim_a"],
                "referenced_fact_ids": ["fact_a"],
                "confidence": "high",
            },
            "executive_summary": {
                "text": "The full report is represented as structured report sections.",
                "referenced_claim_ids": ["claim_a"],
                "referenced_fact_ids": ["fact_a"],
            },
            "key_takeaways": [
                {
                    "takeaway": "The claim is directly source-backed.",
                    "evidence_basis": "The fact quotes the observed source.",
                    "implication": "The report can render it without unsupported expansion.",
                    "confidence": "high",
                    "referenced_claim_ids": ["claim_a"],
                    "referenced_fact_ids": ["fact_a"],
                }
            ],
            "sections": [
                {
                    "id": "section_a",
                    "heading": "Observed evidence supports the bounded finding",
                    "lede": "The source-backed finding is narrow and auditable.",
                    "body": "The report claim is fully backed by the observed fact.",
                    "so_what": "The renderer receives reader-facing prose rather than a schema dump.",
                    "limits": "The conclusion is limited to the observed source payload.",
                    "referenced_claim_ids": ["claim_a"],
                    "referenced_fact_ids": ["fact_a"],
                    "suggested_exhibit_ids": [],
                }
            ],
            "conclusion": {
                "text": "The report should remain bounded to the directly observed evidence.",
                "referenced_claim_ids": ["claim_a"],
                "referenced_fact_ids": ["fact_a"],
            },
            "what_to_watch": [
                {
                    "item": "Whether additional observed sources confirm or narrow the finding.",
                    "why_it_matters": "Additional source observation would test whether the bounded claim generalizes.",
                    "related_claim_ids": ["claim_a"],
                    "related_fact_ids": ["fact_a"],
                }
            ],
        },
        "exhibits": [],
        "methodology": {
            "summary": "A provided source payload was quoted and normalized into facts, claims, and report prose.",
            "source_selection": "Only the observed source was used.",
            "evidence_extraction": "The quoted excerpt was converted into one atomic fact.",
            "confidence_method": "Confidence reflects direct quote support and narrow claim wording.",
            "known_limitations": [],
        },
        "validation_notes": {
            "self_audit_passed": True,
            "issues_found": [],
            "repair_actions_taken": [],
            "validator_risks": [],
        },
    }


def test_research_intake_prompt_is_uploaded_research_foundry_system_prompt() -> None:
    prompt = build_research_intake_system_prompt()
    lowered = prompt.lower()

    assert prompt.startswith("# Report Foundry Research Intake System Prompt")
    assert "You are using the Report Foundry Research Intake Contract." in prompt
    assert "# 1. Core Law" in prompt
    assert "# 4. Research Workflow" in prompt
    assert "# 8. Report Writing Standards" in prompt
    assert "# 14. Validation Checklist" in prompt
    assert "# 23. Final Output Instruction" in prompt
    assert "Runtime JSON Schema" in prompt
    assert "json_schema" in prompt
    assert "research_intake.v1" in prompt
    assert "not \"something like\"" not in lowered
    assert "that's the spine" not in lowered


def test_research_intake_prompt_contains_verifiability_failure_laws() -> None:
    prompt = build_research_intake_system_prompt()

    required_laws = [
        "If you did not observe a source, you cannot cite it.",
        "If you cannot quote or excerpt evidence, you cannot record",
        "Every claim must be built from fact IDs.",
        "A citation must lead a human reader back to the observed",
        "Do not smooth over uncertainty.",
        "No orphan objects are allowed.",
        "This prompt defines structure only.",
        "The runtime user request defines the topic.",
        "Accuracy beats completeness.",
        "Traceability beats fluency.",
        "Evidence beats prior knowledge.",
    ]
    for law in required_laws:
        assert law in prompt


def test_research_intake_prompt_has_no_topic_specific_urls_or_canned_report_content() -> None:
    prompt = build_research_intake_system_prompt().lower()

    for forbidden in ["spacex", "ipo", "example.com", "src_001", "fact_001", "claim_001", "current as of run date"]:
        assert forbidden not in prompt


def test_research_intake_schema_matches_uploaded_prompt_top_level_shape() -> None:
    schema = ResearchIntake.model_json_schema()
    props = set(schema["properties"])

    assert props == {
        "schema_version",
        "intake_id",
        "request",
        "assumptions",
        "sources",
        "failed_sources",
        "excluded_sources",
        "facts",
        "proposed_claims",
        "contradictions",
        "uncertainties",
        "research_gaps",
        "report",
        "exhibits",
        "methodology",
        "validation_notes",
    }


def test_valid_research_intake_converts_to_evidence_pack() -> None:
    intake = ResearchIntake.model_validate(valid_intake_payload())

    pack = research_intake_to_evidence_pack(intake, author="Research Intake Author")
    gate = validate_evidence_pack(pack)

    assert gate.ok, [check.code for check in gate.checks]
    assert pack.title == "Operator keyword report"
    assert pack.author == "Research Intake Author"
    assert pack.scope["topic"] == "operator supplied keyword"
    assert pack.sources[0].source_id == "source_a"
    assert pack.facts[0].source_id == "source_a"
    assert pack.claims[0].fact_ids == ["fact_a"]
    assert pack.professional_report is not None
    assert pack.professional_report.one_sentence_thesis == "The observed evidence supports a bounded descriptive report."
    assert pack.report_sections[0].section_id == "executive_summary"
    assert pack.report_sections[0].paragraphs == ["The full report is represented as structured report sections."]
    assert pack.report_sections[1].paragraphs[0] == "The report claim is fully backed by the observed fact."


def test_research_intake_rejects_claim_referencing_unknown_fact() -> None:
    payload = valid_intake_payload()
    payload["proposed_claims"][0]["supporting_fact_ids"] = ["missing_fact"]  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="claim_references_unknown_fact"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_fact_referencing_unknown_source() -> None:
    payload = valid_intake_payload()
    payload["facts"][0]["source_id"] = "missing_source"  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="fact_references_unknown_source"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_section_without_claim_support() -> None:
    payload = valid_intake_payload()
    payload["report"]["sections"][0]["referenced_claim_ids"] = []  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="section_requires_claim_support"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_compile_intake_cli_turns_structured_authored_output_into_package(tmp_path: Path) -> None:
    intake_path = tmp_path / "research_intake.json"
    out_dir = tmp_path / "compiled"
    intake_path.write_text(json.dumps(valid_intake_payload(), indent=2), encoding="utf-8")

    result = runner.invoke(app, ["compile-intake", str(intake_path), "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "research intake" in result.output
    assert (out_dir / "research_intake.evidence.json").exists()
    assert (out_dir / "research_intake.package_manifest.json").exists()


def test_research_intake_prompt_cli_writes_uploaded_law_without_topic_drift(tmp_path: Path) -> None:
    prompt_path = tmp_path / "research_intake_system.md"

    result = runner.invoke(app, ["research-intake-prompt", "--output", str(prompt_path)])

    assert result.exit_code == 0, result.output
    prompt = prompt_path.read_text(encoding="utf-8")
    assert prompt.startswith("# Report Foundry Research Intake System Prompt")
    assert "# 23. Final Output Instruction" in prompt
    for forbidden in ["spacex", "ipo", "example.com", "src_001", "fact_001", "claim_001"]:
        assert forbidden not in prompt.lower()


def test_research_intake_rejects_extra_fields_at_top_level_and_nested() -> None:
    payload = valid_intake_payload()
    payload["invented_shape"] = True
    with pytest.raises(ValueError):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    payload["sources"][0]["invented_source_field"] = True  # type: ignore[index]
    with pytest.raises(ValueError):
        ResearchIntake.model_validate(payload)


def test_research_intake_rejects_path_shaped_exhibit_id() -> None:
    payload = valid_intake_payload()
    payload["exhibits"] = [
        {
            "id": "../escape",
            "title": "Bad exhibit",
            "exhibit_type": "flow_diagram",
            "purpose": "Demonstrate unsafe path-shaped ID rejection.",
            "referenced_fact_ids": ["fact_a"],
            "referenced_claim_ids": ["claim_a"],
            "data_requirements": [],
            "visual_encoding": "node link",
            "limitations": [],
            "renderer_notes": "render as mermaid",
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
        "id": "exhibit_safe",
        "title": "Safe exhibit",
        "exhibit_type": "flow_diagram",
        "purpose": "Demonstrate duplicate visual ID rejection.",
        "referenced_fact_ids": ["fact_a"],
        "referenced_claim_ids": ["claim_a"],
        "data_requirements": [],
        "visual_encoding": "node link",
        "limitations": [],
        "renderer_notes": "render as mermaid",
    }
    payload["exhibits"] = [dict(exhibit), dict(exhibit)]

    with pytest.raises(IntakeValidationError, match="duplicate_exhibit_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_section_facts_not_covered_by_referenced_claims() -> None:
    payload = valid_intake_payload()
    payload["facts"].append(  # type: ignore[index]
        {
            "id": "fact_b",
            "source_id": "source_a",
            "evidence_quote_or_excerpt": "The observed source states another value.",
            "paraphrase": "The source reports another observed value.",
            "normalized_statement": "Observed subject has another observed value.",
            "date_or_period": None,
            "geography_or_scope": None,
            "units": None,
            "value": "another value",
            "confidence": "high",
            "supports": [],
            "limitations": [],
        }
    )
    payload["report"]["sections"][0]["referenced_fact_ids"] = ["fact_b"]  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="section_a_fact_not_covered_by_claim"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_compile_intake_cli_reports_malformed_json_cleanly(tmp_path: Path) -> None:
    intake_path = tmp_path / "bad_intake.json"
    intake_path.write_text('{"schema_version":"research_intake.v1", "unexpected": true}', encoding="utf-8")

    result = runner.invoke(app, ["compile-intake", str(intake_path), "--out-dir", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "invalid research intake" in result.output.lower()
    assert "traceback" not in result.output.lower()


@pytest.mark.parametrize("reserved_id", ["executive_summary", "scope", "evidence_claims", "fact_table"])
def test_research_intake_rejects_downstream_generated_section_ids(reserved_id: str) -> None:
    payload = valid_intake_payload()
    payload["report"]["sections"][0]["id"] = reserved_id  # type: ignore[index]

    with pytest.raises(IntakeValidationError, match="reserved_section_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))


def test_research_intake_rejects_reserved_generated_visual_id() -> None:
    payload = valid_intake_payload()
    payload["exhibits"] = [
        {
            "id": "evidence_trace_map",
            "title": "Reserved visual",
            "exhibit_type": "evidence_map",
            "purpose": "Demonstrate reserved generated visual ID rejection.",
            "referenced_fact_ids": ["fact_a"],
            "referenced_claim_ids": ["claim_a"],
            "data_requirements": [],
            "visual_encoding": "source to fact to claim",
            "limitations": [],
            "renderer_notes": "render as evidence map",
        }
    ]

    with pytest.raises(IntakeValidationError, match="reserved_visual_id"):
        research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))

def test_compile_spec_accepts_null_source_hash_without_citation_contradiction() -> None:
    payload = valid_intake_payload()
    payload["sources"][0]["content_hash"] = None  # type: ignore[index]

    pack = research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))
    export = citation_export_from_evidence(pack)
    spec = compile_report_spec(pack)

    assert export.records[0].content_sha256 is None
    assert spec.source_appendix.rows[0][1] == "Observed source title"


def test_research_audit_fields_render_into_reader_ir() -> None:
    payload = valid_intake_payload()
    payload["assumptions"] = [
        {
            "assumption": "assumption_a is explicit and bounded.",
            "reason": "Only one source payload was observed.",
            "risk_if_wrong": "The report could overstate the finding.",
        }
    ]
    payload["failed_sources"] = [
        {
            "id": "failed_a",
            "locator_or_description": "Unavailable primary source",
            "reason_failed": "The source could not be observed in this run.",
            "impact_on_report": "The report remains bounded to the observed secondary source.",
        }
    ]
    payload["excluded_sources"] = [
        {
            "id": "excluded_a",
            "locator_or_description": "Unverifiable source snippet",
            "reason_excluded": "No observable quote or payload was available.",
        }
    ]
    payload["contradictions"] = [
        {
            "id": "contradiction_a",
            "description": "No contradiction was resolved beyond the observed source boundary.",
            "fact_ids": ["fact_a"],
            "claim_ids": ["claim_a"],
            "possible_explanations": ["Only one source was available."],
            "recommended_report_treatment": "State the limitation instead of smoothing it away.",
        }
    ]
    payload["uncertainties"] = [
        {
            "id": "uncertainty_a",
            "description": "The finding may change with another observed source.",
            "affected_claim_ids": ["claim_a"],
            "affected_fact_ids": ["fact_a"],
            "severity": "medium",
            "recommended_language": "Based on the observed source only.",
        }
    ]
    payload["research_gaps"] = [
        {
            "id": "gap_a",
            "gap": "A primary source confirmation is still missing.",
            "why_it_matters": "It would raise confidence in the claim.",
            "suggested_source_type": "Primary source document",
            "priority": "high",
        }
    ]
    payload["validation_notes"] = {
        "self_audit_passed": False,
        "issues_found": ["validation_issue_a"],
        "repair_actions_taken": ["repair_action_a"],
        "validator_risks": ["validator_risk_a"],
    }

    pack = research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))
    report = compile_spec_to_report(compile_report_spec(pack))
    rendered_text = report.model_dump_json()

    for expected in [
        "Research audit",
        "Assumptions",
        "assumption_a is explicit and bounded",
        "Failed sources",
        "failed_a",
        "Excluded sources",
        "excluded_a",
        "Contradictions",
        "contradiction_a",
        "Uncertainties",
        "uncertainty_a",
        "Research gaps",
        "gap_a",
        "Validation notes",
        "validation_issue_a",
        "repair_action_a",
        "validator_risk_a",
    ]:
        assert expected in rendered_text


def test_research_intake_rejects_missing_semantic_completeness_fields() -> None:
    payload = valid_intake_payload()
    payload["report"]["what_to_watch"] = []  # type: ignore[index]
    with pytest.raises(ValueError, match="what_to_watch"):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    del payload["report"]["what_to_watch"]  # type: ignore[index]
    with pytest.raises(ValueError, match="what_to_watch"):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    payload["methodology"]["source_selection"] = "   "  # type: ignore[index]
    with pytest.raises(ValueError, match="methodology"):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    payload["report"]["sections"][0]["body"] = "too short"  # type: ignore[index]
    with pytest.raises(ValueError, match="body"):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    payload["report"]["sections"][0]["so_what"] = "   "  # type: ignore[index]
    with pytest.raises(ValueError, match="so_what"):
        ResearchIntake.model_validate(payload)

    payload = valid_intake_payload()
    payload["report"]["sections"][0]["limits"] = "   "  # type: ignore[index]
    with pytest.raises(ValueError, match="limits"):
        ResearchIntake.model_validate(payload)


def test_write_spec_artifacts_manifest_records_generated_mermaid_visuals(tmp_path: Path) -> None:
    payload = valid_intake_payload()
    payload["exhibits"] = [
        {
            "id": "source_to_claim_map",
            "title": "Source to claim map",
            "exhibit_type": "evidence_map",
            "purpose": "Show the observed source to fact to claim path.",
            "referenced_fact_ids": ["fact_a"],
            "referenced_claim_ids": ["claim_a"],
            "data_requirements": ["source_a", "fact_a", "claim_a"],
            "visual_encoding": "source to fact to claim",
            "limitations": ["Only one observed source is represented."],
            "renderer_notes": "Render as a Mermaid evidence map.",
        }
    ]
    payload["report"]["sections"][0]["suggested_exhibit_ids"] = ["source_to_claim_map"]  # type: ignore[index]

    pack = research_intake_to_evidence_pack(ResearchIntake.model_validate(payload))
    paths = write_spec_artifacts(pack, tmp_path, stem="manifest_probe")
    manifest = json.loads(paths["exhibits"].read_text(encoding="utf-8"))
    artifact_ids = {artifact["exhibit_id"] for artifact in manifest["artifacts"]}

    assert "source_to_claim_map" in artifact_ids
    assert "evidence_trace_map" in artifact_ids
    for artifact in manifest["artifacts"]:
        if artifact["exhibit_id"] in {"source_to_claim_map", "evidence_trace_map"}:
            assert artifact["route"] == "mermaid"
            assert artifact["svg_path"].endswith(".svg")
