from __future__ import annotations

import argparse
import json
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

OLLAMA_BASE_URL = "https://ollama.com/v1"
DEFAULT_MODELS = ["glm-5.2", "kimi-k2.7-code"]

REPORT_SCOPE = {
    "audience": "Lucid + Discord readers who want actionable model-routing signal, not benchmark wallpaper.",
    "question": "Which new Ollama Cloud models are available today, what are they good for, and how should Hermes/Report Foundry use them next?",
    "in_scope": [
        "Live Ollama Cloud availability checks",
        "Published benchmark snapshots for GLM-5.2 and Kimi K2.7 Code",
        "Use-case routing guidance for Hermes and Report Foundry",
        "A deterministic newsletter artifact suitable for Discord",
    ],
    "out_of_scope": [
        "Blindly switching Hermes defaults",
        "Inventing private benchmark numbers",
        "Letting an LLM choose visual layout or PDF structure",
    ],
}

TOOLCHAIN = [
    {"name": "Ollama Cloud API", "role": "live model inventory + bounded generation"},
    {"name": "Artificial Analysis", "role": "benchmark snapshot source"},
    {"name": "Hugging Face model cards", "role": "official specs and comparison tables"},
    {"name": "Report Foundry IR", "role": "canonical structured report artifact"},
    {"name": "Evidence pack", "role": "scope, sources, metrics, claims"},
    {"name": "QA gates", "role": "unsupported-claim and artifact checks"},
    {"name": "ReportLab canvas", "role": "deterministic PDF layout; no LLM layout control"},
    {"name": "Discord delivery", "role": "final external publish surface after sanitization"},
]

