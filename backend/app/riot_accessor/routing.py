from __future__ import annotations

from app.domain.enums import Region


_PLATFORM_HOST: dict[Region, str] = {
    Region.NA: "https://na1.api.riotgames.com",
    Region.BR: "https://br1.api.riotgames.com",
    Region.LAN: "https://la1.api.riotgames.com",
    Region.LAS: "https://la2.api.riotgames.com",
    Region.OCE: "https://oc1.api.riotgames.com",
    Region.EUW: "https://euw1.api.riotgames.com",
    Region.EUNE: "https://eun1.api.riotgames.com",
    Region.TR: "https://tr1.api.riotgames.com",
    Region.RU: "https://ru.api.riotgames.com",
    Region.KR: "https://kr.api.riotgames.com",
    Region.JP: "https://jp1.api.riotgames.com",
}

_REGIONAL_HOST: dict[Region, str] = {
    Region.NA: "https://americas.api.riotgames.com",
    Region.BR: "https://americas.api.riotgames.com",
    Region.LAN: "https://americas.api.riotgames.com",
    Region.LAS: "https://americas.api.riotgames.com",
    Region.OCE: "https://americas.api.riotgames.com",
    Region.EUW: "https://europe.api.riotgames.com",
    Region.EUNE: "https://europe.api.riotgames.com",
    Region.TR: "https://europe.api.riotgames.com",
    Region.RU: "https://europe.api.riotgames.com",
    Region.KR: "https://asia.api.riotgames.com",
    Region.JP: "https://asia.api.riotgames.com",
}


def platform_host(region: Region) -> str:
    return _PLATFORM_HOST[region]


def regional_host(region: Region) -> str:
    return _REGIONAL_HOST[region]
