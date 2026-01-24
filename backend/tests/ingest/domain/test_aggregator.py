import pandas as pd
import json
from app.ingest.domain.aggregator import compute_aggregates


def test_compute_aggregates_basic():
    # 1 Match: Blue Wins
    # Blue: Aatrox(Top), Ahri(Mid) ... (assume others irrelevant for minimal test)
    # Red:  Darius(Top), Zed(Mid)

    blue_team = [
        {"c": "Aatrox", "r": "top"},
        {"c": "Ahri", "r": "mid"},
        {"c": "X", "r": "jungle"},
        {"c": "Y", "r": "adc"},
        {"c": "Z", "r": "support"},
    ]
    red_team = [
        {"c": "Darius", "r": "top"},
        {"c": "Zed", "r": "mid"},
        {"c": "A", "r": "jungle"},
        {"c": "B", "r": "adc"},
        {"c": "C", "r": "support"},
    ]

    row = {"blue_team": json.dumps(blue_team), "red_team": json.dumps(red_team), "winner": "BLUE"}
    df = pd.DataFrame([row])

    stats = compute_aggregates(df)

    # Check Aatrox (Winner)
    s = stats["Aatrox"]
    assert s["games"] == 1
    assert s["wins"] == 1
    assert s["roles"]["top"]["games"] == 1
    assert s["roles"]["top"]["wins"] == 1

    # Synergy: Aatrox with Ahri
    assert s["synergy"]["Ahri"]["games"] == 1
    assert s["synergy"]["Ahri"]["wins"] == 1
    # Check exclusion of self (Aatrox shouldn't be in Aatrox's synergy)
    assert "Aatrox" not in s["synergy"]

    # Counter: Aatrox vs Darius
    assert s["counter"]["Darius"]["games"] == 1
    assert s["counter"]["Darius"]["wins"] == 1

    # Check Darius (Loser)
    d = stats["Darius"]
    assert d["games"] == 1
    assert d["wins"] == 0
    # Counter: Darius vs Aatrox
    assert d["counter"]["Aatrox"]["games"] == 1
    assert d["counter"]["Aatrox"]["wins"] == 0


def test_compute_aggregates_red_win():
    blue_team = [{"c": "A", "r": "top"}]  # Minimal list implementation
    red_team = [{"c": "B", "r": "top"}]

    row = {"blue_team": json.dumps(blue_team), "red_team": json.dumps(red_team), "winner": "RED"}
    df = pd.DataFrame([row])

    stats = compute_aggregates(df)

    # B (Red) won
    assert stats["B"]["wins"] == 1
    # A (Blue) lost
    assert stats["A"]["wins"] == 0
