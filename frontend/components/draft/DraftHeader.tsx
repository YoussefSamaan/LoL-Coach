import React from 'react';
import { Role } from '@/types';
import { RoleSelector } from './RoleSelector';

interface DraftHeaderProps {
    onPredict: () => void;
    loading: boolean;
    targetRole: Role;
    setTargetRole: (role: Role) => void;
}

export const DraftHeader: React.FC<DraftHeaderProps> = ({ onPredict, loading, targetRole, setTargetRole }) => {
    return (
        <div className="p-4 border-b border-slate-800/50 bg-[#010a13]">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-amber-500 font-lol text-sm tracking-widest uppercase">Draft Analysis</h2>

                <button
                    onClick={onPredict}
                    disabled={loading}
                    className="bg-amber-600 hover:bg-amber-500 text-slate-900 font-bold px-4 py-1.5 rounded-sm uppercase text-xs tracking-wider transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_10px_rgba(217,119,6,0.5)] hover:shadow-[0_0_15px_rgba(217,119,6,0.8)]"
                >
                    {loading ? 'Analyzing...' : 'Predict'}
                </button>
            </div>

            <RoleSelector targetRole={targetRole} setTargetRole={setTargetRole} />
        </div>
    );
};
