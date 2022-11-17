import bpy

from ..utils.multiuser_data_changer import MultiuserDataChanger


class ApplyModifierBase:
    """Base operator for applying a modifier."""

    # noinspection PyTypeChecker
    multiuser_data_apply_method: bpy.props.EnumProperty(
        items=[
            ('NONE', "None", ""),
            ('APPLY_TO_SINGLE', "Apply To Single", ""),
            ('APPLY_TO_ALL', "Apply To All", ""),
        ],
        default='NONE',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    bl_idname: str = NotImplemented
    name: str = NotImplemented

    def invoke(self, context, _):
        ob = context.object
        if ob.data.users > 1 and self.multiuser_data_apply_method == 'NONE':
            bpy.ops.radial_duplicator.apply_multi_user_data_dialog(
                'INVOKE_DEFAULT', name=self.name, op_name=self.bl_idname
            )
            return {'CANCELLED'}
        else:
            return self.execute(context)

    def execute(self, context):
        ob = context.object
        ob_is_multiuser = ob.data.users > 1

        multiuser_data_changer = MultiuserDataChanger(ob)
        if ob_is_multiuser and self.multiuser_data_apply_method != 'NONE':
            multiuser_data_changer.make_object_data_single_user()

        self.apply(context)

        if ob_is_multiuser and self.multiuser_data_apply_method == 'APPLY_TO_ALL':
            multiuser_data_changer.link_new_object_data_to_instances()
        return {'FINISHED'}

    def apply(self, context):
        raise NotImplementedError()
