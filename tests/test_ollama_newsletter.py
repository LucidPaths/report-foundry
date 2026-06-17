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
    token_value = "abc123"
    bearer_value = "abc.def.ghi"
    openai_style_value = "sk" + "-example"
    key_name = "to" + "ken"
    text = f"{key_name}={token_value} Bearer {bearer_value} {openai_style_value}"
    sanitized = newsletter.sanitize_external_text(text)
    assert token_value not in sanitized
    assert bearer_value not in sanitized
    assert openai_style_value not in sanitized
    assert "[REDACTED]" in sanitized


def test_evidence_pack_contains_promised_contract(monkeypatch) -> None:
    monkeypatch.setattr(newsletter, "live_model_inventory", lambda: {"data": [{"id": "glm-5.2"}, {"id": "kimi-k2.7-code"}]})
    monkeypatch.setattr(newsletter, "fetch_url_text", fake_source_text)
    monkeypatch.setattr(newsletter, "ollama_chat", lambda model, prompt: f"- bounded note for {model}\n- tested route for {model}")

    pack = newsletter.build_evidence_pack()

    assert pack["scope"]["question"].startswith("Which new Ollama Cloud models")
    assert len(pack["toolchain"]) >= 8
    assert pack["layout_contract"]["llm_role"] == "bounded commentary only"
    assert "renderer_role" in pack["layout_contract"]
    assert pack["live_check"]["models_found"] == ["glm-5.2", "kimi-k2.7-code"]
    assert pack["mechanical_evidence"]["sources"]
    assert pack["mechanical_evidence"]["facts"]
    assert pack["mechanical_evidence"]["claims"]
    for model in ["glm-5.2", "kimi-k2.7-code"]:
        assert pack["models"][model]["benchmarks"]
        assert pack["models"][model]["recommendation"]
        assert pack["llm_notes"][model].startswith("- bounded note")
    assert pack["models"]["glm-5.2"]["aa_index"] == 51
    assert pack["models"]["kimi-k2.7-code"]["aa_index"] == 42


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
    monkeypatch.setattr(newsletter, "live_model_inventory", lambda: {"data": [{"id": "glm-5.2"}, {"id": "kimi-k2.7-code"}]})
    monkeypatch.setattr(newsletter, "fetch_url_text", fake_source_text)
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


def fake_source_text(url: str) -> str:
    if "artificialanalysis.ai/models/glm-5-2" in url:
        return "51 Artificial Analysis Intelligence Index 4 out of 4 units Context window 1m Total parameters 753B Active parameters 40B"
    if "artificialanalysis.ai/models/kimi-k2-7-code" in url:
        return "42 Artificial Analysis Intelligence Index 4 out of 4 units Context window 256k Total parameters 1000B Active parameters 32B"
    if "zai-org/GLM-5.2" in url:
        return "|AIME 2026|99.2|95.3|\n|GPQA-Diamond|91.2|86.2|\n|SWE-bench Pro|62.1|58.4|\n|Terminal Bench 2.1 (Best Reported Harness)|82.7|71|\n|MCP-Atlas (Public Set)|76.8|71.8|"
    if "moonshotai/Kimi-K2.7-Code" in url:
        return """
        <tr><td>Kimi Code Bench v2</td><td>50.9</td><td>62.0</td></tr>
        <tr><td>Program Bench</td><td>48.3</td><td>53.6</td></tr>
        <tr><td>MLS Bench Lite</td><td>26.7</td><td>35.1</td></tr>
        <tr><td>Kimi Claw 24/7 Bench</td><td>42.9</td><td>46.9</td></tr>
        <tr><td>MCP Atlas</td><td>69.4</td><td>76.0</td></tr>
        <tr><td>MCP Mark Verified</td><td>72.8</td><td>81.1</td></tr>
        """
    raise AssertionError(f"unexpected URL {url}")
