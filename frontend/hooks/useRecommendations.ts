import { useState, useCallback } from 'react';
import { Recommendation, Role, Champion } from '@/types';
import { DraftState } from './useDraft';

export const useRecommendations = (draft: DraftState, setDraft: React.Dispatch<React.SetStateAction<DraftState>>, championList: Champion[]) => {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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

        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/v1/recommend/draft`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    role: draft.targetRole,
                    allies: cleanAllies,
                    enemies: cleanEnemies,
                    bans: cleanBans,
                    top_k: 10
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to fetch recommendations: ${errorText}`);
            }

            const data = await response.json();

            // Map backend response to Recommendation type
            // Backend returns: 
            // recommendations: [{ champion: string, score: float, reasons: string[], ... }]

            const mappedRecs: Recommendation[] = data.recommendations.map((r: any) => {
                const championInfo = championList.find(c => c.id === r.champion);
                return {
                    championId: r.champion,
                    championName: championInfo ? championInfo.name : r.champion,
                    // Score is probability 0-1, Convert to 0-100 integer for UI
                    score: Math.round(r.score * 100),
                    primaryReason: r.reasons && r.reasons.length > 0 ? r.reasons[0] : 'Recommended based on draft state'
                };
            });

            setRecommendations(mappedRecs);

        } catch (err) {
            console.error("Prediction Error:", err);
            setError('Failed to get recommendations');
        } finally {
            setLoading(false);
        }
    }, [draft, championList, setDraft]);

    // Return error as well, though existing components might not consume it yet
    return { recommendations, loading, error, handlePredict };
};
