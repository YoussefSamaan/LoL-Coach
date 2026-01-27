import React from 'react';
import Image from 'next/image';
import { Recommendation } from '@/types';
import { TrendingUp } from 'lucide-react';

interface RecommendationCardProps {
    rec: Recommendation;
    rank: number;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({ rec, rank }) => {
    return (
        <div className="bg-slate-900/80 rounded-xl overflow-hidden border border-slate-800 hover:border-amber-500/30 transition-all group relative">
            {/* Rank Indicator */}
            <div className="absolute top-0 left-0 bg-slate-950 px-3 py-1 border-b border-r border-slate-800 rounded-br-lg z-10 flex items-center gap-2">
                <span className="text-amber-500 font-black italic text-lg leading-none">#{rank}</span>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Recommendation</span>
            </div>

            <div className="flex flex-row h-32">
                {/* Image Section */}
                <div className="w-1/3 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent to-slate-900 z-10" />
                    <Image
                        src={`https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${rec.championId}_0.jpg`}
                        alt={rec.championName}
                        fill
                        className="object-cover group-hover:scale-110 transition-transform duration-500"
                        sizes="(max-width: 768px) 100vw, 33vw"
                    />
                </div>

                {/* Content Section */}
                <div className="flex-1 p-3 pl-0 flex flex-col justify-center relative z-20">
                    <div className="flex justify-between items-start mb-2 pr-2">
                        <h3 className="text-xl font-bold text-amber-50 font-lol tracking-wide">{rec.championName}</h3>
                        <div className="text-right">
                            <div className="text-amber-500 font-bold text-sm">{rec.score}%</div>
                            <div className="text-[9px] text-slate-600 uppercase">Confidence</div>
                        </div>
                    </div>

                    <div className="bg-slate-950/50 rounded-lg p-2 border border-slate-800/50 backdrop-blur-sm">
                        <div className="flex items-start gap-2">
                            <TrendingUp size={14} className="text-blue-400 mt-0.5 shrink-0" />
                            <div>
                                <span className="text-[10px] text-blue-400 font-bold uppercase block mb-0.5">Coach&apos;s Analysis</span>
                                <p className="text-xs text-slate-300 leading-snug line-clamp-3">
                                    {rec.explanation || rec.primaryReason || "Strong meta pick for this role."}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
