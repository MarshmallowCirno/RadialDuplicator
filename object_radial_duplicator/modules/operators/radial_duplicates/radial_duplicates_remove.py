import bpy

from ...radial_objects.radial_duplicates_object import RadialDuplicates


class RADDUPLICATOR_OT_radial_duplicates_remove(bpy.types.Operator):
    """Remove radial duplicates from the active object"""

    bl_idname = "radial_duplicator.duplicates_remove"
    bl_label = "Remove Radial Duplicates"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (
            context.area.type == 'VIEW_3D'
            and ob is not None
            and ob.mode == 'OBJECT'
            and ob.library is None
            and not (ob.data is not None and ob.data.library is not None)
        )

    def invoke(self, context, _):
        return self.execute(context)

    def execute(self, context):
        ob = context.object
        if ob.parent is not None and len(ob.parent.radial_duplicator.duplicates) > 0:
            center_empty = ob.parent
        elif len(ob.radial_duplicator.duplicates) > 0:
            center_empty = ob
        else:
            return {'CANCELLED'}

        props = center_empty.radial_duplicator.duplicates[0]
        radial_duplicates = RadialDuplicates.from_props(context, props)
        radial_duplicates.remove()
        return {'FINISHED'}


classes = (
    RADDUPLICATOR_OT_radial_duplicates_remove,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
