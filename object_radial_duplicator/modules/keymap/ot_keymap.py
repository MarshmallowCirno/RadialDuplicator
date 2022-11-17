import bpy

addon_ot_km_kmis = []


def register_ot_keymap():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')

        kmi = km.keymap_items.new("radial_duplicator.duplicates_modal", 'D', 'PRESS', shift=True, alt=True)
        kmi.properties.pivot_point = 'CURSOR'
        addon_ot_km_kmis.append((km, kmi))

        kmi = km.keymap_items.new("radial_duplicator.screw_modal", 'S', 'PRESS', shift=True, alt=True)
        addon_ot_km_kmis.append((km, kmi))

        kmi = km.keymap_items.new("radial_duplicator.array_modal", 'R', 'PRESS', shift=True, alt=True)
        addon_ot_km_kmis.append((km, kmi))


def unregister_ot_keymap():
    for km, kmi in addon_ot_km_kmis:
        km.keymap_items.remove(kmi)
    addon_ot_km_kmis.clear()


def register():
    register_ot_keymap()


def unregister():
    unregister_ot_keymap()
