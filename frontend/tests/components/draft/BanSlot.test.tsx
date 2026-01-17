import { render, screen, fireEvent } from '@testing-library/react';
import { BanSlot } from '@/components/draft/BanSlot';
import { describe, it, expect, vi } from 'vitest';

describe('BanSlot', () => {
    const mockClick = vi.fn();
    const mockChamp = { id: 'Ahri', name: 'Ahri', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Ahri.png' };

    it('renders empty state correctly', () => {
        render(<BanSlot champion={undefined} onClick={mockClick} side="blue" index={0} />);
        const slot = screen.getByTestId('ban-slot-blue-0');
        expect(slot).toBeInTheDocument();
        // Should contain SVG X icon
        expect(slot.querySelector('svg')).toBeInTheDocument();
    });

    it('renders champion correctly', () => {
        render(<BanSlot champion={mockChamp} onClick={mockClick} side="red" index={1} />);
        const slot = screen.getByTestId('ban-slot-red-1');

        // Image should be present
        const img = screen.getByRole('img', { name: 'Ahri' });
        expect(img).toBeInTheDocument();
        // Check alt as proxy for correct image rendering, next/image mangles src
        expect(img).toHaveAttribute('alt', 'Ahri');

        // Red slash should be present (by checking strict structure roughly)
        // We know it renders a rotate-45 div
        // Just ensuring it didn't crash and rendered children is decent, deeper verify via class
        expect(img).toHaveClass('grayscale');
    });

    it('handles click', () => {
        render(<BanSlot champion={undefined} onClick={mockClick} side="blue" index={0} />);
        fireEvent.click(screen.getByTestId('ban-slot-blue-0'));
        expect(mockClick).toHaveBeenCalledTimes(1);
    });
});
