"""Connector adapter contract tests.

Lattice: RF-P1 Source Sovereignty; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P7 Secrets Stay Handles.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from report_foundry.connectors import (
    ConnectorRequest,
    ConnectorResult,
    ConnectorSourceCandidate,
    FakeConnectorAdapter,
    RunMode,
    connector_result_gate_checks,
)
from report_foundry.factory import SourcePlan, SourcePlanItem


def source_plan() -> SourcePlan:
    return SourcePlan(
        topic="adapter boundary test",
        items=[
            SourcePlanItem(
                dimension="covered_dimension",
                purpose="prove selected candidates can become observations",
                acceptance_rule="one selected source must cover this dimension",
            ),
            SourcePlanItem(
                dimension="missing_dimension",
                purpose="prove gaps are explicit artifacts",
                acceptance_rule="one selected source must cover this dimension",
            ),
        ],
    )


def connector_request(*, run_mode: RunMode = RunMode.FIXTURE) -> ConnectorRequest:
    return ConnectorRequest(
        run_id="run-001",
        topic="adapter boundary test",
        audience="executive readers",
        source_plan=source_plan(),
        credential_handle="SEARCH_API_KEY",
        run_mode=run_mode,
    )


def test_connector_public_models_reject_raw_secret_fields() -> None:
    with pytest.raises(ValidationError):
        ConnectorRequest.model_validate(
            {
                "run_id": "run-001",
                "topic": "secret leak test",
                "source_plan": source_plan().model_dump(),
                "run_mode": "fixture",
                "credential": "sk-sho...ield",
            }
        )

    with pytest.raises(ValidationError):
        ConnectorResult.model_validate(
            {
                "connector_name": "bad-connector",
                "connector_version": "0.0.1",
                "candidates": [],
                "observations": [],
                "raw_token": "should-not-serialize",
            }
        )


def test_fake_connector_converts_selected_candidate_to_hashed_observation_and_gap_log() -> None:
    adapter = FakeConnectorAdapter(
        candidates=[
            ConnectorSourceCandidate(
                candidate_id="candidate-1",
                title="Primary source for covered dimension",
                url="https://example.test/source",
                source_tier="primary",
                publisher="Example Registry",
                snippet="The source explicitly covers the requested dimension.",
                decision="selected",
                reason="covers covered_dimension",
                dimensions=["covered_dimension"],
            )
        ]
    )

    result = adapter.collect(connector_request())

    assert result.artifact_status == "fixture"
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.source_id == "connector:candidate-1"
    assert observation.content_sha256 and len(observation.content_sha256) == 64
    assert observation.observed_at.endswith("Z")
    assert observation.source_tier == "primary"
    assert result.run_log is not None
    assert [gap.dimension for gap in result.run_log.evidence_gaps] == ["missing_dimension"]
    assert result.run_log.candidates[0].decision == "selected"


def test_product_mode_treats_unclassified_selected_candidate_as_error() -> None:
    result = ConnectorResult(
        connector_name="fake",
        connector_version="test",
        candidates=[
            ConnectorSourceCandidate(
                candidate_id="candidate-1",
                title="Unclassified source",
                url="https://example.test/source",
                decision="selected",
                source_tier="unclassified",
            )
        ],
        observations=[],
    )

    checks = connector_result_gate_checks(connector_request(run_mode=RunMode.PRODUCT), result)

    assert any(check.code == "unclassified_selected_source" and check.severity == "error" for check in checks)


def test_fixture_mode_allows_unclassified_selected_candidate_as_warning_and_non_product() -> None:
    adapter = FakeConnectorAdapter(
        candidates=[
            ConnectorSourceCandidate(
                candidate_id="candidate-1",
                title="Fixture source",
                url="https://example.test/source",
                decision="selected",
                source_tier="unclassified",
                dimensions=["covered_dimension"],
            )
        ]
    )

    result = adapter.collect(connector_request(run_mode=RunMode.FIXTURE))
    checks = connector_result_gate_checks(connector_request(run_mode=RunMode.FIXTURE), result)

    assert result.artifact_status == "fixture"
    assert any(check.code == "unclassified_selected_source" and check.severity == "warning" for check in checks)
    assert not any(check.severity == "error" for check in checks)
