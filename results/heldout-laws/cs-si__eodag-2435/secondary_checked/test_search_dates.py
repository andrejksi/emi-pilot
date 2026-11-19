from contextlib import suppress
from unittest.mock import Mock

from requests import Response, Session

from eodag import EODataAccessGateway, EODAGSettings
from eodag.utils.exceptions import ValidationError


def test_invalid_completion_date_is_checked_before_search(tmp_path, monkeypatch):
    """New: "check dates validity before search" for completionDate=2023-11-31 (A1)."""
    # SARA is a bundled provider with the same startDate and completionDate query fields.
    gateway = EODataAccessGateway(
        settings=EODAGSettings(cfg_dir=tmp_path, providers_whitelist=["sara"])
    )
    response = Response()
    response.status_code = 200
    response._content = b'{"features": []}'
    provider_request = Mock(return_value=response)
    monkeypatch.setattr(Session, "get", provider_request)

    with suppress(ValidationError, ValueError):
        gateway.search(
            collection="S2_MSI_L1C",
            provider="sara",
            start="2020-01-01",
            end="2023-11-31",
        )

    assert provider_request.call_count == 0
