from app.domain.enums import Role, Region, Tier, Division, QueueType


def test_role_enums():
    assert Role.TOP == "TOP"
    assert Role.JUNGLE == "JUNGLE"
    assert Role.MID == "MID"
    assert Role.ADC == "ADC"
    assert Role.SUPPORT == "SUPPORT"


def test_region_enums():
    assert Region.NA == "NA"
    assert Region.KR == "KR"
    assert Region.EUW == "EUW"
    assert Region.EUNE == "EUNE"
    assert Region.BR == "BR"
    assert Region.JP == "JP"
    assert Region.LAN == "LAN"
    assert Region.LAS == "LAS"
    assert Region.OCE == "OCE"
    assert Region.RU == "RU"
    assert Region.TR == "TR"
    assert len(Region) > 0


def test_tier_enums():
    assert Tier.IRON == "IRON"
    assert Tier.CHALLENGER == "CHALLENGER"
    assert Tier.BRONZE == "BRONZE"
    assert Tier.SILVER == "SILVER"
    assert Tier.GOLD == "GOLD"
    assert Tier.PLATINUM == "PLATINUM"
    assert Tier.EMERALD == "EMERALD"
    assert Tier.DIAMOND == "DIAMOND"
    assert Tier.MASTER == "MASTER"
    assert Tier.GRANDMASTER == "GRANDMASTER"
    assert len(Tier) > 0


def test_division_enums():
    assert Division.I == "I"
    assert Division.II == "II"
    assert Division.III == "III"
    assert Division.IV == "IV"
    assert len(Division) > 0


def test_queue_type_enums():
    assert QueueType.RANKED_SOLO_5x5 == "RANKED_SOLO_5x5"
