import React from 'react';
import { Sword } from 'lucide-react';

interface HeaderProps {
    systemStatus: 'ONLINE' | 'OFFLINE';
    version: string;
}

export const Header: React.FC<HeaderProps> = ({ systemStatus, version }) => {
    return (
        <header className="h-24 py-6 bg-[#010a13] border-b border-[#c89b3c]/20 flex items-center justify-between px-6 shrink-0 z-50 shadow-2xl relative">
            <div className="flex items-center gap-3">
                <div className="bg-gradient-to-br from-[#c89b3c] to-[#785a28] p-1.5 rounded rotate-45 shadow-[0_0_10px_rgba(200,155,60,0.3)]">
                    <Sword size={20} className="text-[#010a13] -rotate-45" />
                </div>
                <div>
                    <h1 className="font-lol text-lg font-bold tracking-[0.2em] text-[#f0e6d2]">LoL Draft <span className="text-[#c89b3c]">Coach</span></h1>
                </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-bold text-slate-500 uppercase tracking-widest">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${systemStatus === 'ONLINE' ? 'bg-green-500 shadow-[0_0_5px_green]' : 'bg-red-500 shadow-[0_0_5px_red]'}`} />
                    <span>{systemStatus === 'ONLINE' ? 'System Online' : 'System Offline'}</span>
                </div>
                <span>{version}</span>
            </div>
        </header>
    );
};
