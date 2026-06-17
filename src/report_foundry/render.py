from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .ir import Claim, Figure, MetricCard, Report, TableBlock, TextBlock


def render_html(report: Report) -> str:
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        f"<title>{escape(report.title)}</title>",
        "<style>body{font-family:Inter,system-ui,sans-serif;margin:48px;color:#101828;background:#f8fafc}"
        "main{max-width:900px;margin:auto;background:white;padding:48px;border-radius:24px;box-shadow:0 20px 60px #0001}"
        "h1{font-size:42px;margin-bottom:4px}.subtitle{color:#667085;font-size:18px}.section{page-break-before:always;margin-top:48px}"
        ".metric{display:inline-block;border:1px solid #d0d5dd;border-radius:16px;padding:16px 20px;margin:8px;background:#f9fafb}"
        ".metric strong{font-size:28px;display:block}.claim{border-left:4px solid #7c3aed;padding:12px 16px;background:#f5f3ff;margin:16px 0}"
        ".citation{font-size:12px;color:#475467}.figure{border:1px dashed #98a2b3;border-radius:16px;padding:18px;margin:18px 0;color:#475467}"
        "table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #d0d5dd;padding:8px;text-align:left}</style></head><body><main>",
        f"<h1>{escape(report.title)}</h1>",
    ]
    if report.subtitle:
        parts.append(f"<p class='subtitle'>{escape(report.subtitle)}</p>")
    parts.append(f"<p class='citation'>Generated {escape(report.report_date)} by {escape(report.author)}</p>")
    for section in report.sections:
        parts.append(f"<section class='section'><h2>{escape(section.title)}</h2>")
        if section.kicker:
            parts.append(f"<p class='subtitle'>{escape(section.kicker)}</p>")
        for block in section.blocks:
            if isinstance(block, TextBlock):
                parts.append(f"<p>{escape(block.text)}</p>")
            elif isinstance(block, MetricCard):
                parts.append(f"<div class='metric'><span>{escape(block.label)}</span><strong>{escape(block.value)}</strong><small>{escape(block.note or '')}</small></div>")
            elif isinstance(block, Claim):
                parts.append(f"<div class='claim'><strong>Claim:</strong> {escape(block.text)}")
                for c in block.citations:
                    label = escape(c.title or c.source_id)
                    url = escape(c.url or "")
                    quote = escape(c.quote or "")
                    parts.append(f"<div class='citation'><a href='{url}'>{label}</a> — {quote}</div>")
                parts.append("</div>")
            elif isinstance(block, Figure):
                parts.append(f"<figure class='figure'><strong>{escape(block.title)}</strong><figcaption>{escape(block.caption or block.alt_text or '')}</figcaption></figure>")
            elif isinstance(block, TableBlock):
                parts.append("<table><thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in block.headers) + "</tr></thead><tbody>")
                for row in block.rows:
                    parts.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>")
                parts.append("</tbody></table>")
        parts.append("</section>")
    parts.append("</main></body></html>")
    return "".join(parts)


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
