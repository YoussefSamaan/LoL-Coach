import { render, screen } from '@testing-library/react';
import { DraftCenter } from '@/components/draft/DraftCenter';
import { Role } from '@/types';
import { describe, it, expect, vi } from 'vitest';

describe('DraftCenter', () => {
    const mockProps = {
        recommendations: [],
        loading: false,
        targetRole: Role.JUNGLE,
        setTargetRole: vi.fn(),
        onPredict: vi.fn(),
    };

    it('renders empty state initially', () => {
        render(<DraftCenter {...mockProps} />);
        expect(screen.getByText(/Awaiting Draft Context/)).toBeInTheDocument();
        expect(screen.queryByText('Recommendation')).not.toBeInTheDocument();
    });

    it('renders loading skeletons', () => {
        render(<DraftCenter {...mockProps} loading={true} />);
        // Look for animate-pulse divs
        const skeletons = screen.getAllByText((content, element) => {
            return element!.className.includes('animate-pulse');
        });
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it('renders recommendations', () => {
        const recs = [
            { championId: '1', championName: 'Lee Sin', score: 90, primaryReason: 'High Winrate' },
            { championId: '2', championName: 'Elise', score: 85, primaryReason: 'Counter Pick' },
        ];
        render(<DraftCenter {...mockProps} recommendations={recs} />);

        expect(screen.getByText('Lee Sin')).toBeInTheDocument();
        expect(screen.getByText('Elise')).toBeInTheDocument();
        expect(screen.getByText('Showing Top 3 Recommendations')).toBeInTheDocument();
    });
});
