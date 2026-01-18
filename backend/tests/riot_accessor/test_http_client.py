from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.riot_accessor.client import RiotClient


@pytest.fixture
def client_env_patch(monkeypatch):
    monkeypatch.setenv("RIOT_API_KEY", "test-key")


def test_riot_client_from_env(client_env_patch):
    client = RiotClient.from_env()
    assert client.api_key == "test-key"


def test_riot_client_missing_env(monkeypatch):
    monkeypatch.delenv("RIOT_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Missing RIOT_API_KEY"):
        RiotClient.from_env()


@patch("httpx.Client")
def test_get_json_success(mock_client_cls):
    mock_instance = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_instance

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value"}
    mock_instance.get.return_value = mock_response

    client = RiotClient(api_key="test-key")
    result = client.get_json(url="http://test.com")

    assert result == {"key": "value"}
    mock_instance.get.assert_called_with(
        "http://test.com", headers={"X-Riot-Token": "test-key"}, params=None
    )


@patch("httpx.Client")
def test_get_json_retry_429(mock_client_cls):
    mock_instance = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_instance

    # First call returns 429, second returns 200
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.01"}

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"ok": True}

    mock_instance.get.side_effect = [resp_429, resp_200]

    client = RiotClient(api_key="test-key")
    result = client.get_json(url="http://test.com")

    assert result == {"ok": True}
    assert mock_instance.get.call_count == 2


@patch("httpx.Client")
def test_get_json_retry_500(mock_client_cls):
    mock_instance = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_instance

    # First call raises HTTPStatusError (500), second returns 200
    resp_500 = MagicMock()
    resp_500.status_code = 500
    resp_500.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=resp_500
    )

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"recovered": True}

    # First call returns 5xx status code (not exception directly from .get, but .raise_for_status called)
    # The code checks status code manually.
    mock_instance.get.side_effect = [resp_500, resp_200]

    client = RiotClient(api_key="test-key")
    result = client.get_json(url="http://test.com")

    assert result == {"recovered": True}
    assert mock_instance.get.call_count == 2


@patch("httpx.Client")
def test_get_json_fail_404(mock_client_cls):
    mock_instance = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_instance

    resp_404 = MagicMock()
    resp_404.status_code = 404
    # The code does resp.raise_for_status()
    resp_404.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=resp_404
    )

    mock_instance.get.return_value = resp_404

    client = RiotClient(api_key="test-key")

    with pytest.raises(httpx.HTTPStatusError):
        client.get_json(url="http://test.com")

    # Should not retry 4xx
    assert mock_instance.get.call_count == 1


@patch("httpx.Client")
def test_get_json_exhaust_retries(mock_client_cls):
    mock_instance = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_instance

    # Always raises error
    mock_instance.get.side_effect = Exception("Network Error")

    # Set small stats to speed up test
    client = RiotClient(api_key="test-key", max_retries=2, timeout_s=0.1)

    with pytest.raises(RuntimeError, match="Riot request failed after 2 retries"):
        client.get_json(url="http://test.com")

    assert mock_instance.get.call_count == 2
