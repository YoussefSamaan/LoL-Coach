import { renderHook, waitFor } from '@testing-library/react';
import { useSystemStatus } from '@/hooks/useSystemStatus';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('useSystemStatus', () => {
    const mockFetch = vi.fn();

    beforeEach(() => {
        global.fetch = mockFetch;
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('returns default status initially', () => {
        // Need to simulate pending fetch so we see initial state
        mockFetch.mockImplementation(() => new Promise(() => { }));
        const { result } = renderHook(() => useSystemStatus());
        expect(result.current.systemStatus).toBe('OFFLINE');
        expect(result.current.version).toBe('v0.0.0');
    });

    it('updates status on successful fetch', async () => {
        mockFetch
            .mockResolvedValueOnce({
                json: async () => ({ status: 'ok' })
            })
            .mockResolvedValueOnce({
                json: async () => ({ version: '1.2.3' })
            });

        const { result } = renderHook(() => useSystemStatus());

        await waitFor(() => {
            expect(result.current.systemStatus).toBe('ONLINE');
            expect(result.current.version).toBe('v1.2.3');
        });
    });

    it('handles fetch errors', async () => {
        mockFetch.mockRejectedValue(new Error('Network error'));
        const { result } = renderHook(() => useSystemStatus());

        // Wait a bit to ensure effects ran
        await waitFor(() => {
            expect(result.current.systemStatus).toBe('OFFLINE');
            // Version remains default
            expect(result.current.version).toBe('v0.0.0');
        });
    });

    it('handles non-ok status', async () => {
        mockFetch
            .mockResolvedValueOnce({
                json: async () => ({ status: 'maintenance' })
            })
            .mockResolvedValueOnce({
                json: async () => ({ version: '1.2.3' })
            });

        const { result } = renderHook(() => useSystemStatus());

        await waitFor(() => {
            expect(result.current.systemStatus).toBe('OFFLINE');
            expect(result.current.version).toBe('v1.2.3');
        });
    });
});
