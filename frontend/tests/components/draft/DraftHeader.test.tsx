import { render, screen, fireEvent } from '@testing-library/react';
import { DraftHeader } from '@/components/draft/DraftHeader';
import { Role } from '@/types';
import { describe, it, expect, vi } from 'vitest';

describe('DraftHeader', () => {
    const mockPredict = vi.fn();
    const mockSetTarget = vi.fn();

    it('renders Header Elements', () => {
        render(
            <DraftHeader
                onPredict={mockPredict}
                loading={false}
                targetRole={Role.MID}
                setTargetRole={mockSetTarget}
            />
        );
        expect(screen.getByText('Draft Analysis')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Predict/i })).toBeInTheDocument();
        // RoleSelector presence check (indirectly via role icons)
        expect(screen.getByRole('img', { name: Role.MID })).toBeInTheDocument();
    });

    it('handles Predict click', () => {
        render(
            <DraftHeader
                onPredict={mockPredict}
                loading={false}
                targetRole={Role.MID}
                setTargetRole={mockSetTarget}
            />
        );
        fireEvent.click(screen.getByRole('button', { name: /Predict/i }));
        expect(mockPredict).toHaveBeenCalledTimes(1);
    });

    it('disables Predict when loading', () => {
        render(
            <DraftHeader
                onPredict={mockPredict}
                loading={true}
                targetRole={Role.MID}
                setTargetRole={mockSetTarget}
            />
        );
        const btn = screen.getByRole('button', { name: /Analyzing/i });
        expect(btn).toBeDisabled();
        expect(btn).toHaveTextContent('Analyzing');
    });
});
