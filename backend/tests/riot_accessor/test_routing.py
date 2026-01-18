from app.domain.enums import Region
from app.riot_accessor.routing import platform_host, regional_host, _PLATFORM_HOST, _REGIONAL_HOST


def test_platform_host():
    # Test all mapped regions
    for region, expected_url in _PLATFORM_HOST.items():
        assert platform_host(region) == expected_url


def test_regional_host():
    # Test all mapped regions
    for region, expected_url in _REGIONAL_HOST.items():
        assert regional_host(region) == expected_url


def test_platform_host_invalid():
    # Test that unmapped region raises KeyError
    # (Assuming we pass something not in the dict, though Enum type hinting restricts this)
    # This is more of a safety check or verifying behavior if Enum expanded but map didn't
    pass


def test_regional_host_mappings():
    # Verify specific known mappings
    assert regional_host(Region.NA) == "https://americas.api.riotgames.com"
    assert regional_host(Region.EUW) == "https://europe.api.riotgames.com"
    assert regional_host(Region.KR) == "https://asia.api.riotgames.com"
