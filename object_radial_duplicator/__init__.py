# ruff: noqa: F401
# pyright: reportUnusedImport = false
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
bl_info = {
    "name": "Radial Duplicator",
    "author": "MarshmallowCirno",
    "version": (2, 4),
    "blender": (5, 1, 1),
    "location": "View3D > Sidebar > Item tab",
    "description": "Create radial array, screw or add linked duplicates of selected object and place them radially "
    "around the 3D cursor",
    "warning": "",
    "doc_url": "https://gumroad.com/products/KkDcd",
    "tracker_url": "https://blenderartists.org/t/radial-duplicator-radial-array-and-instances/1212033",
    "category": "Object",
}

_RELOADABLE_MODULE_NAMES = (
    "addon_info",
    "object_data_utils",
    "object_utils",
    "radial_array_builder",
    "math_utils",
    "radial_array_object",
    "radial_duplicates_builder",
    "radial_duplicates_object",
    "radial_screw_builder",
    "radial_screw_object",
    "properties",
    "multiuser_data_changer",
    "apply_base",
    "modal_keymap",
    "ot_keymap",
    "radial_array_add",
    "radial_array_apply",
    "sidebar_ui",
    "layout_draw_utils",
    "addon_preferences",
    "gpu_draw_utils",
    "modal_utils",
    "scene_utils",
    "text_utils",
    "theme_utils",
    "view3d_utils",
    "radial_array_modal",
    "radial_array_refresh",
    "radial_array_remove",
    "radial_array_set_pivot_point",
    "radial_duplicates_add",
    "radial_duplicates_modal",
    "radial_duplicates_remove",
    "radial_duplicates_set_pivot_point",
    "radial_screw_add",
    "radial_screw_apply",
    "radial_screw_modal",
    "radial_screw_refresh",
    "radial_screw_remove",
    "radial_screw_set_pivot_point",
    "apply_dialog_ui",
    "radial_array",
    "radial_duplicates",
    "radial_screw",
    "operators",
    "ui",
)

# Support reloading submodules
if "bpy" in locals():
    import importlib

    for module_name in _RELOADABLE_MODULE_NAMES:
        if module_name in locals():
            importlib.reload(locals()[module_name])
else:
    import bpy

    # Prevent imports when run in the background, since gpu shaders will not be available
    if not bpy.app.background:
        from . import addon_info
        from .modules import operators, properties, ui
        from .modules.base_classes import apply_base
        from .modules.keymap import modal_keymap, ot_keymap
        from .modules.operators import radial_array, radial_duplicates, radial_screw
        from .modules.operators.radial_array import (
            radial_array_add,
            radial_array_apply,
            radial_array_modal,
            radial_array_refresh,
            radial_array_remove,
            radial_array_set_pivot_point,
        )
        from .modules.operators.radial_duplicates import (
            radial_duplicates_add,
            radial_duplicates_modal,
            radial_duplicates_remove,
            radial_duplicates_set_pivot_point,
        )
        from .modules.operators.radial_screw import (
            radial_screw_add,
            radial_screw_apply,
            radial_screw_modal,
            radial_screw_refresh,
            radial_screw_remove,
            radial_screw_set_pivot_point,
        )
        from .modules.preferences import addon_preferences
        from .modules.radial_objects import (
            radial_array_builder,
            radial_array_object,
            radial_duplicates_builder,
            radial_duplicates_object,
            radial_screw_builder,
            radial_screw_object,
        )
        from .modules.ui import apply_dialog_ui, sidebar_ui
        from .modules.utils import (
            gpu_draw_utils,
            layout_draw_utils,
            math_utils,
            modal_utils,
            multiuser_data_changer,
            object_data_utils,
            object_utils,
            scene_utils,
            text_utils,
            theme_utils,
            view3d_utils,
        )

import bpy  # noqa: E402

# Prevent loading in the background, since gpu shaders will not be available
if not bpy.app.background:
    from .modules import operators, properties, ui
    from .modules.keymap import ot_keymap
    from .modules.preferences import addon_preferences

    def register():
        properties.register()
        addon_preferences.register()

        operators.register()

        ui.register()

        ot_keymap.register()

    def unregister():
        ot_keymap.unregister()

        ui.unregister()

        operators.unregister()

        addon_preferences.unregister()
        properties.unregister()
else:
    register = unregister = lambda: None
