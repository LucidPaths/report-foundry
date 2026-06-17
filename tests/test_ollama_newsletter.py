from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ollama_daily_newsletter.py"
spec = importlib.util.spec_from_file_location("ollama_daily_newsletter", MODULE_PATH)
newsletter = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(newsletter)


def test_sanitize_external_text_redacts_secret_shapes() -> None:
    text = "token=abc123 Bearer abc.def.ghi sk-example"
    sanitized = newsletter.sanitize_external_text(text)
    assert "abc123" not in sanitized
    assert "abc.def.ghi" not in sanitized
    assert "sk-example" not in sanitized
    assert "[REDACTED]" in sanitized


def test_build_report_writes_valid_report_without_network(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(newsletter, "live_model_ids", lambda: ["glm-5.2", "kimi-k2.7-code"])
    monkeypatch.setattr(newsletter, "ollama_chat", lambda model, prompt: f"Generated notes for {model}")

    out_json = tmp_path / "report.json"
    discord_md = tmp_path / "discord.md"
    report = newsletter.build_report(out_json, discord_md)

    assert report["title"].startswith("Ollama Cloud Field Brief")
    assert len(report["sections"]) == 3
    assert out_json.exists()
    assert discord_md.exists()
    assert "Generated notes for glm-5.2" in discord_md.read_text(encoding="utf-8")
