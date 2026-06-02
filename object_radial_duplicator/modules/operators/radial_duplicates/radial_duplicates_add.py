from __future__ import annotations

import math
from typing import TYPE_CHECKING, Literal, cast

import bpy

from ...radial_objects import radial_duplicates_object

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class RADDUPLCIATOR_OT_radial_duplicates_add(bpy.types.Operator):
    bl_description = (
        "LMB: Add around object origin.\nLMB + Ctrl: Add around 3D cursor.\nLMB + Shift: Add around active object"
    )
    bl_idname = "radial_duplicator.duplicates_add"
    bl_label = "Add Radial Duplicates"
    bl_options = {'REGISTER', 'UNDO'}

    if TYPE_CHECKING:
        spin_orientation: Literal['GLOBAL', 'LOCAL', 'VIEW']
        spin_axis: Literal['X', 'Y', 'Z']
        duplicates_rotation: Literal['FOLLOW', 'KEEP', 'RANDOM']
        count: int
        end_angle: float
        end_scale: float
        height_offset: float
        pivot_point: Literal['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT']
        from_button: bool
    else:
        spin_orientation: bpy.props.EnumProperty(
            name="Spin Orientation",
            description="Spin orientation",
            items=[
                ('GLOBAL', "Global", "Align the duplication axes to world space", 'ORIENTATION_GLOBAL', 0),
                (
                    'LOCAL',
                    "Local",
                    "Align the duplication axes to selected objects' local space",
                    'ORIENTATION_LOCAL',
                    1,
                ),
                ('VIEW', "View", "Align the duplication axes to the window", 'ORIENTATION_VIEW', 2),
            ],
            default='LOCAL',
            options={'SKIP_SAVE'},
        )
        spin_axis: bpy.props.EnumProperty(
            name="Spin Axis",
            description="Axis along which duplication will be performed",
            items=[
                ('X', "X", "Spin around axis X"),
                ('Y', "Y", "Spin around axis Y"),
                ('Z', "Z", "Spin around axis Z"),
            ],
            default='Z',
            options={'SKIP_SAVE'},
        )
        duplicates_rotation: bpy.props.EnumProperty(
            name="Duplicates Rotation",
            description="Rotation of duplicated objects around their own origin",
            items=[
                ('FOLLOW', "Follow", "Follow rotation around the spin axis"),
                ('KEEP', "Keep", "Keep initial object rotation"),
                ('RANDOM', "Random", "Randomize object rotation around the spin axis"),
            ],
            default='FOLLOW',
            options={'SKIP_SAVE'},
        )
        count: bpy.props.IntProperty(
            name="Count",
            description="Total number of duplicates to make",
            min=1,
            default=6,
            options={'SKIP_SAVE'},
        )
        end_angle: bpy.props.FloatProperty(
            name="End Angle",
            description="Rotation placement for the last duplicated geometry as a number of degrees offset from 0 degrees",
            min=0,
            max=math.radians(360),
            subtype='ANGLE',
            unit='ROTATION',
            step=100,
            default=math.radians(360),
            options={'SKIP_SAVE'},
        )
        end_scale: bpy.props.FloatProperty(
            name="End Scale",
            description="Scale of the last duplicated object as a factor",
            min=0.001,
            step=1,
            default=1.0,
            precision=3,
            options={'SKIP_SAVE'},
        )
        height_offset: bpy.props.FloatProperty(
            name="Height Offset",
            description="Moves each successive duplicate a user-defined distance from the previous duplicate "
            "along the defined Axis. This is useful when combined with an End Angle "
            "greater than 360 degrees to create a spiral",
            subtype='DISTANCE',
            unit='LENGTH',
            default=0.0,
            options={'SKIP_SAVE'},
        )
        pivot_point: bpy.props.EnumProperty(
            name="Center",
            description="Duplication center",
            items=[
                ('ORIGIN', "Origin", "Object origin"),
                ('CURSOR', "Cursor", "3D cursor"),
                ('MESH_SELECTION', "Mesh Selection", "Mesh selection"),
                ('ACTIVE_OBJECT', "Active Object", "Active object"),
            ],
            default='ORIGIN',
            options={'SKIP_SAVE'},
        )
        from_button: bpy.props.BoolProperty(
            name="From Button",
            description="Operator will be executed from a button. Ctrl and shift state determine pivot point",
            default=False,
            options={'SKIP_SAVE'},
        )

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
        # From poll
        assert context.object is not None
        assert isinstance(context.object.data, bpy.types.Mesh | bpy.types.Curve)

        if self.from_button:
            if event.ctrl:
                self.pivot_point = 'CURSOR'
            elif event.shift:
                self.pivot_point = 'ACTIVE_OBJECT'

        self.execute(context)
        return {'FINISHED'}

    def execute(self, context: bpy.types.Context) -> set[OperatorReturnItems]:
        # From poll
        assert context.object is not None
        assert context.selected_objects is not None

        sel_obs = [ob for ob in context.selected_objects]
        active_ob = context.view_layer.objects.active

        if not context.selected_objects:
            sel_obs = [context.object]
        # use active object only as pivot point, don't add radial duplicates from it
        elif self.pivot_point == 'ACTIVE_OBJECT' and active_ob in sel_obs:
            sel_obs.remove(active_ob)

        for starting_ob in sel_obs:
            radial_duplicates = radial_duplicates_object.RadialDuplicates.new(context, starting_ob)
            radial_duplicates.modify(
                self.spin_orientation,
                self.spin_axis,
                self.duplicates_rotation,
                self.count,
                self.end_angle,
                self.end_scale,
                self.height_offset,
                self.pivot_point,
            )
        return {'FINISHED'}

    def draw(self, context: bpy.types.Context) -> None:
        # fake-bpy-module fix
        layout = cast(bpy.types.UILayout, self.layout)

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "spin_orientation")

        row = layout.row()
        row.prop(self, "spin_axis", expand=True)

        row = layout.row()
        row.prop(self, "duplicates_rotation", expand=True)

        layout.prop(self, "count")
        layout.prop(self, "end_angle")
        layout.prop(self, "end_scale")
        layout.prop(self, "height_offset")
        layout.prop(self, "pivot_point")
