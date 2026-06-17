from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from .ir import Report
from .qa import run_quality_gates
from .render import render_html, render_pdf

app = typer.Typer(help="AI-native evidence-to-PDF report compiler.")


@app.command()
def build(input: Path, out_dir: Path = Path(".output")) -> None:
    """Build HTML and PDF from a Report Foundry JSON report."""
    report = Report.model_validate_json(input.read_text(encoding="utf-8"))
    qa = run_quality_gates(report)
    if not qa.ok:
        for check in qa.checks:
            print(f"[red]{check.code}[/red]: {check.message} ({check.location})")
        raise typer.Exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{input.stem}.html"
    pdf_path = out_dir / f"{input.stem}.pdf"
    html_path.write_text(render_html(report), encoding="utf-8")
    render_pdf(report, pdf_path)
    print(f"[green]built[/green] {html_path}")
    print(f"[green]built[/green] {pdf_path}")


@app.command()
def validate(input: Path) -> None:
    """Run report-level quality gates against JSON IR."""
    report = Report.model_validate_json(input.read_text(encoding="utf-8"))
    result = run_quality_gates(report)
    for check in result.checks:
        color = "red" if check.severity == "error" else "yellow"
        print(f"[{color}]{check.severity} {check.code}[/{color}]: {check.message} {check.location or ''}")
    if not result.ok:
        raise typer.Exit(1)
    print("[green]ok[/green]")
