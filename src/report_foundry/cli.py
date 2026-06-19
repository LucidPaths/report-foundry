"""CLI surfaces for planning, fixture research, validation, and rendering.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import typer
from pydantic import ValidationError
from rich import print

from .adequacy import run_artifact_qa, run_research_adequacy_gates
from .draft import parse_markdown_draft_file
from .factory import RunMode, write_run_package
from .ir import Report
from .evidence import EvidencePack
from .qa import run_quality_gates
from .research import write_research_artifacts
from .research_intake import IntakeValidationError, ResearchIntake, ResearchRequest, build_research_intake_system_prompt, research_intake_to_evidence_pack
from .render import render_html, render_pdf
from .renderers import RendererRouteError
from .report_spec import write_spec_artifacts
from .json_repair import JsonRepairError, build_json_repair_prompt, normalize_research_intake_ids, parse_or_repair_json_object
from .run_log import FoundryRunLog, utc_now
from .samples import write_oss_strategy_report

app = typer.Typer(help="AI-native evidence-to-PDF report compiler.")


@app.command("wizard")
def wizard(
    topic: str | None = typer.Option(None, "--topic", "-t", help="Research topic/request. Prompted when omitted."),
    audience: str | None = typer.Option(None, "--audience", "-a", help="Target reader. Prompted when omitted."),
    constraint: list[str] = typer.Option(default_factory=list, show_default=False, help="Research/source/output constraint. Repeatable."),
    out_dir: Path = typer.Option(Path(".foundry_wizard"), help="Directory for the research gate package."),
) -> None:
    """Open the research gate: collect a topic and write the LLM intake package."""
    if topic is None:
        topic = typer.prompt("Research topic")
    if audience is None:
        audience = typer.prompt("Audience", default="executive readers")
    if not constraint:
        entered_constraint = typer.prompt("Research constraint", default="Use concrete observed sources; do not invent evidence")
        constraint = [entered_constraint] if entered_constraint.strip() else []

    request = ResearchRequest(
        user_request=topic,
        topic=topic,
        core_question=topic,
        audience=audience,
        intended_use="professional evidence-backed report",
        depth="deep_research_report",
        format_preferences=["pdf"],
        explicit_constraints=constraint,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    request_path = out_dir / "research_request.json"
    prompt_path = out_dir / "research_gate_prompt.md"
    intake_path = out_dir / "research_intake.json"

    request_json = json.dumps(request.model_dump(), indent=2)
    request_path.write_text(request_json + "\n", encoding="utf-8")
    prompt_path.write_text(_research_gate_prompt(request_json), encoding="utf-8")
    intake_path.write_text("PASTE_RESEARCH_INTAKE_JSON_HERE\n", encoding="utf-8")

    print(f"[green]research gate[/green] {out_dir}")
    print(f"[green]request[/green] {request_path}")
    print(f"[green]llm prompt[/green] {prompt_path}")
    print(f"[green]intake target[/green] {intake_path}")
    print("next: give research_gate_prompt.md to the research LLM, save JSON to research_intake.json, then run:")
    print(f"uv run reportfoundry compile-intake {intake_path} --out-dir {out_dir / 'compiled'}")


def _research_gate_prompt(request_json: str) -> str:
    return f"""# Report Foundry research gate

You are entering Report Foundry. This CLI door is a research gate, not a casual chat prompt.

Operator request:
```json
{request_json}
```

To pass through this door:
- research the operator request using concrete observed sources;
- Do not invent sources, quotes, URLs, facts, claims, or citations;
- write the full report inside the ResearchIntake JSON schema;
- every claim must reference supporting fact IDs;
- every fact must reference an observed source and quote/excerpt;
- return only valid JSON matching the schema below.

