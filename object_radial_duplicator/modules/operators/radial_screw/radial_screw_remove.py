import bpy

from ...radial_objects.radial_screw_object import ObjectRadialScrews


class RADDUPLICATOR_OT_radial_screw_remove(bpy.types.Operator):
    """Remove screw from the active object"""

    bl_idname = "radial_duplicator.screw_remove"
    bl_label = "Remove Screw"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    name: bpy.props.StringProperty(
        name="Name",
        description="Name of the screw to edit",
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (
            context.area.type == 'VIEW_3D'
            and ob is not None
            and ob.mode in {'OBJECT', 'EDIT'}
            and ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}
            and ob.library is None
            and ob.data.library is None
        )

    def invoke(self, context, _):
        return self.execute(context)

    def execute(self, context):
        radial_screws = ObjectRadialScrews(context, context.object)
        radial_screw = radial_screws[self.name]
        radial_screw.remove()
        return {'FINISHED'}


classes = (
    RADDUPLICATOR_OT_radial_screw_remove,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
