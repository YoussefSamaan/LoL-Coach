import { useState, useCallback } from 'react';
import { Role } from '@/types';

export interface SelectorContext {
    idx: number;
    destination: 'ally' | 'enemy' | 'allyBan' | 'enemyBan';
}

export interface DraftState {
    allies: (string | null)[];
    enemies: (string | null)[];
    allyBans: (string | null)[];
    enemyBans: (string | null)[];
    targetRole: Role;
}

export const useDraft = () => {
    const [draft, setDraft] = useState<DraftState>({
        allies: Array(5).fill(null),
        enemies: Array(5).fill(null),
        allyBans: Array(5).fill(null),
        enemyBans: Array(5).fill(null),
        targetRole: Role.TOP,
    });

    const [selectorContext, setSelectorContext] = useState<SelectorContext | null>(null);

    const handleSlotClick = useCallback((index: number, side: 'blue' | 'red', type: 'pick' | 'ban') => {
        let dest: 'ally' | 'enemy' | 'allyBan' | 'enemyBan';

        if (type === 'ban') {
            dest = side === 'blue' ? 'allyBan' : 'enemyBan';
        } else {
            dest = side === 'blue' ? 'ally' : 'enemy';
        }
        setSelectorContext({ idx: index, destination: dest });
    }, []);

    const handleSelect = useCallback((champId: string) => {
        if (!selectorContext) return;
        const { idx, destination } = selectorContext;
        // Handle Reset (empty string)
        const valueToSet = champId === '' ? null : champId;

        setDraft(prev => {
            const next = { ...prev };
            if (destination === 'ally') next.allies = [...next.allies.slice(0, idx), valueToSet, ...next.allies.slice(idx + 1)];
            if (destination === 'enemy') next.enemies = [...next.enemies.slice(0, idx), valueToSet, ...next.enemies.slice(idx + 1)];
            if (destination === 'allyBan') next.allyBans = [...next.allyBans.slice(0, idx), valueToSet, ...next.allyBans.slice(idx + 1)];
            if (destination === 'enemyBan') next.enemyBans = [...next.enemyBans.slice(0, idx), valueToSet, ...next.enemyBans.slice(idx + 1)];
            return next;
        });
        setSelectorContext(null);
    }, [selectorContext]);

    const setTargetRole = useCallback((role: Role) => {
        setDraft(d => ({ ...d, targetRole: role }));
    }, []);

    const closeSelector = useCallback(() => {
        setSelectorContext(null);
    }, []);

    return {
        draft,
        setDraft,
        selectorContext,
        handleSlotClick,
        handleSelect,
        closeSelector,
        setTargetRole
    };
};
