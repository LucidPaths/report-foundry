"""Formal exhibit specifications with provenance-bearing gates.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .evidence import DraftExhibit, EvidenceFact, EvidencePack
from .qa import QualityCheck, QualityResult


class ExhibitKind(StrEnum):
    CHART = "chart"
    TABLE = "table"
    DIAGRAM = "diagram"
    TIMELINE = "timeline"
    MATRIX = "matrix"
    IMAGE = "image"


class ExhibitDataPoint(BaseModel):
    label: str
    value: int | float | str
    unit: str | None = None
    fact_id: str
    transform_note: str | None = None


class ExhibitSpec(BaseModel):
    exhibit_id: str
    title: str
    kind: ExhibitKind
    insight: str
    fact_ids: list[str] = Field(default_factory=list)
    data: list[ExhibitDataPoint] = Field(default_factory=list)
    renderer_route: Literal["vega_lite", "mermaid", "table", "kaleido", "image"]
    alt_text: str
    plain_text_payload: str | None = None
    transform_provenance: list[str] = Field(default_factory=list)

    @field_validator("exhibit_id", "title", "insight", "alt_text")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("exhibit text fields must not be empty")
        return value


class ExhibitArtifact(BaseModel):
    exhibit_id: str
    route: str
    vega_json_path: str | None = None
    html_path: str | None = None
    image_path: str | None = None
    svg_path: str | None = None
    alt_text: str
    source_fact_ids: list[str]


def exhibit_specs_from_evidence(evidence: EvidencePack) -> list[ExhibitSpec]:
    facts_by_id = {fact.fact_id: fact for fact in evidence.facts}
    return [_spec_from_draft_exhibit(exhibit, facts_by_id) for exhibit in evidence.exhibits]


def validate_exhibit_specs(specs: list[ExhibitSpec], evidence: EvidencePack, *, product_mode: bool = False) -> QualityResult:
    checks: list[QualityCheck] = []
    fact_ids = {fact.fact_id for fact in evidence.facts}
    severity = "error" if product_mode else "error"

    for index, spec in enumerate(specs):
        location = f"exhibits[{index}]"
        if not spec.fact_ids:
            checks.append(QualityCheck(code="exhibit_missing_fact_ids", message="Exhibit must reference source-backed fact IDs.", severity=severity, location=f"{location}.fact_ids"))
        for fact_id in spec.fact_ids:
            if fact_id not in fact_ids:
                checks.append(QualityCheck(code="exhibit_unknown_fact_id", message=f"Exhibit references unknown fact {fact_id}.", severity="error", location=f"{location}.fact_ids"))
        for data_index, point in enumerate(spec.data):
            if point.fact_id not in fact_ids:
                checks.append(QualityCheck(code="exhibit_data_unknown_fact_id", message=f"Exhibit data point references unknown fact {point.fact_id}.", severity="error", location=f"{location}.data[{data_index}].fact_id"))
            if point.transform_note and not spec.transform_provenance:
                checks.append(QualityCheck(code="exhibit_missing_transform_provenance", message="Derived exhibit data requires transform provenance.", severity="error" if product_mode else "warning", location=f"{location}.transform_provenance"))
        if not spec.alt_text.strip():
            checks.append(QualityCheck(code="exhibit_missing_alt_text", message="Exhibit requires alt text.", severity="error" if product_mode else "warning", location=f"{location}.alt_text"))
        if spec.renderer_route not in {"vega_lite", "mermaid", "table", "kaleido", "image"}:
            checks.append(QualityCheck(code="exhibit_renderer_unavailable", message=f"Renderer route unavailable: {spec.renderer_route}.", severity="error", location=f"{location}.renderer_route"))
    return QualityResult(ok=not any(check.severity == "error" for check in checks), checks=checks)


def _spec_from_draft_exhibit(exhibit: DraftExhibit, facts_by_id: dict[str, EvidenceFact]) -> ExhibitSpec:
    fact_ids = list(exhibit.provenance_fact_ids)
    data = _data_points_from_payload(exhibit, facts_by_id)
    title = exhibit.title or exhibit.visual_id.replace("_", " ").title()
    kind = ExhibitKind(exhibit.visual_type if exhibit.visual_type in ExhibitKind._value2member_map_ else "diagram")
    route = exhibit.preferred_tool if exhibit.preferred_tool in {"vega_lite", "mermaid"} else "table"
    return ExhibitSpec(
        exhibit_id=exhibit.visual_id,
        title=title,
        kind=kind,
        insight=exhibit.purpose,
        fact_ids=fact_ids,
        data=data,
        renderer_route=route,
        alt_text=f"{title}: {exhibit.purpose}",
        plain_text_payload=exhibit.plain_text_payload,
        transform_provenance=["direct fact value mapping"] if data else [],
    )


def _data_points_from_payload(exhibit: DraftExhibit, facts_by_id: dict[str, EvidenceFact]) -> list[ExhibitDataPoint]:
    lines = [line.strip() for line in exhibit.plain_text_payload.splitlines() if line.strip()]
    points: list[ExhibitDataPoint] = []
    for index, fact_id in enumerate(exhibit.provenance_fact_ids):
        fact = facts_by_id.get(fact_id)
        line = lines[index] if index < len(lines) else ""
        label, value = _label_value_from_line(line)
        if not label and fact:
            label = fact.subject
        if value is None and fact:
            value = _coerce_value(fact.value)
        if label and value is not None:
            points.append(ExhibitDataPoint(label=label, value=value, fact_id=fact_id, transform_note="direct parse from exhibit payload or fact value"))
    return points


def _label_value_from_line(line: str) -> tuple[str, int | float | str | None]:
    if ":" not in line:
        return "", None
    label, raw_value = [part.strip() for part in line.split(":", 1)]
    return label, _coerce_value(raw_value)


def _coerce_value(value: str) -> int | float | str:
    stripped = value.strip().replace(",", "")
    try:
        number = float(stripped)
    except ValueError:
        return value
    return number
