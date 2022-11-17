import bpy
import rna_keymap_ui
from bpy.types import KeyMapItem, UILayout, CollectionProperty


def redraw_sidebar(context) -> None:
    """Redraw all sidebars in screen."""
    for area in context.screen.areas:
        for region in area.regions:
            if region.type == "UI":
                area.tag_redraw()


def draw_keymap_items(keymap_items: list[KeyMapItem],
                      keymap_name: str,
                      allow_removing: bool,
                      column: UILayout) -> None:
    """Draw addon keymap items.

        Args:
            keymap_items: list[KeyMapItem] -- Addon keymap items
            keymap_name: KeyMap.name -- Filter keymap items on this keymap_name
            allow_removing: set[KeyMapItem.map_type] -- Make button for removing keymap active
            column: UILayout -- Layout column
    """

    kc = bpy.context.window_manager.keyconfigs.user
    km = kc.keymaps.get(keymap_name)
    kmi_idnames = [keymap_item.idname for keymap_item in keymap_items]

    if allow_removing:
        column.context_pointer_set("keymap", km)

    kmis = [kmi for kmi in km.keymap_items if kmi.idname in kmi_idnames]

    for kmi in kmis:
        rna_keymap_ui.draw_kmi(['ADDON', 'USER', 'DEFAULT'], kc, km, kmi, column, 0)


def draw_modal_keymap_items(keymap_items: CollectionProperty,
                            tag: str,
                            column: UILayout) -> None:

    for kmi in keymap_items.values():
        if kmi.tag == tag:
            row = column.row()
            row.use_property_split = True
            row.use_property_decorate = False
            row.prop(kmi, "type", text=kmi.label, event=True)

            row.alignment = 'RIGHT'
            row.prop(kmi, "alt", text='Alt', toggle=True)
            row.prop(kmi, "ctrl", text='Ctrl', toggle=True)
            row.prop(kmi, "shift", text='Shift', toggle=True)
