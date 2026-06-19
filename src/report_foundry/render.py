"""HTML and PDF renderer adapters for the semantic report IR.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P6 Visuals Are Claims; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .ir import Claim, Figure, MetricCard, Report, TableBlock, TextBlock


def _render_text_block(text: str) -> str:
    escaped = escape(text)
    lines = [line.strip() for line in escaped.splitlines() if line.strip()]
    if len(lines) > 1 and lines[0].endswith(":") and all(line.startswith("• ") for line in lines[1:]):
        items = "".join(f"<li>{line[2:]}</li>" for line in lines[1:])
        return f"<p><strong>{lines[0]}</strong></p><ul>{items}</ul>"
    if lines and all(line.startswith("• ") for line in lines):
        return "<ul>" + "".join(f"<li>{line[2:]}</li>" for line in lines) + "</ul>"
    return f"<p>{escaped}</p>"


def _starts_pdf_segment(title: str) -> bool:
    return title.strip().lower() in {"evidence-backed claims", "visual contract", "source appendix"}


def _uses_side_segment(index: int, section: object) -> bool:
    if index < 2:
        return False
    if _starts_pdf_segment(section.title):  # type: ignore[attr-defined]
        return False
    return not any(isinstance(block, (TableBlock, Figure)) for block in section.blocks)  # type: ignore[attr-defined]

def render_html(report: Report) -> str:
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        f"<title>{escape(report.title)}</title>",
        "<style>"
        "@page{size:A4;margin:10mm}"
        ":root{--ink:#101828;--muted:#667085;--line:#d0d5dd;--violet:#7c3aed;--cyan:#0891b2;--green:#16a34a}"
        "*{box-sizing:border-box}body{font-family:Inter,system-ui,sans-serif;margin:0;color:var(--ink);background:#0f172a}"
        ".rf-underlay{position:fixed;inset:0;background:radial-gradient(circle at 12% 10%,#38bdf855,transparent 30%),radial-gradient(circle at 88% 4%,#a78bfa55,transparent 28%),linear-gradient(135deg,#0f172a 0%,#1e293b 42%,#f8fafc 42%,#f8fafc 100%);z-index:-1}"
        "main{max-width:1080px;margin:0 auto;background:#fffffff2;min-height:100vh;padding:28px 34px;border-left:1px solid #ffffff66;border-right:1px solid #ffffff66}"
        "header.cover{display:grid;grid-template-columns:1.6fr .8fr;gap:24px;align-items:end;border-bottom:3px solid var(--ink);padding:22px 0 18px;margin-bottom:16px}"
        "h1{font-size:40px;line-height:1.02;margin:0 0 8px}.subtitle{color:var(--muted);font-size:15px;line-height:1.35}.dateline{font-size:11px;color:#475467;text-transform:uppercase;letter-spacing:.08em}"
        ".section{break-inside:auto;margin:16px 0;padding:14px 0;border-top:1px solid #e4e7ec}.segment-page{break-before:page;page-break-before:always;break-inside:auto}.section h2{font-size:22px;line-height:1.1;margin:0 0 8px}"
        ".side-segment{display:grid;grid-template-columns:.34fr 1fr;gap:18px;align-items:start}.side-segment-start{break-before:page;page-break-before:always}.side-segment h2{font-size:18px}.side-segment .section-body{columns:2;column-gap:22px}"
        "p{font-size:12.5px;line-height:1.42;margin:0 0 8px}ul{margin:4px 0 8px 18px;padding:0}li{font-size:12.5px;line-height:1.38;margin:0 0 4px}"
        ".metric{display:inline-block;border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:6px;background:#f9fafb}.metric strong{font-size:24px;display:block}"
        ".claim{break-inside:avoid;border-left:4px solid var(--violet);padding:9px 12px;background:#f5f3ff;margin:10px 0;font-size:12px}.citation{font-size:10px;color:#475467;margin-top:6px}.source-url{font-size:9px;word-break:break-all;color:#2563eb}"
        ".figure{break-inside:avoid;border:1px solid #98a2b3;border-radius:16px;padding:12px;margin:12px 0;background:linear-gradient(180deg,#ffffff,#f8fafc);color:#475467}.figure img{max-width:100%;border-radius:10px;border:1px solid var(--line)}"
        "table{border-collapse:collapse;width:100%;margin:10px 0;font-size:9px}td,th{border:1px solid var(--line);padding:5px;text-align:left;vertical-align:top}th{background:#eef2ff}</style></head><body><div class='rf-underlay'></div><main><header class='cover'><div>",
        f"<h1>{escape(report.title)}</h1>",
    ]
    if report.subtitle:
        parts.append(f"<p class='subtitle'>{escape(report.subtitle)}</p>")
    parts.append("</div><aside>")
    parts.append(f"<p class='dateline'>Generated {escape(report.report_date)}</p><p class='subtitle'>{escape(report.author)}</p>")
    parts.append("</aside></header>")
    side_segment_started = False
    for index, section in enumerate(report.sections):
        if _starts_pdf_segment(section.title):
            section_class = "section segment-page"
        elif _uses_side_segment(index, section):
            section_class = "section side-segment"
            if not side_segment_started:
                section_class += " side-segment-start"
            side_segment_started = True
        else:
            section_class = "section"

        parts.append(f"<section class='{section_class}'><h2>{escape(section.title)}</h2><div class='section-body'>")
        if section.kicker:
            parts.append(f"<p class='subtitle'>{escape(section.kicker)}</p>")
        for block in section.blocks:
            if isinstance(block, TextBlock):
                parts.append(_render_text_block(block.text))
            elif isinstance(block, MetricCard):
                parts.append(f"<div class='metric'><span>{escape(block.label)}</span><strong>{escape(block.value)}</strong><small>{escape(block.note or '')}</small></div>")
            elif isinstance(block, Claim):
                parts.append(f"<div class='claim'><strong>Claim:</strong> {escape(block.text)}")
                for c in block.citations:
                    label = escape(c.title or c.source_id)
                    url = escape(c.url or "")
                    quote = escape(c.quote or "")
                    locator = escape(c.locator or "")
                    link = f"<a href='{url}'>{label}</a><div class='source-url'>{url}</div>" if url else label
                    parts.append(f"<div class='citation'>{link}<div>{quote}</div><div>Evidence: {locator}</div></div>")
                parts.append("</div>")
            elif isinstance(block, Figure):
                image = f"<img src='{escape(block.path)}' alt='{escape(block.alt_text or block.title)}' style='max-width:100%;border-radius:12px;border:1px solid #d0d5dd'>" if block.path else ""
                parts.append(f"<figure class='figure'><strong>{escape(block.title)}</strong>{image}<figcaption>{escape(block.caption or block.alt_text or '')}</figcaption></figure>")
            elif isinstance(block, TableBlock):
                parts.append("<table><thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in block.headers) + "</tr></thead><tbody>")
                for row in block.rows:
                    parts.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>")
                parts.append("</tbody></table>")
        parts.append("</div></section>")
    parts.append("</main></body></html>")
    return "".join(parts)


def render_html_pdf_with_chromium(html_path: str | Path, output_path: str | Path) -> Path:
    """Render an HTML/CSS report to PDF using Chromium's print engine.

    This is the software-backed foundry path: the report/spec becomes HTML/CSS,
    then a browser layout engine paginates and prints it. No LLM page drawing.
    """

    html_path = Path(html_path).resolve()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1240, "height": 1754}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    return output_path


def render_pdf(report: Report, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Kicker", parent=styles["BodyText"], textColor=colors.HexColor("#667085"), fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="Claim", parent=styles["BodyText"], borderColor=colors.HexColor("#7c3aed"), borderWidth=1, borderPadding=8, backColor=colors.HexColor("#f5f3ff"), leading=15))
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm, title=report.title, author=report.author)
    story = [Paragraph(report.title, styles["Title"])]
    if report.subtitle:
        story += [Paragraph(report.subtitle, styles["Kicker"])]
    story += [Paragraph(f"Generated {report.report_date} by {report.author}", styles["Kicker"]), Spacer(1, 10*mm)]
    for index, section in enumerate(report.sections):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(section.title, styles["Heading1"]))
        if section.kicker:
            story.append(Paragraph(section.kicker, styles["Kicker"]))
        for block in section.blocks:
            if isinstance(block, TextBlock):
                story += [Paragraph(block.text, styles["BodyText"]), Spacer(1, 4*mm)]
            elif isinstance(block, MetricCard):
                story += [Paragraph(f"<b>{block.label}</b>: {block.value} — {block.note or ''}", styles["BodyText"]), Spacer(1, 3*mm)]
            elif isinstance(block, Claim):
                citation_text = " ".join(f"[{c.source_id}] {c.quote or c.url or ''}" for c in block.citations)
                story += [Paragraph(f"<b>Claim:</b> {block.text}<br/><font size='8'>{citation_text}</font>", styles["Claim"]), Spacer(1, 4*mm)]
            elif isinstance(block, Figure):
                story += [Paragraph(f"<b>{block.title}</b><br/>{block.caption or block.alt_text or ''}", styles["BodyText"]), Spacer(1, 4*mm)]
            elif isinstance(block, TableBlock):
                table = Table([block.headers] + block.rows, hAlign="LEFT")
                table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d5dd")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                story += [table, Spacer(1, 4*mm)]
    doc.build(story)
    return output_path
