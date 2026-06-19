"""JSON repair helpers for model-generated ResearchIntake payloads.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
import re
from typing import Any


class JsonRepairError(ValueError):
    """Model output could not be normalized into one JSON object."""


def extract_json_object(text: str) -> str:
    """Extract the first balanced JSON object from noisy model output."""
    stripped = _strip_fences(text.strip())
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    if start < 0:
        raise JsonRepairError("no JSON object start found")
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(stripped[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]
    raise JsonRepairError("JSON object was not balanced")


def parse_or_repair_json_object(text: str) -> dict[str, Any]:
    """Parse common model JSON shapes and fail with a repairable error."""
    candidate = extract_json_object(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise JsonRepairError(f"invalid JSON object: {exc}") from exc


def normalize_research_intake_ids(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize common model ID style drift while preserving referential links."""
    mapping: dict[str, str] = {}

    def slug(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
        return normalized or value

    for collection in ("sources", "facts", "proposed_claims", "uncertainties", "research_gaps", "contradictions", "exhibits"):
        items = data.get(collection, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    old = item["id"]
                    new = slug(old)
                    mapping[old] = new
                    item["id"] = new

    def normalize_value(value: Any) -> Any:
        if isinstance(value, str):
            return mapping.get(value, slug(value))
        if isinstance(value, list):
            return [normalize_value(item) for item in value]
        if isinstance(value, dict):
            for key, item in list(value.items()):
                if key.endswith("_id") or key.endswith("_ids") or key in {"source_id"}:
                    value[key] = normalize_value(item)
                elif isinstance(item, (dict, list)):
                    value[key] = normalize_value(item)
        return value

    return normalize_value(data)


def build_json_repair_prompt(*, schema: str, invalid_output: str, error: str) -> str:
    """Prompt for bounded schema repair after a malformed model response."""
    return f"""Repair the malformed ResearchIntake JSON.

Rules:
- Return exactly one JSON object.
- No Markdown fences.
- No prose outside JSON.
- Preserve observed source IDs, fact IDs, claim IDs, citations, limitations, and uncertainty fields.
- Fix only syntax/schema issues needed to satisfy the schema.
- Keep the output bounded: 3-5 sections, 5-12 facts, 4-8 claims, 1-3 exhibits unless the invalid output already has fewer.
- All IDs must be lowercase and may only contain letters, numbers, underscores, or hyphens; examples: source_1, fact_1, claim_1, section_1, exhibit_1.

Validation error:
{error}

Schema:
{schema}

Malformed output:
{invalid_output[:60000]}
"""


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()
