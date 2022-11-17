import bpy

from ...base_classes.apply_base import ApplyModifierBase
from ...radial_objects.radial_array_object import ObjectRadialArrays


class RADDUPLICATOR_OT_radial_array_apply(bpy.types.Operator, ApplyModifierBase):
    """Apply radial array to the active object"""

    bl_idname = "radial_duplicator.array_apply"
    bl_label = "Apply Radial Array"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    name: bpy.props.StringProperty(
        name="Name",
        description="Name of the radial array to edit",
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (
            context.area.type == 'VIEW_3D'
            and ob is not None
            and ob.mode == 'OBJECT'
            and ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}
            and ob.library is None
            and ob.data.library is None
        )

    def apply(self, context):
        radial_arrays = ObjectRadialArrays(context, context.object)
        radial_array = radial_arrays[self.name]
        message = radial_array.apply()
        if message:
            self.report({'INFO'}, message)
        return {'FINISHED'}


classes = (
    RADDUPLICATOR_OT_radial_array_apply,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
