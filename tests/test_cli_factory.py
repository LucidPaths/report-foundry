from __future__ import annotations

import json

from typer.testing import CliRunner

from report_foundry.cli import app


runner = CliRunner()


def test_plan_run_cli_writes_factory_run_package(tmp_path) -> None:
    out_dir = tmp_path / "run"

    result = runner.invoke(
        app,
        [
            "plan-run",
            "current SpaceX IPO launch newsletter",
            "--audience",
            "executive readers",
            "--out-dir",
            str(out_dir),
            "--integration-mode",
            "mcp",
            "--source",
            "company-db",
            "--source",
            "web",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "factory run package" in result.output
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "source_plan.json").exists()
    assert (out_dir / "visual_plan.json").exists()

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    source_plan = json.loads((out_dir / "source_plan.json").read_text(encoding="utf-8"))
    visual_plan = json.loads((out_dir / "visual_plan.json").read_text(encoding="utf-8"))

    assert manifest["integration_mode"] == "mcp"
    assert "company-db" in manifest["connected_sources"]
    assert any(item["dimension"] == "starlink_economics" for item in source_plan["items"])
    assert any(item["visual_id"] == "business_segment_map" for item in visual_plan["items"])
