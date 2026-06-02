from __future__ import annotations

from typing import TYPE_CHECKING

import bpy

from ...radial_objects import radial_screw_object

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class RADDUPLICATOR_OT_radial_screw_remove(bpy.types.Operator):
    """Remove screw from the active object"""

    bl_idname = "radial_duplicator.screw_remove"
    bl_label = "Remove Screw"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    if TYPE_CHECKING:
        name: str
    else:
        name: bpy.props.StringProperty(
            name="Name",
            description="Name of the screw to edit",
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
        return self.execute(context)

    def execute(self, context: bpy.types.Context) -> set[OperatorReturnItems]:
        # From poll
        assert context.object is not None

        radial_screws = radial_screw_object.ObjectRadialScrews(context, context.object)
        radial_screw = radial_screws.get_by_name(self.name)
        if radial_screw is None:
            self.report({'ERROR'}, "Not found")
            return {'CANCELLED'}
        radial_screw.remove()
        return {'FINISHED'}
