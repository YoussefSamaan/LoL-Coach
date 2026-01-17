import React from 'react';
import { Calculator } from 'lucide-react';

export const DraftEmptyState: React.FC = () => {
    return (
        <div className="flex flex-col items-center justify-center h-64 text-slate-600">
            <Calculator size={48} className="mb-4 opacity-20" />
            <p className="uppercase font-bold text-xs tracking-widest text-center">Awaiting Draft Context<br />Select roles to get started</p>
        </div>
    );
};
