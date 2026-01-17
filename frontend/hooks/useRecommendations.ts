import { useState, useCallback } from 'react';
import { Recommendation, Role, Champion } from '@/types';
import { DraftState } from './useDraft';

export const useRecommendations = (draft: DraftState, setDraft: React.Dispatch<React.SetStateAction<DraftState>>, championList: Champion[]) => {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(false);

    const handlePredict = useCallback(() => {
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

        // 1. Construct Payload (using potentially updated allies)
        const myTeam = currentAllies;
        const enemyTeam = draft.enemies;
        const bans = [...draft.allyBans, ...draft.enemyBans];
        const payload = {
            myTeam,
            enemyTeam,
            bans,
            targetRole: draft.targetRole
        };

        console.log("Sending to Backend:", payload);

        setLoading(true);

        // Mock Backend Delay
        setTimeout(() => {
            // Filter candidates
            const taken = new Set([...currentAllies, ...draft.enemies, ...draft.allyBans, ...draft.enemyBans].filter(Boolean));
            const candidates = championList.filter(c => !taken.has(c.id));

            const recs: Recommendation[] = candidates.slice(0, 8).map(c => ({
                championId: c.id,
                championName: c.name,
                score: Math.floor(Math.random() * 30) + 70,
                primaryReason: 'Great synergy with team composition'
            })).sort((a, b) => b.score - a.score);

            setRecommendations(recs);
            setLoading(false);
        }, 500);
    }, [draft, championList, setDraft]);

    return { recommendations, loading, handlePredict };
};
