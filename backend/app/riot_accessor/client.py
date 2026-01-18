from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.domain.enums import Division, QueueType, Region, Tier
from app.riot_accessor.endpoints.league_v4 import list_league_entries
from app.riot_accessor.endpoints.league_v4_high_elo import (
    get_challenger_league,
    get_grandmaster_league,
    get_master_league,
)
from app.riot_accessor.endpoints.match_v5 import get_match, list_match_ids_by_puuid
from app.riot_accessor.schemas import LeagueEntry


@dataclass(frozen=True)
class RiotClient:
    """
    Minimal Riot HTTP client with 429 backoff. Internal-only.
    """

    api_key: str
    timeout_s: float = 10.0
    max_retries: int = 5

    @classmethod
    def from_env(cls) -> "RiotClient":
        from app.config.settings import settings  # noqa: F401

        api_key = (os.getenv("RIOT_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("Missing RIOT_API_KEY in environment")
        return cls(api_key=api_key)

    def get_json(self, *, url: str, params: dict | None = None) -> Any:
        headers = {"X-Riot-Token": self.api_key}

        last_exc: Exception | None = None
        with httpx.Client(timeout=self.timeout_s) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        sleep_s = float(retry_after) if retry_after else min(2.0**attempt, 30.0)
                        time.sleep(sleep_s)
                        continue

                    # Do not retry client errors (404 means "not found", etc).
                    # except 429 (rate limit)
                    if 400 <= resp.status_code < 500:
                        resp.raise_for_status()

                    # Retry server errors.
                    if resp.status_code >= 500:
                        resp.raise_for_status()

                    return resp.json()

                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if 400 <= status < 500 and status != 429:
                        raise
                    last_exc = exc
                    time.sleep(min(2.0**attempt, 5.0))
                except Exception as exc:  # noqa: BLE001 - surface final failure
                    last_exc = exc
                    time.sleep(min(2.0**attempt, 5.0))

        raise RuntimeError(f"Riot request failed after {self.max_retries} retries") from last_exc

    # --- Match endpoints ---
    def match_ids_by_puuid(self, *, region: Region, puuid: str, count: int = 20) -> list[str]:
        return list_match_ids_by_puuid(client=self, region=region, puuid=puuid, count=count)

    def match(self, *, region: Region, match_id: str) -> dict:
        return get_match(client=self, region=region, match_id=match_id)

    # --- League (Rank sampling) ---
    def league_entries_by_rank(
        self,
        *,
        region: Region,
        queue: QueueType,
        tier: Tier,
        division: Division | None = None,
        page: int = 1,
    ) -> list[LeagueEntry]:
        if tier == Tier.CHALLENGER:
            data = get_challenger_league(client=self, region=region, queue=queue)
            entries = data.get("Entries", [])
        elif tier == Tier.GRANDMASTER:
            data = get_grandmaster_league(client=self, region=region, queue=queue)
            entries = data.get("Entries", [])
        elif tier == Tier.MASTER:
            data = get_master_league(client=self, region=region, queue=queue)
            entries = data.get("Entries", [])
        else:
            # Standard tiers require division
            if not division:
                print("No division provided for tier", tier)
                print("Defaulting to Division.I")
                division = Division.I

            entries = list_league_entries(
                client=self,
                region=region,
                queue=queue,
                tier=tier,
                division=division,
                page=page,
            )
            print("Entries", entries)

        return [LeagueEntry.model_validate(e) for e in entries]
