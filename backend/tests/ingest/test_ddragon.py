import json
from unittest.mock import MagicMock, patch

from app.ingest.ddragon import DataDragonClient


def test_fetch_latest_version_success():
    client = DataDragonClient()
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = ["14.5.1", "14.4.1"]
        ver = client.fetch_latest_version()
        assert ver == "14.5.1"
        mock_get.assert_called_with("https://ddragon.leagueoflegends.com/api/versions.json")


def test_fetch_latest_version_failure():
    client = DataDragonClient()
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Network Down")
        ver = client.fetch_latest_version()
        assert ver == "14.1.1"  # Default fallback


def test_fetch_champion_map():
    client = DataDragonClient()

    # Mock version fetch
    with patch.object(client, "fetch_latest_version", return_value="14.1.1"):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": {
                    "Aatrox": {"key": "266", "id": "Aatrox"},
                    "Thresh": {"key": "412", "id": "Thresh"},
                }
            }
            mock_get.return_value = mock_resp

            result = client.fetch_champion_map()

            assert result[266] == "Aatrox"
            assert result[412] == "Thresh"
            mock_get.assert_called_with(
                "https://ddragon.leagueoflegends.com/cdn/14.1.1/data/en_US/champion.json"
            )


def test_save_champion_map(tmp_path):
    client = DataDragonClient()
    out_file = tmp_path / "champs.json"

    fake_map = {1: "Annie", 2: "Olaf"}

    with patch.object(client, "fetch_champion_map", return_value=fake_map):
        client.save_champion_map(out_file)

    assert out_file.exists()
    content = json.loads(out_file.read_text())
    assert content["1"] == "Annie"
    assert content["2"] == "Olaf"
