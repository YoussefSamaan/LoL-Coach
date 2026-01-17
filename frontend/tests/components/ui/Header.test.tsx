import { render, screen } from '@testing-library/react';
import { Header } from '@/components/ui/Header';
import { describe, it, expect } from 'vitest';

describe('Header', () => {
    it('renders the title correctly', () => {
        render(<Header systemStatus="OFFLINE" version="v1.0.0" />);
        expect(screen.getByRole('heading', { name: /LoL Draft/i })).toBeInTheDocument();
        expect(screen.getByText('Coach')).toHaveClass('text-[#c89b3c]');
    });

    it('renders online status correctly', () => {
        render(<Header systemStatus="ONLINE" version="v1.0.0" />);
        expect(screen.getByText('System Online')).toBeInTheDocument();
        // Check green dot class
        const statusText = screen.getByText('System Online');
        // The dot is a sibling div
        const dot = statusText.previousSibling;
        expect(dot).toHaveClass('bg-green-500');
    });

    it('renders offline status correctly', () => {
        render(<Header systemStatus="OFFLINE" version="v1.0.0" />);
        expect(screen.getByText('System Offline')).toBeInTheDocument();
        const statusText = screen.getByText('System Offline');
        const dot = statusText.previousSibling;
        expect(dot).toHaveClass('bg-red-500');
    });

    it('renders version correctly', () => {
        render(<Header systemStatus="ONLINE" version="v2.5.0" />);
        expect(screen.getByText('v2.5.0')).toBeInTheDocument();
    });
});
