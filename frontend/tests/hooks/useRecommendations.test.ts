import { renderHook, act } from '@testing-library/react';
import { useRecommendations } from '@/hooks/useRecommendations';
import { Role } from '@/types';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('useRecommendations', () => {
    const mockSetDraft = vi.fn();
    const mockChampions = [
        { id: 'Ahri', name: 'Ahri', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Ahri.png' },
        { id: 'Zed', name: 'Zed', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Zed.png' }
    ];
    const defaultDraft = {
        allies: Array(5).fill(null),
        enemies: Array(5).fill(null),
        allyBans: Array(5).fill(null),
        enemyBans: Array(5).fill(null),
        targetRole: Role.TOP
    };

    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('initializes correctly', () => {
        const { result } = renderHook(() => useRecommendations(defaultDraft, mockSetDraft, mockChampions));
        expect(result.current.recommendations).toEqual([]);
        expect(result.current.loading).toBe(false);
    });

    it('predicts and sets recommendations', async () => {
        const { result } = renderHook(() => useRecommendations(defaultDraft, mockSetDraft, mockChampions));

        act(() => {
            result.current.handlePredict();
        });

        expect(result.current.loading).toBe(true);

        await act(async () => {
            await vi.advanceTimersByTimeAsync(1000);
        });

        expect(result.current.loading).toBe(false);
        expect(result.current.recommendations.length).toBeGreaterThan(0);
        expect(result.current.recommendations[0].championName).toBeDefined();
    });

    it('clears filled role before predicting', () => {
        const draftWithFilledRole = {
            ...defaultDraft,
            allies: ['Garen', null, null, null, null], // Top is filled
            targetRole: Role.TOP
        };

        const { result } = renderHook(() => useRecommendations(draftWithFilledRole, mockSetDraft, mockChampions));

        act(() => {
            result.current.handlePredict();
        });

        // Expect setDraft call to clear role
        expect(mockSetDraft).toHaveBeenCalled();
        // Verify functional update logic if possible (mock calls)
        const updateFn = mockSetDraft.mock.calls[0][0];
        const newDraft = updateFn(draftWithFilledRole);
        expect(newDraft.allies[0]).toBeNull();
    });

    it('filters taken champions', async () => {
        const draftWithTaken = {
            ...defaultDraft,
            enemies: ['Ahri', null, null, null, null] // Ahri taken
        };

        const { result } = renderHook(() => useRecommendations(draftWithTaken, mockSetDraft, mockChampions));

        act(() => {
            result.current.handlePredict();
        });

        await act(async () => {
            await vi.advanceTimersByTimeAsync(1000);
        });

        // Recommendations should NOT contain Ahri
        const recNames = result.current.recommendations.map(r => r.championName);
        expect(recNames).not.toContain('Ahri');
        expect(recNames).toContain('Zed');
    });
});
