
"use client";

import React, { useState } from 'react';
import Image from 'next/image';
import { Champion } from '@/types';


interface Props {
    onSelect: (id: string) => void;
    onClose: () => void;
    disabledIds: Set<string>;
    champions: Champion[];
}

const ChampionSelector: React.FC<Props> = ({ onSelect, onClose, disabledIds, champions }) => {
    const [search, setSearch] = useState('');

    const filtered = champions.filter(c =>
        c.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-[#091428] border-2 border-[#c89b3c] w-full max-w-2xl max-h-[80vh] flex flex-col rounded-lg">
                <div className="p-4 border-b border-[#c89b3c]/30 flex justify-between items-center bg-[#010a13]">
                    <input
                        autoFocus
                        type="text"
                        placeholder="Search Champion..."
                        className="bg-[#1e2328] border border-[#c89b3c]/50 p-2 text-white w-full max-w-sm rounded outline-none focus:border-[#c89b3c] font-sans"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <button onClick={onClose} className="text-[#c89b3c] hover:text-white ml-4 text-xl font-bold">&times;</button>
                </div>
                <div className="p-4 overflow-y-auto grid grid-cols-4 sm:grid-cols-6 gap-3 custom-scrollbar">
                    {/* Reset Option */}
                    <button
                        onClick={() => onSelect('')}
                        className="flex flex-col items-center group hover:scale-105 transition-transform"
                    >
                        <div className="relative w-full aspect-square border-2 border-red-500/40 group-hover:border-red-500 flex items-center justify-center bg-slate-900">
                            <span className="text-red-500 font-bold text-2xl">X</span>
                        </div>
                        <span className="text-xs mt-1 text-red-500 group-hover:text-red-400 truncate w-full text-center font-lol">
                            None
                        </span>
                    </button>

                    {filtered.map(champ => {
                        const isDisabled = disabledIds.has(champ.id);
                        return (
                            <button
                                key={champ.id}
                                disabled={isDisabled}
                                onClick={() => onSelect(champ.id)}
                                className={`flex flex-col items-center group ${isDisabled ? 'opacity-20 cursor-not-allowed' : 'hover:scale-105 transition-transform'}`}
                            >
                                <div className={`relative w-full aspect-square border-2 ${isDisabled ? 'border-gray-500' : 'border-[#c89b3c]/40 group-hover:border-[#c89b3c]'}`}>
                                    <Image
                                        src={champ.image}
                                        alt={champ.name}
                                        fill
                                        className="object-cover"
                                        sizes="(max-width: 640px) 25vw, 16vw"
                                    />
                                </div>
                                <span className="text-xs mt-1 text-[#f0e6d2] group-hover:text-[#c89b3c] truncate w-full text-center font-lol">
                                    {champ.name}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default ChampionSelector;
