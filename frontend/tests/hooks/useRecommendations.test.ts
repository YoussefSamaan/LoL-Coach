import { renderHook, act } from '@testing-library/react';
import { useRecommendations } from '@/hooks/useRecommendations';
import { Role } from '@/types';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Define Fetch Mock
const mockFetch = vi.fn();
global.fetch = mockFetch;

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
        mockFetch.mockReset();
        mockSetDraft.mockReset();
    });

    it('initializes correctly', () => {
        const { result } = renderHook(() => useRecommendations(defaultDraft, mockSetDraft, mockChampions));
        expect(result.current.recommendations).toEqual([]);
        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBeNull();
    });

    it('predicts and sets recommendations', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                recommendations: [
                    { champion: 'Ahri', score: 0.85, reasons: ['Synergy'] }
                ]
            })
        });

        const { result } = renderHook(() => useRecommendations(defaultDraft, mockSetDraft, mockChampions));

        await act(async () => {
            await result.current.handlePredict();
        });

        expect(result.current.loading).toBe(false);
        expect(result.current.recommendations).toHaveLength(1);
        expect(result.current.recommendations[0].championName).toBe('Ahri');
        expect(result.current.recommendations[0].score).toBe(85); // 0.85 * 100
        expect(mockFetch).toHaveBeenCalledWith(
            expect.stringContaining('/v1/recommend/draft'),
            expect.objectContaining({
                method: 'POST',
                body: expect.any(String)
            })
        );
    });

    it('clears filled role before predicting', async () => {
        const draftWithFilledRole = {
            ...defaultDraft,
            allies: ['Garen', null, null, null, null], // Top is filled
            targetRole: Role.TOP
        };

        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ recommendations: [] })
        });

        const { result } = renderHook(() => useRecommendations(draftWithFilledRole, mockSetDraft, mockChampions));

        await act(async () => {
            await result.current.handlePredict();
        });

        // Expect setDraft call to clear role
        expect(mockSetDraft).toHaveBeenCalled();
        const updateFn = mockSetDraft.mock.calls[0][0];
        // Mock the functional update
        const prev = { ...draftWithFilledRole };
        const newDraft = updateFn(prev);
        expect(newDraft.allies[0]).toBeNull();
    });

    it('handles error state correctly', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            text: async () => 'Internal Server Error'
        });

        const { result } = renderHook(() => useRecommendations(defaultDraft, mockSetDraft, mockChampions));

        await act(async () => {
            await result.current.handlePredict();
        });

        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBe('Failed to get recommendations');
        expect(result.current.recommendations).toEqual([]);
    });

    it('sends correct payload structure', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ recommendations: [] })
        });

        const { result } = renderHook(() => useRecommendations(defaultDraft, mockSetDraft, mockChampions));

        await act(async () => {
            await result.current.handlePredict();
        });

        const expectedPayload = {
            role: defaultDraft.targetRole,
            allies: [],
            enemies: [],
            bans: [],
            top_k: 10
        };

        const callArgs = mockFetch.mock.calls[0];
        const requestBody = JSON.parse(callArgs[1].body);

        expect(requestBody).toEqual(expectedPayload);
    });
});
