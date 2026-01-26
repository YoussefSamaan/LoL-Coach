from app.genai.prompts import DraftPrompts


def test_simple_explanation():
    """Test generating simple explanation prompt."""
    prompt = DraftPrompts.simple_explanation(
        champion_name="Ahri", team_comp=["Malphite"], enemy_comp=["Zed"]
    )

    assert "Ahri" in prompt
    assert "Malphite" in prompt
    assert "Zed" in prompt
    assert "Requirements" in prompt


def test_explain_with_strict_structure():
    """Test strict structure prompt generation."""
    prompt = DraftPrompts.explain_with_strict_structure(
        patch="14.1",
        role="MID",
        champion="Ahri",
        overall_score=8.5,
        ally_list="Malphite",
        enemy_list="Zed",
        synergy_evidence="Good synergy",
        counter_evidence="Bad counter",
    )

    assert "Patch: 14.1" in prompt
    assert "Role: MID" in prompt
    assert "Ahri" in prompt
    assert "Evidence (my model outputs):" in prompt
    assert "OUTPUT (STRICT)" in prompt


def test_explain_concise_2_sentences():
    """Test concise 2-sentence prompt generation."""
    prompt = DraftPrompts.explain_concise_2_sentences(
        patch="14.1",
        role="MID",
        champion="Ahri",
        overall_score=8.5,
        synergy_evidence="Good synergy",
        counter_evidence="Bad counter",
    )

    assert "EXACTLY 2 sentences" in prompt
    assert "Patch: 14.1" in prompt
    assert "Ahri" in prompt
