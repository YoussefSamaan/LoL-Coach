import { render, screen, fireEvent } from '@testing-library/react';
import { PickSlot } from '@/components/draft/PickSlot';
import { Role } from '@/types';
import { describe, it, expect, vi } from 'vitest';

describe('PickSlot', () => {
    const mockClick = vi.fn();
    const mockChamp = { id: 'Zed', name: 'Zed', image: 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/Zed.png' };

    it('renders empty state correctly', () => {
        render(
            <PickSlot
                champion={undefined}
                role={Role.MID}
                isActive={false}
                isTarget={false}
                side="blue"
                onClick={mockClick}
            />
        );
        expect(screen.getByText('Select Champion')).toBeInTheDocument();
        // Role icon should be present in two places (header and placeholder)
        const roleIcons = screen.getAllByRole('img', { name: 'MID' });
        expect(roleIcons.length).toBe(2);
    });

    it('renders filled state correctly', () => {
        render(
            <PickSlot
                champion={mockChamp}
                role={Role.MID}
                isActive={false}
                isTarget={false}
                side="blue"
                onClick={mockClick}
            />
        );
        expect(screen.getByText('Zed')).toBeInTheDocument();
        expect(screen.getByRole('img', { name: 'Zed' })).toBeInTheDocument();
    });

    it('renders active state styling', () => {
        const { container } = render(
            <PickSlot
                champion={undefined}
                role={Role.MID}
                isActive={true}
                isTarget={false}
                side="blue"
                onClick={mockClick}
            />
        );
        // Active has border-amber-400
        expect(container.firstChild).toHaveClass('border-amber-400');
    });

    it('renders target state styling and logic', () => {
        render(
            <PickSlot
                champion={undefined}
                role={Role.MID}
                isActive={false}
                isTarget={true}
                side="blue"
                onClick={mockClick}
            />
        );
        expect(screen.getByText('Recommended')).toBeInTheDocument();
    });

    it('handles red side layout (reverse)', () => {
        const { container } = render(
            <PickSlot
                champion={undefined}
                role={Role.MID}
                isActive={false}
                isTarget={false}
                side="red"
                onClick={mockClick}
            />
        );
        expect(container.firstChild).toHaveClass('flex-row-reverse');
    });

    it('handles click', () => {
        render(
            <PickSlot
                champion={undefined}
                role={Role.MID}
                isActive={false}
                isTarget={false}
                side="blue"
                onClick={mockClick}
            />
        );
        fireEvent.click(screen.getByText('Select Champion').closest('div')!.parentElement!);
        expect(mockClick).toHaveBeenCalledTimes(1);
    });
});
