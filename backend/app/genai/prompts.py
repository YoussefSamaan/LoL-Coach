class DraftPrompts:
    """Collection of prompts for draft recommendations."""

    @staticmethod
    def simple_explanation(champion_name: str, team_comp: list[str], enemy_comp: list[str]) -> str:
        """
        Generates a simple prompt to explain a champion pick (legacy/fallback).
        """
        ally_str = ", ".join(team_comp) if team_comp else "None"
        enemy_str = ", ".join(enemy_comp) if enemy_comp else "None"

        return f"""
You are a professional League of Legends coach.
Your task is to explain why picking {champion_name} is the best strategic choice given the current draft.

Current State:
- Ally Team: {ally_str}
- Enemy Team: {enemy_str}

Requirements:
1. Focus on synergies with allies and counters to enemies.
2. Keep the explanation concise (under 50 words).
3. Use a professional, analytical tone.

Explanation:
""".strip()

    @staticmethod
    def explain_with_strict_structure(
        *,
        patch: str,
        role: str,
        champion: str,
        overall_score: float | str,
        ally_list: str,
        enemy_list: str,
        synergy_evidence: str,
        counter_evidence: str,
    ) -> str:
        """
        Prompt for a strictly formatted 3-line explanation using provided evidence.
        """
        return f"""
You are a LoL draft coach. Your job is to explain why THIS champion is a good pick in THIS draft context.
You MUST use ONLY the evidence I provide (scores/labels). Do NOT invent patch notes, winrates, or matchup facts.

INPUT
- Patch: {patch}
- Role: {role}
- Candidate champion: {champion}
- Overall score: {overall_score}
- Allies: {ally_list}
- Enemies: {enemy_list}

Evidence (my model outputs):
Synergy vs allies (higher = better):
{synergy_evidence}

Counters vs enemies (higher = better for {champion} into that enemy):
{counter_evidence}

Each row has: target_champ, score, label where label ∈ {{ "good", "careful", "avoid" }}.

OUTPUT (STRICT)
Return EXACTLY 3 lines, no extra text:
1) "{champion} — score={overall_score} (patch {patch}, role {role})."
2) "Why it fits our team: <1 sentence citing 1-2 ally synergies with their scores + labels>."
3) "Why it fits vs them: <1 sentence citing 1-2 enemy counters with their scores + labels; if mostly 'avoid', say so>."

Rules:
- 1 sentence max on line 2 and line 3.
- Mention at least one ally by name on line 2 and one enemy by name on line 3.
- Prefer the strongest evidence: pick the top 1-2 synergies and top 1-2 counters by score, but do not mention more than 2 names per line.
- If top evidence is weak/negative (labels "careful"/"avoid"), say that directly.
""".strip()

    @staticmethod
    def explain_concise_2_sentences(
        *,
        patch: str,
        role: str,
        champion: str,
        overall_score: float | str,
        synergy_evidence: str,
        counter_evidence: str,
    ) -> str:
        """
        Prompt for a concise 2-sentence explanation using provided evidence.
        """
        return f"""
You are a LoL draft coach. Use ONLY the provided numeric evidence. No patch-note claims.

Patch: {patch}
Role: {role}
Champion: {champion}
Overall score: {overall_score}

Synergy (ally -> score, label): {synergy_evidence}
Counters (enemy -> score, label): {counter_evidence}

Write EXACTLY 2 sentences:
- Sentence 1: why {champion} is good with our allies (cite 1-2 allies + scores + labels).
- Sentence 2: why {champion} is good/bad into enemies (cite 1-2 enemies + scores + labels, and mention if there’s an "avoid" threat).
No extra text.
""".strip()
