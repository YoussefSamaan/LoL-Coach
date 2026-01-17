
"use client";

import React from 'react';
import { Recommendation, Role } from '@/types';
import { DraftHeader } from './DraftHeader';
import { RecommendationCard } from './RecommendationCard';
import { DraftEmptyState } from './DraftEmptyState';

interface DraftCenterProps {
    recommendations: Recommendation[];
    loading: boolean;
    targetRole: Role;
    setTargetRole: (r: Role) => void;
    onPredict: () => void;
}

export const DraftCenter: React.FC<DraftCenterProps> = ({
    recommendations,
    loading,
    targetRole,
    setTargetRole,
    onPredict
}) => {
    return (
        <div className="flex flex-col h-full bg-slate-950/80 border-x border-slate-800">
            {/* Header / Role Selector */}
            <DraftHeader
                onPredict={onPredict}
                loading={loading}
                targetRole={targetRole}
                setTargetRole={setTargetRole}
            />

            {/* Recommendations Feed */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-[#061120]">
                {loading ? (
                    // Skeletons
                    [1, 2, 3].map(i => (
                        <div key={i} className="h-32 bg-slate-900/50 border border-slate-800 rounded-xl animate-pulse" />
                    ))
                ) : recommendations.length === 0 ? (
                    <DraftEmptyState />
                ) : (
                    recommendations.slice(0, 3).map((rec, i) => (
                        <RecommendationCard
                            key={rec.championId}
                            rec={rec}
                            rank={i + 1}
                        />
                    ))
                )}

                {recommendations.length > 0 && (
                    <div className="text-center pb-4 pt-2">
                        <span className="text-[10px] text-slate-600 uppercase tracking-widest">Showing Top 3 Recommendations</span>
                    </div>
                )}
            </div>
        </div>
    );
};
