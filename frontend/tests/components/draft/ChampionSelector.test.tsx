import { render, screen, fireEvent } from '@testing-library/react';
import ChampionSelector from '@/components/draft/ChampionSelector';
import { describe, it, expect, vi } from 'vitest';

describe('ChampionSelector', () => {
    const mockSelect = vi.fn();
    const mockClose = vi.fn();
    const mockChamps = [
        { id: 'Ahri', name: 'Ahri', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Ahri.png' },
        { id: 'Zed', name: 'Zed', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Zed.png' },
        { id: 'Yasuo', name: 'Yasuo', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Yasuo.png' }
    ];

    it('renders champions and search bar', () => {
        render(
            <ChampionSelector
                champions={mockChamps}
                onSelect={mockSelect}
                onClose={mockClose}
                disabledIds={new Set()}
            />
        );
        expect(screen.getByPlaceholderText('Search Champion...')).toBeInTheDocument();
        expect(screen.getByText('Ahri')).toBeInTheDocument();
        expect(screen.getByText('Zed')).toBeInTheDocument();
    });

    it('filters champions', () => {
        render(
            <ChampionSelector
                champions={mockChamps}
                onSelect={mockSelect}
                onClose={mockClose}
                disabledIds={new Set()}
            />
        );
        fireEvent.change(screen.getByPlaceholderText('Search Champion...'), { target: { value: 'Zed' } });
        expect(screen.getByText('Zed')).toBeInTheDocument();
        expect(screen.queryByText('Ahri')).not.toBeInTheDocument();
    });

    it('disables taken champions', () => {
        const taken = new Set(['Ahri']);
        render(
            <ChampionSelector
                champions={mockChamps}
                onSelect={mockSelect}
                onClose={mockClose}
                disabledIds={taken}
            />
        );
        const ahriBtn = screen.getByText('Ahri').closest('button');
        expect(ahriBtn).toBeDisabled();
        expect(ahriBtn).toHaveClass('opacity-20', 'cursor-not-allowed');

        const zedBtn = screen.getByText('Zed').closest('button');
        expect(zedBtn).not.toBeDisabled();
    });

    it('calls onSelect when champion clicked', () => {
        render(
            <ChampionSelector
                champions={mockChamps}
                onSelect={mockSelect}
                onClose={mockClose}
                disabledIds={new Set()}
            />
        );
        fireEvent.click(screen.getByText('Zed'));
        expect(mockSelect).toHaveBeenCalledWith('Zed');
    });

    it('allows clearing selection (None)', () => {
        render(
            <ChampionSelector
                champions={mockChamps}
                onSelect={mockSelect}
                onClose={mockClose}
                disabledIds={new Set()}
            />
        );
        fireEvent.click(screen.getByText('None'));
        expect(mockSelect).toHaveBeenCalledWith('');
    });


});
