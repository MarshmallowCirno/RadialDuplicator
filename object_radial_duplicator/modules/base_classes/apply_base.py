from typing import TYPE_CHECKING, Any, Literal

import bpy

from ..utils import multiuser_data_changer

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class ApplyModifierBase:
    """Base operator for applying a modifier."""

    if TYPE_CHECKING:
        multiuser_data_apply_method: Literal['NONE', 'APPLY_TO_SINGLE', 'APPLY_TO_ALL']
    else:
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

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event) -> set[OperatorReturnItems]:
        ob = context.object
        assert ob is not None
        assert ob.data is not None

        if ob.data.users > 1 and self.multiuser_data_apply_method == 'NONE':
            bpy.ops.radial_duplicator.apply_multi_user_data_dialog(  # pyright: ignore[reportAttributeAccessIssue]
                'INVOKE_DEFAULT', name=self.name, op_name=self.bl_idname
            )
            return {'CANCELLED'}
        else:
            return self.execute(context)

    def execute(self, context: bpy.types.Context) -> set[OperatorReturnItems]:
        ob = context.object
        assert ob is not None
        assert ob.data is not None

        ob_is_multiuser = ob.data.users > 1

        data_changer = multiuser_data_changer.MultiuserDataChanger(ob)
        if ob_is_multiuser and self.multiuser_data_apply_method != 'NONE':
            data_changer.make_object_data_single_user()

        self.apply(context)

        if ob_is_multiuser and self.multiuser_data_apply_method == 'APPLY_TO_ALL':
            data_changer.link_new_object_data_to_instances()
        return {'FINISHED'}

    def apply(self, _context: bpy.types.Context) -> Any:
        raise NotImplementedError()
