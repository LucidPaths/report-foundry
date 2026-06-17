from __future__ import annotations

import importlib.util
import json
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


def test_evidence_pack_contains_promised_contract(monkeypatch) -> None:
    monkeypatch.setattr(newsletter, "live_model_ids", lambda: ["glm-5.2", "kimi-k2.7-code"])
    monkeypatch.setattr(newsletter, "ollama_chat", lambda model, prompt: f"- bounded note for {model}\n- tested route for {model}")

    pack = newsletter.build_evidence_pack()

    assert pack["scope"]["question"].startswith("Which new Ollama Cloud models")
    assert len(pack["toolchain"]) >= 8
    assert pack["layout_contract"]["llm_role"] == "bounded commentary only"
    assert "renderer_role" in pack["layout_contract"]
    assert pack["live_check"]["models_found"] == ["glm-5.2", "kimi-k2.7-code"]
    for model in ["glm-5.2", "kimi-k2.7-code"]:
        assert pack["models"][model]["benchmarks"]
        assert pack["models"][model]["recommendation"]
        assert pack["llm_notes"][model].startswith("- bounded note")


def test_enforce_bounded_note_strips_model_reasoning() -> None:
    raw = """
The user wants exactly two concise newsletter bullets. Let me count words carefully.

- glm-5.2 is live on Ollama Cloud with 1M context and AA Intelligence Index 51.
- Hermes should route glm-5.2 to long-context synthesis and report drafting.

Word count looks fine.
"""
    note = newsletter.enforce_bounded_note("glm-5.2", newsletter.MODEL_EVIDENCE["glm-5.2"], raw)

    assert note.startswith("- glm-5.2 is live")
    assert "The user wants" not in note
    assert "Let me" not in note
    assert "Word count" not in note
    assert len(note.splitlines()) == 2


def test_build_artifacts_writes_structured_outputs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(newsletter, "live_model_ids", lambda: ["glm-5.2", "kimi-k2.7-code"])
    monkeypatch.setattr(newsletter, "ollama_chat", lambda model, prompt: f"- bounded note for {model}\n- tested route for {model}")

    paths = newsletter.build_artifacts(tmp_path)

    assert set(paths) == {"evidence", "ir", "html", "pdf", "discord"}
    for path in paths.values():
        assert path.exists(), path
        assert path.stat().st_size > 0, path

    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))
    html = paths["html"].read_text(encoding="utf-8")
    discord = paths["discord"].read_text(encoding="utf-8")

    assert evidence["layout_contract"]["llm_role"] == "bounded commentary only"
    assert "Tools represented" in html
    assert "model cards with benchmark bars" in discord
    assert "MEDIA:" in discord
    assert paths["pdf"].stat().st_size > 8_000
