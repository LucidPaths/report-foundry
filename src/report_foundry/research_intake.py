"""Strict LLM research intake contract and EvidencePack normalization.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .evidence import (
    Confidence,
    DraftExhibit,
    EvidenceClaim,
    EvidenceFact,
    EvidencePack,
    ReportNarrativeSection,
    SourceObservation,
)

SCHEMA_VERSION = "research_intake.v1"
RESERVED_SECTION_IDS = {"executive_summary", "scope", "evidence_claims", "fact_table"}
RESERVED_VISUAL_IDS = {"evidence_trace_map"}


class IntakeValidationError(ValueError):
    """ResearchIntake violates Foundry evidence law."""


class StrictIntakeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_id(value: str) -> str:
    if not _ID_RE.fullmatch(value):
        raise ValueError("IDs may only contain letters, numbers, underscores, and hyphens")
    return value


class IntakeSourceObservation(SourceObservation):
    model_config = ConfigDict(extra="forbid")

    @field_validator("source_id")
    @classmethod
    def source_id_safe(cls, value: str) -> str:
        return _safe_id(value)


class IntakeEvidenceFact(EvidenceFact):
    model_config = ConfigDict(extra="forbid")

    @field_validator("fact_id")
    @classmethod
    def fact_id_safe(cls, value: str) -> str:
        return _safe_id(value)


class IntakeDraftExhibit(DraftExhibit):
    model_config = ConfigDict(extra="forbid")

    @field_validator("visual_id")
    @classmethod
    def visual_id_safe(cls, value: str) -> str:
        return _safe_id(value)


class ResearchRequest(StrictIntakeModel):
    keyword: str = Field(description="Operator-supplied keyword, topic, or report request. Do not replace with a canned topic.")
    audience: str | None = Field(default=None, description="Operator-supplied audience or null when not provided.")
    task: Literal["deep_research_report"] = "deep_research_report"
    constraints: list[str] = Field(default_factory=list, description="Operator-provided constraints only; do not invent hidden requirements.")

    @field_validator("keyword")
    @classmethod
    def keyword_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request keyword is required")
        return value


class IntakeClaim(StrictIntakeModel):
    claim_id: str

    @field_validator("claim_id")
    @classmethod
    def claim_id_safe(cls, value: str) -> str:
        return _safe_id(value)
    text: str
    fact_ids: list[str]
    confidence: Confidence = "unknown"

    @field_validator("fact_ids")
    @classmethod
    def fact_support_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("intake claims require backing fact IDs")
        return value


class IntakeReportSection(StrictIntakeModel):
    section_id: str

    @field_validator("section_id")
    @classmethod
    def section_id_safe(cls, value: str) -> str:
        return _safe_id(value)
    title: str
    paragraphs: list[str]
    claim_ids: list[str]
    fact_ids: list[str]
    kicker: str | None = None

    @field_validator("paragraphs")
    @classmethod
    def paragraphs_required(cls, value: list[str]) -> list[str]:
        if not value or not any(item.strip() for item in value):
            raise ValueError("report sections must contain full prose paragraphs")
        return value


class IntakeReport(StrictIntakeModel):
    title: str
    subtitle: str | None = None
    summary: list[str] = Field(default_factory=list, description="Executive-summary prose. This is part of the full report, not free text outside JSON.")
    sections: list[IntakeReportSection]

    @field_validator("title")
    @classmethod
    def title_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("report title is required")
        return value

    @field_validator("sections")
    @classmethod
    def sections_required(cls, value: list[IntakeReportSection]) -> list[IntakeReportSection]:
        if not value:
            raise ValueError("full report requires at least one structured section")
        return value


class IntakeContradiction(StrictIntakeModel):
    contradiction_id: str

    @field_validator("contradiction_id")
    @classmethod
    def contradiction_id_safe(cls, value: str) -> str:
        return _safe_id(value)
    description: str
    fact_ids: list[str]


class FailedSource(StrictIntakeModel):
    source_hint: str
    reason: str


class ResearchIntake(StrictIntakeModel):
    schema_version: Literal["research_intake.v1"] = SCHEMA_VERSION
    request: ResearchRequest
    sources_observed: list[IntakeSourceObservation]
    extracted_facts: list[IntakeEvidenceFact]
    proposed_claims: list[IntakeClaim]
    report: IntakeReport
    proposed_exhibits: list[IntakeDraftExhibit] = Field(default_factory=list)
    contradictions: list[IntakeContradiction] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    omitted_or_failed_sources: list[FailedSource] = Field(default_factory=list)

    @field_validator("sources_observed", "extracted_facts", "proposed_claims")
    @classmethod
    def required_lists(cls, value: list[object]) -> list[object]:
        if not value:
            raise ValueError("research intake requires observed sources, extracted facts, and proposed claims")
        return value


def build_research_intake_system_prompt() -> str:
    """Return the law prompt for LLM researchers.

    The prompt intentionally contains no topic, URL, source ID, fact ID, or claim ID
    examples. Operators provide the keyword/request at runtime; the schema defines
    output structure only.
    """
    schema = json.dumps(ResearchIntake.model_json_schema(), indent=2, sort_keys=True)
    return f"""You are the Report Foundry research intake writer.

Your task is deep research, but your output is not a free-form essay. You must write the full report inside the JSON fields of the ResearchIntake schema: observed sources, extracted facts, supported claims, structured report summary, structured report sections, proposed exhibits, contradictions, uncertainty notes, and omitted/failed sources.

