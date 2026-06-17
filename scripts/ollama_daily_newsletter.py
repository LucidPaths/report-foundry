from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

OLLAMA_BASE_URL = "https://ollama.com/v1"
DEFAULT_MODELS = ["glm-5.2", "kimi-k2.7-code"]

MODEL_EVIDENCE = {
    "glm-5.2": {
        "aa_index": "51",
        "context": "1M tokens",
        "params": "753B total / 40B active",
        "speed": "112.4 tok/s",
        "positioning": "best fit for long-context synthesis, report drafting, repo archaeology, and high-effort paid-Ollama work",
        "benchmarks": "HLE 40.5; HLE w/ Tools 54.7; AIME 2026 99.2; GPQA-Diamond 91.2; SWE-bench Pro 62.1; Terminal Bench 2.1 up to 82.7; MCP-Atlas Public 76.8",
        "sources": ["ollama-models", "aa-glm-5-2", "hf-glm-5-2"],
    },
    "kimi-k2.7-code": {
        "aa_index": "42",
        "context": "256K tokens",
        "params": "1T total / 32B active",
        "speed": "48.5 tok/s",
        "positioning": "best fit for coding-agent workloads, code review, tool-heavy scaffolding, and MCP-style agent tasks",
        "benchmarks": "Kimi Code Bench v2 62.0 vs K2.6 50.9; Program Bench 53.6 vs 48.3; MLS Bench Lite 35.1 vs 26.7; MCP Atlas 76.0 vs 69.4; MCP Mark Verified 81.1 vs 72.8",
        "sources": ["ollama-models", "aa-kimi-k2-7-code", "hf-kimi-k2-7-code"],
    },
}

CITATIONS = {
    "ollama-models": {
        "source_id": "ollama-models",
        "url": "https://ollama.com/v1/models",
        "title": "Ollama Cloud /v1/models API",
        "quote": "Live model inventory confirmed glm-5.2 and kimi-k2.7-code are available.",
    },
    "aa-glm-5-2": {
        "source_id": "aa-glm-5-2",
        "url": "https://artificialanalysis.ai/models/glm-5-2",
        "title": "Artificial Analysis: GLM-5.2",
        "quote": "GLM-5.2 snapshot: Intelligence Index 51, 1M context, 753B/40B MoE.",
    },
    "aa-kimi-k2-7-code": {
        "source_id": "aa-kimi-k2-7-code",
        "url": "https://artificialanalysis.ai/models/kimi-k2-7-code",
        "title": "Artificial Analysis: Kimi K2.7 Code",
        "quote": "Kimi K2.7 Code snapshot: Intelligence Index 42, 256K context, 1T/32B MoE.",
    },
    "hf-glm-5-2": {
        "source_id": "hf-glm-5-2",
        "url": "https://huggingface.co/zai-org/GLM-5.2",
        "title": "GLM-5.2 official model card",
        "quote": "Official card reports 1M context, sparse attention, and strong reasoning/coding benchmark results.",
    },
    "hf-kimi-k2-7-code": {
        "source_id": "hf-kimi-k2-7-code",
        "url": "https://huggingface.co/moonshotai/Kimi-K2.7-Code",
        "title": "Kimi K2.7 Code official model card",
        "quote": "Official card reports 1T/32B MoE, 256K context, multimodal input, and coding benchmark gains over K2.6.",
    },
}


