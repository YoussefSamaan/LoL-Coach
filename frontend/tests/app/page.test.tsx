import { render, screen, waitFor } from '@testing-library/react';
import Home from '@/app/page';
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Home Page', () => {
    const mockFetch = vi.fn();

    beforeEach(() => {
        mockFetch.mockReset();
        global.fetch = mockFetch;
    });

    it('renders the draft board with correct roles', async () => {
        // Mock successful backend responses
        mockFetch
            .mockResolvedValueOnce({
                json: async () => ({ status: 'ok', service: 'lol-coach-backend' }),
            })
            .mockResolvedValueOnce({
                json: async () => ({ version: '0.1.0' }),
            });

        render(<Home />);

        // Check Header
        expect(screen.getByText('LoL Coach Draft M0')).toBeInTheDocument();

        // Check Blue Team Roles
        const roles = ['Top', 'Jungle', 'Mid', 'Bot', 'Support'];
        roles.forEach(role => {
            // Using getAllByText because roles appear twice (once for Blue, once for Red)
            expect(screen.getAllByText(role).length).toBe(2);
        });

        // Check Backend Status (Wait for fetch)
        await waitFor(() => {
            expect(screen.getByText(/"status": "ok"/)).toBeInTheDocument();
            expect(screen.getByText(/"version": "0.1.0"/)).toBeInTheDocument();
        });
    });

    it('handles backend errors gracefully', async () => {
        // Mock fetch error
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
        mockFetch.mockRejectedValue(new Error('Network error'));

        render(<Home />);

        // Backend status should imply null or stay empty, but the page should still render
        expect(screen.getByText('LoL Coach Draft M0')).toBeInTheDocument();

        // Check error logging
        await waitFor(() => {
            expect(consoleSpy).toHaveBeenCalledWith('Health fetch error:', expect.any(Error));
            expect(consoleSpy).toHaveBeenCalledWith('Version fetch error:', expect.any(Error));
        });

        consoleSpy.mockRestore();
    });
});
