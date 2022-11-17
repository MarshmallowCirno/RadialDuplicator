from math import radians

import bpy

from ...radial_objects.radial_array_object import ObjectRadialArrays
from ...utils.object_data import data_is_selected


class RADDUPLCIATOR_OT_radial_array_add(bpy.types.Operator):
    bl_description = ("LMB: Add around object origin.\n"
                      "LMB + Ctrl: Add around 3D cursor.\n"
                      "LMB + Shift: Add around active object")
    bl_idname = "radial_duplicator.array_add"
    bl_label = "Add Radial Array"
    bl_options = {'REGISTER', 'UNDO'}

    # noinspection PyTypeChecker
    spin_orientation: bpy.props.EnumProperty(
        name="Spin Orientation",
        description="Spin orientation",
        items=[
            ('GLOBAL', "Global", "Align the array axes to world space", 'ORIENTATION_GLOBAL', 0),
            ('LOCAL', "Local", "Align the array axes to selected objects' local space", 'ORIENTATION_LOCAL', 1),
            ('VIEW', "View", "Align the array axes to the window", 'ORIENTATION_VIEW', 2),
            ('NORMAL', "Normal", "Align the array axes to average normal of selected mesh elements",
             'ORIENTATION_NORMAL', 3),
        ],
        default='LOCAL',
        options={'SKIP_SAVE'},
    )
    # noinspection PyTypeChecker
    spin_axis: bpy.props.EnumProperty(
        name="Spin Axis",
        description="Axis along which spin will be performed",
        items=[
            ('X', "X", "Spin around axis X"),
            ('Y', "Y", "Spin around axis Y"),
            ('Z', "Z", "Spin around axis Z"),
        ],
        default='Z',
        options={'SKIP_SAVE'},
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="Total number of duplicates to make",
        min=1,
        default=6,
        options={'SKIP_SAVE'},
    )
    radius_offset: bpy.props.FloatProperty(
        name="Radius Offset",
        description="Moves each duplicate a user-defined distance from the pivot point",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
        options={'SKIP_SAVE'},
    )
    start_angle: bpy.props.FloatProperty(
        name="Start Angle",
        description="Rotation placement for the first duplicated geometry as a number of degrees "
        "offset from the initial 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(0),
        options={'SKIP_SAVE'},
    )
    end_angle: bpy.props.FloatProperty(
        name="End Angle",
        description="Rotation placement for the last duplicated geometry as a number of degrees "
        "offset from 0 degrees",
        min=0,
        max=radians(360),
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(360),
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
    # noinspection PyTypeChecker
    pivot_point: bpy.props.EnumProperty(
        name="Center",
        description="Array center",
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

    def invoke(self, context, event):
        # Use NORMAL orientation if data element is selected
        # noinspection PyTypeChecker
        if context.object.mode == 'EDIT' and data_is_selected(context.object.data):
            self.spin_orientation = 'NORMAL'
            self.pivot_point = 'MESH_SELECTION'

        if self.from_button:
            if event.ctrl:
                self.pivot_point = 'CURSOR'
            elif event.shift:
                self.pivot_point = 'ACTIVE_OBJECT'

        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        sel_obs = [ob for ob in context.selected_objects if ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}]
        active_ob = context.view_layer.objects.active

        if not context.selected_objects:
            sel_obs = [context.object]
        # use active object only as pivot point, don't add radial array to it
        elif self.pivot_point == 'ACTIVE_OBJECT' and active_ob in sel_obs:
            sel_obs.remove(active_ob)

        for ob in sel_obs:
            radial_arrays = ObjectRadialArrays(context, ob)
            radial_array = radial_arrays.new()
            radial_array.modify(
                self.spin_orientation,
                self.spin_axis,
                self.count,
                self.radius_offset,
                self.start_angle,
                self.end_angle,
                self.height_offset,
                self.pivot_point,
            )
        return {'FINISHED'}

    # noinspection PyTypeChecker
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "spin_orientation")

        row = layout.row()
        row.prop(self, "spin_axis", expand=True)

        layout.prop(self, "count")
        if context.object.type == 'MESH':
            layout.prop(self, "radius_offset")
        layout.prop(self, "start_angle")
        layout.prop(self, "end_angle")
        layout.prop(self, "height_offset")
        layout.prop(self, "pivot_point")


classes = (
    RADDUPLCIATOR_OT_radial_array_add,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
