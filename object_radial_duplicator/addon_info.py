from __future__ import annotations

from typing import TYPE_CHECKING, cast

import bpy

if TYPE_CHECKING:
    from .modules.preferences import addon_preferences


def get_addon_package() -> str:
    """Return the name of the addon package."""
    assert isinstance(__package__, str)
    return __package__


def get_preferences() -> addon_preferences.RADDUPLICATOR_preferences:
    assert isinstance(__package__, str)
    return cast(addon_preferences.RADDUPLICATOR_preferences, bpy.context.preferences.addons[__package__].preferences)