{build_research_intake_system_prompt()}
"""


@app.command("plan-run")
def plan_run(
    topic: str,
    audience: str = "executive readers",
    out_dir: Path = Path(".factory-run"),
    integration_mode: str = "cli",
    source: list[str] = typer.Option(default_factory=list, help="Connected source namespace, MCP tool, database, or web connector."),
    run_mode: RunMode = typer.Option(RunMode.FIXTURE, help="Artifact governance mode: fixture, product, or experiment."),
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
        run_mode=run_mode,
    )
    print(f"[green]factory run package[/green] {package.run_dir}")
    print(f"mode={package.manifest.run_mode.value}")
    print(f"route_back={package.initial_gate_result.route_back_department or 'none'} score={package.initial_gate_result.score}")


@app.command("research-run")
def research_run(
    run_dir: Path,
    source_dir: Path = typer.Option(..., help="Directory containing .md/.txt marked source files."),
    allow_fixture_sources: bool = typer.Option(False, help="Allow local marked sources even when manifest.run_mode is product."),
) -> None:
    """Fixture adapter: extract evidence from local marked sources."""
    try:
        result = write_research_artifacts(run_dir=run_dir, source_dir=source_dir, allow_fixture_sources=allow_fixture_sources)
    except ValueError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    print(f"[green]research evidence[/green] {run_dir / 'evidence_pack.json'}")
    print(f"mode={result.manifest.run_mode.value}")
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
    print(f"[green]package manifest[/green] {paths['package_manifest']}")
    print(f"[green]layout metrics[/green] {paths['layout_metrics']}")
    print(f"[green]page previews[/green] {paths['page_previews']}")


@app.command("compile-spec")
def compile_spec(input: Path, out_dir: Path = Path(".output_spec"), route: str = typer.Option("playwright_chromium", help="Renderer route: playwright_chromium, typst, or pandoc.")) -> None:
    """Compile an EvidencePack into strict ReportSpec, IR, HTML, and PDF artifacts."""
    pack = EvidencePack.model_validate_json(input.read_text(encoding="utf-8"))
    try:
        paths = write_spec_artifacts(pack, out_dir, stem=input.stem, route=route)
    except RendererRouteError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]route[/green]={route}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]package manifest[/green] {paths['package_manifest']}")


@app.command("research-intake-prompt")
def research_intake_prompt(output: Path = typer.Option(..., help="Path to write the strict research-intake system prompt.")) -> None:
    """Write the schema-only LLM researcher prompt used before EvidencePack normalization."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_research_intake_system_prompt(), encoding="utf-8")
    print(f"[green]research intake prompt[/green] {output}")


@app.command("compile-intake")
def compile_intake(input: Path, out_dir: Path = Path(".output_intake"), route: str = typer.Option("playwright_chromium", help="Renderer route: playwright_chromium, typst, pandoc, weasyprint, kaleido, or csl.")) -> None:
    """Compile strict LLM ResearchIntake JSON into EvidencePack, ReportSpec, and package artifacts."""
    run_log = FoundryRunLog(run_id=out_dir.name or input.stem, topic=None, started_at=utc_now())
    try:
        evidence_path, paths = _compile_intake_to_artifacts(input, out_dir, route=route, run_log=run_log)
    except (IntakeValidationError, ValidationError, ValueError) as exc:
        run_log.finish(status="failed", error=str(exc))
        run_log.write(out_dir / "run_log.json")
        print(f"[red]invalid research intake[/red]: {exc}")
        raise typer.Exit(1) from exc
    except RendererRouteError as exc:
        run_log.finish(status="failed", error=str(exc))
        run_log.write(out_dir / "run_log.json")
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    run_log.artifacts.update(_artifact_strings(paths, extra={"evidence_pack": evidence_path}))
    run_log.add_step("final_handoff", details={"pdf": str(paths["pdf"]), "package_manifest": str(paths["package_manifest"])})
    run_log.finish(status="success", pdf=str(paths["pdf"]), package_manifest=str(paths["package_manifest"]))
    run_log.write(out_dir / "run_log.json")
    _print_final_handoff(paths, run_log_path=out_dir / "run_log.json")


