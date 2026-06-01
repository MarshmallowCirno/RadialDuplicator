from __future__ import annotations

from typing import TYPE_CHECKING, cast

import bpy

from ... import properties
from ...radial_objects import radial_duplicates_object

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class RADDUPLICATOR_OT_radial_duplicates_remove(bpy.types.Operator):
    """Remove radial duplicates from the active object"""

    bl_idname = "radial_duplicator.duplicates_remove"
    bl_label = "Remove Radial Duplicates"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        ob = context.object
        return (
            context.area.type == 'VIEW_3D'
            and ob is not None
            and ob.mode == 'OBJECT'
            and ob.library is None  # pyright: ignore[reportUnnecessaryComparison]
            and not (ob.data is not None and ob.data.library is not None)  # pyright: ignore[reportUnnecessaryComparison]
        )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[OperatorReturnItems]:
        return self.execute(context)

    def execute(self, context: bpy.types.Context) -> set[OperatorReturnItems]:
        # From poll
        assert context.object is not None

        ob = context.object
        if (
            ob.parent is not None
            and len(cast(properties.RadialCollections, ob.parent.radial_duplicator).duplicates) > 0  # pyright: ignore[reportAttributeAccessIssue]
        ):
            center_empty = ob.parent
        elif len(cast(properties.RadialCollections, ob.radial_duplicator).duplicates) > 0:  # pyright: ignore[reportAttributeAccessIssue]
            center_empty = ob
        else:
            return {'CANCELLED'}

        props_collection = cast(properties.RadialCollections, center_empty.radial_duplicator)  # pyright: ignore[reportAttributeAccessIssue]
        props = props_collection.duplicates[0]
        radial_duplicates = radial_duplicates_object.RadialDuplicates.from_props(context, props)
        radial_duplicates.remove()
        return {'FINISHED'}


classes = (RADDUPLICATOR_OT_radial_duplicates_remove,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in classes:
        unregister_class(cls)
