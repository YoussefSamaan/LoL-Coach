from __future__ import annotations

import json
import requests
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataDragonClient:
    """
    Handles interactions with Riot's DataDragon CDN for static data.
    """

    BASE_URL = "https://ddragon.leagueoflegends.com"

    def fetch_latest_version(self) -> str:
        """
        Retrieves the latest version string (e.g., '14.1.1').
        """
        try:
            url = f"{self.BASE_URL}/api/versions.json"
            versions = requests.get(url).json()
            latest = versions[0]
            logger.info(f"Latest DataDragon version: {latest}")
            return latest
        except Exception as e:
            logger.warning(f"Failed to fetch version: {e}. Defaulting to hardcoded fallback.")
            return "14.1.1"

    def fetch_champion_map(self) -> dict[int, str]:
        """
        Downloads champion data and returns {id: name} mapping.
        """
        version = self.fetch_latest_version()
        url = f"{self.BASE_URL}/cdn/{version}/data/en_US/champion.json"

        logger.info(f"Fetching champion data from {url}...")
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        id_map = {}
        for _, entry in data["data"].items():
            # Riot uses 'key' for ID (e.g. 266), 'id' for string ID (e.g. "Aatrox")
            key = int(entry["key"])
            name = entry["id"]
            id_map[key] = name

        return id_map

    def save_champion_map(self, output_path: Path) -> None:
        """
        Fetches and saves the map to a JSON file.
        """
        champion_map = self.fetch_champion_map()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(champion_map, indent=2), encoding="utf-8")
        logger.info(f"Saved {len(champion_map)} champions to {output_path}")
