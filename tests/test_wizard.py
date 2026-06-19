"""Wizard front-door tests for Report Foundry research intake.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from report_foundry.cli import app

runner = CliRunner()


def test_wizard_prompts_for_topic_and_writes_research_gate_package(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["wizard", "--out-dir", str(tmp_path / "run")],
        input="QUIC protocol portfolio\nCTO readers\nUse primary standards sources only\n",
    )

    assert result.exit_code == 0, result.output
    assert "research gate" in result.output.lower()
    assert "compile-intake" in result.output

    request_path = tmp_path / "run" / "research_request.json"
    prompt_path = tmp_path / "run" / "research_gate_prompt.md"
    intake_path = tmp_path / "run" / "research_intake.json"
    assert request_path.exists()
    assert prompt_path.exists()
    assert intake_path.exists()

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request == {
        "keyword": "QUIC protocol portfolio",
        "audience": "CTO readers",
        "task": "deep_research_report",
        "constraints": ["Use primary standards sources only"],
    }

    prompt = prompt_path.read_text(encoding="utf-8")
    assert "You are entering Report Foundry" in prompt
    assert "Return only valid JSON" in prompt
    assert "ResearchIntake" in prompt
    assert "QUIC protocol portfolio" in prompt
    assert "Do not invent sources" in prompt

    intake_stub = intake_path.read_text(encoding="utf-8")
    assert "PASTE_RESEARCH_INTAKE_JSON_HERE" in intake_stub


def test_wizard_accepts_topic_options_without_interactive_prompt(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "wizard",
            "--topic",
            "AI datacenter power constraints",
            "--audience",
            "infrastructure investors",
            "--constraint",
            "Prefer regulator and grid-operator sources",
            "--out-dir",
            str(tmp_path / "run"),
        ],
    )

    assert result.exit_code == 0, result.output
    request = json.loads((tmp_path / "run" / "research_request.json").read_text(encoding="utf-8"))
    assert request["keyword"] == "AI datacenter power constraints"
    assert request["audience"] == "infrastructure investors"
    assert request["constraints"] == ["Prefer regulator and grid-operator sources"]
