from . import radial_array, radial_duplicates, radial_screw

_classes = (
    radial_array.RADDUPLCIATOR_OT_radial_array_add,
    radial_array.RADDUPLICATOR_OT_radial_array_apply,
    radial_array.RADDUPLICATOR_OT_radial_array_modal,
    radial_array.RADDUPLICATOR_OT_radial_array_refresh,
    radial_array.RADDUPLICATOR_OT_radial_array_remove,
    radial_array.RADDUPLCIATOR_OT_radial_array_set_pivot_point,
    radial_screw.RADDUPLCIATOR_OT_radial_screw_add,
    radial_screw.RADDUPLICATOR_OT_radial_screw_apply,
    radial_screw.RADDUPLICATOR_OT_radial_screw_modal,
    radial_screw.RADDUPLICATOR_OT_radial_screw_refresh,
    radial_screw.RADDUPLICATOR_OT_radial_screw_remove,
    radial_screw.RADDUPLCIATOR_OT_radial_screw_set_pivot_point,
    radial_duplicates.RADDUPLCIATOR_OT_radial_duplicates_add,
    radial_duplicates.RADDUPLICATOR_OT_radial_duplicates_modal,
    radial_duplicates.RADDUPLICATOR_OT_radial_duplicates_remove,
    radial_duplicates.RADDUPLCIATOR_OT_radial_duplicates_set_pivot_point,
)


def register():
    from bpy.utils import register_class

    for cls in _classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in _classes:
        unregister_class(cls)
