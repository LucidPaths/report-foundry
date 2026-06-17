"""Evidence contracts for observed sources, extracted facts, and supported claims.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .ir import Citation, Report
from .qa import QualityCheck, QualityResult

Confidence = Literal["high", "medium", "low", "unknown"]
ProfessionalSectionRole = Literal[
    "market_context",
    "thesis",
    "trend_analysis",
    "operating_analysis",
    "financial_analysis",
    "scenario_analysis",
    "risk_analysis",
    "implications",
    "recommendations",
    "methodology",
]


class SourceObservation(BaseModel):
    """A concrete source payload observed by the workflow."""

    source_id: str
    title: str
    url: str | None = None
    observed_at: str
    content_sha256: str
    extractor: str
    locator: str | None = None

    @field_validator("content_sha256")
    @classmethod
    def sha256_must_look_real(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value.lower()):
            raise ValueError("content_sha256 must be a 64-character hex sha256 digest")
        return value.lower()


class EvidenceFact(BaseModel):
    """A normalized fact extracted from exactly one observed source."""

    fact_id: str
    subject: str
    predicate: str
    value: str
    source_id: str
    quote: str
    locator: str | None = None

    @field_validator("quote")
    @classmethod
    def quote_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fact quote is required")
        return value


class EvidenceClaim(BaseModel):
    """A claim allowed into a report only when all backing facts resolve."""

    text: str
    fact_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = "unknown"


class ReportNarrativeSection(BaseModel):
    """Plain-language report prose produced upstream and rendered by the foundry."""

    section_id: str
    title: str
    kicker: str | None = None
    paragraphs: list[str]
    fact_ids: list[str] = Field(default_factory=list)

    @field_validator("paragraphs")
    @classmethod
    def paragraphs_required(cls, value: list[str]) -> list[str]:
        if not value or not any(item.strip() for item in value):
            raise ValueError("report narrative sections must contain prose paragraphs")
        return value


class ProfessionalKeyTakeaway(BaseModel):
    """Executive takeaway: conclusion first, with explicit evidence support."""

    takeaway: str
    fact_ids: list[str]
    implication: str | None = None


class ProfessionalReportSection(BaseModel):
    """Professional report section contract observed in consulting/investor reports.

    Headline is a conclusion, lede orients the reader, evidence supports the
    argument, so_what explains decision relevance, limitations bound certainty.
    """

    section_id: str
    role: ProfessionalSectionRole
    headline: str
    lede: str
    paragraphs: list[str]
    fact_ids: list[str]
    so_what: str
    limitations: list[str] = Field(default_factory=list)
    exhibit_refs: list[str] = Field(default_factory=list)

    @field_validator("paragraphs")
    @classmethod
    def paragraphs_required(cls, value: list[str]) -> list[str]:
        if not value or not any(item.strip() for item in value):
            raise ValueError("professional sections must contain report prose")
        return value


class ProfessionalReportContent(BaseModel):
    """Reader-facing report schema derived from public professional reports."""

    one_sentence_thesis: str
    executive_summary: list[str]
    key_takeaways: list[ProfessionalKeyTakeaway]
    sections: list[ProfessionalReportSection]
    what_to_watch: list[str] = Field(default_factory=list)
    methodology: str | None = None

    @field_validator("executive_summary", "key_takeaways", "sections")
    @classmethod
    def required_lists(cls, value: list[object]) -> list[object]:
        if not value:
            raise ValueError("professional report content requires summary, takeaways, and sections")
        return value


class DraftExhibit(BaseModel):
    """Visual intent selected by the LLM/report writer and rendered by adapters."""

    visual_id: str
    visual_type: Literal["evidence_map", "chart", "matrix", "timeline", "diagram"] = "diagram"
    title: str | None = None
    purpose: str
    preferred_tool: Literal["mermaid", "vega_lite", "typst", "html_css"] = "mermaid"
    provenance_fact_ids: list[str]
    plain_text_payload: str

    @field_validator("provenance_fact_ids")
    @classmethod
    def exhibit_provenance_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("draft exhibits require source-backed fact IDs")
        return value


class EvidencePack(BaseModel):
    title: str
    subtitle: str | None = None
    report_date: str = Field(default_factory=lambda: date.today().isoformat())
    author: str = "Report Foundry"
    scope: dict[str, object] = Field(default_factory=dict)
    sources: list[SourceObservation] = Field(default_factory=list)
    facts: list[EvidenceFact] = Field(default_factory=list)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    report_sections: list[ReportNarrativeSection] = Field(default_factory=list)
    professional_report: ProfessionalReportContent | None = None
    exhibits: list[DraftExhibit] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


def validate_evidence_pack(pack: EvidencePack) -> QualityResult:
    checks: list[QualityCheck] = []
    source_ids = {source.source_id for source in pack.sources}
    fact_ids = {fact.fact_id for fact in pack.facts}

    if not pack.title.strip():
        checks.append(QualityCheck(code="missing_title", message="Evidence pack title is required."))

    if len(source_ids) != len(pack.sources):
        checks.append(QualityCheck(code="duplicate_source_id", message="Source IDs must be unique."))
    if len(fact_ids) != len(pack.facts):
        checks.append(QualityCheck(code="duplicate_fact_id", message="Fact IDs must be unique."))

    for index, fact in enumerate(pack.facts):
        if fact.source_id not in source_ids:
            checks.append(
                QualityCheck(
                    code="missing_source",
                    message=f"Fact references unknown source {fact.source_id}.",
                    location=f"facts[{index}]",
                )
            )

    for claim_index, claim in enumerate(pack.claims):
        if not claim.fact_ids:
            checks.append(
                QualityCheck(
                    code="unsupported_claim",
                    message="Claim must reference at least one fact.",
                    location=f"claims[{claim_index}]",
                )
            )
        for fact_id in claim.fact_ids:
            if fact_id not in fact_ids:
                checks.append(
                    QualityCheck(
                        code="missing_fact",
                        message=f"Claim references unknown fact {fact_id}.",
                        location=f"claims[{claim_index}].fact_ids",
                    )
                )

    for section_index, section in enumerate(pack.report_sections):
        for fact_id in section.fact_ids:
            if fact_id not in fact_ids:
                checks.append(
                    QualityCheck(
                        code="missing_fact",
                        message=f"Narrative section references unknown fact {fact_id}.",
                        location=f"report_sections[{section_index}].fact_ids",
                    )
                )

    if pack.professional_report:
        for takeaway_index, takeaway in enumerate(pack.professional_report.key_takeaways):
            for fact_id in takeaway.fact_ids:
                if fact_id not in fact_ids:
                    checks.append(
                        QualityCheck(
                            code="missing_fact",
                            message=f"Professional takeaway references unknown fact {fact_id}.",
                            location=f"professional_report.key_takeaways[{takeaway_index}].fact_ids",
                        )
                    )
        for section_index, section in enumerate(pack.professional_report.sections):
            for fact_id in section.fact_ids:
                if fact_id not in fact_ids:
                    checks.append(
                        QualityCheck(
                            code="missing_fact",
                            message=f"Professional section references unknown fact {fact_id}.",
                            location=f"professional_report.sections[{section_index}].fact_ids",
                        )
                    )

    for exhibit_index, exhibit in enumerate(pack.exhibits):
        for fact_id in exhibit.provenance_fact_ids:
            if fact_id not in fact_ids:
                checks.append(
                    QualityCheck(
                        code="missing_fact",
                        message=f"Draft exhibit references unknown fact {fact_id}.",
                        location=f"exhibits[{exhibit_index}].provenance_fact_ids",
                    )
                )

    return QualityResult(ok=not any(check.severity == "error" for check in checks), checks=checks)


def build_report_from_evidence(pack: EvidencePack) -> Report:
    result = validate_evidence_pack(pack)
    if not result.ok:
        codes = ", ".join(check.code for check in result.checks if check.severity == "error")
        raise ValueError(f"Invalid evidence pack: {codes}")

    sources_by_id = {source.source_id: source for source in pack.sources}
    facts_by_id = {fact.fact_id: fact for fact in pack.facts}
    claim_blocks: list[dict[str, object]] = []

    for claim in pack.claims:
        citations: list[Citation] = []
        for fact_id in claim.fact_ids:
            fact = facts_by_id[fact_id]
            source = sources_by_id[fact.source_id]
            citations.append(
                Citation(
                    source_id=source.source_id,
                    url=source.url,
                    title=source.title,
                    quote=fact.quote,
                    accessed_at=source.observed_at,
                    locator=fact.locator or source.locator or fact.fact_id,
                )
            )
        claim_blocks.append(
            {
                "type": "claim",
                "text": claim.text,
                "confidence": claim.confidence,
                "verification_status": "supported",
                "citations": [citation.model_dump() for citation in citations],
            }
        )

    scope_rows = [[str(key), _stringify_scope_value(value)] for key, value in pack.scope.items()]
    sections = [
        {
            "title": "Scope",
            "kicker": "Report boundary declared before claims are generated.",
            "blocks": [{"type": "table", "headers": ["Field", "Value"], "rows": scope_rows}] if scope_rows else [],
        },
        {
            "title": "Evidence-backed claims",
            "kicker": "Every claim below resolves to one or more observed source facts.",
            "blocks": claim_blocks,
        },
        {
            "title": "Source observations",
            "kicker": "Hashes identify the concrete payloads observed by the workflow.",
            "blocks": [
                {
                    "type": "table",
                    "headers": ["Source", "Observed", "SHA-256", "Extractor"],
                    "rows": [
                        [source.source_id, source.observed_at, source.content_sha256[:16] + "…", source.extractor]
                        for source in pack.sources
                    ],
                }
            ],
        },
    ]

    return Report(
        title=pack.title,
        subtitle=pack.subtitle,
        report_date=pack.report_date,
        author=pack.author,
        tags=pack.tags,
        sections=sections,
    )


def _stringify_scope_value(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {item}" for key, item in value.items())
    return str(value)
