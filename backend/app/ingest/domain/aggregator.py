from __future__ import annotations

import pandas as pd
import json


def compute_aggregates(df: pd.DataFrame) -> dict:
    """
    Process Clean Matches into Stats Grid (Role Winrates, Synergy, Counters).

    Args:
        df: DataFrame containing 'Clean Match' objects.
            Columns expected: [blue_team, red_team, winner]
            Teams are JSON-serialized lists of {c: champ, r: role}.

    Returns:
        dict: A nested dictionary of stats.

        Example Output:
        {
            "Aatrox": {
                "wins": 10,
                "games": 20,
                "roles": {
                    "top": { "wins": 10, "games": 20 }
                },
                "synergy": {
                    "Ahri": { "wins": 5, "games": 8 }
                },
                "counter": {
                    "Darius": { "wins": 2, "games": 5 }
                }
            }
        }
    """
    stats = {}

    def update_stats(champion_name, role, is_win, allied_champions, enemy_champions):
        if champion_name not in stats:
            stats[champion_name] = {
                "wins": 0,
                "games": 0,
                "roles": {},
                "synergy": {},
                "counter": {},
            }

        champion_stats = stats[champion_name]
        champion_stats["games"] += 1
        if is_win:
            champion_stats["wins"] += 1

        # Role Stats
        if role not in champion_stats["roles"]:
            champion_stats["roles"][role] = {"wins": 0, "games": 0}
        champion_stats["roles"][role]["games"] += 1
        if is_win:
            champion_stats["roles"][role]["wins"] += 1

        # Synergy Stats (Allies)
        # Note: Input data uses 'c' (champion) and 'r' (role) keys for storage efficiency
        for ally in allied_champions:
            ally_champion_name = ally["c"]
            if ally_champion_name not in champion_stats["synergy"]:
                champion_stats["synergy"][ally_champion_name] = {"wins": 0, "games": 0}
            champion_stats["synergy"][ally_champion_name]["games"] += 1
            if is_win:
                champion_stats["synergy"][ally_champion_name]["wins"] += 1

        # Counter Stats (Enemies)
        for enemy in enemy_champions:
            enemy_champion_name = enemy["c"]
            if enemy_champion_name not in champion_stats["counter"]:
                champion_stats["counter"][enemy_champion_name] = {"wins": 0, "games": 0}
            champion_stats["counter"][enemy_champion_name]["games"] += 1
            if is_win:
                champion_stats["counter"][enemy_champion_name]["wins"] += 1

    def process_team(team_champions, opponent_champions, is_win):
        for champion in team_champions:
            # The other 4 champions on the same team are "Allies" (Synergy).
            # We filter out the champion itself to prevent self-synergy.
            allied_champions = [x for x in team_champions if x["c"] != champion["c"]]
            # The 5 Opposing champions are "Enemies" (Counters)
            enemy_champions = opponent_champions

            update_stats(champion["c"], champion["r"], is_win, allied_champions, enemy_champions)

    for _, row in df.iterrows():
        # Deserialize teams
        blue_team_champions = json.loads(row["blue_team"])
        red_team_champions = json.loads(row["red_team"])
        winner = row["winner"]

        # 1. Process Blue Team
        process_team(
            team_champions=blue_team_champions,
            opponent_champions=red_team_champions,
            is_win=(winner == "BLUE"),
        )

        # 2. Process Red Team
        process_team(
            team_champions=red_team_champions,
            opponent_champions=blue_team_champions,
            is_win=(winner == "RED"),
        )

    return stats
