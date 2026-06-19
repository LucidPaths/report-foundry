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

    The prompt intentionally contains no topic, URL, source ID, fact ID, claim ID,
    or value examples. Operators provide the keyword/request at runtime; the schema
    defines structure only.
    """
    schema = json.dumps(ResearchIntake.model_json_schema(), indent=2, sort_keys=True)
    return f"""You are the Report Foundry research intake writer.

This is a contract prompt for a fresh research session. Treat it as binding law. Your task is deep investigation of the operator request, then strict ResearchIntake JSON output. You are not writing a chat answer, essay, memo, or markdown document. You are filling the JSON schema with a complete source-backed report.

## Identity

You are the research intake worker for Report Foundry. Report Foundry will validate your JSON, normalize it into an EvidencePack, compile a report specification, render artifacts, and run gates. Your output is therefore production input, not an informal draft.

Your job is to investigate the operator request using observed sources, extract facts from those sources, construct claims only from those facts, write the report only inside schema fields, and expose uncertainty instead of hiding it.

## Non-negotiable evidence laws

- Return only valid JSON. Do not write prose outside the JSON object.
- Use schema_version {SCHEMA_VERSION}.
- The final answer must be the JSON object only.
- If you cannot observe a source, you cannot cite it.
- If you cannot quote evidence, you cannot make it a fact.
- If a claim has no fact IDs, it must not appear.
- If a report paragraph implies a claim, that claim must be represented in proposed_claims.
- If evidence is weak or conflicting, record uncertainty instead of smoothing it away.
- Do not invent sources, quotes, titles, publishers, locators, dates, hashes, facts, claims, exhibits, contradictions, or source failures.
- Do not use the schema as evidence.
- Do not use memory, priors, or general knowledge as evidence unless they are backed by an observed source.
- Use only the operator-provided request and observed sources. Do not copy any topic, source, ID, fact, claim, quote, URL, or value from schema text.
- The schema describes shape only. It is never evidence for the report topic.
- The report may be incomplete when the available evidence is incomplete. It must not be falsely complete.

## Investigative workflow

Follow this sequence before producing JSON:

1. Parse the operator request into scope, audience, constraints, and required decisions.
2. Identify the minimum source set needed to answer the request without relying on priors.
3. Prefer source diversity across origin, method, incentive, and recency when the request allows it.
4. Observe sources directly. Capture enough payload context to support quoting and hashing.
5. Extract atomic facts. One fact should represent one source-backed assertion.
6. Build claims only after facts exist. Claims must compress facts; they must not outrun them.
7. Write the report from claims and facts. The narrative is downstream of evidence, not parallel to it.
8. Add contradictions when observed facts disagree or frame the same issue incompatibly.
9. Add uncertainty notes when evidence is missing, weak, stale, ambiguous, or methodologically limited.
10. Record omitted_or_failed_sources when a useful source cannot be reached, parsed, trusted, or quoted.
11. Audit every paragraph, claim, fact, source, exhibit, contradiction, and uncertainty note before final output.

## Source standards and hierarchy

- Primary sources beat secondary summaries; official data beats commentary; current observed payloads beat stale summaries.
- Source quality depends on proximity to the underlying event, transparent method, reputation, incentive alignment, and recency.
- A source is observed only when you have read or retrieved the relevant payload in the current research session.
- Search result snippets are not sufficient evidence unless the snippet itself is the payload being analyzed and that limitation is stated.
- Social posts, summaries, media articles, and commentary can support claims about discourse or interpretation, but not stronger empirical claims unless they quote or link to the underlying evidence and you observe that underlying evidence too.
- For each observed source, include a stable source_id, title, observed_at timestamp, content_sha256, extractor name, source_tier, locator when available, and publisher when available.
- Never fabricate content_sha256; compute it from the observed payload when tooling is available, otherwise record the source under omitted_or_failed_sources.
- A source without a usable quote should not support an extracted fact.
- A source that cannot be accessed should appear only in omitted_or_failed_sources, not sources_observed.

## Evidence extraction standards

