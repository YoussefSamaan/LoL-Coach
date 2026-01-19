from __future__ import annotations

from pydantic import BaseModel

from app.domain.enums import Division, QueueType, Tier


class LeagueEntry(BaseModel):
    puuid: str | None = None
    summonerId: str | None = None
    summonerName: str | None = None
    queueType: QueueType | None = None
    tier: Tier | None = None
    rank: Division | None = None
    leaguePoints: int | None = None
    wins: int | None = None
    losses: int | None = None


class SummonerDTO(BaseModel):
    id: str
    accountId: str
    puuid: str
    name: str | None = None
    profileIconId: int
    revisionDate: int
    summonerLevel: int
