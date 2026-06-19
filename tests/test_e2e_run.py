"""One-command E2E run and artifact-log tests.

Lattice: RF-P1 Source Sovereignty; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pytest
from typer.testing import CliRunner

from report_foundry.adequacy import run_research_adequacy_gates
from report_foundry.cli import _validated_ollama_chat_endpoint, app
from report_foundry.json_repair import normalize_research_intake_ids, parse_or_repair_json_object
from report_foundry.research_intake import ResearchIntake
from report_foundry.source_extract import _validate_fetch_url, fetch_readable_text, readable_text_from_html

runner = CliRunner()


def valid_intake_payload() -> dict[str, object]:
    source_path = Path(__file__).with_name("test_research_intake.py")
    spec = importlib.util.spec_from_file_location("test_research_intake_helpers", source_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.valid_intake_payload()


def write_valid_intake(path: Path) -> Path:
    path.write_text(json.dumps(valid_intake_payload(), indent=2), encoding="utf-8")
    return path


def test_compile_intake_prints_clean_pdf_handoff_and_writes_run_log(tmp_path: Path) -> None:
    intake_path = write_valid_intake(tmp_path / "research_intake.json")
    out_dir = tmp_path / "compiled"

    result = runner.invoke(app, ["compile-intake", str(intake_path), "--out-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "Here is your PDF" in result.output
    assert "package manifest" in result.output
    assert (out_dir / "research_intake.pdf").exists()
    run_log = json.loads((out_dir / "run_log.json").read_text(encoding="utf-8"))
    assert [step["name"] for step in run_log["steps"]] == ["validate_intake", "compile_artifacts", "final_handoff"]
    assert all(step["status"] == "ok" for step in run_log["steps"])
    assert run_log["artifacts"]["pdf"].endswith("research_intake.pdf")
    assert run_log["summary"]["status"] == "success"


def test_glm_run_can_execute_one_command_from_existing_intake_fixture(tmp_path: Path) -> None:
    intake_path = write_valid_intake(tmp_path / "seed_intake.json")
    run_dir = tmp_path / "run"

    result = runner.invoke(
        app,
        [
            "glm-run",
            "--topic",
            "nvidia company history",
            "--intake-json",
            str(intake_path),
            "--out-dir",
            str(run_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Here is your PDF" in result.output
    assert (run_dir / "gate" / "research_gate_prompt.md").exists()
    assert (run_dir / "gate" / "research_intake.json").exists()
    assert (run_dir / "compiled" / "research_intake.pdf").exists()
    run_log = json.loads((run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert [step["name"] for step in run_log["steps"]] == [
        "create_research_gate",
        "load_seed_intake",
        "validate_intake",
        "compile_artifacts",
        "verify_artifacts",
        "final_handoff",
    ]
    assert run_log["summary"]["topic"] == "nvidia company history"
    assert run_log["artifacts"]["pdf"].endswith("research_intake.pdf")


def test_readable_html_extractor_removes_script_noise_and_preserves_body_text() -> None:
    html = """
    <html><head><style>.x{display:none}</style><script>window.noise = 'bad';</script></head>
    <body><nav>Products</nav><main><h1>NVIDIA history</h1><p>NVIDIA was founded in 1993.</p></main></body></html>
    """

    text = readable_text_from_html(html)

    assert "NVIDIA history" in text
    assert "NVIDIA was founded in 1993." in text
    assert "window.noise" not in text
    assert "display:none" not in text


def test_json_repair_extracts_object_from_fenced_model_output() -> None:
    payload = parse_or_repair_json_object('```json\n{"ok": true,}\n```')

    assert payload == {"ok": True}


def test_json_repair_normalizes_uppercase_model_ids_and_references() -> None:
    payload = {
        "sources": [{"id": "S1"}],
        "facts": [{"id": "F1", "source_id": "S1"}],
        "proposed_claims": [{"id": "C1", "supporting_fact_ids": ["F1"]}],
        "report": {"sections": [{"id": "SEC1", "referenced_claim_ids": ["C1"], "referenced_fact_ids": ["F1"]}]},
    }

    normalized = normalize_research_intake_ids(payload)

    assert normalized["sources"][0]["id"] == "s1"
    assert normalized["facts"][0]["source_id"] == "s1"
    assert normalized["proposed_claims"][0]["supporting_fact_ids"] == ["f1"]
    assert normalized["report"]["sections"][0]["referenced_claim_ids"] == ["c1"]


def test_source_fetch_url_validation_blocks_local_and_non_http_targets() -> None:
    with pytest.raises(ValueError, match="http or https"):
        _validate_fetch_url("file:///etc/passwd")
    with pytest.raises(ValueError, match="non-public"):
        _validate_fetch_url("http://127.0.0.1/metadata")
    with pytest.raises(ValueError, match="non-public"):
        _validate_fetch_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(RuntimeError, match="connector policy"):
        fetch_readable_text("https://example.com/source")


def test_ollama_endpoint_validation_requires_https_except_localhost() -> None:
    assert _validated_ollama_chat_endpoint("https://ollama.com/v1") == "https://ollama.com/v1/chat/completions"
    assert _validated_ollama_chat_endpoint("http://localhost:11434/v1") == "http://localhost:11434/v1/chat/completions"
    with pytest.raises(RuntimeError, match="https"):
        _validated_ollama_chat_endpoint("http://ollama.com/v1")
    with pytest.raises(RuntimeError, match="credentials"):
        _validated_ollama_chat_endpoint("https://user:pass@ollama.com/v1?x=1")


def test_adequacy_gates_log_thin_research_without_breaking_structural_validation() -> None:
    intake = ResearchIntake.model_validate(valid_intake_payload())

    result = run_research_adequacy_gates(intake)

    assert result.ok is True
    assert any(check.code == "low_source_count" for check in result.checks)