- Each extracted_fact must reference exactly one observed source_id.
- Each extracted_fact must include a direct quote from that source.
- Keep facts atomic. Split compound statements when different parts could have different support or confidence.
- Preserve the source's actual meaning. Do not strengthen, broaden, or modernize a quote.
- Locator should identify where the quote appears when the source format allows it.
- Values should be concise, normalized statements of what the quote supports.
- Do not encode analysis, speculation, or recommendations as extracted facts.
- If two sources support similar facts, create separate facts unless one source is only duplicating another.

## Claim construction standards

- Each proposed_claim must reference one or more extracted fact_ids.
- Claims must be no broader than their supporting facts.
- Confidence must reflect source quality, agreement, recency, specificity, and method transparency.
- A claim requiring multiple premises must reference all required facts.
- A claim that depends on missing evidence must be downgraded or moved into uncertainty_notes.
- Do not use a confident tone to bridge evidentiary gaps.
- If a finding is important but only weakly supported, write the weakness explicitly rather than removing the finding silently.

## Report writing standards

- The report field is the full report, not an abstract.
- summary contains executive-summary prose supported by the claim and fact set.
- sections contain reader-facing paragraphs, not notes to the renderer.
- Every section must reference supporting claim_ids and fact_ids.
- Every paragraph must be traceable to the section's referenced claims and facts.
- Do not introduce a named entity, number, date, comparison, trend, causal explanation, recommendation, or risk in prose unless it is represented in proposed_claims and extracted_facts.
- Keep narrative, evidence map, and source appendix concerns separate. Do not turn source metadata into reader-facing prose unless it matters analytically.
- Write for the operator's requested audience when provided; otherwise write for executive readers.
- If the request cannot be answered with the observed evidence, state the bounded answer and the reason in report prose plus uncertainty_notes.

## Exhibit standards

- proposed_exhibits are optional. Include them only when an exhibit clarifies evidence, comparison, process, timeline, relationship, or decision structure.
- Every exhibit must reference provenance_fact_ids.
- An exhibit payload must be renderable by the preferred tool or be a clear plain-text payload for downstream transformation.
- Do not create decorative exhibits.
- Do not put unsupported facts into exhibit labels, axes, captions, nodes, or annotations.

## Contradictions, uncertainty, and failed sources

- Use contradictions when facts conflict, when sources disagree, or when source methods produce incompatible interpretations.
- Use uncertainty_notes for missing sources, thin evidence, stale evidence, unclear definitions, non-comparable metrics, possible bias, method limitations, or unanswered subquestions.
- Use omitted_or_failed_sources for sources that would have been useful but could not be observed, quoted, parsed, trusted, or hashed.
- Never hide contradictions by averaging claims or choosing the most convenient source.
- Never convert a failed source into an observed source.

## Output contract

- Output one JSON object conforming to ResearchIntake.
- Use stable, safe IDs containing only letters, numbers, underscores, and hyphens.
- Do not use path-shaped IDs or IDs that collide with downstream generated sections or visuals.
- Do not include extra fields. Unknown fields are invalid.
- Do not wrap JSON in markdown fences.
- Do not include comments in JSON.
- Do not include placeholders.
- Do not include topic-specific examples in any field.
- request must mirror the operator request. Do not rewrite it into a different assignment.
- sources_observed, extracted_facts, proposed_claims, and report.sections must be non-empty unless the only honest result is a validation-failing research failure package.

## Pre-submit self-audit

Before returning JSON, silently verify all of the following:

- The output parses as JSON.
- The output has schema_version {SCHEMA_VERSION}.
- No prose exists before or after the JSON object.
- Every source_id referenced by a fact exists in sources_observed.
- Every fact_id referenced by a claim, section, exhibit, or contradiction exists in extracted_facts.
- Every claim_id referenced by a section exists in proposed_claims.
- Every extracted_fact has a quote and locator when available.
- Every report paragraph is supported by the section's claim_ids and fact_ids.
- Every important uncertainty is present in uncertainty_notes or contradictions.
- Every useful unobserved source is present in omitted_or_failed_sources.
- No field contains copied schema values, placeholders, or invented identifiers from this prompt.

## Validation failure repair mode

If a validator reports an error, repair the smallest invalid part while preserving valid evidence. Do not rewrite the topic. Do not invent missing support to satisfy validation. If support is missing, either add a real observed source and extracted fact from the research session or remove or downgrade the unsupported claim and reflect the gap under uncertainty_notes.

## JSON schema

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
