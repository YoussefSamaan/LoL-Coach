import { useState, useCallback } from 'react';
import { Recommendation, Role, Champion } from '@/types';
import { DraftState } from './useDraft';

export const useRecommendations = (draft: DraftState, setDraft: React.Dispatch<React.SetStateAction<DraftState>>, championList: Champion[]) => {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Helper to fetch explanations
    const fetchExplanations = useCallback(async (backendUrl: string, role: Role, recs: Recommendation[]) => {
        try {
            // Get current allies and enemies from draft state
            const cleanAllies = draft.allies.filter((c): c is string => !!c);
            const cleanEnemies = draft.enemies.filter((c): c is string => !!c);

            const explainPayload = {
                role: role,
                recommendations: recs.map(r => ({
                    champion: r.championId,
                    allies: cleanAllies,
                    enemies: cleanEnemies,
                    reasons: r.reasons || []
                }))
            };

            const response = await fetch(`${backendUrl}/v1/explain/draft`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(explainPayload)
            });

            if (response.ok) {
                const data = await response.json();

                interface ExplanationItem {
                    champion: string;
                    explanation: string;
                }

                // Update recommendations with new explanations
                setRecommendations(prevRecs => {
                    return prevRecs.map(rec => {
                        const explanation = data.explanations.find((e: ExplanationItem) => e.champion === rec.championId);
                        return explanation ? { ...rec, explanation: explanation.explanation } : rec;
                    });
                });
            }
        } catch (err) {
            console.error("Explanation fetch error:", err);
            // Fail silently, user still has recommendations
        }
    }, [draft.allies, draft.enemies]);

    const handlePredict = useCallback(async () => {
        // 2. Check if target role is already filled
        const roleIndex = [Role.TOP, Role.JUNGLE, Role.MID, Role.ADC, Role.SUPPORT].indexOf(draft.targetRole);
        const isRoleFilled = draft.allies[roleIndex] !== null;

        const currentAllies = [...draft.allies];

        if (isRoleFilled) {
            // If role is filled, we clear it for the prediction and update UI
            currentAllies[roleIndex] = null;
            setDraft(prev => {
                const newAllies = [...prev.allies];
                newAllies[roleIndex] = null;
                return { ...prev, allies: newAllies };
            });
        }

        const cleanAllies = currentAllies.filter((c): c is string => !!c);
        const cleanEnemies = draft.enemies.filter((c): c is string => !!c);
        const cleanBans = [...draft.allyBans, ...draft.enemyBans].filter((c): c is string => !!c);

        setLoading(true);
        setError(null);
        setRecommendations([]); // Clear previous

        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

            // Step 1: Get Recommendations (Fast)
            const response = await fetch(`${backendUrl}/v1/recommend/draft`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    role: draft.targetRole,
                    allies: cleanAllies,
                    enemies: cleanEnemies,
                    bans: cleanBans,
                    top_k: 3
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to fetch recommendations: ${errorText}`);
            }

            const data = await response.json();

            interface BackendRecommendation {
                champion: string;
                score: number;
                reasons?: string[];
                explanation?: string;
            }

            const mappedRecs: Recommendation[] = data.recommendations.map((r: BackendRecommendation) => {
                const championInfo = championList.find(c => c.id === r.champion);
                return {
                    championId: r.champion,
                    championName: championInfo ? championInfo.name : r.champion,
                    score: Math.round(r.score * 100),
                    primaryReason: r.reasons && r.reasons.length > 0 ? r.reasons[0] : 'Recommended based on draft state',
                    explanation: "", // Empty initially to show loading state
                    reasons: r.reasons || [] // Store reasons for explain request
                };
            });

            setRecommendations(mappedRecs);
            setLoading(false); // Stop main loading spinner

            // Step 2: Get Explanations (Async/Slow)
            // We do this without await so UI unblocks immediately
            fetchExplanations(backendUrl, draft.targetRole, mappedRecs);

        } catch (err) {
            console.error("Prediction Error:", err);
            setError('Failed to get recommendations');
            setLoading(false);
        }
    }, [draft, championList, setDraft, fetchExplanations]);

    // Return error as well, though existing components might not consume it yet
    return { recommendations, loading, error, handlePredict };
};
