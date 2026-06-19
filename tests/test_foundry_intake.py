"""Foundry intake tests for topic/source-namespace contracts.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P7 Secrets Stay Handles.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from report_foundry.factory import FoundryRunRequest, build_foundry_run_request


def test_foundry_run_request_is_keyword_plus_optional_source_namespaces() -> None:
    request = build_foundry_run_request(
        keyword="current SpaceX IPO launch newsletter",
        source_namespaces=["company-db", "public-web"],
        audience="executive readers",
    )

    assert request.keyword == "current SpaceX IPO launch newsletter"
    assert request.audience == "executive readers"
    assert request.source_namespaces == ["company-db", "public-web"]
    assert request.pipeline == [
        "keyword_intake",
        "source_observation",
        "fact_extraction",
        "claim_synthesis",
        "visual_layout",
        "qa_export",
    ]


def test_foundry_run_request_rejects_provider_credentials_as_core_fields() -> None:
    with pytest.raises(ValidationError):
        FoundryRunRequest.model_validate(
            {
                "keyword": "SpaceX IPO",
                "ai": {"provider": "vendor", "api" + "_key": "raw-key-field-is-forbidden"},
                "provider_runtime": {"provider": "search", "credential_ref": "USER_SECRET"},
            }
        )


def test_foundry_run_request_requires_non_empty_keyword() -> None:
    with pytest.raises(ValidationError):
        build_foundry_run_request(keyword="   ")
