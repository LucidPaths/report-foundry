"""Renderer adapter tests for HTML and PDF outputs from the semantic IR.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P8 Low Floor, High Ceiling.
"""

from pathlib import Path

from report_foundry.ir import Citation, Claim, Figure, MetricCard, Report, Section, TextBlock
from report_foundry.render import render_html, render_pdf


def sample_report():
    return Report(
        title="Daily Systems Brief",
        subtitle="AI-native report pipeline smoke test",
        sections=[
            Section(
                title="Model Signals",
                blocks=[
                    TextBlock(text="This report is generated from structured blocks."),
                    MetricCard(label="Sources", value="3", note="Evidence-backed inputs"),
                    Claim(
                        text="Claim-level citations survive rendering.",
                        citations=[Citation(source_id="src1", url="https://example.com/source", quote="citations survive")],
                    ),
                    Figure(title="Signal map", caption="Vector-first visual slot", alt_text="A placeholder signal map"),
                ],
            )
        ],
    )


def test_render_html_contains_sections_and_citations():
    html = render_html(sample_report())

    assert "Daily Systems Brief" in html
    assert "Model Signals" in html
    assert "https://example.com/source" in html


def test_render_html_uses_professional_density_and_design_primitives():
    html = render_html(sample_report())

    assert "page-break-before:always" not in html
    assert "rf-underlay" in html
    assert "linear-gradient" in html or "radial-gradient" in html
    assert "display:grid" in html
    assert "break-inside:avoid" in html


def test_render_pdf_writes_real_pdf(tmp_path: Path):
    out = tmp_path / "report.pdf"

    render_pdf(sample_report(), out)

    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 1000