@app.command("glm-run")
def glm_run(
    topic: str = typer.Option(..., "--topic", "-t", help="Keyword/topic for the E2E GLM-style run."),
    out_dir: Path = typer.Option(Path(".foundry_runs/glm"), help="Run directory."),
    audience: str = typer.Option("executive readers", help="Target reader."),
    constraint: list[str] = typer.Option(default_factory=list, show_default=False, help="Research/source/output constraint. Repeatable."),
    model: str = typer.Option("glm-5.2", help="Model label recorded in the run log."),
    intake_json: Path | None = typer.Option(None, help="Existing ResearchIntake JSON for deterministic E2E smoke runs."),
    ollama_base_url: str = typer.Option("https://ollama.com/v1", help="OpenAI-compatible Ollama base URL."),
    max_repair_attempts: int = typer.Option(1, help="JSON repair attempts after malformed model output."),
    route: str = typer.Option("playwright_chromium", help="Renderer route."),
) -> None:
    """One-command keyword -> gate -> ResearchIntake -> PDF/package loop.

    The deterministic path accepts --intake-json for CI/local E2E testing. Live
    execution calls the configured Ollama-compatible GLM endpoint, validates the
    model JSON, retries through the repair prompt when needed, then compiles and
    verifies the artifact package.
    """
    run_log = FoundryRunLog(run_id=out_dir.name or "glm-run", topic=topic, model=model, started_at=utc_now())
    gate_dir = out_dir / "gate"
    compiled_dir = out_dir / "compiled"
    gate_started, gate_perf = utc_now(), perf_counter()
    gate_dir.mkdir(parents=True, exist_ok=True)
    request = ResearchRequest(
        user_request=topic,
        topic=topic,
        core_question=topic,
        audience=audience,
        intended_use="professional evidence-backed report",
        depth="deep_research_report",
        format_preferences=["pdf"],
        explicit_constraints=constraint or ["Use concrete observed sources; do not invent evidence"],
    )
    request_json = json.dumps(request.model_dump(), indent=2)
    (gate_dir / "research_request.json").write_text(request_json + "\n", encoding="utf-8")
    (gate_dir / "research_gate_prompt.md").write_text(_research_gate_prompt(request_json), encoding="utf-8")
    run_log.add_step("create_research_gate", started_at=gate_started, started_perf=gate_perf, details={"request": str(gate_dir / "research_request.json"), "prompt": str(gate_dir / "research_gate_prompt.md")})

    intake_path = gate_dir / "research_intake.json"
    if intake_json is None:
        try:
            _call_model_until_valid_intake(
                prompt_path=gate_dir / "research_gate_prompt.md",
                output_path=intake_path,
                run_log=run_log,
                model=model,
                base_url=ollama_base_url,
                max_repair_attempts=max_repair_attempts,
            )
        except (RuntimeError, JsonRepairError, ValidationError, IntakeValidationError, ValueError) as exc:
            run_log.finish(status="failed", topic=topic, error=str(exc))
            run_log.write(out_dir / "run_log.json")
            print(f"[red]glm-run failed[/red]: {exc}")
            raise typer.Exit(1) from exc
    else:
        load_started, load_perf = utc_now(), perf_counter()
        shutil.copyfile(intake_json, intake_path)
        run_log.add_step("load_seed_intake", started_at=load_started, started_perf=load_perf, details={"source": str(intake_json), "target": str(intake_path)})

    try:
        evidence_path, paths = _compile_intake_to_artifacts(intake_path, compiled_dir, route=route, run_log=run_log)
    except (IntakeValidationError, ValidationError, ValueError, RendererRouteError) as exc:
        run_log.finish(status="failed", topic=topic, error=str(exc))
        run_log.write(out_dir / "run_log.json")
        print(f"[red]glm-run failed[/red]: {exc}")
        raise typer.Exit(1) from exc

    verify_started, verify_perf = utc_now(), perf_counter()
    missing = [name for name in ("pdf", "html", "package_manifest") if not Path(paths[name]).exists()]
    if missing:
        run_log.add_step("verify_artifacts", status="error", started_at=verify_started, started_perf=verify_perf, details={"missing": missing})
        run_log.finish(status="failed", topic=topic, missing=missing)
        run_log.write(out_dir / "run_log.json")
        raise typer.Exit(1)
    run_log.add_step("verify_artifacts", started_at=verify_started, started_perf=verify_perf, details={"pdf": str(paths["pdf"]), "html": str(paths["html"])})
    run_log.artifacts.update(_artifact_strings(paths, extra={"evidence_pack": evidence_path, "research_intake": intake_path, "prompt": gate_dir / "research_gate_prompt.md"}))
    run_log.add_step("final_handoff", details={"pdf": str(paths["pdf"]), "package_manifest": str(paths["package_manifest"])})
    run_log.finish(status="success", topic=topic, pdf=str(paths["pdf"]), package_manifest=str(paths["package_manifest"]))
    run_log.write(out_dir / "run_log.json")
    _print_final_handoff(paths, run_log_path=out_dir / "run_log.json")


