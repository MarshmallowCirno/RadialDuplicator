from . import apply_dialog_ui, sidebar_ui

_classes = (
    apply_dialog_ui.RADDUPLICATOR_OT_apply_multi_user_data_dialog,
    sidebar_ui.RADDUPLCIATOR_PT_sidebar,
)


def register():
    from bpy.utils import register_class

    for cls in _classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in _classes:
        unregister_class(cls)
