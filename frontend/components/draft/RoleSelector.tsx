import React from 'react';
import { Role } from '@/types';
import { ROLES } from '@/constants';
import { RoleIcon } from '@/components/ui/RoleIcon';

interface RoleSelectorProps {
    targetRole: Role;
    setTargetRole: (role: Role) => void;
}

export const RoleSelector: React.FC<RoleSelectorProps> = ({ targetRole, setTargetRole }) => {
    return (
        <div className="flex p-1 bg-slate-900 rounded-lg border border-slate-800">
            {ROLES.map(role => {
                const isActive = targetRole === role;
                return (
                    <button
                        key={role}
                        onClick={() => setTargetRole(role)}
                        className={`flex-1 flex items-center justify-center py-2 rounded transition-all relative ${isActive ? 'bg-amber-500/10 text-amber-500 shadow-[inset_0_0_10px_rgba(251,191,36,0.1)]' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                            }`}
                    >
                        <RoleIcon role={role} className={`w-5 h-5 ${isActive ? 'scale-110 brightness-125' : 'grayscale opacity-50'}`} />
                        {isActive && <div className="absolute inset-x-0 -bottom-1 h-0.5 bg-amber-500 shadow-[0_0_5px_rgba(251,191,36,0.8)] mx-4 rounded-full" />}
                    </button>
                );
            })}
        </div>
    );
};
