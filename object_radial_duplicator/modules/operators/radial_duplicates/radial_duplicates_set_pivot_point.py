import bpy

from ...radial_objects.radial_duplicates_object import RadialDuplicates


class RADDUPLCIATOR_OT_radial_duplicates_set_pivot_point(bpy.types.Operator):
    """Set radial duplicates pivot point"""

    bl_idname = "radial_duplicator.duplicates_set_pivot_point"
    bl_label = "Set Radial Duplicates Pivot Point"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    # noinspection PyTypeChecker
    pivot_point: bpy.props.EnumProperty(
        name="Center",
        description="Duplicates center",
        items=[
            ('ORIGIN', "Origin", "Object origin", 'OBJECT_ORIGIN', 0),
            ('CURSOR', "3D Cursor", "3D cursor", 'PIVOT_CURSOR', 1),
            ('MESH_SELECTION', "Mesh Selection", "Mesh selection", 'EDITMODE_HLT', 2),
            ('ACTIVE_OBJECT', "Active Object", "Active object", 'PIVOT_ACTIVE', 3),
        ],
        default='ORIGIN',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

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
        self.execute(context)
        return {'FINISHED'}

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
        radial_duplicates.set_pivot_point(self.pivot_point)
        return {'FINISHED'}


classes = (
    RADDUPLCIATOR_OT_radial_duplicates_set_pivot_point,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
