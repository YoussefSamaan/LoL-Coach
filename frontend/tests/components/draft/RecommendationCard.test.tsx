import { render, screen, fireEvent } from '@testing-library/react';
import { RecommendationCard } from '@/components/draft/RecommendationCard';
import { describe, it, expect } from 'vitest';

describe('RecommendationCard', () => {
    const mockRec = {
        championId: 'Yasuo',
        championName: 'Yasuo',
        score: 95,
        primaryReason: 'Wombo Combo',
        explanation: 'Great synergy with your team composition. Yasuo excels when paired with knock-up champions and can turn team fights in your favor.'
    };

    it('renders basic info correctly', () => {
        render(<RecommendationCard rec={mockRec} rank={1} />);
        expect(screen.getByText('#1')).toBeInTheDocument();
        expect(screen.getByText('Yasuo')).toBeInTheDocument();
        expect(screen.getByText('95%')).toBeInTheDocument();
        expect(screen.getByRole('img', { name: 'Yasuo' })).toBeInTheDocument();
    });

    it('renders explanation when available', () => {
        render(<RecommendationCard rec={mockRec} rank={2} />);
        expect(screen.getByText(/Great synergy with your team composition/)).toBeInTheDocument();
    });

    it('shows loading state when explanation is empty', () => {
        const loadingRec = { ...mockRec, explanation: '' };
        render(<RecommendationCard rec={loadingRec} rank={1} />);
        expect(screen.getByText('Analyzing strategies...')).toBeInTheDocument();
    });

    it('expands and collapses explanation on click', () => {
        const { container } = render(<RecommendationCard rec={mockRec} rank={1} />);

        // Find the explanation container
        const explanationDiv = container.querySelector('.bg-slate-950\\/50');
        expect(explanationDiv).toBeInTheDocument();

        // Initially should have line-clamp-3
        const explanationText = screen.getByText(/Great synergy with your team composition/);
        expect(explanationText.className).toContain('line-clamp-3');

        // Click to expand
        fireEvent.click(explanationDiv!);

        // Should not have line-clamp-3 after expansion
        expect(explanationText.className).not.toContain('line-clamp-3');

        // Click to collapse
        fireEvent.click(explanationDiv!);

        // Should have line-clamp-3 again
        expect(explanationText.className).toContain('line-clamp-3');
    });

    it('shows chevron icons when explanation is available', () => {
        render(<RecommendationCard rec={mockRec} rank={1} />);

        // Should show ChevronDown initially
        expect(screen.getByLabelText('Expand')).toBeInTheDocument();
    });

    it('does not show chevron when explanation is loading', () => {
        const loadingRec = { ...mockRec, explanation: '' };
        render(<RecommendationCard rec={loadingRec} rank={1} />);

        // Should not show expand/collapse button
        expect(screen.queryByLabelText('Expand')).not.toBeInTheDocument();
        expect(screen.queryByLabelText('Collapse')).not.toBeInTheDocument();
    });
});
