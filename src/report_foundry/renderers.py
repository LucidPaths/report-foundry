"""Renderer adapter seams for route-specific report rendering.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol
import shutil

from pydantic import BaseModel, Field

from .factory import RunMode
from .qa import QualityCheck, QualityResult
from .render import render_html_pdf_with_chromium


class RendererRouteError(RuntimeError):
    def __init__(self, message: str, gate_result: QualityResult):
        super().__init__(message)
        self.gate_result = gate_result


class RenderRequest(BaseModel):
    report_spec_path: Path
    evidence_pack_path: Path
    citation_records_path: Path | None = None
    exhibit_specs_path: Path | None = None
    html_path: Path | None = None
    pdf_path: Path | None = None
    metrics_path: Path | None = None
    previews_dir: Path | None = None
    route: str
    out_dir: Path
    run_mode: RunMode


class RenderArtifact(BaseModel):
    route: str
    html_path: str | None = None
    pdf_path: str | None = None
    source_paths: list[str] = Field(default_factory=list)
    preview_paths: list[str] = Field(default_factory=list)
    metrics_path: str | None = None
    gate_result_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RendererAdapter(Protocol):
    route: str

    def render(self, request: RenderRequest) -> RenderArtifact:
        ...


class PlaywrightChromiumRendererAdapter:
    route = "playwright_chromium"

    def render(self, request: RenderRequest) -> RenderArtifact:
        if request.html_path is None:
            gate = _write_gate(request, [QualityCheck(code="missing_html_input", message="Playwright renderer requires html_path.")])
            raise RendererRouteError("Playwright renderer requires html_path", gate)
        pdf_path = request.pdf_path or request.out_dir / "report.pdf"
        metrics_path = request.metrics_path or request.out_dir / "layout_metrics.json"
        previews_dir = request.previews_dir or request.out_dir / "previews"
        render_html_pdf_with_chromium(request.html_path, pdf_path)
        metrics = analyze_pdf_layout(pdf_path)
        _assert_pdf_layout_quality(metrics)
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        preview_paths = _write_pdf_page_previews(pdf_path, previews_dir)
        gate = _write_gate(request, [])
        return RenderArtifact(
            route=self.route,
            html_path=str(request.html_path),
            pdf_path=str(pdf_path),
            source_paths=[str(path) for path in _existing_paths([request.report_spec_path, request.evidence_pack_path, request.citation_records_path, request.exhibit_specs_path])],
            preview_paths=[str(path) for path in preview_paths],
            metrics_path=str(metrics_path),
            gate_result_path=str(request.out_dir / "render_gate_result.json"),
        )


class TypstRendererAdapter:
    route = "typst"

    def render(self, request: RenderRequest) -> RenderArtifact:
        if shutil.which("typst") is None:
            gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="typst binary unavailable on PATH.")])
            raise RendererRouteError("typst renderer unavailable", gate)
        gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="typst route is scaffolded but not implemented yet.")])
        raise RendererRouteError("typst renderer not implemented", gate)


class PandocRendererAdapter:
    route = "pandoc"

    def render(self, request: RenderRequest) -> RenderArtifact:
        if shutil.which("pandoc") is None:
            gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="pandoc binary unavailable on PATH.")])
            raise RendererRouteError("pandoc renderer unavailable", gate)
        gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="pandoc route is scaffolded but not implemented yet.")])
        raise RendererRouteError("pandoc renderer not implemented", gate)


class WeasyPrintRendererAdapter:
    route = "weasyprint"

    def render(self, request: RenderRequest) -> RenderArtifact:
        if shutil.which("weasyprint") is None:
            gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="weasyprint binary unavailable on PATH.")])
            raise RendererRouteError("weasyprint renderer unavailable", gate)
        gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="weasyprint route is scaffolded but not implemented yet.")])
        raise RendererRouteError("weasyprint renderer not implemented", gate)


class KaleidoRendererAdapter:
    route = "kaleido"

    def render(self, request: RenderRequest) -> RenderArtifact:
        gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="kaleido is a chart export adapter, not a full report renderer yet.")])
        raise RendererRouteError("kaleido renderer not implemented", gate)


class CslRendererAdapter:
    route = "csl"

    def render(self, request: RenderRequest) -> RenderArtifact:
        gate = _write_gate(request, [QualityCheck(code="renderer_unavailable", message="csl/citeproc is a citation adapter, not a full report renderer yet.")])
        raise RendererRouteError("csl renderer not implemented", gate)


def render_with_route(request: RenderRequest) -> RenderArtifact:
    adapters: dict[str, RendererAdapter] = {
        PlaywrightChromiumRendererAdapter.route: PlaywrightChromiumRendererAdapter(),
        TypstRendererAdapter.route: TypstRendererAdapter(),
        PandocRendererAdapter.route: PandocRendererAdapter(),
        WeasyPrintRendererAdapter.route: WeasyPrintRendererAdapter(),
        KaleidoRendererAdapter.route: KaleidoRendererAdapter(),
        CslRendererAdapter.route: CslRendererAdapter(),
    }
    adapter = adapters.get(request.route)
    if adapter is None:
        gate = _write_gate(request, [QualityCheck(code="unknown_renderer_route", message=f"Unknown renderer route: {request.route}.")])
        raise RendererRouteError(f"Unknown renderer route: {request.route}", gate)
    return adapter.render(request)


def analyze_pdf_layout(pdf_path: Path) -> dict[str, object]:
    import fitz

    document = fitz.open(pdf_path)
    page_metrics: list[dict[str, object]] = []
    total_words = 0
    total_images = 0
    total_drawings = 0
    for index, page in enumerate(document, 1):
        text = page.get_text("text")
        words = [word for word in text.replace("\n", " ").split(" ") if word.strip()]
        image_count = len(page.get_images(full=True))
        drawing_count = len(page.get_drawings())
        total_words += len(words)
        total_images += image_count
        total_drawings += drawing_count
        page_metrics.append(
            {
                "page_number": index,
                "word_count": len(words),
                "char_count": len(text),
                "image_count": image_count,
                "drawing_count": drawing_count,
                "visual_object_count": image_count + drawing_count,
            }
        )
    producer = document.metadata.get("producer") or ""
    return {
        "page_count": document.page_count,
        "word_count": total_words,
        "average_words_per_page": round(total_words / max(document.page_count, 1), 1),
        "image_count": total_images,
        "drawing_count": total_drawings,
        "visual_object_count": total_images + total_drawings,
        "producer": "Skia/PDF" if "Skia/PDF" in producer else producer,
        "creator": document.metadata.get("creator") or "",
        "pages": page_metrics,
    }


def _write_pdf_page_previews(pdf_path: Path, previews_dir: Path) -> list[Path]:
    import fitz

    previews_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    paths: list[Path] = []
    for index, page in enumerate(document, 1):
        pixmap = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5), alpha=False)
        path = previews_dir / f"page_{index:03d}.png"
        pixmap.save(path)
        paths.append(path)
    return paths


def _assert_pdf_layout_quality(metrics: dict[str, object]) -> None:
    page_count = int(metrics["page_count"])
    average_words_per_page = float(metrics["average_words_per_page"])
    if page_count >= 6 and average_words_per_page < 160:
        raise ValueError(
            "Rendered PDF failed layout density gate: "
            f"{page_count} pages, {average_words_per_page} average words/page."
        )


def _write_gate(request: RenderRequest, checks: list[QualityCheck]) -> QualityResult:
    result = QualityResult(ok=not any(check.severity == "error" for check in checks), checks=checks)
    request.out_dir.mkdir(parents=True, exist_ok=True)
    (request.out_dir / "render_gate_result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def _existing_paths(paths: list[Path | None]) -> list[Path]:
    return [path for path in paths if path is not None and path.exists()]
