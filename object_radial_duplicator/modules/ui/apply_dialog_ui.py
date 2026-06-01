from __future__ import annotations

from typing import TYPE_CHECKING

import bpy

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class RADDUPLICATOR_OT_apply_multi_user_data_dialog(bpy.types.Operator):
    bl_idname = "radial_duplicator.apply_multi_user_data_dialog"
    bl_label = "Apply Multiuser Data Dialog"
    bl_options = {'INTERNAL'}

    if TYPE_CHECKING:
        name: str
        op_name: str
    else:
        name: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
        op_name: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context: bpy.types.Context) -> set[OperatorReturnItems]:
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[OperatorReturnItems]:
        return context.window_manager.invoke_popup(self, width=360)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        assert layout is not None
        ob = context.object
        assert ob is not None

        # Don't draw after applying a modifier
        if ob.modifiers.get(self.name) is None:
            return

        layout.operator_context = 'EXEC_DEFAULT'

        layout.label(text="Object's data is used by multiple objects. What would you like to do?")
        layout.separator()

        op = layout.operator(self.op_name, text="Apply To Active Object Only (Break Link)")
        op.multiuser_data_apply_method = 'APPLY_TO_SINGLE'
        op.name = self.name

        op = layout.operator(self.op_name, text="Apply To All Objects")
        op.multiuser_data_apply_method = 'APPLY_TO_ALL'
        op.name = self.name


classes = (RADDUPLICATOR_OT_apply_multi_user_data_dialog,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in classes:
        unregister_class(cls)
