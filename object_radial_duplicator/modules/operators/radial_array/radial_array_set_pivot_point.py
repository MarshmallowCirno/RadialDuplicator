from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import bpy

from ...radial_objects import radial_array_object

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class RADDUPLCIATOR_OT_radial_array_set_pivot_point(bpy.types.Operator):
    """Set radial array pivot point"""

    bl_idname = "radial_duplicator.array_set_pivot_point"
    bl_label = "Set Radial Array Pivot Point"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    if TYPE_CHECKING:
        name: str
        pivot_point: Literal['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT']
    else:
        name: bpy.props.StringProperty(
            name="Name",
            description="Name of the radial array to edit",
            options={'HIDDEN', 'SKIP_SAVE'},
        )
        pivot_point: bpy.props.EnumProperty(
            name="Center",
            description="Array center",
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
    def poll(cls, context: bpy.types.Context) -> bool:
        ob = context.object
        return (
            context.area.type == 'VIEW_3D'
            and ob is not None
            and ob.mode in {'OBJECT', 'EDIT'}
            and ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}
            and ob.library is None  # pyright: ignore[reportUnnecessaryComparison]
            and not (ob.data is not None and ob.data.library is not None)  # pyright: ignore[reportUnnecessaryComparison]
        )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[OperatorReturnItems]:
        self.execute(context)
        return {'FINISHED'}

    def execute(self, context: bpy.types.Context) -> set[OperatorReturnItems]:
        # From poll
        assert context.object is not None

        radial_arrays = radial_array_object.ObjectRadialArrays(context, context.object)
        radial_array = radial_arrays.get_by_name(self.name)
        if radial_array is None:
            self.report({'ERROR'}, "Not found")
            return {'CANCELLED'}
        radial_array.set_pivot_point(self.pivot_point)
        return {'FINISHED'}


classes = (RADDUPLCIATOR_OT_radial_array_set_pivot_point,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in classes:
        unregister_class(cls)
