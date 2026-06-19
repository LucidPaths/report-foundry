"""Reader-facing citation contracts and export seams.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .evidence import EvidencePack, SourceTier
from .qa import QualityCheck


class CitationRecord(BaseModel):
    """Reader-facing citation metadata linked back to audit provenance."""

    citation_id: str
    source_id: str
    title: str
    url: str | None = None
    author: list[str] = Field(default_factory=list)
    publisher: str | None = None
    issued: str | None = None
    accessed: str
    locator: str | None = None
    source_tier: SourceTier = "unclassified"
    content_sha256: str | None = None

    @field_validator("citation_id", "source_id", "title", "accessed")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("citation required text fields must not be empty")
        return value

    @field_validator("content_sha256")
    @classmethod
    def hash_valid_or_null(cls, value: str | None) -> str | None:
        if value is None:
            return value
        lowered = value.lower()
        if len(lowered) != 64 or any(ch not in "0123456789abcdef" for ch in lowered):
            raise ValueError("citation content_sha256 must be a 64-character hex sha256 digest or null")
        return lowered


class CitationExport(BaseModel):
    records: list[CitationRecord]
    csl_json: list[dict[str, Any]]
    bibtex: str | None = None


def citation_records_from_evidence(evidence: EvidencePack) -> list[CitationRecord]:
    locators_by_source: dict[str, list[str]] = {}
    for fact in evidence.facts:
        if fact.locator:
            locators_by_source.setdefault(fact.source_id, []).append(fact.locator)

    records: list[CitationRecord] = []
    for source in evidence.sources:
        metadata = source.citation_metadata
        authors = _authors(metadata.get("author") or metadata.get("authors"))
        locator_parts = [source.locator or "", *locators_by_source.get(source.source_id, [])]
        locator = "; ".join(dict.fromkeys(part for part in locator_parts if part)) or None
        records.append(
            CitationRecord(
                citation_id=_citation_id(source.source_id),
                source_id=source.source_id,
                title=source.title,
                url=source.url,
                author=authors,
                publisher=source.publisher,
                issued=source.published_at,
                accessed=source.observed_at,
                locator=locator,
                source_tier=source.source_tier,
                content_sha256=source.content_sha256,
            )
        )
    return records


def citation_export_from_evidence(evidence: EvidencePack) -> CitationExport:
    records = citation_records_from_evidence(evidence)
    return CitationExport(records=records, csl_json=export_csl_json(records), bibtex=export_bibtex(records))


def export_csl_json(records: list[CitationRecord]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in records:
        item: dict[str, Any] = {
            "id": record.citation_id,
            "type": "webpage",
            "title": record.title,
            "accessed": {"literal": record.accessed},
        }
        if record.url:
            item["URL"] = record.url
        if record.author:
            item["author"] = [{"literal": author} for author in record.author]
        if record.publisher:
            item["publisher"] = record.publisher
        if record.issued:
            item["issued"] = {"literal": record.issued}
        out.append(item)
    return out


def export_bibtex(records: list[CitationRecord]) -> str:
    entries: list[str] = []
    for record in records:
        fields = [
            ("title", record.title),
            ("url", record.url),
            ("urldate", record.accessed),
            ("author", " and ".join(record.author) if record.author else None),
            ("publisher", record.publisher),
            ("date", record.issued),
            ("note", record.locator),
        ]
        lines = [f"@online{{{record.citation_id},"]
        for key, value in fields:
            if value:
                lines.append(f"  {key} = {{{_bibtex_escape(value)}}},")
        if lines[-1].endswith(","):
            lines[-1] = lines[-1][:-1]
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) + ("\n" if entries else "")


def render_source_appendix_markdown(records: list[CitationRecord]) -> str:
    lines = ["# Source Appendix", ""]
    for record in records:
        locator = f" — {record.locator}" if record.locator else ""
        url_or_path = record.url or record.locator or record.source_id
        publisher = f", {record.publisher}" if record.publisher else ""
        lines.append(f"- **{record.title}**{publisher}: {url_or_path} (accessed {record.accessed}{locator})")
    return "\n".join(lines) + "\n"


def source_appendix_rows(records: list[CitationRecord]) -> list[list[str]]:
    return [[record.citation_id, record.title, record.url or record.locator or "", record.accessed, record.locator or ""] for record in records]


def citation_gate_checks(evidence: EvidencePack, *, product_mode: bool = False) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    records = citation_records_from_evidence(evidence)
    citation_ids = [record.citation_id for record in records]
    if len(citation_ids) != len(set(citation_ids)):
        checks.append(QualityCheck(code="duplicate_citation_id", message="Citation IDs must be unique."))

    records_by_source = {record.source_id: record for record in records}
    facts_by_id = {fact.fact_id: fact for fact in evidence.facts}
    severity = "error" if product_mode else "warning"

    for index, record in enumerate(records):
        location = f"citations[{index}]"
        if not record.title.strip():
            checks.append(QualityCheck(code="citation_missing_title", message="Citation record missing reader title.", severity=severity, location=location))
        if not (record.url or record.locator):
            checks.append(QualityCheck(code="citation_missing_reader_locator", message="Citation record missing URL/path/locator for reader use.", severity=severity, location=location))
        if product_mode and not record.accessed.strip():
            checks.append(QualityCheck(code="citation_missing_accessed", message="Product citation missing accessed timestamp.", severity="error", location=location))

    for claim_index, claim in enumerate(evidence.claims):
        for fact_id in claim.fact_ids:
            fact = facts_by_id.get(fact_id)
            if fact is None:
                continue
            if fact.source_id not in records_by_source:
                checks.append(
                    QualityCheck(
                        code="claim_source_missing_citation",
                        message=f"Claim references fact whose source has no citation record: {fact.source_id}.",
                        severity="error" if product_mode else "warning",
                        location=f"claims[{claim_index}].fact_ids",
                    )
                )
    return checks


def _citation_id(source_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", source_id).strip("_").lower() or "source"
    return f"cite_{cleaned}"


def _authors(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in re.split(r";|\|", raw) if part.strip()]


def _bibtex_escape(value: str) -> str:
    return value.replace("{", "\\{").replace("}", "\\}")
