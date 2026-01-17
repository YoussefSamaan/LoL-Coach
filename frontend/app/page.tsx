"use client";

import React from 'react';
import { TeamColumn } from '@/components/draft/TeamColumn';
import { DraftCenter } from '@/components/draft/DraftCenter';
import ChampionSelector from '@/components/draft/ChampionSelector';
import { Header } from '@/components/ui/Header';
import { useSystemStatus } from '@/hooks/useSystemStatus';
import { useChampions } from '@/hooks/useChampions';
import { useDraft } from '@/hooks/useDraft';
import { useRecommendations } from '@/hooks/useRecommendations';

export default function Home() {
  const { systemStatus, version } = useSystemStatus();
  const championList = useChampions();
  const {
    draft,
    setDraft,
    selectorContext,
    handleSlotClick,
    handleSelect,
    closeSelector,
    setTargetRole
  } = useDraft();

  const { recommendations, loading, handlePredict } = useRecommendations(draft, setDraft, championList);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">

      <Header systemStatus={systemStatus} version={version} />

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-12 min-h-0 bg-[#010a13]">

        {/* LEFT: Blue Team */}
        <div className="col-span-3 border-r border-[#c89b3c]/10 bg-[#091428]/30 backdrop-blur-sm relative">
          <div className="p-6 h-full">
            <div className="flex items-center justify-between mb-4 px-2">
              <span className="text-blue-400 font-lol tracking-widest uppercase text-sm font-bold">Blue Team</span>
              <span className="text-[10px] text-slate-500 font-bold uppercase">First Pick</span>
            </div>
            <TeamColumn
              side="blue"
              picks={draft.allies}
              bans={draft.allyBans}
              activeSlot={selectorContext?.destination === 'ally' ? selectorContext.idx : null}
              targetRole={draft.targetRole}
              onSlotClick={(idx, type) => handleSlotClick(idx, 'blue', type)}
              champions={championList}
            />
          </div>
        </div>

        {/* CENTER: Recommendations */}
        <div className="col-span-6 h-full min-h-0 bg-[#061120] relative">
          <DraftCenter
            recommendations={recommendations}
            loading={loading}
            targetRole={draft.targetRole}
            setTargetRole={setTargetRole}
            onPredict={handlePredict}
          />
        </div>

        {/* RIGHT: Red Team */}
        <div className="col-span-3 border-l border-[#c89b3c]/10 bg-[#091428]/30 backdrop-blur-sm relative">
          <div className="p-6 h-full">
            <div className="flex items-center justify-between mb-4 px-2 flex-row-reverse">
              <span className="text-red-400 font-lol tracking-widest uppercase text-sm font-bold">Red Team</span>
              <span className="text-[10px] text-slate-500 font-bold uppercase">Counter Pick</span>
            </div>
            <TeamColumn
              side="red"
              picks={draft.enemies}
              bans={draft.enemyBans}
              activeSlot={selectorContext?.destination === 'enemy' ? selectorContext.idx : null}
              targetRole={draft.targetRole}
              onSlotClick={(idx, type) => handleSlotClick(idx, 'red', type)}
              champions={championList}
            />
          </div>
        </div>

      </div>

      {/* Modal */}
      {selectorContext && (
        <ChampionSelector
          onSelect={handleSelect}
          onClose={closeSelector}
          disabledIds={new Set([...draft.allies, ...draft.enemies, ...draft.allyBans, ...draft.enemyBans] as string[])}
          champions={championList}
        />
      )}

    </div>
  );
}
