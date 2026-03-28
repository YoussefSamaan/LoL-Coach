from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MID = "MID"
    ADC = "ADC"
    SUPPORT = "SUPPORT"


class Region(str, Enum):
    NA = "NA"
    EUW = "EUW"
    EUNE = "EUNE"
    KR = "KR"
    BR = "BR"
    JP = "JP"
    LAN = "LAN"
    LAS = "LAS"
    OCE = "OCE"
    RU = "RU"
    TR = "TR"


class Tier(str, Enum):
    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"


class Division(str, Enum):
    I = "I"  # noqa: E741
    II = "II"
    III = "III"
    IV = "IV"


class QueueType(str, Enum):
    RANKED_SOLO_5x5 = "RANKED_SOLO_5x5"
