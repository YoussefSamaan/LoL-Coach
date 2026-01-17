import { renderHook, waitFor } from '@testing-library/react';
import { useChampions } from '@/hooks/useChampions';
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('useChampions', () => {
    const mockFetch = vi.fn();

    beforeEach(() => {
        global.fetch = mockFetch;
    });

    it('fetches and formats champions', async () => {
        const mockData = {
            data: {
                Aatrox: { id: 'Aatrox', name: 'Aatrox', image: { full: 'Aatrox.png' } },
                Zed: { id: 'Zed', name: 'Zed', image: { full: 'Zed.png' } }
            }
        };

        mockFetch.mockResolvedValueOnce({
            json: async () => mockData
        });

        const { result } = renderHook(() => useChampions());

        await waitFor(() => {
            expect(result.current).toHaveLength(2);
        });

        expect(result.current[0]).toEqual({
            id: 'Aatrox',
            name: 'Aatrox',
            image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Aatrox.png'
        });
    });

    it('handles fetch error gracefully', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
        mockFetch.mockRejectedValue(new Error('Fail'));

        const { result } = renderHook(() => useChampions());

        // Should remain empty (initial state)
        await waitFor(() => expect(consoleSpy).toHaveBeenCalled());
        expect(result.current).toEqual([]);

        consoleSpy.mockRestore();
    });
});
