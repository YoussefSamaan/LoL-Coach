import React from 'react';
import Image from 'next/image';
import { Role } from '@/types';
import { ROLE_ICONS } from '@/constants';

interface RoleIconProps {
    role: Role;
    className?: string;
}

export const RoleIcon: React.FC<RoleIconProps> = ({ role, className = "w-5 h-5" }) => {
    return (
        <div className={`relative ${className}`}>
            <Image
                src={ROLE_ICONS[role]}
                alt={role}
                fill
                className="object-contain"
                sizes="20px"
            />
        </div>
    );
};
