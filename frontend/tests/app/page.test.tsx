import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import Home from '@/app/page';
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Home Page', () => {
    const mockFetch = vi.fn();
    let mockChampionData: Record<string, { id: string; name: string; image: { full: string } }> = {};

    beforeEach(() => {
        mockFetch.mockReset();
        mockChampionData = {};
        mockFetch.mockImplementation(async (input: RequestInfo | URL) => {
            let url = '';
            if (typeof input === 'string') {
                url = input;
            } else if (input instanceof URL) {
                url = input.toString();
            } else if (input && typeof input === 'object' && 'url' in input) {
                url = (input as Request).url;
            }

            if (url.includes('/version')) {
                return {
                    json: async () => ({ version: '0.1.0' })
                };
            }
            // Strict check for health to avoid overlap if ordering was wrong (though version check is first)
            if (url.endsWith('/health') || url.includes('/health?')) {
                return {
                    json: async () => ({ status: 'ok', service: 'lol-coach-backend' })
                };
            }
            if (url.includes('champion.json')) {
                if (!mockChampionData || Object.keys(mockChampionData).length === 0) {
                    return { json: async () => ({ data: {} }) };
                }
                return {
                    json: async () => ({
                        data: mockChampionData
                    })
                };
            }
            if (url.includes('/recommend/draft')) {
                return {
                    ok: true,
                    json: async () => ({
                        recommendations: [
                            { champion: 'Garen', score: 0.9, reasons: ['Good match'] },
                            { champion: 'Darius', score: 0.8, reasons: ['Lane bully'] },
                            { champion: 'Mordekaiser', score: 0.7, reasons: ['AP threat'] }
                        ]
                    })
                };
            }
            return {
                ok: true,
                json: async () => ({})
            };
        });
        global.fetch = mockFetch;
    });

    it('renders the draft board with correct roles', async () => {
        mockChampionData = {
            Aatrox: { id: 'Aatrox', name: 'Aatrox', image: { full: 'Aatrox.png' } }
        };

        render(<Home />);

        // Check Header
        expect(screen.getByRole('heading', { name: /LoL Draft/i })).toBeInTheDocument();

        // Check Blue Team Roles
        const roles = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
        roles.forEach(role => {
            expect(screen.getAllByText(role).length).toBe(2);
        });

        // Check Backend Status
        await waitFor(() => {
            expect(screen.getByText('System Online')).toBeInTheDocument();
            expect(screen.getByText('v0.1.0')).toBeInTheDocument();
        });
    });

    it('handles backend errors gracefully', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
        // Override mock for this test to fail
        mockFetch.mockRejectedValue(new Error('Network error'));

        render(<Home />);

        expect(screen.getByRole('heading', { name: /LoL Draft/i })).toBeInTheDocument();

        await waitFor(() => {
            expect(consoleSpy).toHaveBeenCalledWith('Failed to fetch champions', expect.any(Error));
        });

        consoleSpy.mockRestore();
    });

    it('allows picking champions, resetting, and updating recommendations', async () => {
        mockChampionData = {
            Aatrox: { id: 'Aatrox', name: 'Aatrox', image: { full: 'Aatrox.png' } },
            Ahri: { id: 'Ahri', name: 'Ahri', image: { full: 'Ahri.png' } }
        };

        render(<Home />);
        await waitFor(() => expect(screen.getByText('System Online')).toBeInTheDocument());

        // 1. Open Selector for Blue Top (First slot)
        const slots = screen.getAllByText('TOP');
        expect(slots[0]).toBeInTheDocument();
        fireEvent.click(slots[0].closest('div')!.parentElement!);

        const selectTexts = screen.getAllByText('Select Champion');
        fireEvent.click(selectTexts[0]);

        await waitFor(() => {
            expect(screen.getByPlaceholderText('Search Champion...')).toBeInTheDocument();
            expect(screen.getByText('Aatrox')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Aatrox'));

        await waitFor(() => {
            expect(screen.queryByPlaceholderText('Search Champion...')).not.toBeInTheDocument();
            expect(screen.getByText('Aatrox', { selector: '.font-lol.text-lg' })).toBeInTheDocument();
        });

        // Test Reset
        fireEvent.click(screen.getByText('Aatrox'));
        await waitFor(() => expect(screen.getByText('None')).toBeInTheDocument());
        fireEvent.click(screen.getByText('None'));

        await waitFor(() => {
            expect(screen.queryByText('Aatrox', { selector: '.font-lol.text-lg' })).not.toBeInTheDocument();
            expect(screen.getAllByText('Select Champion')[0]).toBeInTheDocument();
        });
    });

    it('filters champions in search', async () => {
        mockChampionData = {
            Aatrox: { id: 'Aatrox', name: 'Aatrox', image: { full: 'Aatrox.png' } },
            Ahri: { id: 'Ahri', name: 'Ahri', image: { full: 'Ahri.png' } },
            Zed: { id: 'Zed', name: 'Zed', image: { full: 'Zed.png' } }
        };

        render(<Home />);
        await waitFor(() => expect(screen.getByText('System Online')).toBeInTheDocument());

        const selectTexts = screen.getAllByText('Select Champion');
        fireEvent.click(selectTexts[0]);

        await waitFor(() => expect(screen.getByPlaceholderText('Search Champion...')).toBeInTheDocument());

        fireEvent.change(screen.getByPlaceholderText('Search Champion...'), { target: { value: 'Zed' } });

        await waitFor(() => {
            expect(screen.getByText('Zed')).toBeInTheDocument();
        });
        expect(screen.queryByText('Aatrox')).not.toBeInTheDocument();
        expect(screen.queryByText('Ahri')).not.toBeInTheDocument();
    });

    it('interacts with Red Team and Bans', async () => {
        mockChampionData = {
            Aatrox: { id: 'Aatrox', name: 'Aatrox', image: { full: 'Aatrox.png' } },
            Ahri: { id: 'Ahri', name: 'Ahri', image: { full: 'Ahri.png' } }
        };

        render(<Home />);
        await waitFor(() => expect(screen.getByText('System Online')).toBeInTheDocument());

        // 1. Click Red Team First Pick
        const selectTexts = screen.getAllByText('Select Champion');
        fireEvent.click(selectTexts[5]); // Red Top

        await waitFor(() => expect(screen.getAllByText('Aatrox').length).toBeGreaterThan(0));

        const aatroxInstances = screen.getAllByText('Aatrox');
        fireEvent.click(aatroxInstances[aatroxInstances.length - 1]);

        await waitFor(() => {
            expect(screen.getByText('Aatrox', { selector: '.font-lol.text-lg' })).toBeInTheDocument();
        });

        // 2. Click Blue Ban (First ban slot)
        const banSlot = screen.getByTestId('ban-slot-blue-0');
        fireEvent.click(banSlot);

        // Expect Ahri (mocked) to be available
        await waitFor(() => expect(screen.getAllByText('Ahri').length).toBeGreaterThan(0));

        const buttons = screen.getAllByRole('button');
        // Pick Ahri instead of Aatrox because Aatrox is taken
        const ahriBtn = buttons.find(b => b.textContent?.includes('Ahri') && !(b as HTMLButtonElement).disabled);
        fireEvent.click(ahriBtn!);

        await waitFor(() => expect(screen.queryByText('Search Champion...')).not.toBeInTheDocument());
    });

    it('handles prediction flow including filled role overwrite', async () => {
        mockChampionData = {
            Garen: { id: 'Garen', name: 'Garen', image: { full: 'Garen.png' } }
        };

        render(<Home />);
        await waitFor(() => expect(screen.getByText('System Online')).toBeInTheDocument());

        expect(screen.getByText(/Awaiting Draft Context/i)).toBeInTheDocument();
        const selectTexts = screen.getAllByText('Select Champion');
        fireEvent.click(selectTexts[0]);
        await waitFor(() => expect(screen.getByText('Garen')).toBeInTheDocument());
        fireEvent.click(screen.getByText('Garen'));
        await waitFor(() => expect(screen.queryByPlaceholderText('Search Champion...')).not.toBeInTheDocument());

        const predictBtn = screen.getByText('Predict');
        fireEvent.click(predictBtn);

        await waitFor(() => {
            const selects = screen.getAllByText('Select Champion');
            expect(selects[0]).toBeInTheDocument();
        });

        await waitFor(() => {
            expect(screen.getByText('Showing Top 3 Recommendations')).toBeInTheDocument();
        }, { timeout: 3000 });
    });
});
