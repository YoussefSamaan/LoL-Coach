import { render, screen } from '@testing-library/react';
import { RoleIcon } from '@/components/ui/RoleIcon';
import { Role } from '@/types';
import { describe, it, expect } from 'vitest';

describe('RoleIcon', () => {
    it('renders the role icon correctly', () => {
        render(<RoleIcon role={Role.TOP} />);
        const img = screen.getByRole('img', { name: /TOP/i });
        expect(img).toBeInTheDocument();
        expect(img).toHaveAttribute('alt', 'TOP');
    });

    it('applies custom class names', () => {
        render(<RoleIcon role={Role.MID} className="custom-class" />);
        // The outer div should have the class
        // Since component structure is <div><Image /></div>
        // We might need to find the container.
        const img = screen.getByRole('img', { name: /MID/i });
        expect(img.parentElement).toHaveClass('custom-class');
    });

    it('uses default class name if none provided', () => {
        render(<RoleIcon role={Role.ADC} />);
        const img = screen.getByRole('img', { name: /ADC/i });
        expect(img.parentElement).toHaveClass('w-5', 'h-5');
    });
});
