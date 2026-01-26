from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone

from app.utils.logger import get_logger
from app.domain.enums import Role

RIOT_ROLE_TO_DOMAIN = {
    "TOP": Role.TOP,
    "JUNGLE": Role.JUNGLE,
    "MIDDLE": Role.MID,
    "BOTTOM": Role.ADC,
    "UTILITY": Role.SUPPORT,
}

logger = get_logger(__name__)


def parse_match_row(match_data: dict, id_map: dict, rank_ctx: dict) -> dict | None:
    """
    Parses Raw JSON into a 'Clean Match' Object.

    Args:
        match_data (dict): The raw JSON dictionary from Riot API.
        id_map (dict): Mapping of Champion ID (int) -> Name (str).
        rank_ctx (dict): Context info {tier, division, region} for this match.

    Returns:
        dict | None: The flattened clean match object, or None if invalid.
    """
    info = match_data.get("info", {})
    metadata = match_data.get("metadata", {})

    if info.get("gameMode") != "CLASSIC":
        return None

    # Extract Patch
    game_version = info.get("gameVersion", "0.0.0")
    patch_parts = game_version.split(".")
    patch = f"{patch_parts[0]}.{patch_parts[1]}" if len(patch_parts) >= 2 else game_version

    # Date
    game_creation = info.get("gameCreation", 0)
    date_str = datetime.fromtimestamp(game_creation // 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    match_id = metadata.get("matchId")

    # Rank Context
    tier = rank_ctx.get("tier", "UNKNOWN")
    division = rank_ctx.get("division", "IV")

    # Teams
    blue_team = []
    red_team = []
    blue_win = False

    for p in info.get("participants", []):
        team_id = p.get("teamId")
        champ = p.get("championName")
        pos = p.get("teamPosition")

        # Skip invalid roles/champs
        if not champ or pos not in RIOT_ROLE_TO_DOMAIN:
            logger.warning(f"Match id: [{match_id}] Invalid role/champ: {champ} ({pos})")
            continue

        entry = {"c": champ, "r": RIOT_ROLE_TO_DOMAIN[pos].lower()}

        # In Riot API, Team ID 100 is always Blue Team, 200 is Red Team.
        if team_id == 100:
            blue_team.append(entry)
            blue_win = p.get("win", False)
        else:
            red_team.append(entry)

    if len(blue_team) != 5 or len(red_team) != 5:
        duration = info.get("gameDuration", 0)
        logger.warning(
            f"Match id: [{match_id}] Invalid team size (Duration: {duration}s): \n"
            f"Blue={len(blue_team)}, Red={len(red_team)}\n"
            f"Blue Team: {blue_team}\n"
            f"Red Team: {red_team}"
        )
        return None

    # Bans
    blue_bans: list[str] = []
    red_bans: list[str] = []
    for team in info.get("teams", []):
        is_blue = team.get("teamId") == 100
        target = blue_bans if is_blue else red_bans
        for ban in team.get("bans", []):
            cid = str(ban.get("championId"))
            # " -1" often signifies no ban in Riot API
            if cid == "-1":
                continue

            cname = id_map.get(cid)
            if cname:
                target.append(cname)
            else:
                logger.warning(f"Match id: [{match_id}] Invalid ban: {cid}")

    return {
        "match_id": match_id,
        "day": date_str,
        "patch": patch,
        "tier": tier,
        "division": division,
        "blue_team": json.dumps(blue_team),
        "red_team": json.dumps(red_team),
        "blue_bans": blue_bans,
        "red_bans": red_bans,
        "winner": "BLUE" if blue_win else "RED",
    }
