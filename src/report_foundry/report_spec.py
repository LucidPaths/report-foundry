"""Strict ReportSpec compiler between evidence cognition and renderer/tool embodiment.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .evidence import EvidencePack, validate_evidence_pack
from .ir import Citation, Claim, Figure, Report, Section, TableBlock, TextBlock
from .qa import run_quality_gates
from .render import render_html, render_pdf

RenderTarget = Literal["html", "pdf"]
ToolRoute = Literal["html_css", "reportlab", "vega_lite", "mermaid", "typst"]


class SpecClaim(BaseModel):
    claim_id: str
    text: str
    fact_ids: list[str]
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"

    @field_validator("fact_ids")
    @classmethod
    def fact_ids_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Spec claims must carry fact IDs")
        return value


class SpecBlock(BaseModel):
    role: Literal["text", "claim", "table", "visual"]
    content: str
    fact_ids: list[str] = Field(default_factory=list)


class SpecSection(BaseModel):
    section_id: str
    title: str
    role: Literal["scope", "evidence", "analysis", "visual", "appendix"]
    blocks: list[SpecBlock]
    claims: list[SpecClaim] = Field(default_factory=list)


class SpecVisual(BaseModel):
    visual_id: str
    visual_type: Literal["evidence_map", "chart", "matrix", "timeline", "diagram"]
    purpose: str
    preferred_tool: ToolRoute
    provenance_fact_ids: list[str]
    plain_text_payload: str

    @field_validator("provenance_fact_ids")
    @classmethod
    def provenance_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Visuals are claims and require provenance fact IDs")
        return value


class SourceAppendix(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class ReportSpec(BaseModel):
    title: str
    subtitle: str | None = None
    audience: str = "executive readers"
    render_targets: list[RenderTarget] = Field(default_factory=lambda: ["html", "pdf"])
    tool_routes: dict[RenderTarget, ToolRoute] = Field(default_factory=lambda: {"html": "html_css", "pdf": "reportlab"})
    sections: list[SpecSection]
    visuals: list[SpecVisual]
    source_appendix: SourceAppendix
    source_fact_map: dict[str, list[str]]


def compile_report_spec(pack: EvidencePack) -> ReportSpec:
    _ensure_valid_evidence(pack)
    facts_by_id = {fact.fact_id: fact for fact in pack.facts}
    claims = [
        SpecClaim(claim_id=f"claim_{index + 1:03d}", text=claim.text, fact_ids=claim.fact_ids, confidence=claim.confidence)
        for index, claim in enumerate(pack.claims)
    ]
    scope_lines = [f"{key}: {_stringify(value)}" for key, value in pack.scope.items()]
    evidence_rows = [[fact.subject, fact.predicate, fact.value, fact.fact_id] for fact in pack.facts]
    source_rows = [
        [source.source_id, source.title, source.observed_at, source.content_sha256[:16] + "…", source.extractor]
        for source in pack.sources
    ]
    return ReportSpec(
        title=pack.title,
        subtitle=pack.subtitle,
        audience=str(pack.scope.get("audience", "executive readers")),
        sections=[
            SpecSection(
                section_id="scope",
                title="Scope",
                role="scope",
                blocks=[SpecBlock(role="text", content="\n".join(scope_lines) or "Scope not declared.")],
            ),
            SpecSection(
                section_id="evidence_claims",
                title="Evidence-backed claims",
                role="analysis",
                blocks=[SpecBlock(role="claim", content=claim.text, fact_ids=claim.fact_ids) for claim in claims],
                claims=claims,
            ),
            SpecSection(
                section_id="fact_table",
                title="Fact Table",
                role="evidence",
                blocks=[SpecBlock(role="table", content="subject | predicate | value | fact_id", fact_ids=list(facts_by_id))],
            ),
        ],
        visuals=[
            SpecVisual(
                visual_id="evidence_trace_map",
                visual_type="evidence_map",
                purpose="Show how source observations support facts and claims before PDF rendering.",
                preferred_tool="mermaid",
                provenance_fact_ids=list(facts_by_id),
                plain_text_payload=_evidence_map_payload(pack),
            )
        ],
        source_appendix=SourceAppendix(headers=["Source", "Title", "Observed", "SHA-256", "Extractor"], rows=source_rows),
        source_fact_map={source.source_id: [fact.fact_id for fact in pack.facts if fact.source_id == source.source_id] for source in pack.sources},
    )


def compile_spec_to_report(spec: ReportSpec) -> Report:
    sections: list[Section] = []
    for section in spec.sections:
        if section.section_id == "scope":
            sections.append(Section(title=section.title, kicker="Typed report boundary before claims.", blocks=[TextBlock(text=section.blocks[0].content)]))
        elif section.section_id == "evidence_claims":
            sections.append(
                Section(
                    title=section.title,
                    kicker="Every claim carries fact IDs from the strict ReportSpec.",
                    blocks=[
                        Claim(
                            text=claim.text,
                            confidence=claim.confidence,
                            verification_status="supported",
                            citations=_citations_for_claim(spec, claim),
                        )
                        for claim in section.claims
                    ],
                )
            )
        elif section.section_id == "fact_table":
            sections.append(
                Section(
                    title=section.title,
                    kicker="Renderer/tool payload receives explicit data, not vague instructions.",
                    blocks=[TableBlock(headers=["Source", "Fact IDs"], rows=[[source_id, "; ".join(fact_ids)] for source_id, fact_ids in spec.source_fact_map.items()])],
                )
            )
    sections.append(
        Section(
            title="Visual Contract",
            kicker="Visuals are source-backed claims, routed to tools by type.",
            blocks=[
                Figure(
                    title=visual.visual_id.replace("_", " ").title(),
                    caption=f"{visual.visual_type} routed to {visual.preferred_tool}; source-backed by {', '.join(visual.provenance_fact_ids)}.",
                    alt_text=visual.plain_text_payload,
                )
                for visual in spec.visuals
            ],
        )
    )
    sections.append(
        Section(
            title="Source Appendix",
            kicker="Observed payloads and hashes used by this artifact.",
            blocks=[TableBlock(headers=spec.source_appendix.headers, rows=spec.source_appendix.rows)],
        )
    )
    return Report(title=spec.title, subtitle=spec.subtitle, sections=sections, tags=["report-spec", *spec.render_targets])


def write_spec_artifacts(pack: EvidencePack, out_dir: Path, *, stem: str | None = None) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = compile_report_spec(pack)
    report = compile_spec_to_report(spec)
    qa = run_quality_gates(report)
    if not qa.ok:
        codes = ", ".join(check.code for check in qa.checks if check.severity == "error")
        raise ValueError(f"ReportSpec compiled invalid report: {codes}")
    artifact_stem = _stem(stem or pack.title)
    spec_path = out_dir / f"{artifact_stem}.spec.json"
    ir_path = out_dir / f"{artifact_stem}.json"
    html_path = out_dir / f"{artifact_stem}.html"
    pdf_path = out_dir / f"{artifact_stem}.pdf"
    spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    ir_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    render_pdf(report, pdf_path)
    return {"spec": spec_path, "ir": ir_path, "html": html_path, "pdf": pdf_path}


def _ensure_valid_evidence(pack: EvidencePack) -> None:
    result = validate_evidence_pack(pack)
    if not result.ok:
        codes = ", ".join(check.code for check in result.checks if check.severity == "error")
        raise ValueError(f"Invalid evidence pack: {codes}")


def _citations_for_claim(spec: ReportSpec, claim: SpecClaim) -> list[Citation]:
    citations: list[Citation] = []
    for source_row in spec.source_appendix.rows:
        source_id = source_row[0]
        fact_ids = set(spec.source_fact_map.get(source_id, []))
        if fact_ids.intersection(claim.fact_ids):
            citations.append(Citation(source_id=source_id, title=source_row[1], quote="facts: " + ", ".join(claim.fact_ids), accessed_at=source_row[2], locator="ReportSpec source_fact_map"))
    return citations


def _evidence_map_payload(pack: EvidencePack) -> str:
    lines = ["source -> fact -> claim"]
    claims_by_fact = {fact_id: [] for fact_id in [fact.fact_id for fact in pack.facts]}
    for index, claim in enumerate(pack.claims, 1):
        for fact_id in claim.fact_ids:
            claims_by_fact.setdefault(fact_id, []).append(f"claim_{index:03d}")
    for fact in pack.facts:
        lines.append(f"{fact.source_id} -> {fact.fact_id} -> {', '.join(claims_by_fact.get(fact.fact_id, [])) or 'no_claim'}")
    return "\n".join(lines)


def _stringify(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {item}" for key, item in value.items())
    return str(value)


def _stem(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return "_".join(part for part in cleaned.split("_") if part) or "report"
