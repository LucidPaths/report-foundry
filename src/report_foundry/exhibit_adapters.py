"""Exhibit renderer adapter seams.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Protocol

from .evidence import EvidencePack
from .exhibits import ExhibitArtifact, ExhibitSpec, validate_exhibit_specs


class ExhibitAdapter(Protocol):
    route: str

    def render(self, spec: ExhibitSpec, evidence: EvidencePack, out_dir: Path) -> ExhibitArtifact:
        ...


class VegaLiteExhibitAdapter:
    route = "vega_lite"

    def render(self, spec: ExhibitSpec, evidence: EvidencePack, out_dir: Path) -> ExhibitArtifact:
        if spec.renderer_route != self.route:
            raise ValueError(f"VegaLiteExhibitAdapter cannot render route {spec.renderer_route}")
        result = validate_exhibit_specs([spec], evidence, product_mode=str(evidence.scope.get("run_mode", "fixture")) == "product")
        if not result.ok:
            codes = ", ".join(check.code for check in result.checks if check.severity == "error")
            raise ValueError(f"Invalid exhibit spec: {codes}")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{spec.exhibit_id}.vega.json"
        path.write_text(json.dumps(_vega_lite_payload(spec), indent=2), encoding="utf-8")
        return ExhibitArtifact(
            exhibit_id=spec.exhibit_id,
            route=self.route,
            vega_json_path=str(path),
            alt_text=spec.alt_text,
            source_fact_ids=spec.fact_ids,
        )


class HtmlExhibitAdapter:
    route = "table"

    def render(self, spec: ExhibitSpec, evidence: EvidencePack, out_dir: Path) -> ExhibitArtifact:
        if spec.renderer_route != self.route:
            raise ValueError(f"HtmlExhibitAdapter cannot render route {spec.renderer_route}")
        result = validate_exhibit_specs([spec], evidence, product_mode=str(evidence.scope.get("run_mode", "fixture")) == "product")
        if not result.ok:
            codes = ", ".join(check.code for check in result.checks if check.severity == "error")
            raise ValueError(f"Invalid exhibit spec: {codes}")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{spec.exhibit_id}.html"
        rows = "\n".join(
            f"<tr><td>{html.escape(point.label)}</td><td>{html.escape(str(point.value))}</td><td>{html.escape(point.fact_id)}</td></tr>"
            for point in spec.data
        )
        payload = html.escape(spec.plain_text_payload or spec.alt_text)
        body = (
            f"<!doctype html><meta charset='utf-8'><title>{html.escape(spec.title)}</title>"
            f"<figure><figcaption>{html.escape(spec.insight)}</figcaption>"
            f"<table><thead><tr><th>Label</th><th>Value</th><th>Fact ID</th></tr></thead><tbody>{rows}</tbody></table>"
            f"<pre>{payload}</pre></figure>"
        )
        path.write_text(body, encoding="utf-8")
        return ExhibitArtifact(
            exhibit_id=spec.exhibit_id,
            route=self.route,
            html_path=str(path),
            alt_text=spec.alt_text,
            source_fact_ids=spec.fact_ids,
        )


def write_exhibit_artifacts(specs: list[ExhibitSpec], evidence: EvidencePack, out_dir: Path) -> list[ExhibitArtifact]:
    result = validate_exhibit_specs(specs, evidence, product_mode=str(evidence.scope.get("run_mode", "fixture")) == "product")
    if not result.ok:
        codes = ", ".join(check.code for check in result.checks if check.severity == "error")
        raise ValueError(f"Invalid exhibit specs: {codes}")
    artifacts: list[ExhibitArtifact] = []
    adapters: dict[str, ExhibitAdapter] = {"vega_lite": VegaLiteExhibitAdapter(), "table": HtmlExhibitAdapter()}
    for spec in specs:
        adapter = adapters.get(spec.renderer_route)
        if adapter is None:
            # Step 4 formalizes Vega-Lite first. Existing Mermaid visuals remain
            # rendered by report_spec._write_visual_artifacts until Mermaid gets
            # its own ExhibitAdapter in a later pass.
            continue
        artifacts.append(adapter.render(spec, evidence, out_dir))
    return artifacts


def write_exhibit_manifest(artifacts: list[ExhibitArtifact], path: Path) -> Path:
    path.write_text(json.dumps({"artifacts": [artifact.model_dump() for artifact in artifacts]}, indent=2), encoding="utf-8")
    return path


def _vega_lite_payload(spec: ExhibitSpec) -> dict[str, object]:
    values = [
        {"label": point.label, "value": point.value, "fact_id": point.fact_id}
        for point in spec.data
    ]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": spec.title,
        "description": spec.alt_text,
        "mark": "bar",
        "data": {"values": values},
        "encoding": {
            "x": {"field": "label", "type": "nominal", "title": "Label"},
            "y": {"field": "value", "type": "quantitative", "title": "Value"},
            "tooltip": [
                {"field": "label", "type": "nominal"},
                {"field": "value", "type": "quantitative"},
                {"field": "fact_id", "type": "nominal"},
            ],
        },
        "usermeta": {
            "exhibit_id": spec.exhibit_id,
            "fact_ids": spec.fact_ids,
            "transform_provenance": spec.transform_provenance,
        },
    }
