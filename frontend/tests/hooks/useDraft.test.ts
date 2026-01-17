import { renderHook, act } from '@testing-library/react';
import { useDraft } from '@/hooks/useDraft';
import { Role } from '@/types';
import { describe, it, expect } from 'vitest';

describe('useDraft', () => {
    it('initializes with default state', () => {
        const { result } = renderHook(() => useDraft());
        expect(result.current.draft.allies).toHaveLength(5);
        expect(result.current.draft.allies.every(x => x === null)).toBe(true);
        expect(result.current.draft.targetRole).toBe(Role.TOP);
        expect(result.current.selectorContext).toBeNull();
    });

    it('sets target role', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.setTargetRole(Role.MID);
        });
        expect(result.current.draft.targetRole).toBe(Role.MID);
    });

    it('opens selector on slot click', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(0, 'blue', 'pick');
        });
        expect(result.current.selectorContext).toEqual({
            idx: 0,
            destination: 'ally' // Blue Pick -> Ally
        });
    });

    it('handles red side pick -> enemy', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(1, 'red', 'pick');
        });
        expect(result.current.selectorContext?.destination).toBe('enemy');
    });

    it('handles ban click', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(2, 'blue', 'ban');
        });
        expect(result.current.selectorContext?.destination).toBe('allyBan');
    });

    it('selects champion', () => {
        const { result } = renderHook(() => useDraft());
        // Open selector first
        act(() => {
            result.current.handleSlotClick(0, 'blue', 'pick');
        });
        // Select
        act(() => {
            result.current.handleSelect('Ahri');
        });
        expect(result.current.draft.allies[0]).toBe('Ahri');
        expect(result.current.selectorContext).toBeNull();
    });

    it('closes selector', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(0, 'blue', 'pick');
        });
        act(() => {
            result.current.closeSelector();
        });
        expect(result.current.selectorContext).toBeNull();
    });

    it('handles red side ban -> enemyBan', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(0, 'red', 'ban');
        });
        expect(result.current.selectorContext?.destination).toBe('enemyBan');
    });

    it('updates enemy bans', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(0, 'red', 'ban');
        });
        act(() => {
            result.current.handleSelect('Zed');
        });
        expect(result.current.draft.enemyBans[0]).toBe('Zed');
    });

    it('does nothing if no context', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSelect('Zed');
        });
        expect(result.current.draft.allies.every(x => x === null)).toBe(true);
    });

    it('resets slot', () => {
        const { result } = renderHook(() => useDraft());
        act(() => {
            result.current.handleSlotClick(0, 'blue', 'pick');
        });
        act(() => {
            result.current.handleSelect('Ahri');
        });
        expect(result.current.draft.allies[0]).toBe('Ahri');

        // Reset
        act(() => {
            result.current.handleSlotClick(0, 'blue', 'pick');
        });
        act(() => {
            result.current.handleSelect('');
        });
        expect(result.current.draft.allies[0]).toBeNull();
    });
});
