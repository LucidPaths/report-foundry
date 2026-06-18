"""Connector adapter boundary for external research/search tools.

Lattice: RF-P1 Source Sovereignty; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P7 Secrets Stay Handles.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .evidence import SourceObservation, SourceTier
from .factory import Department, FactoryGateCheck, RunMode, SourcePlan
from .research import ResearchEvidenceGap, ResearchRunLog, ResearchSourceCandidate


class ConnectorKind(StrEnum):
    GPT_RESEARCHER = "gpt_researcher"
    STORM = "storm"
    PAPERQA = "paperqa"
    MCP = "mcp"
    LOCAL_FIXTURE = "local_fixture"


ArtifactStatus = Literal["fixture", "product", "experiment"]
CandidateDecision = Literal["selected", "rejected", "pending"]


class ConnectorRequest(BaseModel):
    """Connector execution contract.

    Credentials are handles only. Raw provider secret fields are rejected by
    `extra="forbid"` and by the field name policy below.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    topic: str
    source_plan: SourcePlan
    audience: str | None = None
    credential_handle: str | None = None
    max_sources: int = 20
    run_mode: RunMode = RunMode.FIXTURE

    @field_validator("run_id", "topic")
    @classmethod
    def non_empty_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("connector request text fields must not be empty")
        return value

    @field_validator("credential_handle")
    @classmethod
    def credential_handle_only(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("credential_handle must not be blank")
        if _looks_like_secret_value(value):
            raise ValueError("credential_handle must be an env var/key handle, not a raw secret")
        return value


class ConnectorSourceCandidate(BaseModel):
    """A possible source from an adapter before Foundry admits it as evidence."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    title: str
    url: str | None = None
    raw_locator: str | None = None
    source_tier: SourceTier = "unclassified"
    publisher: str | None = None
    published_at: str | None = None
    snippet: str | None = None
    decision: CandidateDecision = "pending"
    reason: str | None = None
    dimensions: list[str] = Field(default_factory=list)

    @field_validator("candidate_id")
    @classmethod
    def candidate_id_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidate_id is required")
        return value


class ConnectorResult(BaseModel):
    """Public handoff from connector adapter into Foundry law."""

    model_config = ConfigDict(extra="forbid")

    connector_name: str
    connector_version: str
    candidates: list[ConnectorSourceCandidate]
    observations: list[SourceObservation]
    raw_artifact_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifact_status: ArtifactStatus = "fixture"
    run_log: ResearchRunLog | None = None


class ConnectorAdapter(Protocol):
    name: str

    def collect(self, request: ConnectorRequest) -> ConnectorResult:
        ...


class FakeConnectorAdapter:
    """Deterministic connector for tests and local contract development."""

    name = "fake_connector"
    version = "0.1.0"

    def __init__(self, candidates: list[ConnectorSourceCandidate]) -> None:
        self.candidates = candidates

    def collect(self, request: ConnectorRequest) -> ConnectorResult:
        selected = [candidate for candidate in self.candidates if candidate.decision == "selected"]
        observations = [source_observation_from_candidate(candidate, connector_name=self.name) for candidate in selected]
        run_log = research_run_log_from_connector_result(
            request,
            candidates=self.candidates,
            observations=observations,
        )
        warnings = [check.message for check in connector_result_gate_checks(request, _partial_result(request, self.candidates, observations, run_log)) if check.severity == "warning"]
        return ConnectorResult(
            connector_name=self.name,
            connector_version=self.version,
            candidates=self.candidates,
            observations=observations,
            warnings=warnings,
            artifact_status=_artifact_status(request.run_mode),
            run_log=run_log,
        )


def source_observation_from_candidate(candidate: ConnectorSourceCandidate, *, connector_name: str) -> SourceObservation:
    """Normalize one selected connector candidate into a hashed source observation."""

    if candidate.decision != "selected":
        raise ValueError("only selected candidates can become source observations")
    locator = candidate.url or candidate.raw_locator
    payload = {
        "candidate_id": candidate.candidate_id,
        "title": candidate.title,
        "url": candidate.url,
        "raw_locator": candidate.raw_locator,
        "publisher": candidate.publisher,
        "published_at": candidate.published_at,
        "snippet": candidate.snippet,
        "dimensions": candidate.dimensions,
    }
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return SourceObservation(
        source_id=f"connector:{candidate.candidate_id}",
        title=candidate.title,
        url=candidate.url,
        observed_at=observed_at,
        content_sha256=hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
        extractor=f"{connector_name}:candidate_v1",
        locator=locator,
        source_tier=candidate.source_tier,
        publisher=candidate.publisher,
        published_at=candidate.published_at,
        citation_metadata={"candidate_id": candidate.candidate_id, "raw_locator": candidate.raw_locator or ""},
    )


def research_run_log_from_connector_result(
    request: ConnectorRequest,
    *,
    candidates: list[ConnectorSourceCandidate],
    observations: list[SourceObservation],
) -> ResearchRunLog:
    selected_dimensions = {
        dimension
        for candidate in candidates
        if candidate.decision == "selected"
        for dimension in candidate.dimensions
    }
    evidence_gaps = [
        ResearchEvidenceGap(
            dimension=item.dimension,
            reason="No selected connector candidate covered the required source-plan dimension.",
        )
        for item in request.source_plan.items
        if item.dimension not in selected_dimensions
    ]
    return ResearchRunLog(
        run_dir=request.run_id,
        source_dir="connector",
        source_plan_dimensions=[item.dimension for item in request.source_plan.items],
        candidates=[
            ResearchSourceCandidate(
                source_id=f"connector:{candidate.candidate_id}",
                path=candidate.url or candidate.raw_locator or candidate.candidate_id,
                decision="selected" if candidate.decision == "selected" else "rejected",
                reason=candidate.reason or candidate.decision,
            )
            for candidate in candidates
            if candidate.decision != "pending"
        ],
        evidence_gaps=evidence_gaps,
    )


def connector_result_gate_checks(request: ConnectorRequest, result: ConnectorResult) -> list[FactoryGateCheck]:
    checks: list[FactoryGateCheck] = []
    selected = [candidate for candidate in result.candidates if candidate.decision == "selected"]
    selected_ids = {candidate.candidate_id for candidate in selected}
    observations_by_candidate = {
        source.citation_metadata.get("candidate_id"): source
        for source in result.observations
    }

    for candidate in selected:
        if not candidate.title.strip():
            checks.append(_check("selected_source_missing_title", "Selected connector source is missing a title.", request.run_mode))
        if not (candidate.url or candidate.raw_locator):
            checks.append(_check("selected_source_missing_locator", "Selected connector source is missing URL/path/raw locator.", request.run_mode))
        if candidate.source_tier == "unclassified":
            checks.append(_check("unclassified_selected_source", "Selected connector source has unclassified source tier.", request.run_mode))
        if _contains_credential_shaped_text(candidate.snippet or "") or _contains_credential_shaped_text(candidate.raw_locator or ""):
            checks.append(_check("credential_shaped_connector_payload", "Connector candidate contains credential-looking text.", RunMode.PRODUCT))

        observation = observations_by_candidate.get(candidate.candidate_id)
        if observation is None:
            checks.append(_check("selected_source_missing_observation", f"Selected candidate {candidate.candidate_id} has no SourceObservation.", request.run_mode))
        elif not observation.content_sha256:
            checks.append(_check("missing_source_hash", f"Observation for selected candidate {candidate.candidate_id} has no hash.", request.run_mode))

    covered_dimensions = {dimension for candidate in selected for dimension in candidate.dimensions}
    for item in request.source_plan.items:
        if item.dimension not in covered_dimensions:
            checks.append(
                FactoryGateCheck(
                    code="missing_required_dimension",
                    message=f"Connector selected no source for required dimension: {item.dimension}.",
                    department=Department.RESEARCH,
                    severity="warning" if request.run_mode == RunMode.FIXTURE else "error",
                )
            )

    for observation in result.observations:
        candidate_id = observation.citation_metadata.get("candidate_id")
        if candidate_id not in selected_ids:
            checks.append(_check("orphan_connector_observation", f"Observation {observation.source_id} does not map to a selected connector candidate.", request.run_mode))
        if observation.extractor.endswith("generated_prose") and not (observation.url or observation.locator):
            checks.append(_check("generated_prose_without_locator", "Generated prose cannot be admitted as a source without a real locator.", request.run_mode))

    for path in result.raw_artifact_paths:
        if _contains_credential_shaped_text(path):
            checks.append(_check("credential_shaped_artifact_path", "Connector artifact path contains credential-looking text.", RunMode.PRODUCT))

    return checks


def _partial_result(
    request: ConnectorRequest,
    candidates: list[ConnectorSourceCandidate],
    observations: list[SourceObservation],
    run_log: ResearchRunLog,
) -> ConnectorResult:
    return ConnectorResult(
        connector_name="fake_connector",
        connector_version="0.1.0",
        candidates=candidates,
        observations=observations,
        artifact_status=_artifact_status(request.run_mode),
        run_log=run_log,
    )


def _artifact_status(run_mode: RunMode) -> ArtifactStatus:
    if run_mode == RunMode.PRODUCT:
        return "product"
    if run_mode == RunMode.EXPERIMENT:
        return "experiment"
    return "fixture"


def _check(code: str, message: str, run_mode: RunMode) -> FactoryGateCheck:
    return FactoryGateCheck(
        code=code,
        message=message,
        department=Department.RESEARCH,
        severity="warning" if run_mode == RunMode.FIXTURE else "error",
    )


def _looks_like_secret_value(value: str) -> bool:
    return bool(re.search(r"(?i)(^sk-[a-z0-9_-]{8,}|ghp_[a-z0-9_]{8,}|bearer\s+[a-z0-9._-]{12,})", value.strip()))


def _contains_credential_shaped_text(value: str) -> bool:
    return bool(re.search(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]+|sk-[a-z0-9_-]{8,}|ghp_[a-z0-9_]{8,}", value))
