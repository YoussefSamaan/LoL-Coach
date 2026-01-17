"use client";

import React from 'react';
import { Champion, Role } from '@/types';
import { ROLES } from '@/constants';
import { BanSlot } from './BanSlot';
import { PickSlot } from './PickSlot';

interface TeamColumnProps {
    side: 'blue' | 'red';
    picks: (string | null)[]; // Champion IDs
    bans: (string | null)[];  // Champion IDs
    activeSlot: number | null; // active pick slot index
    targetRole: Role;
    onSlotClick: (index: number, type: 'pick' | 'ban') => void;
    champions: Champion[];
}

export const TeamColumn: React.FC<TeamColumnProps> = ({
    side,
    picks,
    bans,
    activeSlot,
    targetRole,
    onSlotClick,
    champions
}) => {
    // Helper to resolve champion data from ID
    const getChamp = (id: string | null): Champion | undefined => champions.find(c => c.id === id);

    const isBlue = side === 'blue';

    return (
        <div className={`flex flex-col h-full ${isBlue ? 'items-start' : 'items-end'}`}>

            {/* Bans Row */}
            <div className={`w-full flex gap-2 mb-6 px-4 ${isBlue ? 'justify-start' : 'justify-end'}`}>
                {bans.map((banId, idx) => (
                    <BanSlot
                        key={`ban-${idx}`}
                        champion={getChamp(banId)}
                        onClick={() => onSlotClick(idx, 'ban')}
                        side={side}
                        index={idx}
                    />
                ))}
            </div>

            {/* Picks Column */}
            <div className="flex-1 w-full space-y-4 px-4 pt-4 overflow-y-auto custom-scrollbar">
                {picks.map((pickId, idx) => {
                    const role = ROLES[idx];
                    const champ = getChamp(pickId);
                    const isActive = activeSlot === idx;
                    const isTarget = isBlue && role === targetRole;

                    return (
                        <PickSlot
                            key={`pick-${idx}`}
                            champion={champ}
                            role={role}
                            isActive={isActive}
                            isTarget={isTarget}
                            side={side}
                            onClick={() => onSlotClick(idx, 'pick')}
                        />
                    );
                })}
            </div>
        </div>
    );
};