def _call_model_until_valid_intake(*, prompt_path: Path, output_path: Path, run_log: FoundryRunLog, model: str, base_url: str, max_repair_attempts: int) -> ResearchIntake:
    prompt = prompt_path.read_text(encoding="utf-8")
    schema = json.dumps(ResearchIntake.model_json_schema(), indent=2, sort_keys=True)
    attempts = max(0, max_repair_attempts) + 1
    last_error = ""
    last_output = ""
    for attempt in range(1, attempts + 1):
        step_name = "call_glm_model" if attempt == 1 else "repair_json"
        started, perf = utc_now(), perf_counter()
        active_prompt = prompt if attempt == 1 else build_json_repair_prompt(schema=schema, invalid_output=last_output, error=last_error)
        try:
            last_output = _ollama_chat_json(model=model, base_url=base_url, prompt=active_prompt)
            data = normalize_research_intake_ids(parse_or_repair_json_object(last_output))
            intake = ResearchIntake.model_validate(data)
            output_path.write_text(intake.model_dump_json(indent=2), encoding="utf-8")
            run_log.add_step(step_name, started_at=started, started_perf=perf, details={"attempt": attempt, "model": model, "output": str(output_path)})
            return intake
        except (RuntimeError, JsonRepairError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            attempt_path = output_path.with_name(f"{output_path.stem}.attempt_{attempt}.txt")
            attempt_path.write_text(last_output or last_error, encoding="utf-8")
            status = "error" if attempt == attempts else "ok"
            run_log.add_step(step_name, status=status, started_at=started, started_perf=perf, message=last_error, details={"attempt": attempt, "saved_output": str(attempt_path)})
    raise JsonRepairError(last_error or "model did not produce valid ResearchIntake JSON")


def _ollama_chat_json(*, model: str, base_url: str, prompt: str) -> str:
    endpoint = _validated_ollama_chat_endpoint(base_url)
    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEY is required for live glm-run; use --intake-json for deterministic E2E")
    payload = json.dumps({"model": model, "messages": [{"role": "system", "content": prompt}], "temperature": 0, "response_format": {"type": "json_object"}}).encode("utf-8")
    request = Request(endpoint, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=600) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Ollama model call failed: {exc}") from exc
    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama model response did not match chat completion shape") from exc
    if not isinstance(content, str):
        raise RuntimeError("Ollama model response content was not text")
    return content


def _validated_ollama_chat_endpoint(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("ollama base URL must be http(s) with a host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("ollama base URL must not include credentials, query, or fragment")
    localhost = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not localhost:
        raise RuntimeError("ollama base URL must use https unless it targets localhost")
    return base_url.rstrip("/") + "/chat/completions"


def _compile_intake_to_artifacts(input: Path, out_dir: Path, *, route: str, run_log: FoundryRunLog) -> tuple[Path, dict[str, Path]]:
    validate_started, validate_perf = utc_now(), perf_counter()
    intake = ResearchIntake.model_validate_json(input.read_text(encoding="utf-8"))
    pack = research_intake_to_evidence_pack(intake)
    adequacy = run_research_adequacy_gates(intake)
    run_log.topic = run_log.topic or intake.request.topic
    run_log.add_step(
        "validate_intake",
        started_at=validate_started,
        started_perf=validate_perf,
        details={
            "sources": len(intake.sources),
            "facts": len(intake.facts),
            "claims": len(intake.proposed_claims),
            "sections": len(intake.report.sections),
            "exhibits": len(intake.exhibits),
            "adequacy_checks": [check.model_dump() for check in adequacy.checks],
        },
    )

    compile_started, compile_perf = utc_now(), perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = out_dir / f"{input.stem}.evidence.json"
    evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    paths = write_spec_artifacts(pack, out_dir, stem=input.stem, route=route)
    artifact_qa = run_artifact_qa(paths)
    run_log.add_step(
        "compile_artifacts",
        started_at=compile_started,
        started_perf=compile_perf,
        details={"route": route, "pdf": str(paths["pdf"]), "html": str(paths["html"]), "package_manifest": str(paths["package_manifest"]), "artifact_qa_checks": [check.model_dump() for check in artifact_qa.checks]},
    )
    if not artifact_qa.ok:
        raise ValueError("artifact QA failed: " + ", ".join(check.code for check in artifact_qa.checks if check.severity == "error"))
    return evidence_path, paths


def _artifact_strings(paths: dict[str, Path], *, extra: dict[str, Path] | None = None) -> dict[str, str]:
    all_paths = {**paths, **(extra or {})}
    return {name: str(path) for name, path in all_paths.items()}


def _print_final_handoff(paths: dict[str, Path], *, run_log_path: Path) -> None:
    print("[green]Here is your PDF[/green]")
    print(f"research intake: compiled")
    print(f"pdf: {paths['pdf']}")
    print(f"html: {paths['html']}")
    print(f"package manifest: {paths['package_manifest']}")
    print(f"run log: {run_log_path}")


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
    print(f"[green]package manifest[/green] {paths['package_manifest']}")
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
