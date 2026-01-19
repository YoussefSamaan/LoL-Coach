from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from app.domain.enums import Role
from app.utils.logger import get_logger

logger = get_logger(__name__)

RIOT_ROLE_TO_DOMAIN = {
    "TOP": Role.TOP,
    "JUNGLE": Role.JUNGLE,
    "MIDDLE": Role.MID,
    "BOTTOM": Role.ADC,
    "UTILITY": Role.SUPPORT,
}


class MatchProcessor:
    def __init__(self, champion_map_path: Path):
        self.id_map = {}
        if champion_map_path.exists():
            try:
                self.id_map = json.loads(champion_map_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Champion map load failed: {e}")

    def parse_match_row(self, match_data: dict) -> dict | None:
        info = match_data.get("info", {})
        if info.get("gameMode") != "CLASSIC":
            return None

        row = {
            "match_id": match_data.get("metadata", {}).get("matchId"),
            "game_creation": info.get("gameCreation", 0),
            "blue_win": False,
        }

        for p in info.get("participants", []):
            team_id = p.get("teamId")
            c_name = p.get("championName")
            pos = p.get("teamPosition")

            if team_id == 100:
                row["blue_win"] = p.get("win", False)

            if pos in RIOT_ROLE_TO_DOMAIN:
                prefix = "blue" if team_id == 100 else "red"
                role_key = RIOT_ROLE_TO_DOMAIN[pos].lower()
                col_name = f"{prefix}_{role_key}"
                row[col_name] = c_name

        blue_bans: list[str] = []
        red_bans: list[str] = []
        for team in info.get("teams", []):
            is_blue = team.get("teamId") == 100
            target_list = blue_bans if is_blue else red_bans
            for ban in team.get("bans", []):
                cid = ban.get("championId")
                if cid and cid != -1:
                    cname = self.id_map.get(str(cid), str(cid))
                    target_list.append(cname)

        row["blue_bans"] = blue_bans
        row["red_bans"] = red_bans

        return row

    def process_dir(
        self, input_dir: Path, output_file: Path, min_time: int = 0, fmt: str = "parquet"
    ) -> None:
        """
        Reads JSONs -> parsing -> DataFrame -> [Parquet | CSV]
        """
        rows = []
        files = list(input_dir.glob("*.json"))

        logger.info(f"Processing {len(files)} matches from {input_dir.name}...")

        for f in files:
            try:
                raw = json.loads(f.read_text())

                creation = raw.get("info", {}).get("gameCreation", 0) // 1000
                if min_time > 0 and creation < min_time:
                    continue

                row = self.parse_match_row(raw)
                if row:
                    rows.append(row)
            except Exception:
                pass

        if not rows:
            logger.warning("No valid match entries found.")
            return

        df = pd.DataFrame(rows)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if fmt.lower() == "csv":
            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(df)} rows to {output_file} (CSV)")
        else:
            df.to_parquet(output_file, index=False)
            logger.info(f"Saved {len(df)} rows to {output_file} (Parquet)")
