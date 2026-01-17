import { render, screen, fireEvent } from '@testing-library/react';
import { TeamColumn } from '@/components/draft/TeamColumn';
import { Role } from '@/types';
import { describe, it, expect, vi } from 'vitest';

describe('TeamColumn', () => {
    const mockClick = vi.fn();
    const mockChamps = [
        { id: 'Ahri', name: 'Ahri', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Ahri.png' },
        { id: 'Zed', name: 'Zed', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Zed.png' }
    ];
    const defaultProps = {
        side: 'blue' as const,
        picks: Array(5).fill(null),
        bans: Array(5).fill(null),
        activeSlot: null,
        targetRole: Role.TOP,
        onSlotClick: mockClick,
        champions: mockChamps
    };

    it('renders correct number of slots', () => {
        render(<TeamColumn {...defaultProps} />);
        // 5 bans, 5 picks
        // Bans have testid 'ban-slot-{side}-{idx}'
        expect(screen.getAllByTestId(/ban-slot/)).toHaveLength(5);
        // Picks have role text 'Select Champion' initially
        expect(screen.getAllByText('Select Champion')).toHaveLength(5);
    });

    it('renders picks and bans', () => {
        const picks = [...defaultProps.picks];
        picks[0] = 'Ahri';
        const bans = [...defaultProps.bans];
        bans[0] = 'Zed';

        render(<TeamColumn {...defaultProps} picks={picks} bans={bans} />);

        // Pick
        expect(screen.getByText('Ahri')).toBeInTheDocument();
        // Ban (image alt should correspond to champ?)
        // BanSlot renders RoleIcon if no champ, or Image if champ
        // Let's verify ban call on click
        fireEvent.click(screen.getByTestId('ban-slot-blue-0'));
        expect(mockClick).toHaveBeenCalledWith(0, 'ban');

        // Pick click
        fireEvent.click(screen.getByText('Ahri').closest('div')!.parentElement!);
        expect(mockClick).toHaveBeenCalledWith(0, 'pick');
    });

    it('handles red side alignment', () => {
        const { container } = render(<TeamColumn {...defaultProps} side="red" />);
        expect(container.firstChild).toHaveClass('items-end');
    });
});