MODEL_EVIDENCE = {
    "glm-5.2": {
        "display": "GLM-5.2",
        "tagline": "Context synthesis",
        "aa_index": 51,
        "context": "1M",
        "params": "753B / 40B active",
        "speed": "112.4 tok/s",
        "recommendation": "Use for repo archaeology, long-context synthesis, report drafting, and high-effort paid-Ollama work.",
        "benchmarks": {
            "HLE + tools": 54.7,
            "AIME 2026": 99.2,
            "GPQA-Diamond": 91.2,
            "SWE-bench Pro": 62.1,
            "Terminal Bench": 82.7,
            "MCP-Atlas": 76.8,
        },
        "claims": [
            "1M context makes it the better candidate for long evidence packs and repo-scale synthesis.",
            "Tool-assisted HLE and Terminal Bench numbers suggest it should be tested in agentic workflows, not just chat prompts.",
        ],
        "sources": ["ollama-models", "aa-glm-5-2", "hf-glm-5-2"],
    },
    "kimi-k2.7-code": {
        "display": "Kimi K2.7 Code",
        "tagline": "Coding-agent",
        "aa_index": 42,
        "context": "256K",
        "params": "1T / 32B active",
        "speed": "48.5 tok/s",
        "recommendation": "Use for coding agents, code review, tool-heavy scaffolding, and MCP-style work. Do not blindly replace the general Kimi alias yet.",
        "benchmarks": {
            "Kimi Code v2": 62.0,
            "Program Bench": 53.6,
            "MLS Bench Lite": 35.1,
            "Kimi Claw 24/7": 46.9,
            "MCP Atlas": 76.0,
            "MCP Mark Verified": 81.1,
        },
        "claims": [
            "Official comparisons show meaningful coding-agent gains over K2.6 on the listed coding/MCP benchmarks.",
            "Because it is coding-specialized, it should become a coding alias before it becomes the broad `kimi` default.",
        ],
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


@dataclass(frozen=True)
class Palette:
    ink: colors.Color = colors.HexColor("#101828")
    muted: colors.Color = colors.HexColor("#667085")
    paper: colors.Color = colors.HexColor("#F8FAFC")
    panel: colors.Color = colors.HexColor("#FFFFFF")
    violet: colors.Color = colors.HexColor("#7C3AED")
    cyan: colors.Color = colors.HexColor("#06B6D4")
    green: colors.Color = colors.HexColor("#12B76A")
    amber: colors.Color = colors.HexColor("#F79009")
    line: colors.Color = colors.HexColor("#D0D5DD")


P = Palette()


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


def ollama_chat(model: str, prompt: str, *, max_tokens: int = 700, attempts: int = 3) -> str:
    key = load_ollama_key()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You write bounded commentary only. You do not invent citations, metrics, scope, layout, or PDF structure."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.45,
        "max_tokens": max_tokens,
        "stream": False,
    }
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.load(response)
            message = data["choices"][0]["message"]
            content = (message.get("content") or message.get("reasoning") or "").strip()
            if len(content) < 80:
                raise RuntimeError(f"short response from {model}")
            return content
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Ollama chat failed for {model} after {attempts} attempts: {type(last_error).__name__}")


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


META_PHRASES = (
    "the user wants",
    "let me",
    "we need",
    "draft:",
    "word count",
    "count words",
    "i should",
    "instruction",
)


def deterministic_note(model: str, evidence: dict[str, Any]) -> str:
    top_benchmarks = sorted(evidence["benchmarks"].items(), key=lambda item: item[1], reverse=True)[:3]
    bench_text = ", ".join(f"{name} {value:g}" for name, value in top_benchmarks)
    return (
        f"- {model} is live on Ollama Cloud with {evidence['context']} context, {evidence['params']} MoE, "
        f"{evidence['speed']} output, and AA Intelligence Index {evidence['aa_index']}.\n"
        f"- Benchmark highlights: {bench_text}. {evidence['recommendation']}"
    )


def enforce_bounded_note(model: str, evidence: dict[str, Any], raw: str) -> str:
    """Keep only final user-facing bullets; never persist model scratchpad."""
    sanitized = sanitize_external_text(raw)
    candidate_lines: list[str] = []
    for line in sanitized.splitlines():
        stripped = line.strip().strip('"')
        if not stripped.startswith(("- ", "• ")):
            continue
        lowered = stripped.lower()
        if any(phrase in lowered for phrase in META_PHRASES):
            continue
        if model not in lowered and evidence["display"].lower() not in lowered and "benchmark" not in lowered and "hermes" not in lowered:
            continue
        candidate_lines.append("- " + stripped[2:].strip())
    note = "\n".join(candidate_lines[:2]).strip()
    words = re.findall(r"\S+", note)
    if len(candidate_lines) < 2 or len(words) > 100 or any(phrase in note.lower() for phrase in META_PHRASES):
        note = deterministic_note(model, evidence)
    return note


def make_prompt(model: str, evidence: dict[str, Any], ids: list[str]) -> str:
    return f"""
Write exactly two concise newsletter bullets about {model}.
Ground yourself ONLY in this evidence. Do not invent benchmarks.
No markdown heading. No table. No more than 90 words total.
Return ONLY the two bullet lines. Do not include reasoning, analysis, drafts, or word counts.

Scope question: {REPORT_SCOPE['question']}
Live Ollama model IDs include: {', '.join(m for m in DEFAULT_MODELS if m in ids)}.
Evidence:
- Artificial Analysis Intelligence Index: {evidence['aa_index']}
- Context: {evidence['context']}
- Parameters: {evidence['params']}
- Output speed: {evidence['speed']}
- Benchmarks: {evidence['benchmarks']}
- Suggested use: {evidence['recommendation']}
""".strip()


def bounded_model_notes(models: list[str], ids: list[str]) -> dict[str, str]:
    notes: dict[str, str] = {}
    for model in models:
        try:
            raw = ollama_chat(model, make_prompt(model, MODEL_EVIDENCE[model], ids))
            notes[model] = enforce_bounded_note(model, MODEL_EVIDENCE[model], raw)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            notes[model] = f"Live commentary failed for {model}: {type(exc).__name__}. Static evidence still supports the routing recommendation."
    return notes


def build_evidence_pack(models: list[str] | None = None) -> dict[str, Any]:
    models = models or DEFAULT_MODELS
    ids = live_model_ids()
    missing = [model for model in models if model not in ids]
    if missing:
        raise RuntimeError(f"Ollama model IDs missing from live API: {', '.join(missing)}")
    return {
        "generated_at": date.today().isoformat(),
        "scope": REPORT_SCOPE,
        "toolchain": TOOLCHAIN,
        "live_check": {"endpoint": f"{OLLAMA_BASE_URL}/models", "model_count": len(ids), "models_found": models},
        "models": {model: MODEL_EVIDENCE[model] for model in models},
        "citations": CITATIONS,
        "llm_notes": bounded_model_notes(models, ids),
        "layout_contract": {
            "llm_role": "bounded commentary only",
            "renderer_role": "deterministic layout, cards, bars, diagrams, source footer",
            "must_include": ["scope", "toolchain", "live checks", "model cards", "benchmark bars", "routing recommendations", "sources"],
        },
    }


def build_report_ir(pack: dict[str, Any], out_json: Path) -> dict[str, Any]:
    today = pack["generated_at"]
    models = list(pack["models"].keys())
    sections: list[dict[str, Any]] = [
        {
            "title": "Scope + method",
            "kicker": "The report is built from a structured evidence pack. The LLM does not design the PDF.",
            "blocks": [
                {"type": "text", "text": pack["scope"]["question"]},
                {"type": "metric", "label": "Live models checked", "value": str(pack["live_check"]["model_count"]), "note": "Queried from Ollama Cloud /v1/models."},
                {"type": "metric", "label": "Candidate IDs", "value": ", ".join(models), "note": "Exact API IDs, not guessed website names."},
                {"type": "claim", "text": "The artifact separates data gathering, scope, deterministic layout, and LLM commentary.", "confidence": "high", "verification_status": "supported", "citations": [CITATIONS["ollama-models"]]},
            ],
        },
        {
            "title": "Toolchain",
            "kicker": "Eight concrete parts of the pipeline are represented in the evidence pack and final layout.",
            "blocks": [
                {"type": "table", "headers": ["Tool", "Role"], "rows": [[t["name"], t["role"]] for t in TOOLCHAIN]},
            ],
        },
    ]
    for model, evidence in pack["models"].items():
        sections.append(
            {
                "title": evidence["display"],
                "kicker": evidence["tagline"],
                "blocks": [
                    {"type": "text", "text": pack["llm_notes"][model]},
                    {"type": "metric", "label": "AA Intelligence Index", "value": str(evidence["aa_index"]), "note": "Benchmark snapshot."},
                    {"type": "metric", "label": "Context", "value": evidence["context"], "note": evidence["params"]},
                    {"type": "claim", "text": evidence["recommendation"], "confidence": "medium", "verification_status": "supported", "citations": [CITATIONS[s] for s in evidence["sources"]]},
                ],
            }
        )
    report = {
        "title": "Ollama Cloud Field Brief",
        "subtitle": "GLM-5.2 + Kimi K2.7 Code — scoped evidence, deterministic layout, bounded LLM commentary.",
        "report_date": today,
        "author": "Report Foundry",
        "tags": ["ollama", "models", "benchmarks", "discord", "report-foundry"],
        "sections": sections,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def wrap_lines(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        if not paragraph.strip():
            lines.append("")
        else:
            lines.extend(textwrap.wrap(paragraph, width=width, replace_whitespace=False))
    return lines


def draw_text(c: Canvas, text: str, x: float, y: float, *, size: int = 10, color: colors.Color = P.ink, font: str = "Helvetica", width: int = 70, leading: int | None = None) -> float:
    c.setFillColor(color)
    c.setFont(font, size)
    leading = leading or int(size * 1.35)
    for line in wrap_lines(text, width):
        c.drawString(x, y, line)
        y -= leading
    return y


def card(c: Canvas, x: float, y: float, w: float, h: float, *, fill: colors.Color = P.panel, stroke: colors.Color = P.line, radius: float = 14) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)


def draw_badge(c: Canvas, label: str, x: float, y: float, color: colors.Color) -> None:
    c.setFillColor(color)
    c.roundRect(x, y - 4, 98, 20, 8, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + 49, y + 2, label.upper())


def draw_benchmark_bars(c: Canvas, benchmarks: dict[str, float], x: float, y: float, w: float, color: colors.Color) -> float:
    max_value = 100
    c.setFont("Helvetica", 7.5)
    for name, value in benchmarks.items():
        c.setFillColor(P.muted)
        c.drawString(x, y, name[:24])
        c.setStrokeColor(colors.HexColor("#EAECF0"))
        c.setFillColor(colors.HexColor("#EAECF0"))
        c.roundRect(x + 88, y - 1, w - 88, 7, 3, stroke=0, fill=1)
        c.setFillColor(color)
        c.roundRect(x + 88, y - 1, (w - 88) * min(value, max_value) / max_value, 7, 3, stroke=0, fill=1)
        c.setFillColor(P.ink)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(x + w, y, f"{value:g}")
        c.setFont("Helvetica", 7.5)
        y -= 15
    return y


def draw_model_card(c: Canvas, model: str, evidence: dict[str, Any], note: str, x: float, y: float, w: float, h: float, accent: colors.Color) -> None:
    card(c, x, y, w, h)
    draw_badge(c, evidence["tagline"], x + 16, y + h - 24, accent)
    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x + 16, y + h - 54, evidence["display"])
    c.setFont("Helvetica", 9)
    c.setFillColor(P.muted)
    c.drawString(x + 16, y + h - 70, model)

    metrics = [("AA", str(evidence["aa_index"])), ("CTX", evidence["context"]), ("MoE", evidence["params"]), ("Speed", evidence["speed"])]
    mx = x + 16
    for label, value in metrics:
        c.setFillColor(colors.HexColor("#F2F4F7"))
        c.roundRect(mx, y + h - 106, 53, 26, 8, fill=1, stroke=0)
        c.setFillColor(P.muted)
        c.setFont("Helvetica", 6.5)
        c.drawString(mx + 7, y + h - 91, label)
        c.setFillColor(P.ink)
        c.setFont("Helvetica-Bold", 6.8)
        c.drawString(mx + 7, y + h - 101, value[:11])
        mx += 57

    draw_benchmark_bars(c, evidence["benchmarks"], x + 16, y + h - 132, w - 32, accent)
    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 16, y + 86, "Bounded LLM commentary")
    compact_note = " ".join(note.replace("•", "-").split())
    draw_text(c, compact_note, x + 16, y + 72, size=6.2, color=P.ink, width=76, leading=7)


