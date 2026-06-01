from collections.abc import Sequence
from typing import Literal

import bpy


def get_axis_color(context: bpy.types.Context, spin_axis: Literal['X', 'Y', 'Z']) -> Sequence[float]:
    """Get axis colors from blender theme."""
    theme = context.preferences.themes[0]
    axis_color = {
        'X': lambda: (*theme.user_interface.axis_x, 1),
        'Y': lambda: (*theme.user_interface.axis_y, 1),
        'Z': lambda: (*theme.user_interface.axis_z, 1),
    }[spin_axis]()
    return axis_color
