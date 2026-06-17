"""Foundry intake tests for provider/key-reference contracts.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P7 Secrets Stay Handles.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from report_foundry.factory import FoundryRunRequest, build_foundry_run_request


def test_foundry_run_request_is_keyword_plus_user_connected_ai_key_reference() -> None:
    request = build_foundry_run_request(
        keyword="current SpaceX IPO launch newsletter",
        ai_provider="openai-compatible",
        ai_api_key_env_var="USER_AI_API_KEY",
        search_provider="ai-search",
        audience="executive readers",
    )

    assert request.keyword == "current SpaceX IPO launch newsletter"
    assert request.audience == "executive readers"
    assert request.ai.provider == "openai-compatible"
    assert request.ai.api_key_env_var == "USER_AI_API_KEY"
    assert request.search.provider == "ai-search"
    assert request.search.api_key_env_var == "USER_AI_API_KEY"
    assert request.pipeline == [
        "keyword_intake",
        "ai_search",
        "source_observation",
        "fact_extraction",
        "claim_synthesis",
        "visual_layout",
        "qa_export",
    ]


def test_foundry_run_request_never_accepts_raw_api_key_fields() -> None:
    with pytest.raises(ValidationError):
        FoundryRunRequest.model_validate(
            {
                "keyword": "SpaceX IPO",
                "ai": {"provider": "openai-compatible", "api" + "_key": "raw-key-field-is-forbidden"},
                "search": {"provider": "ai-search", "api_key_env_var": "USER_AI_API_KEY"},
            }
        )


def test_foundry_run_request_requires_non_empty_keyword() -> None:
    with pytest.raises(ValidationError):
        build_foundry_run_request(keyword="   ", ai_provider="openai-compatible", ai_api_key_env_var="USER_AI_API_KEY")
