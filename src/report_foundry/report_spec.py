"""Strict ReportSpec compiler between evidence cognition and renderer/tool embodiment.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .citations import citation_export_from_evidence, render_source_appendix_markdown, source_appendix_rows
from .evidence import EvidencePack, validate_evidence_pack
from .factory import RunMode
from .exhibit_adapters import write_exhibit_artifacts, write_exhibit_manifest
from .exhibits import ExhibitSpec, exhibit_specs_from_evidence, validate_exhibit_specs
from .ir import Citation, Claim, Figure, Report, Section, TextBlock
from .package import build_package_manifest, write_package_manifest
from .qa import run_quality_gates
from .render import render_html
from .renderers import RenderRequest, RendererRouteError, render_with_route

RenderTarget = Literal["html", "pdf"]
ToolRoute = Literal["html_css", "playwright_chromium", "reportlab", "vega_lite", "mermaid", "typst"]


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
    role: Literal["text", "paragraph", "claim", "table", "visual"]
    content: str
    fact_ids: list[str] = Field(default_factory=list)


class SpecSection(BaseModel):
    section_id: str
    title: str
    role: Literal["scope", "evidence", "analysis", "report", "visual", "appendix"]
    blocks: list[SpecBlock]
    claims: list[SpecClaim] = Field(default_factory=list)


class SpecFact(BaseModel):
    fact_id: str
    subject: str
    predicate: str
    value: str
    source_id: str
    quote: str
    locator: str | None = None


class SpecVisual(BaseModel):
    visual_id: str
    visual_type: Literal["evidence_map", "chart", "matrix", "timeline", "diagram"]
    purpose: str
    preferred_tool: ToolRoute
    provenance_fact_ids: list[str]
    plain_text_payload: str
    alt_text: str | None = None

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
    tool_routes: dict[RenderTarget, ToolRoute] = Field(default_factory=lambda: {"html": "html_css", "pdf": "playwright_chromium"})
    sections: list[SpecSection]
    visuals: list[SpecVisual]
    exhibits: list[ExhibitSpec] = Field(default_factory=list)
    source_appendix: SourceAppendix
    source_fact_map: dict[str, list[str]]
    citation_source_map: dict[str, str] = Field(default_factory=dict)
    fact_details: dict[str, SpecFact]
    generation_metadata: dict[str, str] = Field(default_factory=dict)


def _professional_report_sections(pack: EvidencePack) -> list[SpecSection]:
    professional = pack.professional_report
    if professional is None:
        return []

    sections = [
        SpecSection(
            section_id="executive_brief",
            title="Executive brief",
            role="report",
            blocks=[
                SpecBlock(role="paragraph", content=professional.one_sentence_thesis),
                *[SpecBlock(role="paragraph", content=paragraph) for paragraph in professional.executive_summary],
                SpecBlock(
                    role="paragraph",
                    content="Key takeaways:\n" + "\n".join(
                        f"• {takeaway.takeaway}" + (f" — {takeaway.implication}" if takeaway.implication else "")
                        for takeaway in professional.key_takeaways
                    ),
                    fact_ids=sorted({fact_id for takeaway in professional.key_takeaways for fact_id in takeaway.fact_ids}),
                ),
            ],
        )
    ]
    for section in professional.sections:
        blocks = [
            SpecBlock(role="paragraph", content=section.lede, fact_ids=section.fact_ids),
            *[SpecBlock(role="paragraph", content=paragraph, fact_ids=section.fact_ids) for paragraph in section.paragraphs],
            SpecBlock(role="paragraph", content=f"So what: {section.so_what}", fact_ids=section.fact_ids),
        ]
        if section.limitations:
            blocks.append(SpecBlock(role="paragraph", content="Limits: " + " ".join(section.limitations), fact_ids=section.fact_ids))
        sections.append(
            SpecSection(
                section_id=section.section_id,
                title=section.headline,
                role="report",
                blocks=blocks,
            )
        )
    if professional.what_to_watch:
        sections.append(
            SpecSection(
                section_id="what_to_watch",
                title="What to watch",
                role="report",
                blocks=[SpecBlock(role="paragraph", content="\n".join(f"• {item}" for item in professional.what_to_watch))],
            )
        )
    if professional.methodology:
        sections.append(
            SpecSection(
                section_id="methodology",
                title="Methodology",
                role="report",
                blocks=[SpecBlock(role="paragraph", content=professional.methodology)],
            )
        )
    return sections


def compile_report_spec(pack: EvidencePack) -> ReportSpec:
    _ensure_valid_evidence(pack)
    facts_by_id = {fact.fact_id: fact for fact in pack.facts}
    claims = [
        SpecClaim(claim_id=f"claim_{index + 1:03d}", text=claim.text, fact_ids=claim.fact_ids, confidence=claim.confidence)
        for index, claim in enumerate(pack.claims)
    ]
    scope_lines = [f"{key}: {_stringify(value)}" for key, value in pack.scope.items()]
    citation_export = citation_export_from_evidence(pack)
    source_rows = source_appendix_rows(citation_export.records)
    exhibit_specs = exhibit_specs_from_evidence(pack)
    exhibit_result = validate_exhibit_specs(exhibit_specs, pack, product_mode=str(pack.scope.get("run_mode", "fixture")) == "product")
    if not exhibit_result.ok:
        codes = ", ".join(check.code for check in exhibit_result.checks if check.severity == "error")
        raise ValueError(f"Invalid exhibit specs: {codes}")
    report_sections = _professional_report_sections(pack)
    if not report_sections:
        report_sections = [
            SpecSection(
                section_id=section.section_id,
                title=section.title,
                role="report",
                blocks=[SpecBlock(role="paragraph", content=paragraph, fact_ids=section.fact_ids) for paragraph in section.paragraphs],
            )
            for section in pack.report_sections
        ]
    if not report_sections:
        report_sections = [
            SpecSection(
                section_id="executive_brief",
                title="Executive brief",
                role="report",
                blocks=[
                    SpecBlock(
                        role="paragraph",
                        content="This report pack contains sourced claims but no full narrative sections. Add report_sections to the EvidencePack so the foundry can render an actual analyst report instead of schema plumbing.",
                        fact_ids=list(facts_by_id),
                    )
                ],
            )
        ]
    return ReportSpec(
        title=pack.title,
        subtitle=pack.subtitle,
        audience=str(pack.scope.get("audience", "executive readers")),
        sections=[
            *report_sections,
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
            *[
                SpecVisual(
                    visual_id=exhibit.exhibit_id,
                    visual_type=exhibit.kind.value if exhibit.kind.value in {"evidence_map", "chart", "matrix", "timeline", "diagram"} else "chart",
                    purpose=exhibit.insight,
                    preferred_tool=exhibit.renderer_route,
                    provenance_fact_ids=exhibit.fact_ids,
                    plain_text_payload=exhibit.alt_text,
                    alt_text=exhibit.alt_text,
                )
                for exhibit in exhibit_specs
            ],
            SpecVisual(
                visual_id="evidence_trace_map",
                visual_type="evidence_map",
                purpose="Show how source observations support facts and claims before PDF rendering.",
                preferred_tool="mermaid",
                provenance_fact_ids=list(facts_by_id),
                plain_text_payload=_evidence_map_payload(pack),
            ),
        ],
        exhibits=exhibit_specs,
        source_appendix=SourceAppendix(headers=["Citation", "Title", "URL/Path", "Accessed", "Locator"], rows=source_rows),
        source_fact_map={source.source_id: [fact.fact_id for fact in pack.facts if fact.source_id == source.source_id] for source in pack.sources},
        citation_source_map={record.citation_id: record.source_id for record in citation_export.records},
        fact_details={fact.fact_id: SpecFact(**fact.model_dump()) for fact in pack.facts},
        generation_metadata={
            "run_mode": str(pack.scope.get("run_mode", "fixture")),
            "artifact_status": str(pack.scope.get("artifact_status", pack.scope.get("run_mode", "fixture"))),
        },
    )


def compile_spec_to_report(spec: ReportSpec, visual_paths: dict[str, Path] | None = None) -> Report:
    visual_paths = visual_paths or {}
    sections: list[Section] = []
    for section in spec.sections:
        if section.role == "report":
            sections.append(
                Section(
                    title=section.title,
                    kicker=None,
                    blocks=[TextBlock(text=block.content) for block in section.blocks if block.role == "paragraph"],
                )
            )
        elif section.section_id == "scope":
            continue
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
            continue
    sections.append(
        Section(
            title="Visual Contract",
            kicker="Visuals are source-backed claims, routed to tools by type.",
            blocks=[
                Figure(
                    title=visual.visual_id.replace("_", " ").title(),
                    path=visual_paths[visual.visual_id].name if visual.visual_id in visual_paths else None,
                    caption=f"{visual.visual_type} routed to {visual.preferred_tool}; source-backed by {', '.join(visual.provenance_fact_ids)}.",
                    alt_text=visual.alt_text or visual.plain_text_payload,
                )
                for visual in spec.visuals
            ],
        )
    )
    sections.append(
        Section(
            title="Source Appendix",
            kicker="Reader-facing source links; full hashes stay in the ReportSpec JSON.",
            blocks=[
                TextBlock(
                    text="\n".join(
                        f"• {row[1]} — {row[2] or row[0]} ({row[0]}, observed {row[3]})"
                        for row in spec.source_appendix.rows
                    )
                )
            ],
        )
    )
    return Report(title=spec.title, subtitle=spec.subtitle, sections=sections, tags=["report-spec", *spec.render_targets])


def write_spec_artifacts(pack: EvidencePack, out_dir: Path, *, stem: str | None = None, route: str = "playwright_chromium") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = compile_report_spec(pack)
    artifact_stem = _stem(stem or pack.title)
    visual_paths = _write_visual_artifacts(spec, out_dir, artifact_stem)
    exhibit_artifacts = write_exhibit_artifacts(spec.exhibits, pack, out_dir / "exhibits")
    visual_paths.update({artifact.exhibit_id: Path(artifact.vega_json_path) for artifact in exhibit_artifacts if artifact.vega_json_path})
    report = compile_spec_to_report(spec, visual_paths)
    qa = run_quality_gates(report)
    if not qa.ok:
        codes = ", ".join(check.code for check in qa.checks if check.severity == "error")
        raise ValueError(f"ReportSpec compiled invalid report: {codes}")
    spec_path = out_dir / f"{artifact_stem}.spec.json"
    ir_path = out_dir / f"{artifact_stem}.json"
    html_path = out_dir / f"{artifact_stem}.html"
    pdf_path = out_dir / f"{artifact_stem}.pdf"
    layout_metrics_path = out_dir / f"{artifact_stem}.layout.json"
    evidence_path = out_dir / f"{artifact_stem}.evidence.json"
    render_artifact_path = out_dir / f"{artifact_stem}.render_artifact.json"
    citations_path = out_dir / f"{artifact_stem}.citations.json"
    csl_path = out_dir / f"{artifact_stem}.citations.csl.json"
    bibtex_path = out_dir / f"{artifact_stem}.citations.bib"
    source_appendix_path = out_dir / f"{artifact_stem}.source_appendix.md"
    exhibits_manifest_path = out_dir / "exhibits.json"
    package_manifest_path = out_dir / f"{artifact_stem}.package_manifest.json"
    evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    citation_export = citation_export_from_evidence(pack)
    citations_path.write_text(citation_export.model_dump_json(indent=2), encoding="utf-8")
    csl_path.write_text(json.dumps(citation_export.csl_json, indent=2), encoding="utf-8")
    bibtex_path.write_text(citation_export.bibtex or "", encoding="utf-8")
    source_appendix_path.write_text(render_source_appendix_markdown(citation_export.records), encoding="utf-8")
    write_exhibit_manifest(exhibit_artifacts, exhibits_manifest_path)
    spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    ir_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    run_mode = RunMode(str(pack.scope.get("run_mode", "fixture")))
    render_request = RenderRequest(
        report_spec_path=spec_path,
        evidence_pack_path=evidence_path,
        citation_records_path=citations_path,
        exhibit_specs_path=exhibits_manifest_path,
        html_path=html_path,
        pdf_path=pdf_path,
        metrics_path=layout_metrics_path,
        previews_dir=out_dir / f"{artifact_stem}.pages",
        route=route,
        out_dir=out_dir,
        run_mode=run_mode,
    )
    base_artifacts = {
        "spec": spec_path,
        "ir": ir_path,
        "html": html_path,
        "pdf": pdf_path,
        "layout_metrics": layout_metrics_path,
        "page_previews": render_request.previews_dir,
        "evidence_pack": evidence_path,
        "render_artifact": render_artifact_path,
        "citations": citations_path,
        "csl": csl_path,
        "bibtex": bibtex_path,
        "source_appendix": source_appendix_path,
        "exhibits": exhibits_manifest_path,
        **visual_paths,
    }
    render_gate_result_path = out_dir / "render_gate_result.json"
    try:
        render_artifact = render_with_route(render_request)
    except RendererRouteError as exc:
        write_package_manifest(
            build_package_manifest(
                package_id=artifact_stem,
                route=route,
                run_mode=run_mode,
                status="failed",
                out_dir=out_dir,
                artifact_paths={**base_artifacts, "render_gate_result": render_gate_result_path},
                gates={"render": render_gate_result_path},
                source_paths=[evidence_path, spec_path, citations_path, exhibits_manifest_path],
                errors=[str(exc)],
            ),
            package_manifest_path,
        )
        raise
    render_artifact_path.write_text(render_artifact.model_dump_json(indent=2), encoding="utf-8")
    page_previews_dir = Path(render_artifact.preview_paths[0]).parent if render_artifact.preview_paths else render_request.previews_dir
    render_gate_result_path = Path(render_artifact.gate_result_path or render_gate_result_path)
    paths = {**base_artifacts, "page_previews": page_previews_dir, "render_gate_result": render_gate_result_path}
    write_package_manifest(
        build_package_manifest(
            package_id=artifact_stem,
            route=route,
            run_mode=run_mode,
            status="success",
            out_dir=out_dir,
            artifact_paths=paths,
            gates={"render": render_gate_result_path},
            source_paths=[Path(path) for path in render_artifact.source_paths],
        ),
        package_manifest_path,
    )
    return {**paths, "package_manifest": package_manifest_path}


def _write_visual_artifacts(spec: ReportSpec, out_dir: Path, artifact_stem: str) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for visual in spec.visuals:
        if visual.preferred_tool != "mermaid":
            continue
        source_path = out_dir / f"{artifact_stem}.{visual.visual_id}.mmd"
        svg_path = out_dir / f"{artifact_stem}.{visual.visual_id}.svg"
        source_path.write_text(_mermaid_payload(visual), encoding="utf-8")
        _render_mermaid_svg(source_path, svg_path)
        paths[visual.visual_id] = svg_path
    return paths


def _render_mermaid_svg(source_path: Path, output_path: Path) -> None:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("Mermaid visual rendering requires npx on PATH")
    result = subprocess.run(
        [npx, "--yes", "@mermaid-js/mermaid-cli", "--quiet", "-i", str(source_path), "-o", str(output_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Mermaid render failed for {source_path}: {result.stderr or result.stdout}")


def _mermaid_payload(visual: SpecVisual) -> str:
    payload = visual.plain_text_payload.strip()
    if payload.startswith(("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "timeline", "mindmap", "erDiagram")):
        return payload + "\n"
    lines = ["flowchart LR"]
    for row in [line for line in visual.plain_text_payload.splitlines()[1:] if "->" in line]:
        parts = [part.strip() for part in row.split("->")]
        if len(parts) < 3:
            continue
        source, fact, claims = parts[0], parts[1], parts[2]
        source_id = _node_id(source, "source")
        fact_id = _node_id(fact, "fact")
        lines.append(f'  {source_id}["{_escape_mermaid(source)}"] --> {fact_id}["{_escape_mermaid(fact)}"]')
        for claim in [item.strip() for item in claims.split(",") if item.strip()]:
            claim_id = _node_id(claim, "claim")
            lines.append(f'  {fact_id} --> {claim_id}["{_escape_mermaid(claim)}"]')
    lines.extend([
        "  classDef source fill:#ecfeff,stroke:#0891b2,color:#164e63",
        "  classDef fact fill:#f5f3ff,stroke:#7c3aed,color:#3b0764",
        "  classDef claim fill:#f0fdf4,stroke:#16a34a,color:#14532d",
        "  class source_0 source",
    ])
    return "\n".join(lines) + "\n"


def _node_id(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_") or prefix
    return f"{prefix}_{cleaned[:48]}"


def _escape_mermaid(value: str) -> str:
    return value.replace('"', "'")[:80]


def _ensure_valid_evidence(pack: EvidencePack) -> None:
    result = validate_evidence_pack(pack)
    if not result.ok:
        codes = ", ".join(check.code for check in result.checks if check.severity == "error")
        raise ValueError(f"Invalid evidence pack: {codes}")


def _citations_for_claim(spec: ReportSpec, claim: SpecClaim) -> list[Citation]:
    citations: list[Citation] = []
    claim_fact_ids = set(claim.fact_ids)
    for source_row in spec.source_appendix.rows:
        citation_id = source_row[0]
        source_id = spec.citation_source_map.get(citation_id, citation_id)
        source_fact_ids = [fact_id for fact_id in spec.source_fact_map.get(source_id, []) if fact_id in claim_fact_ids]
        if source_fact_ids:
            quotes = [spec.fact_details[fact_id].quote for fact_id in source_fact_ids if fact_id in spec.fact_details]
            citations.append(
                Citation(
                    source_id=source_id,
                    title=source_row[1],
                    url=source_row[2],
                    quote="; ".join(quotes),
                    accessed_at=source_row[3],
                    locator="; ".join(source_fact_ids),
                )
            )
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
