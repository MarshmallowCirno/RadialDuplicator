import bpy


class RADDUPLICATOR_OT_apply_multi_user_data_dialog(bpy.types.Operator):
    bl_idname = "radial_duplicator.apply_multi_user_data_dialog"
    bl_label = "Apply Multiuser Data Dialog"
    bl_options = {'INTERNAL'}

    name: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    op_name: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=360)

    def draw(self, context):
        layout = self.layout

        # Don't draw after applying an modifier
        if context.object.modifiers.get(self.name) is None:
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


classes = (
    RADDUPLICATOR_OT_apply_multi_user_data_dialog,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
