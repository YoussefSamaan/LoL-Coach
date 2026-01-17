import React from 'react';
import Image from 'next/image';
import { Champion } from '@/types';

interface BanSlotProps {
    champion: Champion | undefined;
    onClick: () => void;
    side: 'blue' | 'red';
    index: number;
}

export const BanSlot: React.FC<BanSlotProps> = ({ champion, onClick, side, index }) => {
    return (
        <div
            data-testid={`ban-slot-${side}-${index}`}
            onClick={onClick}
            className="w-10 h-10 border border-slate-800 bg-slate-900/50 rounded relative group overflow-hidden cursor-pointer hover:border-slate-600 transition-colors"
        >
            {champion ? (
                <>
                    <Image
                        src={champion.image}
                        alt={champion.name}
                        fill
                        className="object-cover grayscale opacity-60"
                        sizes="40px"
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-[120%] h-px bg-red-500/50 rotate-45 absolute" />
                    </div>
                </>
            ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-700 text-xs">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </div>
            )}
        </div>
    );
};
