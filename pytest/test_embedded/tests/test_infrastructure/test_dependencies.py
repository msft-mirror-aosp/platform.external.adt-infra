import pytest
import logging
from emu.emulator import BaseEmulator


@pytest.fixture(autouse=True, scope="function")
def patch_reset_state(request, mocker):
    """Patches BaseEmulator.reset_state for testing purposes."""
    return mocker.patch.object(BaseEmulator, "reset_state", return_value=None)


@pytest.mark.dependency()
async def test_avd_reset_state_dependent_parent(avd, patch_reset_state):
    """Tests avd fixture's reset_state behavior for dependent tests (parent).

    This test verifies that the `avd` fixture resets the emulator state
    to its initial configuration before running a test marked as a dependency parent.
    This ensures a clean starting state for dependent tests.
    """
    patch_reset_state.assert_called()


@pytest.mark.dependency(depends=["test_avd_reset_state_dependent_parent"])
async def test_avd_reset_state_dependent_child(avd, patch_reset_state):
    """Tests avd fixture's reset_state behavior for dependent tests (child).

    This test verifies that the `avd` fixture *does not* reset the emulator state
    when running a test that depends on another test (a dependency child).
    This allows subsequent tests to inherit the state modified by the parent test.
    """
    patch_reset_state.assert_not_called()


async def test_avd_reset_state_independent(avd, patch_reset_state):
    """Tests avd fixture's reset_state behavior for independent tests.

    This test verifies that the `avd` fixture resets the emulator state
    to its initial configuration before running independent tests
    (tests not marked with `pytest.mark.dependency`).
    This guarantees isolated testing environments between unrelated tests.
    """
    patch_reset_state.assert_called()
