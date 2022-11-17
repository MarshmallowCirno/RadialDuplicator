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
    "version": (2, 0),
    "blender": (3, 3, 1),
    "location": "View3D > Sidebar > Item tab",
    "description": "Create radial array, screw or add linked duplicates of selected object and place them radially "
                   "around the 3D cursor",
    "warning": "",
    "doc_url": "https://gumroad.com/products/KkDcd",
    "category": "Object",
}


reloadable_modules = (
    "debug_shader",
    "layout_draw",
    "math",
    "modal",
    "multiuser_data_changer",
    "object",
    "object_data",
    "opengl_draw",
    "scene",
    "text",
    "theme",
    "view3d",

    "modal_keymap",
    "ot_keymap",

    "properties",
    "preferences",

    "apply_base",
    "apply_dialog",

    "radial_array_builder",
    "radial_array_object",
    "radial_duplicates_builder",
    "radial_duplicates_object",
    "radial_screw_builder",
    "radial_screw_object",

    "radial_array_add",
    "radial_array_apply",
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

    "sidebar",
)


# when bpy is already in local, we know this is not the initial import,
# so we need to reload our submodule(s) using importlib.
if "bpy" in locals():
    import importlib

    # reload modules twice so modules that import from other modules
    # always get stuff that's up-to-date.
    for _ in range(2):
        for module in reloadable_modules:
            if module in locals():
                importlib.reload(locals()[module])
else:
    from .modules.utils import (
        layout_draw,
        math,
        modal,
        multiuser_data_changer,
        object,
        object_data,
        opengl_draw,
        scene,
        text,
        theme,
        view3d
    )
    from .modules import properties
    from .modules.keymap import modal_keymap
    from .modules.keymap import ot_keymap
    from .modules.preferences import preferences
    from .modules.base_classes import apply_base
    from .modules.ui import apply_dialog

    from .modules.radial_objects import (
        radial_array_builder,
        radial_array_object,
        radial_duplicates_builder,
        radial_duplicates_object,
        radial_screw_builder,
        radial_screw_object,
    )
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
    from .modules.ui import sidebar


import bpy


def register():
    properties.register()
    preferences.register()

    radial_array_add.register()
    radial_array_apply.register()
    radial_array_modal.register()
    radial_array_refresh.register()
    radial_array_remove.register()
    radial_array_set_pivot_point.register()

    radial_duplicates_add.register()
    radial_duplicates_modal.register()
    radial_duplicates_remove.register()
    radial_duplicates_set_pivot_point.register()

    radial_screw_add.register()
    radial_screw_apply.register()
    radial_screw_modal.register()
    radial_screw_refresh.register()
    radial_screw_remove.register()
    radial_screw_set_pivot_point.register()

    ot_keymap.register()

    apply_dialog.register()
    sidebar.register()


def unregister():
    apply_dialog.unregister()
    sidebar.unregister()

    radial_array_add.unregister()
    radial_array_apply.unregister()
    radial_array_modal.unregister()
    radial_array_refresh.unregister()
    radial_array_remove.unregister()
    radial_array_set_pivot_point.unregister()

    radial_duplicates_add.unregister()
    radial_duplicates_modal.unregister()
    radial_duplicates_remove.unregister()
    radial_duplicates_set_pivot_point.unregister()

    radial_screw_add.unregister()
    radial_screw_apply.unregister()
    radial_screw_modal.unregister()
    radial_screw_refresh.unregister()
    radial_screw_remove.unregister()
    radial_screw_set_pivot_point.unregister()

    preferences.unregister()
    ot_keymap.unregister()
    properties.unregister()
