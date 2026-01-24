import pytest
from unittest.mock import patch, MagicMock
from app.ingest.clients.ddragon import DataDragonClient


@pytest.fixture
def client():
    return DataDragonClient()


@patch("app.ingest.clients.ddragon.requests.get")
def test_fetch_latest_version_success(mock_get, client):
    mock_get.return_value.json.return_value = ["14.1.1", "13.24.1"]
    version = client.fetch_latest_version()
    assert version == "14.1.1"


@patch("app.ingest.clients.ddragon.requests.get")
def test_fetch_latest_version_failure(mock_get, client):
    mock_get.side_effect = Exception("Network Error")
    version = client.fetch_latest_version()
    # Should default to fallback
    assert version == "14.1.1"


@patch("app.ingest.clients.ddragon.requests.get")
def test_fetch_champion_map(mock_get, client):
    # First call is version, second is data
    mock_version_resp = MagicMock()
    mock_version_resp.json.return_value = ["14.1.1"]

    mock_data_resp = MagicMock()
    mock_data_resp.json.return_value = {
        "data": {"Aatrox": {"key": "266", "id": "Aatrox"}, "Ahri": {"key": "103", "id": "Ahri"}}
    }

    mock_get.side_effect = [mock_version_resp, mock_data_resp]

    id_map = client.fetch_champion_map()

    assert id_map[266] == "Aatrox"
    assert id_map[103] == "Ahri"


@patch("app.ingest.clients.ddragon.requests.get")
def test_save_champion_map(mock_get, client, tmp_path):
    mock_version_resp = MagicMock()
    mock_version_resp.json.return_value = ["14.1.1"]

    mock_data_resp = MagicMock()
    mock_data_resp.json.return_value = {"data": {"Aatrox": {"key": "266", "id": "Aatrox"}}}

    mock_get.side_effect = [mock_version_resp, mock_data_resp]

    out_file = tmp_path / "map.json"
    client.save_champion_map(out_file)

    assert out_file.exists()
    assert '"266": "Aatrox"' in out_file.read_text()
