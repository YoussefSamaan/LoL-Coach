import { render, screen } from '@testing-library/react';
import { RecommendationCard } from '@/components/draft/RecommendationCard';
import { describe, it, expect } from 'vitest';

describe('RecommendationCard', () => {
    const mockRec = {
        championId: 'Yasuo',
        championName: 'Yasuo',
        score: 95,
        primaryReason: 'Wombo Combo'
    };

    it('renders basic info correctly', () => {
        render(<RecommendationCard rec={mockRec} rank={1} />);
        expect(screen.getByText('#1')).toBeInTheDocument();
        expect(screen.getByText('Yasuo')).toBeInTheDocument();
        expect(screen.getByText('95%')).toBeInTheDocument();
        expect(screen.getByRole('img', { name: 'Yasuo' })).toBeInTheDocument();
    });

    it('renders primary reason', () => {
        render(<RecommendationCard rec={mockRec} rank={2} />);
        expect(screen.getByText('Wombo Combo')).toBeInTheDocument();
    });

    it('falls back if no reasons provided', () => {
        const emptyReasonsRec = { ...mockRec, primaryReason: '' };
        render(<RecommendationCard rec={emptyReasonsRec} rank={1} />);
        expect(screen.getByText('Strong meta pick for this role.')).toBeInTheDocument();
    });
});