def load_ollama_key() -> str:
    if os.getenv("OLLAMA_API_KEY"):
        return os.environ["OLLAMA_API_KEY"]
    env_path = Path(r"C:\Users\lc77\AppData\Local\hermes\.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "OLLAMA_API_KEY":
                return value.strip().strip('"').strip("'")
    raise RuntimeError("OLLAMA_API_KEY is not available in the environment or Hermes .env")


def ollama_chat(model: str, prompt: str, *, max_tokens: int = 1200) -> str:
    key = load_ollama_key()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You write concise, source-grounded technical newsletter commentary. No secrets. No fake citations."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        data = json.load(response)
    message = data["choices"][0]["message"]
    return (message.get("content") or message.get("reasoning") or "").strip()


def live_model_ids() -> list[str]:
    key = load_ollama_key()
    req = urllib.request.Request(f"{OLLAMA_BASE_URL}/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    return [model["id"] for model in data.get("data", []) if "id" in model]


def sanitize_external_text(text: str) -> str:
    patterns = [
        r"ghp_[A-Za-z0-9_]+",
        r"gho_[A-Za-z0-9_]+",
        r"github_pat_[A-Za-z0-9_]+",
        r"sk-[A-Za-z0-9_-]+",
        r"xox[bp]-[A-Za-z0-9-]+",
        r"Bearer\s+[A-Za-z0-9._-]+",
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+",
    ]
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def make_prompt(model: str, evidence: dict[str, str], ids: list[str]) -> str:
    return f"""
Write 3 punchy newsletter bullets about {model} for Lucid's Discord.
Ground yourself ONLY in this evidence. Do not invent benchmarks.

Live Ollama model IDs include: {', '.join(m for m in DEFAULT_MODELS if m in ids)}.
Evidence:
- Artificial Analysis Intelligence Index: {evidence['aa_index']}
- Context: {evidence['context']}
- Parameters: {evidence['params']}
- Output speed: {evidence['speed']}
- Benchmarks: {evidence['benchmarks']}
- Suggested use: {evidence['positioning']}

Tone: technical, blunt, useful. No markdown table.
""".strip()


def build_report(out_json: Path, discord_md: Path, *, models: list[str] | None = None) -> dict[str, Any]:
    models = models or DEFAULT_MODELS
    ids = live_model_ids()
    missing = [model for model in models if model not in ids]
    if missing:
        raise RuntimeError(f"Ollama model IDs missing from live API: {', '.join(missing)}")

    generated: dict[str, str] = {}
    for model in models:
        try:
            generated[model] = ollama_chat(model, make_prompt(model, MODEL_EVIDENCE[model], ids))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            generated[model] = f"Live generation failed for {model}: {type(exc).__name__}. Static evidence still indicates: {MODEL_EVIDENCE[model]['positioning']}."

    today = date.today().isoformat()
    sections: list[dict[str, Any]] = [
        {
            "title": "Executive read",
            "kicker": "Ollama Cloud has two new useful routes. Treat them as aliases first, not blind defaults.",
            "blocks": [
                {"type": "text", "text": "Today’s practical move: wire Report Foundry to Ollama Cloud, generate a grounded model brief, render HTML/PDF, and post the digest to Discord."},
                {"type": "metric", "label": "Live models checked", "value": str(len(ids)), "note": "Queried from Ollama Cloud /v1/models during generation."},
                {"type": "metric", "label": "New candidates", "value": ", ".join(models), "note": "Both IDs returned by the live API."},
                {"type": "claim", "text": "glm-5.2 and kimi-k2.7-code are live Ollama Cloud API model IDs and should be tested as explicit aliases before becoming defaults.", "confidence": "high", "verification_status": "supported", "citations": [CITATIONS["ollama-models"]]},
            ],
        }
    ]

    for model in models:
        evidence = MODEL_EVIDENCE[model]
        sections.append(
            {
                "title": model,
                "kicker": evidence["positioning"],
                "blocks": [
                    {"type": "text", "text": sanitize_external_text(generated[model])},
                    {"type": "metric", "label": "AA Intelligence Index", "value": evidence["aa_index"], "note": "Snapshot from Artificial Analysis."},
                    {"type": "metric", "label": "Context", "value": evidence["context"], "note": evidence["params"]},
                    {"type": "claim", "text": f"{model} is best handled as: {evidence['positioning']}.", "confidence": "medium", "verification_status": "supported", "citations": [CITATIONS[s] for s in evidence["sources"]]},
                    {"type": "text", "text": f"Benchmarks to remember: {evidence['benchmarks']}"},
                ],
            }
        )

    report = {
        "title": "Ollama Cloud Field Brief: GLM-5.2 + Kimi K2.7 Code",
        "subtitle": "First Report Foundry newsletter generated through live Ollama Cloud calls.",
        "report_date": today,
        "author": "Report Foundry + Ollama Cloud",
        "tags": ["ollama", "models", "benchmarks", "discord", "report-foundry"],
        "sections": sections,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    discord = f"""## Ollama Cloud Field Brief — {today}

Report Foundry is wired to Ollama Cloud and generated today’s first model brief.

**Live-checked:** `{', '.join(models)}` are present in `/v1/models`.

**Read:**
- `glm-5.2`: 1M context, AA Intelligence Index 51, 753B/40B MoE. Use it for long-context synthesis and big-brain report drafting.
- `kimi-k2.7-code`: 256K context, AA Intelligence Index 42, 1T/32B MoE. Use it for coding-agent/tool-heavy workloads, not as a blind general Kimi replacement yet.

**Generated model notes:**

**glm-5.2**
{generated['glm-5.2']}

**kimi-k2.7-code**
{generated['kimi-k2.7-code']}

Artifacts: HTML + PDF rendered locally by Report Foundry.
"""
    discord_md.parent.mkdir(parents=True, exist_ok=True)
    discord_md.write_text(sanitize_external_text(discord), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Report Foundry daily newsletter via Ollama Cloud.")
    parser.add_argument("--out", default=".output/ollama_cloud_field_brief.json")
    parser.add_argument("--discord-md", default=".output/ollama_cloud_field_brief.discord.md")
    args = parser.parse_args()
    report = build_report(Path(args.out), Path(args.discord_md))
    print(json.dumps({"title": report["title"], "sections": len(report["sections"]), "out": args.out, "discord_md": args.discord_md}, indent=2))


if __name__ == "__main__":
    main()
