import React from 'react';
import Image from 'next/image';
import { Champion, Role } from '@/types';
import { RoleIcon } from '@/components/ui/RoleIcon';

interface PickSlotProps {
    champion: Champion | undefined;
    role: Role;
    isActive: boolean;
    isTarget: boolean;
    side: 'blue' | 'red';
    onClick: () => void;
}

export const PickSlot: React.FC<PickSlotProps> = ({ champion, role, isActive, isTarget, side, onClick }) => {
    const isBlue = side === 'blue';

    return (
        <div
            onClick={onClick}
            className={`
                relative flex items-center gap-3 p-2 rounded-lg border transition-all h-20 cursor-pointer
                ${isBlue ? 'flex-row' : 'flex-row-reverse text-right'}
                ${isActive
                    ? 'border-amber-400 bg-amber-400/10 shadow-[0_0_15px_rgba(251,191,36,0.15)]'
                    : isTarget ? 'border-amber-500/30 bg-amber-500/5' : 'border-slate-800 bg-slate-900/40 hover:bg-slate-900/60'}
              `}
        >
            <div className={`absolute -top-2.5 ${isBlue ? 'left-2' : 'right-2'} bg-slate-950 px-1 z-10`}>
                <div className="flex items-center gap-1">
                    <RoleIcon role={role} className="w-3 h-3" />
                    <span className="text-[9px] font-bold tracking-widest text-slate-500 uppercase">{role}</span>
                </div>
            </div>

            {/* Champion Image/Circle */}
            <div className={`
                 w-14 h-14 rounded-full border-2 overflow-hidden relative shrink-0
                 ${champion ? 'border-amber-400/50' : 'border-dashed border-slate-700 bg-slate-800'}
              `}>
                {champion ? (
                    <Image
                        src={champion.image}
                        alt={champion.name}
                        fill
                        className="object-cover scale-110"
                        sizes="56px"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center opacity-20 text-slate-500">
                        <RoleIcon role={role} className="w-6 h-6" />
                    </div>
                )}
            </div>

            {/* Text Info */}
            <div className="flex-1 min-w-0 flex flex-col justify-center">
                <div className={`font-lol text-lg leading-none ${champion ? 'text-amber-50' : 'text-slate-600 italic'}`}>
                    {champion ? champion.name : 'Select Champion'}
                </div>
                {isTarget && !champion && <div className="text-[10px] text-amber-500/80 uppercase font-bold mt-1">Recommended</div>}
            </div>

            {/* Active Indicator */}
            {isActive && (
                <div className={`absolute top-1/2 -translate-y-1/2 ${isBlue ? '-left-1' : '-right-1'} w-1 h-12 bg-amber-400 rounded-full blur-[2px]`} />
            )}
        </div>
    );
};
