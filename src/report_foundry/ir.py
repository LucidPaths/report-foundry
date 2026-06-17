"""Renderer-neutral semantic report IR.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, HttpUrl


class Citation(BaseModel):
    source_id: str
    url: str | None = None
    title: str | None = None
    quote: str | None = None
    accessed_at: str | None = None
    locator: str | None = None


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Claim(BaseModel):
    type: Literal["claim"] = "claim"
    text: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    verification_status: Literal["supported", "partial", "unsupported", "unchecked"] = "unchecked"


class MetricCard(BaseModel):
    type: Literal["metric"] = "metric"
    label: str
    value: str
    note: str | None = None


class Figure(BaseModel):
    type: Literal["figure"] = "figure"
    title: str
    path: str | None = None
    caption: str | None = None
    alt_text: str | None = None


class TableBlock(BaseModel):
    type: Literal["table"] = "table"
    caption: str | None = None
    headers: list[str]
    rows: list[list[str]]


Block = Annotated[
    Union[TextBlock, Claim, MetricCard, Figure, TableBlock], Field(discriminator="type")
]


class Section(BaseModel):
    title: str
    kicker: str | None = None
    blocks: list[Block] = Field(default_factory=list)


class Report(BaseModel):
    title: str
    subtitle: str | None = None
    report_date: str = Field(default_factory=lambda: date.today().isoformat())
    author: str = "Report Foundry"
    sections: list[Section] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    def claims(self) -> list[Claim]:
        return [block for section in self.sections for block in section.blocks if isinstance(block, Claim)]

    def sources(self) -> list[Citation]:
        seen: set[tuple[str, str | None]] = set()
        out: list[Citation] = []
        for claim in self.claims():
            for citation in claim.citations:
                key = (citation.source_id, citation.url)
                if key not in seen:
                    seen.add(key)
                    out.append(citation)
        return out
