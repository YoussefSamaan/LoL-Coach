import { render, screen } from '@testing-library/react';
import { DraftEmptyState } from '@/components/draft/DraftEmptyState';
import { describe, it, expect } from 'vitest';

describe('DraftEmptyState', () => {
    it('renders correctly', () => {
        render(<DraftEmptyState />);
        expect(screen.getByText(/Awaiting Draft Context/)).toBeInTheDocument();
        expect(screen.getByText(/Select roles/)).toBeInTheDocument();
        // Check for icon presence
        const svg = screen.getByText(/Awaiting Draft Context/).previousSibling;
        expect(svg).toHaveClass('lucide-calculator');
    });
});