Law:
- Return only valid JSON. Do not write prose outside the JSON object.
- Use schema_version {SCHEMA_VERSION}.
- Use only the operator-provided keyword/request and discovered sources. Do not copy any topic, URL, ID, fact, claim, or source from the schema text.
- Every source_observed entry must describe a concrete observed source payload with observed_at, content_sha256, extractor, title, and locator when available.
- Every extracted_fact must reference exactly one observed source_id and include a direct quote.
- Every proposed_claim must reference one or more extracted fact_ids.
- Every report section must contain the actual report prose and must reference supporting claim_ids and fact_ids.
- If evidence conflicts or is weak, record it under contradictions or uncertainty_notes instead of hiding it.
- If a useful source could not be accessed, record it under omitted_or_failed_sources instead of fabricating it.

json_schema:
{schema}
"""


def research_intake_to_evidence_pack(intake: ResearchIntake, *, author: str = "Research Intake LLM") -> EvidencePack:
    _validate_research_intake_links(intake)
    sections = [
        ReportNarrativeSection(
            section_id=section.section_id,
            title=section.title,
            kicker=section.kicker,
            paragraphs=section.paragraphs,
            fact_ids=section.fact_ids,
        )
        for section in intake.report.sections
    ]
    if intake.report.summary:
        summary_fact_ids = _ordered_unique(fact_id for claim in intake.proposed_claims for fact_id in claim.fact_ids)
        sections.insert(
            0,
            ReportNarrativeSection(
                section_id="executive_summary",
                title="Executive summary",
                paragraphs=intake.report.summary,
                fact_ids=summary_fact_ids,
            ),
        )
    return EvidencePack(
        title=intake.report.title,
        subtitle=intake.report.subtitle,
        author=author,
        scope={
            "keyword": intake.request.keyword,
            "audience": intake.request.audience,
            "task": intake.request.task,
            "constraints": intake.request.constraints,
            "schema_version": intake.schema_version,
            "uncertainty_notes": intake.uncertainty_notes,
            "omitted_or_failed_sources": [item.model_dump() for item in intake.omitted_or_failed_sources],
            "contradictions": [item.model_dump() for item in intake.contradictions],
        },
        sources=intake.sources_observed,
        facts=intake.extracted_facts,
        claims=[EvidenceClaim(text=claim.text, fact_ids=claim.fact_ids, confidence=claim.confidence) for claim in intake.proposed_claims],
        report_sections=sections,
        exhibits=intake.proposed_exhibits,
        tags=["research-intake", intake.schema_version],
    )


def _validate_research_intake_links(intake: ResearchIntake) -> None:
    source_ids = {source.source_id for source in intake.sources_observed}
    fact_ids = {fact.fact_id for fact in intake.extracted_facts}
    claim_ids = {claim.claim_id for claim in intake.proposed_claims}
    section_ids = {section.section_id for section in intake.report.sections}
    exhibit_ids = {exhibit.visual_id for exhibit in intake.proposed_exhibits}
    contradiction_ids = {contradiction.contradiction_id for contradiction in intake.contradictions}
    if len(source_ids) != len(intake.sources_observed):
        raise IntakeValidationError("duplicate_source_id")
    if len(fact_ids) != len(intake.extracted_facts):
        raise IntakeValidationError("duplicate_fact_id")
    if len(claim_ids) != len(intake.proposed_claims):
        raise IntakeValidationError("duplicate_claim_id")
    if len(section_ids) != len(intake.report.sections):
        raise IntakeValidationError("duplicate_section_id")
    if len(exhibit_ids) != len(intake.proposed_exhibits):
        raise IntakeValidationError("duplicate_exhibit_id")
    if len(contradiction_ids) != len(intake.contradictions):
        raise IntakeValidationError("duplicate_contradiction_id")

    claim_fact_ids = {claim.claim_id: set(claim.fact_ids) for claim in intake.proposed_claims}

    for fact in intake.extracted_facts:
        if fact.source_id not in source_ids:
            raise IntakeValidationError(f"fact_references_unknown_source: {fact.fact_id} -> {fact.source_id}")
    for claim in intake.proposed_claims:
        for fact_id in claim.fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"claim_references_unknown_fact: {claim.claim_id} -> {fact_id}")
    for section in intake.report.sections:
        if section.section_id in RESERVED_SECTION_IDS:
            raise IntakeValidationError(f"reserved_section_id: {section.section_id}")
        if not section.claim_ids:
            raise IntakeValidationError(f"section_requires_claim_support: {section.section_id}")
        if not section.fact_ids:
            raise IntakeValidationError(f"section_requires_fact_support: {section.section_id}")
        for claim_id in section.claim_ids:
            if claim_id not in claim_ids:
                raise IntakeValidationError(f"section_references_unknown_claim: {section.section_id} -> {claim_id}")
        referenced_claim_facts: set[str] = set()
        for claim_id in section.claim_ids:
            referenced_claim_facts.update(claim_fact_ids.get(claim_id, set()))
        for fact_id in section.fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"section_references_unknown_fact: {section.section_id} -> {fact_id}")
            if fact_id not in referenced_claim_facts:
                raise IntakeValidationError(f"section_fact_not_covered_by_claim: {section.section_id} -> {fact_id}")
    for exhibit in intake.proposed_exhibits:
        if exhibit.visual_id in RESERVED_VISUAL_IDS:
            raise IntakeValidationError(f"reserved_visual_id: {exhibit.visual_id}")
        for fact_id in exhibit.provenance_fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"exhibit_references_unknown_fact: {exhibit.visual_id} -> {fact_id}")
    for contradiction in intake.contradictions:
        for fact_id in contradiction.fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"contradiction_references_unknown_fact: {contradiction.contradiction_id} -> {fact_id}")


def _ordered_unique(values: object) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:  # type: ignore[union-attr]
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
