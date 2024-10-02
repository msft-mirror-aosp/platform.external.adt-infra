import pytest


@pytest.mark.boot
def test_discovery_contains_display_name(avd):
    """Make sure the discovery file contains the proper display name with utf-8."""
    displayname: str = avd.configuration.hardware["avd.ini.displayname"]
    assert (
        len(displayname) > 0
    ), "The avd.ini.displayname should not be empty! Did you modify conftest.py?"
    assert (
        not displayname.isascii()
    ), "The avd.ini.displayname should contain unicode characters!"
    assert displayname == avd.description.get("avd.name")