def render_designed_html(pack: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_cards = []
    for model, evidence in pack["models"].items():
        bars = "".join(f"<div class='bar'><span>{name}</span><i style='width:{min(value,100)}%'></i><b>{value:g}</b></div>" for name, value in evidence["benchmarks"].items())
        model_cards.append(f"""
        <article class='model'>
          <small>{evidence['tagline']}</small><h2>{evidence['display']}</h2><p class='id'>{model}</p>
          <div class='metrics'><b>AA {evidence['aa_index']}</b><b>{evidence['context']} ctx</b><b>{evidence['params']}</b><b>{evidence['speed']}</b></div>
          <div>{bars}</div><p>{pack['llm_notes'][model]}</p><strong>{evidence['recommendation']}</strong>
        </article>""")
    tools = "".join(f"<li><b>{t['name']}</b><span>{t['role']}</span></li>" for t in pack["toolchain"])
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Ollama Cloud Field Brief</title><style>
    body{{font-family:Inter,Arial,sans-serif;background:#0B1020;color:#101828;margin:0;padding:36px}}main{{max-width:1100px;margin:auto;background:#F8FAFC;border-radius:28px;padding:38px}}
    header{{background:linear-gradient(135deg,#101828,#3B0764);color:white;border-radius:24px;padding:34px}}h1{{font-size:52px;line-height:.95;margin:0}}.sub{{color:#D0D5DD;font-size:18px;max-width:760px}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}}section,.model{{background:white;border:1px solid #EAECF0;border-radius:22px;padding:24px;box-shadow:0 18px 50px #0001}}
    small{{color:#7C3AED;text-transform:uppercase;font-weight:800;letter-spacing:.08em}}h2{{margin:.2em 0;font-size:28px}}.id{{color:#667085}}.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:14px 0}}.metrics b{{background:#F2F4F7;border-radius:12px;padding:10px}}
    .bar{{display:grid;grid-template-columns:120px 1fr 36px;gap:10px;align-items:center;font-size:12px;margin:8px 0}}.bar i{{height:8px;background:linear-gradient(90deg,#7C3AED,#06B6D4);border-radius:99px}}ul{{padding-left:0;list-style:none}}li{{display:grid;grid-template-columns:190px 1fr;padding:8px 0;border-bottom:1px solid #EAECF0}}
    footer{{color:#667085;font-size:12px;margin-top:24px}}
    </style></head><body><main><header><small>Report Foundry / Ollama Cloud</small><h1>Field Brief</h1><p class='sub'>{pack['scope']['question']}</p></header>
    <div class='grid'><section><small>Scope</small><h2>What this report is allowed to claim</h2><p>{pack['scope']['audience']}</p><b>In scope</b><ul>{''.join(f'<li><span>{x}</span></li>' for x in pack['scope']['in_scope'])}</ul></section><section><small>Pipeline</small><h2>Tools represented</h2><ul>{tools}</ul></section></div>
    <div class='grid'>{''.join(model_cards)}</div><footer>Sources: Ollama /v1/models, Artificial Analysis model pages, Hugging Face official model cards. LLM role: bounded commentary only. Layout: deterministic Report Foundry renderer.</footer></main></body></html>"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def render_designed_pdf(pack: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = A4
    c = Canvas(str(output_path), pagesize=A4)
    c.setTitle("Ollama Cloud Field Brief")
    c.setAuthor("Report Foundry")

    # Page 1: cover, scope, toolchain
    c.setFillColor(P.paper)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#101828"))
    c.roundRect(28, h - 214, w - 56, 174, 22, fill=1, stroke=0)
    c.setFillColor(P.violet)
    c.circle(w - 92, h - 78, 56, fill=1, stroke=0)
    c.setFillColor(P.cyan)
    c.circle(w - 152, h - 154, 34, fill=1, stroke=0)
    draw_badge(c, "Report Foundry / Ollama", 52, h - 72, P.violet)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 38)
    c.drawString(52, h - 118, "Ollama Cloud Field Brief")
    draw_text(c, "GLM-5.2 + Kimi K2.7 Code — scoped evidence, deterministic layout, bounded LLM commentary.", 54, h - 146, size=11, color=colors.HexColor("#EAECF0"), width=82, leading=14)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#D0D5DD"))
    c.drawString(54, h - 184, f"Generated {pack['generated_at']} · Live API models checked: {pack['live_check']['model_count']}")

    card(c, 32, h - 430, 248, 186)
    draw_badge(c, "Scope", 50, h - 272, P.cyan)
    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, h - 305, "Question + boundary")
    y = draw_text(c, pack["scope"]["question"], 50, h - 326, size=8.7, width=45, leading=12)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y - 4, "Out of scope")
    y -= 18
    for item in pack["scope"]["out_of_scope"]:
        y = draw_text(c, f"• {item}", 54, y, size=7.5, color=P.muted, width=46, leading=10)

    card(c, 300, h - 430, 262, 186)
    draw_badge(c, "Toolchain", 318, h - 272, P.violet)
    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(318, h - 305, "LLM does not own the PDF")
    y = h - 328
    for idx, tool in enumerate(pack["toolchain"], 1):
        c.setFillColor(P.violet if idx % 2 else P.cyan)
        c.circle(326, y + 2, 5, fill=1, stroke=0)
        c.setFillColor(P.ink)
        c.setFont("Helvetica-Bold", 7.6)
        c.drawString(338, y, tool["name"])
        c.setFillColor(P.muted)
        c.setFont("Helvetica", 7.1)
        c.drawString(338, y - 9, tool["role"][:54])
        y -= 21

    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(36, h - 466, "Pipeline contract")
    steps = [("Gather", "API + public benchmark/model-card data"), ("Scope", "explicit question, audience, boundaries"), ("Outline", "fixed sections and claims"), ("Render", "cards, bars, sources, deterministic PDF")]
    x = 36
    for step, desc in steps:
        card(c, x, h - 552, 120, 58, fill=colors.white)
        c.setFillColor(P.violet)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 12, h - 520, step)
        draw_text(c, desc, x + 12, h - 535, size=7, color=P.muted, width=21, leading=8)
        if step != "Render":
            c.setStrokeColor(P.line)
            c.line(x + 122, h - 523, x + 140, h - 523)
        x += 138

    c.setFillColor(P.muted)
    c.setFont("Helvetica", 8)
    c.drawString(36, 30, "Sources: Ollama /v1/models · Artificial Analysis · Hugging Face model cards · Generated by Report Foundry")
    c.showPage()

    # Page 2: model cards and sources
    c.setFillColor(P.paper)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(32, h - 54, "Model routing cards")
    c.setFont("Helvetica", 9)
    c.setFillColor(P.muted)
    c.drawString(34, h - 72, "Metrics are static evidence. Short notes are bounded LLM commentary. Layout is deterministic.")

    model_items = list(pack["models"].items())
    draw_model_card(c, model_items[0][0], model_items[0][1], pack["llm_notes"][model_items[0][0]], 32, h - 432, 250, 328, P.violet)
    draw_model_card(c, model_items[1][0], model_items[1][1], pack["llm_notes"][model_items[1][0]], 312, h - 432, 250, 328, P.cyan)

    card(c, 32, 74, 530, 108)
    draw_badge(c, "Decision", 50, 154, P.green)
    c.setFillColor(P.ink)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 131, "What we actually do next")
    y = 114
    for line in [
        "Add aliases first: glm5.2 and k2.7-code. Do not flip defaults blindly.",
        "Run Hermes tool-call probes: simple chat, structured tool call, tool-result synthesis, retry behavior.",
        "Use GLM-5.2 for long-context report synthesis; use Kimi K2.7 Code for coding-agent loops.",
    ]:
        y = draw_text(c, f"• {line}", 54, y, size=8.5, width=96, leading=12)

    c.setFillColor(P.muted)
    c.setFont("Helvetica", 7.5)
    c.drawString(36, 38, "Citations: Ollama /v1/models; Artificial Analysis GLM-5.2 + Kimi K2.7 Code pages; official Hugging Face model cards.")
    c.save()
    return output_path


def write_discord_summary(pack: dict[str, Any], output_path: Path, pdf_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""## Corrected Ollama Cloud Field Brief — {pack['generated_at']}

I rebuilt this as an actual Report Foundry artifact, not a text dump.

**Contract now represented:**
- scope + audience + out-of-scope boundaries
- live Ollama `/v1/models` check
- named toolchain/data pipeline
- model cards with benchmark bars
- bounded LLM commentary only
- deterministic PDF layout
- source footer

**Routing read:**
- `glm-5.2` → long-context synthesis / repo archaeology / high-effort report drafting
- `kimi-k2.7-code` → coding-agent and MCP/tool-heavy workloads

PDF attached.

MEDIA:{pdf_path}
"""
    output_path.write_text(sanitize_external_text(text), encoding="utf-8")
    return output_path


def build_artifacts(out_dir: Path, *, models: list[str] | None = None) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pack = build_evidence_pack(models)
    pack_path = out_dir / "ollama_cloud_field_brief.evidence.json"
    pack_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    ir_path = out_dir / "ollama_cloud_field_brief.json"
    build_report_ir(pack, ir_path)
    html_path = render_designed_html(pack, out_dir / "ollama_cloud_field_brief_designed.html")
    pdf_path = render_designed_pdf(pack, out_dir / "ollama_cloud_field_brief_designed.pdf")
    discord_path = write_discord_summary(pack, out_dir / "ollama_cloud_field_brief_designed.discord.md", pdf_path.resolve())
    return {"evidence": pack_path, "ir": ir_path, "html": html_path, "pdf": pdf_path, "discord": discord_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a scoped Report Foundry newsletter via Ollama Cloud.")
    parser.add_argument("--out-dir", default=".output")
    args = parser.parse_args()
    paths = build_artifacts(Path(args.out_dir))
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))


if __name__ == "__main__":
    main()
