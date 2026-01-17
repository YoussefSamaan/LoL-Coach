import { render, screen, fireEvent } from '@testing-library/react';
import { RoleSelector } from '@/components/draft/RoleSelector';
import { Role } from '@/types';
import { describe, it, expect, vi } from 'vitest';

describe('RoleSelector', () => {
    const mockSetTarget = vi.fn();

    it('renders all roles', () => {
        render(<RoleSelector targetRole={Role.TOP} setTargetRole={mockSetTarget} />);
        expect(screen.getAllByRole('button')).toHaveLength(5);
        expect(screen.getByRole('img', { name: Role.TOP })).toBeInTheDocument();
        expect(screen.getByRole('img', { name: Role.SUPPORT })).toBeInTheDocument();
    });

    it('highlights active role', () => {
        render(<RoleSelector targetRole={Role.JUNGLE} setTargetRole={mockSetTarget} />);
        // Active role button usually has different class or structure (an underline div)
        // Let's find button containing JUNGLE icon
        const jungleBtn = screen.getByRole('img', { name: Role.JUNGLE }).closest('button');
        expect(jungleBtn).toHaveClass('text-amber-500');

        // Inactive
        const topBtn = screen.getByRole('img', { name: Role.TOP }).closest('button');
        expect(topBtn).toHaveClass('text-slate-500');
    });

    it('calls setTargetRole on click', () => {
        render(<RoleSelector targetRole={Role.TOP} setTargetRole={mockSetTarget} />);
        const midBtn = screen.getByRole('img', { name: Role.MID }).closest('button');
        fireEvent.click(midBtn!);
        expect(mockSetTarget).toHaveBeenCalledWith(Role.MID);
    });
});
