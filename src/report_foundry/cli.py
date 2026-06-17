"""CLI surfaces for planning, fixture research, validation, and rendering.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from .draft import parse_markdown_draft_file
from .factory import write_run_package
from .ir import Report
from .evidence import EvidencePack
from .qa import run_quality_gates
from .research import write_research_artifacts
from .render import render_html, render_pdf
from .report_spec import write_spec_artifacts
from .samples import write_oss_strategy_report

app = typer.Typer(help="AI-native evidence-to-PDF report compiler.")


@app.command("plan-run")
def plan_run(
    topic: str,
    audience: str = "executive readers",
    out_dir: Path = Path(".factory-run"),
    integration_mode: str = "cli",
    source: list[str] = typer.Option(default_factory=list, help="Connected source namespace, MCP tool, database, or web connector."),
) -> None:
    """Create a factory run package from a topic before research starts."""
    if integration_mode not in {"cli", "mcp", "server", "library"}:
        print(f"[red]invalid integration mode[/red]: {integration_mode}")
        raise typer.Exit(1)
    package = write_run_package(
        topic=topic,
        audience=audience,
        out_dir=out_dir,
        integration_mode=integration_mode,  # type: ignore[arg-type]
        connected_sources=source,
    )
    print(f"[green]factory run package[/green] {package.run_dir}")
    print(f"route_back={package.initial_gate_result.route_back_department or 'none'} score={package.initial_gate_result.score}")


@app.command("research-run")
def research_run(run_dir: Path, source_dir: Path = typer.Option(..., help="Directory containing .md/.txt marked source files.")) -> None:
    """Fixture adapter: extract evidence from local marked sources."""
    result = write_research_artifacts(run_dir=run_dir, source_dir=source_dir)
    print(f"[green]research evidence[/green] {run_dir / 'evidence_pack.json'}")
    print(f"route_back={result.gate_result.route_back_department or 'none'} score={result.gate_result.score}")
    if not result.gate_result.ok:
        raise typer.Exit(1)


@app.command("compile-draft")
def compile_draft(
    input: Path,
    out_dir: Path = Path(".output_draft"),
    author: str = typer.Option("Research LLM", help="Author label stored in the generated EvidencePack."),
) -> None:
    """Compile an LLM-authored Markdown draft into Foundry artifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pack = parse_markdown_draft_file(input, author=author)
    evidence_path = out_dir / f"{input.stem}.evidence.json"
    evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    paths = write_spec_artifacts(pack, out_dir, stem=input.stem)
    print(f"[green]evidence pack[/green] {evidence_path}")
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]layout metrics[/green] {paths['layout_metrics']}")
    print(f"[green]page previews[/green] {paths['page_previews']}")


@app.command("compile-spec")
def compile_spec(input: Path, out_dir: Path = Path(".output_spec")) -> None:
    """Compile an EvidencePack into strict ReportSpec, IR, HTML, and PDF artifacts."""
    pack = EvidencePack.model_validate_json(input.read_text(encoding="utf-8"))
    paths = write_spec_artifacts(pack, out_dir, stem=input.stem)
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")


@app.command("oss-strategy-report")
def oss_strategy_report(
    out_dir: Path = Path(".output_oss_strategy"),
    offline: bool = typer.Option(False, help="Use packaged repository metadata instead of live GitHub API calls."),
) -> None:
    """Build the canonical OSS strategy sample through the full foundry pipeline."""
    paths = write_oss_strategy_report(out_dir, offline=offline)
    print(f"[green]evidence pack[/green] {paths['evidence_pack']}")
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]layout metrics[/green] {paths['layout_metrics']}")
    print(f"[green]page previews[/green] {paths['page_previews']}")


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
