from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import bpy

from ... import addon_info
from .. import properties
from ..keymap import modal_keymap, ot_keymap
from ..ui import sidebar_ui
from ..utils import layout_draw_utils


def update_sidebar_category(self: RADDUPLICATOR_preferences, _):
    is_panel = hasattr(bpy.types, 'RADDUPLCIATOR_PT_sidebar')
    if is_panel:
        try:
            bpy.utils.unregister_class(sidebar_ui.RADDUPLCIATOR_PT_sidebar)
        except:  # noqa
            pass
    sidebar_ui.RADDUPLCIATOR_PT_sidebar.bl_category = self.sidebar_category
    bpy.utils.register_class(sidebar_ui.RADDUPLCIATOR_PT_sidebar)


def get_empties_collection(self: RADDUPLICATOR_preferences) -> str:
    return self.get("empties_collection", "Radial Empties")


def set_empties_collection(self: RADDUPLICATOR_preferences, value: str):
    if value == "":
        value = "Radial Empties"
    self["empties_collection"] = value


class RADDUPLICATOR_preferences(bpy.types.AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = addon_info.get_addon_package()

    if TYPE_CHECKING:
        tabs: Literal['GENERAL', 'KEYMAP', 'COLORS']
        keymaps: bpy.types.bpy_prop_collection_idprop[properties.AddonKeyMap]
        overlay_colors: properties.OverlayColors
        mouse_sensitivity: float
        use_wheelmouse: bool
        hide_sidebar: bool
        modal_buttons: bool
        sidebar_category: str
        move_empties_to_collection: bool
        empties_collection: str
    else:
        tabs: bpy.props.EnumProperty(
            name="Tabs",
            items=[
                ('GENERAL', "General", ""),
                ('KEYMAP', "Keymap", ""),
                ('COLORS', "Colors", ""),
            ],
            default='GENERAL',
            options={'SKIP_SAVE'},
        )
        keymaps: bpy.props.CollectionProperty(type=properties.AddonKeyMap)
        overlay_colors: bpy.props.PointerProperty(type=properties.OverlayColors)

        mouse_sensitivity: bpy.props.FloatProperty(
            name="Mouse Sensitivity",
            description="How much values will be offsetted when you move the mouse cursor during a modal operator",
            default=1.0,
        )
        use_wheelmouse: bpy.props.BoolProperty(
            name="Mousewheel Changes Count",
            description="Use the mousewheel for changing a count number in a modal operator",
            default=True,
        )
        hide_sidebar: bpy.props.BoolProperty(
            name="Auto-Hide Sidebar",
            description="Hide the sidebar during a modal operator and restore it after finishing an operator",
            default=True,
        )
        modal_buttons: bpy.props.BoolProperty(
            name="Modal Operator on Sidebar Buttons",
            description="After adding duplicates with sidebar buttons show popup for changing their parameters",
            default=False,
        )
        sidebar_category: bpy.props.StringProperty(
            name="Sidebar Category",
            description="Name for the tab in the sidebar panel",
            default="Item",
            update=update_sidebar_category,
        )
        move_empties_to_collection: bpy.props.BoolProperty(
            name="Move Empties to Collection",
            description="Move newly created empties to scene collection to hide them",
            default=False,
        )
        empties_collection: bpy.props.StringProperty(
            name="Empties Collection",
            description="Name of the scene collection for newly created empties",
            default="Radial Empties",
            get=get_empties_collection,
            set=set_empties_collection,
        )

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, "tabs", expand=True)
        box = col.box()

        if self.tabs == 'GENERAL':
            self.draw_general_preferences(box)
        elif self.tabs == 'KEYMAP':
            self.draw_keymap(box)
        elif self.tabs == 'COLORS':
            self.draw_colors(box)

    def draw_general_preferences(self, box: bpy.types.UILayout) -> None:
        col = box.column()
        col.use_property_split = True
        col.use_property_decorate = False

        col.prop(self, "mouse_sensitivity")
        col.prop(self, "sidebar_category")

        col.prop(self, "use_wheelmouse")
        col.prop(self, "hide_sidebar")
        col.prop(self, "modal_buttons")

        col.prop(self, "move_empties_to_collection")

        sub = col.column()
        sub.active = self.move_empties_to_collection
        sub.prop(self, "empties_collection")

    def draw_keymap(self, box: bpy.types.UILayout) -> None:
        col = box.column()
        keymap_items = [km_kmi[1] for km_kmi in ot_keymap.addon_ot_km_kmis]
        layout_draw_utils.draw_keymap_items(
            keymap_items=keymap_items, keymap_name="3D View", allow_removing=False, column=col
        )

        col = box.column()
        col.label(text="Modal Keymap")
        keymap_items = self.keymaps["modal"].keymap_items
        layout_draw_utils.draw_modal_keymap_items(keymap_items=keymap_items, tag="Default", column=col)
        col.separator()
        layout_draw_utils.draw_modal_keymap_items(keymap_items=keymap_items, tag="Mode", column=col)
        col.separator()
        layout_draw_utils.draw_modal_keymap_items(keymap_items=keymap_items, tag="Reset", column=col)

    def draw_colors(self, box: bpy.types.UILayout) -> None:
        col = box.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.label(text="Overlay Colors")
        col.prop(self.overlay_colors, "use_from_theme")

        sub = col.column()
        if self.overlay_colors.use_from_theme:
            sub.enabled = False

        sub.prop(self.overlay_colors, "main")
        sub.prop(self.overlay_colors, "key")
        sub.prop(self.overlay_colors, "val")
        sub.prop(self.overlay_colors, "bg")


classes = (RADDUPLICATOR_preferences,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    modal_keymap.register_modal_keymap()


def unregister():
    from bpy.utils import unregister_class

    for cls in classes:
        unregister_class(cls)
