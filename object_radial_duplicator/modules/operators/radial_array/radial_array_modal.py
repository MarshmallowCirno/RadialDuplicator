from math import ceil
from math import degrees
from math import radians
from typing import Optional, Union

import bpy
import gpu
import numpy as np
from bgl import glEnable
from bgl import glClear
from bgl import glColorMask
from bgl import glDisable
from bgl import glLineWidth
from bgl import glStencilFunc
from bgl import glStencilMask
from bgl import glStencilOp
from bgl import GL_ALWAYS
from bgl import GL_BLEND
from bgl import GL_EQUAL
from bgl import GL_FALSE
from bgl import GL_INVERT
from bgl import GL_KEEP
from bgl import GL_LINE_SMOOTH
from bgl import GL_STENCIL_BUFFER_BIT
from bgl import GL_STENCIL_TEST
from bgl import GL_TRUE
from bpy.types import Object
from gpu_extras.batch import batch_for_shader
from gpu.types import GPUBatch
from mathutils import Matrix
from mathutils import Vector

from ....package import get_preferences
from ...preferences.preferences import RADDUPLICATOR_preferences
from ...properties import ModalKeyMapItem
from ...radial_objects.radial_array_object import ObjectRadialArrays
from ...radial_objects.radial_array_object import RadialArray
from ...utils.math import build_circle
from ...utils.math import flatten_vec
from ...utils.math import get_axis_vec
from ...utils.modal import event_match_kmi
from ...utils.modal import event_type_is_digit
from ...utils.modal import event_type_to_digit
from ...utils.modal import get_property_default
from ...utils.object import set_origin
from ...utils.object_data import data_is_selected
from ...utils.object_data import get_data_center_co_world
from ...utils.opengl_draw import draw_bg
from ...utils.scene import get_unit
from ...utils.text import draw_text_block
from ...utils.text import get_text_block_dimensions
from ...utils.theme import get_axis_color
from ...utils.view3d import get_non_overlap_width
from ...utils.view3d import hide_sidebar
from ...utils.view3d import restore_sidebar

shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
shader_3d = gpu.shader.from_builtin('3D_UNIFORM_COLOR')


class RADDUPLICATOR_OT_radial_array_modal(bpy.types.Operator):
    bl_description = ("LMB: Edit radial array or add a new one if it doesn't exist.\n"
                      "+ Shift: Add a new radial array instead of trying to edit existing.\n"
                      "+ Ctrl: Set array center to the 3D cursor instead of object pivot")
    bl_idname = "radial_duplicator.array_modal"
    bl_label = "Radial Array Modal"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

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
            ('CENTER_EMPTY', "Center Empty", "Center empty"),
        ],
        default='ORIGIN',
        options={'SKIP_SAVE'}
    )
    new: bpy.props.BoolProperty(
        name="Force New Array",
        description="Add a new radial array instead of trying to pick up and edit existing",
        default=False,
        options={'SKIP_SAVE'}
    )
    from_button: bpy.props.BoolProperty(
        name="From Button",
        description="Operator is executed from a button. Ctrl and shift state determine pivot point",
        default=False,
        options={'SKIP_SAVE', 'HIDDEN'},
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

    def __init__(self):
        self.master_ob: Optional[Object] = None   # active selected object
        self.slave_obs: Optional[list[Object]] = None  # nonactive selected objects

        self.master_ob_radial_arrays: Optional[ObjectRadialArrays] = None  # class from all radial arrays of master_ob
        self.master_radial_array: Optional[RadialArray] = None  # class from active radial array of master_ob
        self.slave_radial_arrays: list[RadialArray] = []  # class from top radial arrays of slave_obs

        self.preferences: RADDUPLICATOR_preferences = get_preferences()
        self.keymap_items: ModalKeyMapItem = self.preferences.keymaps["modal"].keymap_items

        self.sidebar_initial_state: bool = False
        self.master_ob_initial_origin: Vector = Vector((0, 0, 0))
        self.radial_array_initial_attrs: dict[RadialArray:dict[str:str]] = {}
        self.radial_array_last_set_pivot_points: dict[RadialArray:str] = {}

        self.new_radial_arrays: list[RadialArray] = []
        self.modified_radial_arrays: set[RadialArray] = set()

        self.typed_string: Optional[str] = None
        self.count_before_typing: int = 0

        self.count_float: float = self.count
        self.radius_offset_float: float = self.radius_offset
        self.start_angle_float: float = self.start_angle
        self.end_angle_float: float = self.end_angle
        self.height_offset_float: float = self.height_offset

        self.count_changing: bool = False
        self.radius_offset_changing: bool = False
        self.start_angle_changing: bool = False
        self.end_angle_changing: bool = False
        self.height_offset_changing: bool = False

        self.last_mouse_co: tuple[float, float] = (0, 0)
        self.use_wheelmouse: bool = self.preferences.use_wheelmouse

        self.handler_2d: object = None
        self.handler_3d: object = None
        self.axis_circle_batch: Optional[GPUBatch] = None
        self.angle_lines_batch: Optional[GPUBatch] = None
        self.angle_fill_stencil_mask_batch: Optional[GPUBatch] = None
        self.angle_fill_batch: Optional[GPUBatch] = None

    def invoke(self, context, event):
        # Store initial settings, build radial arrays,
        self.sidebar_initial_state = context.space_data.show_region_ui
        self.collect_objects_with_radial_array(context)
        self.master_ob_initial_origin = self.master_ob.matrix_world.to_translation()
        self.build_radial_arrays_on_init(context)
        if self.master_radial_array not in self.new_radial_arrays:
            self.set_operator_properties_from_master_radial_array()
        self.set_operator_properties_from_event_and_context(context, event)
        self.last_mouse_co = (event.mouse_region_x, event.mouse_region_y)

        # Update arrays
        self.modify_all_radial_arrays()

        # Set blender UI
        self.redraw_status(context)
        self.redraw_header(context)
        hide_sidebar(context)

        # Set shaders
        self.build_3d_shader_batches()
        self.handler_2d = context.space_data.draw_handler_add(self.draw_2d_shaders, (context,), 'WINDOW', 'POST_PIXEL')
        self.handler_3d = context.space_data.draw_handler_add(self.draw_3d_shaders, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def collect_objects_with_radial_array(self, context) -> None:
        """Find objects for adding/getting radial arrays."""
        self.master_ob = context.object
        self.slave_obs = [
            ob
            for ob in context.selected_objects
            if ob is not self.master_ob and ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}
        ]
        # use active object only as pivot point, don't add radial array to it
        active_ob = context.view_layer.objects.active
        if self.pivot_point == 'ACTIVE_OBJECT' and active_ob in self.slave_obs:
            self.slave_obs.remove(active_ob)

    def build_radial_arrays_on_init(self, context) -> None:
        """Build radial array classes from array modifiers and store initial attributes
        or build new radial array classes."""
        self.master_ob_radial_arrays = ObjectRadialArrays(context, self.master_ob)
        if self.new:
            self.build_new_radial_arrays(context)
        else:
            success = self.build_radial_arrays_from_modifiers(context)
            if not success:
                self.build_new_radial_arrays(context)

    def build_radial_arrays_from_modifiers(self, context) -> bool:
        """Try building radial array classes from array modifiers, then store their initial attributes."""
        self.master_radial_array = self.master_ob_radial_arrays[-1]
        success = self.master_radial_array is not None
        if success:
            self.store_existing_radial_array_attrs(self.master_radial_array)
            if self.slave_obs:
                for slave_ob in self.slave_obs:
                    slave_ob_radial_arrays = ObjectRadialArrays(context, slave_ob)
                    slave_radial_array = slave_ob_radial_arrays[-1]
                    if slave_radial_array is None:
                        slave_radial_array = slave_ob_radial_arrays.new()
                        self.new_radial_arrays.append(slave_radial_array)
                    self.slave_radial_arrays.append(slave_radial_array)
                    self.store_existing_radial_array_attrs(slave_radial_array)
        return success

    def build_new_radial_arrays(self, context) -> None:
        """Build new radial array classes."""
        self.master_radial_array = self.master_ob_radial_arrays.new()
        self.new_radial_arrays.append(self.master_radial_array)
        if self.slave_obs:
            for slave_ob in self.slave_obs:
                slave_ob_radial_arrays = ObjectRadialArrays(context, slave_ob)
                slave_radial_array = slave_ob_radial_arrays.new()
                self.new_radial_arrays.append(slave_radial_array)
                self.slave_radial_arrays.append(slave_radial_array)

    def store_existing_radial_array_attrs(self, radial_array: RadialArray) -> None:
        """Store existing radial array classes initial attributes on initialization or after switching to it
        to be able to restore them on CANCEL"""
        name = radial_array.name
        if name not in self.radial_array_initial_attrs.keys():
            props = radial_array.properties.value
            center_empty = radial_array.center_empty.value

            if center_empty is not None:
                pivot_point = 'CENTER_EMPTY'
            else:
                pivot_point = 'ORIGIN'
            pivot_point_co_world = radial_array.pivot_point.co_world

            self.radial_array_initial_attrs[name] = {
                "spin_orientation": props.spin_orientation,
                "spin_orientation_matrix_object": props.spin_orientation_matrix_object.copy(),
                "spin_axis": props.spin_axis,
                "count": props.count,
                "radius_offset": props.radius_offset,
                "start_angle": props.start_angle,
                "end_angle": props.end_angle,
                "height_offset": props.height_offset,
                "pivot_point": pivot_point,
                "pivot_point_co_world": pivot_point_co_world}

    def set_operator_properties_from_master_radial_array(self) -> None:
        """Set operator properties to active existing radial array properties on initialization or array switching."""
        name = self.master_radial_array.name
        props = self.master_radial_array.properties.value
        last_set_pivot_point = self.radial_array_last_set_pivot_points.get(name)
        center_empty = self.master_radial_array.center_empty.value

        # on switching try to find last pivot => center empty => object origin
        if last_set_pivot_point is not None:
            self.pivot_point = last_set_pivot_point
        elif center_empty is not None:
            self.pivot_point = 'CENTER_EMPTY'
        else:
            self.pivot_point = 'ORIGIN'

        self.spin_orientation = props.spin_orientation
        self.spin_axis = props.spin_axis
        self.count = self.count_float = props.count
        self.radius_offset = self.radius_offset_float = props.radius_offset
        self.start_angle = self.start_angle_float = props.start_angle
        self.end_angle = self.end_angle_float = props.end_angle
        self.height_offset = self.height_offset_float = props.height_offset

    def set_operator_properties_from_event_and_context(self, context, event) -> None:
        """Set operator properties from object data selection and event."""
        if context.object.mode == 'EDIT' and data_is_selected(context.object.data):
            self.spin_orientation = 'NORMAL'
            self.pivot_point = 'MESH_SELECTION'

        if self.from_button:
            if event.ctrl:
                self.pivot_point = 'CURSOR'
            elif event.shift:
                self.pivot_point = 'ACTIVE_OBJECT'

    def modify_all_radial_arrays(self) -> None:
        """Modify radial arrays with operator properties."""
        for radial_array in [self.master_radial_array] + self.slave_radial_arrays:
            pivot_point = self.get_pivot_point(radial_array)

            radial_array.modify(self.spin_orientation,
                                self.spin_axis,
                                self.count,
                                self.radius_offset,
                                self.start_angle,
                                self.end_angle,
                                self.height_offset,
                                pivot_point)

            self.modified_radial_arrays.add(radial_array)

            self.radial_array_last_set_pivot_points[radial_array.name] = self.pivot_point
            # store first used pivot point value of newly created arrays
            if radial_array.name not in self.radial_array_initial_attrs:
                pivot_point_co_world = radial_array.pivot_point.co_world
                self.radial_array_initial_attrs[radial_array.name] = {
                    "pivot_point": pivot_point,
                    "pivot_point_co_world": pivot_point_co_world
                }

    def get_pivot_point(self, radial_array) -> Union[str, Vector]:
        """Get pivot point value taking into account changes of object origin. Allows toggling between stored initial
        pivot point."""
        last_set_pivot_point = self.radial_array_last_set_pivot_points.get(radial_array.name)
        initial_attrs = self.radial_array_initial_attrs.get(radial_array.name)

        # Pivot point remains the same
        if last_set_pivot_point == self.pivot_point:
            pivot_point = None
        # Get initial ORIGIN co
        elif (
            self.pivot_point == 'ORIGIN'
            and initial_attrs is not None
            and initial_attrs["pivot_point"] == 'ORIGIN'
        ):
            pivot_point = initial_attrs["pivot_point_co_world"]
        # Get initial CENTER_EMPTY co
        elif (
            self.pivot_point == 'CENTER_EMPTY'
            and initial_attrs is not None
            and initial_attrs["pivot_point"] == 'CENTER_EMPTY'
        ):
            pivot_point = initial_attrs["pivot_point_co_world"]
        else:
            pivot_point = self.pivot_point

        return pivot_point

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            event_mouse_offset_x = event.mouse_region_x - self.last_mouse_co[0]

            if self.count_changing:
                divisor = 300 if event.shift else 90
                offset = event_mouse_offset_x / divisor
                self.count_float += offset
                rounded = int(self.count_float)
                if self.count != rounded:
                    self.count = rounded
                    self.modify_all_radial_arrays()

            if self.radius_offset_changing:
                divisor = 6000 if event.shift else 600
                offset = event_mouse_offset_x / divisor
                self.radius_offset_float += offset
                if event.ctrl or (context.scene.tool_settings.use_snap
                                  and context.scene.tool_settings.use_snap_scale
                                  and context.scene.tool_settings.snap_elements == 'INCREMENT'
                                  and not event.ctrl):
                    rounded = round(self.radius_offset_float / .1) * .1
                    if self.radius_offset != rounded:
                        self.radius_offset = rounded
                        self.modify_all_radial_arrays()
                        self.build_3d_shader_batches()
                        context.region.tag_redraw()
                else:
                    self.radius_offset = self.radius_offset_float
                    self.modify_all_radial_arrays()
                    self.build_3d_shader_batches()
                    context.region.tag_redraw()

            if self.start_angle_changing:
                divisor = 1800 if event.shift else 200
                offset = event_mouse_offset_x / divisor
                self.start_angle_float += offset
                if event.ctrl or (context.scene.tool_settings.use_snap
                                  and context.scene.tool_settings.use_snap_rotate
                                  and context.scene.tool_settings.snap_elements == 'INCREMENT'
                                  and not event.ctrl):
                    rounded = radians(round(degrees(self.start_angle_float) / 10) * 10)
                    if self.start_angle != rounded:
                        self.start_angle = rounded
                        self.modify_all_radial_arrays()
                        self.build_3d_shader_batches()
                        context.region.tag_redraw()
                else:
                    self.start_angle = self.start_angle_float
                    self.modify_all_radial_arrays()
                    self.build_3d_shader_batches()
                    context.region.tag_redraw()

            if self.end_angle_changing:
                divisor = 1800 if event.shift else 200
                offset = event_mouse_offset_x / divisor
                self.end_angle_float += offset
                if event.ctrl or (context.scene.tool_settings.use_snap
                                  and context.scene.tool_settings.use_snap_rotate
                                  and context.scene.tool_settings.snap_elements == 'INCREMENT'
                                  and not event.ctrl):
                    rounded = radians(round(degrees(self.end_angle_float) / 10) * 10)
                    if self.end_angle != rounded:
                        self.end_angle = rounded
                        self.modify_all_radial_arrays()
                        self.build_3d_shader_batches()
                        context.region.tag_redraw()
                else:
                    self.end_angle = self.end_angle_float
                    self.modify_all_radial_arrays()
                    self.build_3d_shader_batches()
                    context.region.tag_redraw()

            if self.height_offset_changing:
                divisor = 1800 if event.shift else 200
                offset = event_mouse_offset_x / divisor
                self.height_offset_float += offset
                if event.ctrl or (context.scene.tool_settings.use_snap
                                  and context.scene.tool_settings.use_snap_scale
                                  and context.scene.tool_settings.snap_elements == 'INCREMENT'
                                  and not event.ctrl):
                    rounded = round(self.height_offset_float / .1) * .1
                    if self.height_offset != rounded:
                        self.height_offset = rounded
                        self.modify_all_radial_arrays()
                        self.build_3d_shader_batches()
                        context.region.tag_redraw()
                else:
                    self.height_offset = self.height_offset_float
                    self.modify_all_radial_arrays()
                    self.build_3d_shader_batches()
                    context.region.tag_redraw()

            self.last_mouse_co = (event.mouse_region_x, event.mouse_region_y)

        if event.value == 'PRESS':
            if event.type == 'MIDDLEMOUSE':
                return {'PASS_THROUGH'}

            elif event.type == 'UP_ARROW' or event.type == 'WHEELUPMOUSE' and event.ctrl:
                self.switch_radial_array(context, 'PREV')

            elif event.type == 'DOWN_ARROW' or event.type == 'WHEELDOWNMOUSE' and event.ctrl:
                self.switch_radial_array(context, 'NEXT')

            elif event.type == 'WHEELUPMOUSE':
                if self.use_wheelmouse:
                    self.cancel_typing(context)
                    self.count += 1
                    self.modify_all_radial_arrays()
                else:
                    return {'PASS_THROUGH'}

            elif event.type == 'WHEELDOWNMOUSE':
                if self.use_wheelmouse:
                    self.cancel_typing(context)
                    self.count = max(1, self.count - 1)
                    self.modify_all_radial_arrays()
                else:
                    return {'PASS_THROUGH'}

            elif event_type_is_digit(event.type):
                digit = event_type_to_digit(event.type)
                if self.typed_string is None:
                    if digit != 0:
                        self.count_before_typing = self.count
                        self.count = digit
                        self.typed_string = str(digit)
                        self.modify_all_radial_arrays()
                else:
                    self.typed_string += str(digit)
                    self.count = int(self.typed_string)
                    self.modify_all_radial_arrays()
                self.redraw_header(context)

            elif event.type == 'BACK_SPACE':
                if self.typed_string is not None:
                    if self.typed_string:
                        self.typed_string = self.typed_string[:-1]
                        self.count = int(self.typed_string) if self.typed_string else 1
                        self.modify_all_radial_arrays()
                    else:
                        self.count = self.count_before_typing
                        self.typed_string = None
                        self.modify_all_radial_arrays()
                    self.redraw_header(context)

            elif event_match_kmi(self, event, "spin_orientation"):
                if context.mode == 'OBJECT':
                    self.spin_orientation = {
                        'GLOBAL': 'LOCAL',
                        'LOCAL': 'VIEW',
                        'VIEW': 'GLOBAL'
                    }[self.spin_orientation]
                elif context.mode == 'EDIT_MESH':
                    self.spin_orientation = {
                        'GLOBAL': 'LOCAL',
                        'LOCAL': 'VIEW',
                        'VIEW': 'NORMAL',
                        'NORMAL': 'GLOBAL'
                    }[self.spin_orientation]
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "spin_axis"):
                self.spin_axis = {
                    'X': 'Y',
                    'Y': 'Z',
                    'Z': 'X'
                }[self.spin_axis]
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "x_axis"):
                self.spin_axis = 'X'
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "y_axis"):
                self.spin_axis = 'Y'
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "z_axis"):
                self.spin_axis = 'Z'
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "pivot_point"):
                self.set_next_pivot_point(context)
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "count_changing"):
                self.cancel_typing(context)
                self.count_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "radius_offset_changing") and context.object.type == 'MESH':
                self.radius_offset_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "start_angle_changing"):
                self.start_angle_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "end_angle_changing"):
                self.end_angle_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "height_offset_changing"):
                self.height_offset_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "reset_count"):
                self.count = self.count_float = get_property_default(self, "count")
                self.modify_all_radial_arrays()

            elif event_match_kmi(self, event, "reset_radius_offset"):
                self.radius_offset = self.radius_offset_float = get_property_default(self, "radius_offset")
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "reset_start_angle"):
                self.start_angle = self.start_angle_float = get_property_default(self, "start_angle")
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "reset_end_angle"):
                self.end_angle = self.end_angle_float = get_property_default(self, "end_angle")
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "reset_height_offset"):
                self.height_offset = self.height_offset_float = get_property_default(self, "height_offset")
                self.modify_all_radial_arrays()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "add"):
                self.add_radial_arrays(context)

            elif event_match_kmi(self, event, "apply") and context.object.type == 'MESH':
                self.apply_active_radial_arrays()
                self.finish_modal(context)
                return {'FINISHED'}

            elif event_match_kmi(self, event, "remove"):
                self.remove_active_radial_arrays()
                self.finish_modal(context)
                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.restore_all_radial_arrays()
                self.restore_ob_origin(context)
                self.finish_modal(context)
                return {'CANCELLED'}

            elif event.type in {'SPACE', 'LEFTMOUSE'}:
                self.finish_modal(context)
                return {'FINISHED'}

        elif event.value == 'RELEASE':
            if event_match_kmi(self, event, "count_changing", release=True):
                self.cancel_typing(context)
                self.count_changing = False
                context.window.cursor_modal_restore()

            elif event_match_kmi(self, event, "radius_offset_changing", release=True):
                self.radius_offset_changing = False
                context.window.cursor_modal_restore()

            elif event_match_kmi(self, event, "start_angle_changing", release=True):
                self.start_angle_changing = False
                context.window.cursor_modal_restore()

            elif event_match_kmi(self, event, "end_angle_changing", release=True):
                self.end_angle_changing = False
                context.window.cursor_modal_restore()

            elif event_match_kmi(self, event, "height_offset_changing", release=True):
                self.height_offset_changing = False
                context.window.cursor_modal_restore()

        return {'RUNNING_MODAL'}

    def cancel_typing(self, context) -> None:
        if self.typed_string is not None:
            self.typed_string = None
            self.redraw_header(context)

    def set_next_pivot_point(self, context) -> None:
        """Set next pivot point from cycle."""
        is_top = self.master_ob_radial_arrays[-1] == self.master_radial_array

        if context.mode == 'OBJECT':
            if is_top:
                self.pivot_point = {
                    'CURSOR': 'ORIGIN',
                    'ORIGIN': 'CURSOR'
                }[self.pivot_point]
            else:
                self.pivot_point = {
                    'CURSOR': 'ORIGIN',
                    'ORIGIN': 'CENTER_EMPTY',
                    'CENTER_EMPTY': 'CURSOR'
                }[self.pivot_point]
        elif context.mode == 'EDIT_MESH':
            if is_top:
                self.pivot_point = {
                    'CURSOR': 'ORIGIN',
                    'ORIGIN': 'MESH_SELECTION',
                    'MESH_SELECTION': 'CURSOR'
                }[self.pivot_point]
            else:
                self.pivot_point = {
                    'CURSOR': 'ORIGIN',
                    'ORIGIN': 'CENTER_EMPTY',
                    'CENTER_EMPTY': 'MESH_SELECTION',
                    'MESH_SELECTION': 'CURSOR'
                }[self.pivot_point]

    def switch_radial_array(self, context, direction: str) -> None:
        """Search for next/prev radial array and switch to it if it's found."""
        active_idx = self.master_ob_radial_arrays.value.index(self.master_radial_array)

        if direction == 'PREV':
            idx = active_idx - 1
        elif direction == 'NEXT':
            idx = active_idx + 1
        else:
            raise ValueError("direction is invalid")

        if 0 <= idx < len(self.master_ob_radial_arrays.value):
            self.master_radial_array = self.master_ob_radial_arrays[idx]
            if self.master_radial_array not in self.radial_array_initial_attrs:
                self.store_existing_radial_array_attrs(self.master_radial_array)
            self.set_operator_properties_from_master_radial_array()
            self.modify_all_radial_arrays()
            self.build_3d_shader_batches()
            context.region.tag_redraw()

    def restore_all_radial_arrays(self) -> None:
        """Restore radial arrays existed before invoking modal."""
        self.restore_radial_array_attributes()
        self.restore_radial_array_pivot_points_or_refresh()
        self.remove_new_radial_arrays()

    def restore_ob_origin(self, context) -> None:
        if not self.master_ob_radial_arrays.value:
            set_origin(context, self.master_ob, self.master_ob_initial_origin)

    def remove_new_radial_arrays(self) -> None:
        """Remove radial arrays added after invoking modal."""
        for radial_array in self.new_radial_arrays:
            radial_array.remove()

    def restore_radial_array_attributes(self) -> None:
        """Fill radial array properties with initial attributes."""
        for radial_array in self.modified_radial_arrays - set(self.new_radial_arrays):
            name = radial_array.name
            props = radial_array.properties.value
            attrs = self.radial_array_initial_attrs[name]

            props["spin_orientation_matrix_object"] = np.array(attrs["spin_orientation_matrix_object"]).T.ravel()
            spin_orientation_enums = props.bl_rna.properties["spin_orientation"].enum_items
            props["spin_orientation"] = spin_orientation_enums.find(attrs["spin_orientation"])
            spin_axis_enums = props.bl_rna.properties["spin_axis"].enum_items
            props["spin_axis"] = spin_axis_enums.find(attrs["spin_axis"])

            props["count"] = attrs["count"]
            props["radius_offset"] = attrs["radius_offset"]
            props["start_angle"] = attrs["start_angle"]
            props["end_angle"] = attrs["end_angle"]
            props["height_offset"] = attrs["height_offset"]

    def restore_radial_array_pivot_points_or_refresh(self):
        for radial_array in self.modified_radial_arrays:
            if radial_array.name in self.radial_array_last_set_pivot_points:
                co = self.radial_array_initial_attrs[radial_array.name]["pivot_point_co_world"]
                radial_array.set_pivot_point(co)
            else:
                radial_array.refresh()

    def add_radial_arrays(self, context) -> None:
        """Add radial arrays to selected objects."""
        self.pivot_point = 'CURSOR'
        self.build_new_radial_arrays(context)
        self.modify_all_radial_arrays()
        self.build_3d_shader_batches()
        context.region.tag_redraw()

    def apply_active_radial_arrays(self) -> None:
        """Apply active radial arrays."""
        for radial_array in [self.master_radial_array] + self.slave_radial_arrays:
            message = radial_array.apply()
            if message:
                self.report({'INFO'}, message)

    def remove_active_radial_arrays(self) -> None:
        """Remove active radial arrays."""
        for radial_array in [self.master_radial_array] + self.slave_radial_arrays:
            radial_array.remove()

    def finish_modal(self, context) -> None:
        """Remove status, header, sidebar, cursor, shaders."""
        restore_sidebar(context, self.sidebar_initial_state)
        context.area.header_text_set(text=None)
        context.workspace.status_text_set(text=None)
        context.window.cursor_modal_restore()
        context.space_data.draw_handler_remove(self.handler_2d, 'WINDOW')
        context.space_data.draw_handler_remove(self.handler_3d, 'WINDOW')
        context.region.tag_redraw()

    def redraw_header(self, context) -> None:
        """Draw count and spin axis in the header."""
        text = (
            f"count: {self.count}  Spin Axis: {self.spin_axis.title()}"
            if self.typed_string is None
            else f"count: [{self.typed_string}|]  Spin Axis: {self.spin_axis.title()}"
        )
        context.area.header_text_set(text)

    def redraw_status(self, context) -> None:
        """Draw shortcuts in the status."""
        x_axis_key = self.keymap_items["x_axis"].type
        y_axis_key = self.keymap_items["y_axis"].type
        z_axis_key = self.keymap_items["z_axis"].type
        spin_orientation_key = self.keymap_items["spin_orientation"].type
        spin_axis_key = self.keymap_items["spin_axis"].type
        pivot_point_key = self.keymap_items["pivot_point"].type
        apply_key = self.keymap_items["apply"].type
        remove_key = self.keymap_items["remove"].type

        apply_line = f"{apply_key}: Apply | " if self.master_ob.type == 'MESH' else ""

        status_text = (
            f"LMB, ENTER: Confirm | "
            f"RMB, ESC: Cancel | "
            f"{x_axis_key}{y_axis_key}{z_axis_key}: Axis | "
            f"{spin_orientation_key}: Cycle Orientation | "
            f"{spin_axis_key}: Cycle Axis | "
            f"{pivot_point_key}: Cycle Center | "
            f"{apply_line}"
            f"{remove_key}: Delete"
        )
        context.workspace.status_text_set(status_text)

    def draw_2d_shaders(self, context):
        """Draw 2d overlay with shortcuts and attributes in 3d view."""
        ui_scale = context.preferences.view.ui_scale
        dpi = context.preferences.system.dpi
        op_properties = self.properties.bl_rna.properties
        unit = get_unit(context)

        # Colors
        main_color = self.preferences.overlay_colors.main
        val_color = self.preferences.overlay_colors.val
        key_color = self.preferences.overlay_colors.key
        bg_color = self.preferences.overlay_colors.bg

        # Props strings
        count_key = self.keymap_items["count_changing"].type
        count = str(self.count)

        x_axis_key = self.keymap_items["x_axis"].type
        y_axis_key = self.keymap_items["y_axis"].type
        z_axis_key = self.keymap_items["z_axis"].type

        spin_axis_key = self.keymap_items["spin_axis"].type
        spin_axis = op_properties["spin_axis"].enum_items[self.spin_axis].name

        spin_orientation_key = self.keymap_items["spin_orientation"].type
        spin_orientation = op_properties["spin_orientation"].enum_items[self.spin_orientation].name

        radius_offset_key = self.keymap_items["radius_offset_changing"].type
        radius_offset = round(self.radius_offset, 2)

        start_angle_key = self.keymap_items["start_angle_changing"].type
        start_angle = round(degrees(self.start_angle), 2)

        end_angle_key = self.keymap_items["end_angle_changing"].type
        end_angle = round(degrees(self.end_angle), 2)

        height_offset_key = self.keymap_items["height_offset_changing"].type
        height_offset = round(self.height_offset, 2)

        pivot_point_key = self.keymap_items["pivot_point"].type
        pivot_point = op_properties["pivot_point"].enum_items[self.pivot_point].name

        # Props lines
        count_line = [
            ("Count:", main_color),
            (f" ({count_key})", key_color),
            (f" {count}", val_color),
        ]
        spin_axis_line = [
            ("Spin Axis:", main_color),
            (f" ({spin_axis_key}{x_axis_key}{y_axis_key}{z_axis_key})", key_color),
            (f" {spin_axis}", val_color),
        ]
        spin_orientation_line = [
            ("Orientation:", main_color),
            (f" ({spin_orientation_key})", key_color),
            (f" {spin_orientation}", val_color),
        ]
        radius_offset_line = [
            ("Radius Offset:", main_color),
            (f" ({radius_offset_key})", key_color),
            (f" {radius_offset:.2f}{unit}", val_color),
        ]
        start_angle_line = [
            ("Start Angle:", main_color),
            (f" ({start_angle_key})", key_color),
            (f" {start_angle:.2f}°", val_color)
        ]
        end_angle_line = [
            ("End Angle:", main_color),
            (f" ({end_angle_key})", key_color),
            (f" {end_angle:.2f}°", val_color)
        ]
        height_offset_line = [
            ("Height Offset:", main_color),
            (f" ({height_offset_key})", key_color),
            (f" {height_offset:.2f}{unit}", val_color),
        ]
        pivot_point_line = [
            ("Center:", main_color),
            (f" ({pivot_point_key})", key_color),
            (f" {pivot_point}", val_color)
        ]

        # Props lines joined
        props_text_lines = [
            count_line,
            spin_axis_line,
            spin_orientation_line,
            radius_offset_line,
            start_angle_line,
            end_angle_line,
            height_offset_line,
            pivot_point_line,
        ]
        if context.object.type != 'MESH':
            props_text_lines.remove(radius_offset_line)

        # Radial array name lines
        radial_array_name = self.master_radial_array.name
        radial_array_count = len(self.master_ob_radial_arrays.value)

        if radial_array_count > 1:
            current_idx = self.master_ob_radial_arrays.value.index(self.master_radial_array) + 1
            name_text_lines = [[
                (radial_array_name, main_color),
                (f" (\u21c5)", key_color),
                (f" {current_idx}/{radial_array_count}", val_color)
            ]]
        else:
            name_text_lines = [[]]

        # Font
        font_id = 0
        font_size = int(13 * ui_scale)
        align = 'LEFT'

        # Text params
        bg_padding = 14
        line_padding = 5
        separator_height = 4
        offset_x, offset_y = 100, 100  # offset of overlay box from 3d view borders

        # Calculate text dimensions
        props_text_block_width, props_text_block_height = \
            get_text_block_dimensions(props_text_lines, line_padding, font_id, font_size, dpi)
        name_text_block_width, name_text_block_height = \
            get_text_block_dimensions(name_text_lines, line_padding, font_id, font_size, dpi)

        # Calculate text coordinates
        props_text_block_x_right = get_non_overlap_width(context) - offset_x
        props_text_block_x_left = props_text_block_x_right - max(props_text_block_width, name_text_block_width)
        props_text_block_y_bottom = offset_y
        props_text_block_y_top = props_text_block_y_bottom + props_text_block_height

        # Draw
        draw_bg(shader_2d,
                props_text_block_x_right,
                props_text_block_y_bottom,
                props_text_block_x_left,
                props_text_block_y_top,
                bg_padding,
                bg_color)

        draw_text_block(props_text_lines,
                        props_text_block_x_left,
                        props_text_block_y_top,
                        line_padding, align, font_id, font_size, dpi)

        if radial_array_count > 1:
            # Calculate text coordinates
            name_text_block_x_right = props_text_block_x_right
            name_text_block_x_left = props_text_block_x_left
            name_text_block_y_bottom = props_text_block_y_top + separator_height + 2 * bg_padding
            name_text_block_y_top = name_text_block_y_bottom + name_text_block_height

            # Draw
            draw_bg(shader_2d,
                    name_text_block_x_right,
                    name_text_block_y_bottom,
                    name_text_block_x_left,
                    name_text_block_y_top,
                    bg_padding,
                    bg_color)

            draw_text_block(name_text_lines,
                            name_text_block_x_left,
                            name_text_block_y_top,
                            line_padding, align, font_id, font_size, dpi)

    def build_3d_shader_batches(self):
        """Build axis circle and angle lines shader batches."""
        properties = self.master_radial_array.properties.value
        pivot_point_co_world = self.master_radial_array.pivot_point.co_world
        spin_orientation_matrix_world = self.master_ob.matrix_world @ properties.spin_orientation_matrix_object
        spin_orientation_matrix_world.translation = pivot_point_co_world
        spin_vec_world = get_axis_vec(self.spin_axis, spin_orientation_matrix_world)

        spin_vec_spin = spin_vec_world @ spin_orientation_matrix_world
        def_radius = 5

        data_center_co_world = get_data_center_co_world(self.master_ob)
        data_center_vec_spin = spin_orientation_matrix_world.inverted() @ data_center_co_world
        data_center_flat_vec_spin = flatten_vec(data_center_vec_spin, self.spin_axis)

        # Radius vector of 1 unit length
        if data_center_flat_vec_spin.length < 0.001:
            direction_base_vec_spin = flatten_vec(Vector((1, 1, 1)), self.spin_axis).normalized()
        else:
            direction_base_vec_spin = data_center_flat_vec_spin.normalized()

        # Scaled radius vector
        if properties.radius_offset == 0:
            if data_center_flat_vec_spin.length < 0.001:
                radius_vec_spin = direction_base_vec_spin * def_radius
            else:
                radius_vec_spin = data_center_flat_vec_spin / 2
        else:
            displace_offset_vec_spin = direction_base_vec_spin * properties.radius_offset
            radius_vec_spin = (data_center_flat_vec_spin + displace_offset_vec_spin) / 2

        # Build axis circle batch
        axis_circle_radius = radius_vec_spin.length

        # Compose axis circle matrix
        if self.spin_axis == 'X':
            rot_matrix = Matrix([Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))])
            axis_circle_matrix_world = spin_orientation_matrix_world @ rot_matrix.to_4x4()
        elif self.spin_axis == 'Y':
            rot_matrix = Matrix([Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))])
            axis_circle_matrix_world = spin_orientation_matrix_world @ rot_matrix.to_4x4()
        elif self.spin_axis == 'Z':
            axis_circle_matrix_world = spin_orientation_matrix_world
        else:
            raise ValueError("spin_axis is invalid")

        # Get axis circle vertices co in local space
        axis_circle_vertices = build_circle(axis_circle_radius, 40)

        # Convert axis circle vertices co to world space
        axis_circle_matrix_world_np = np.array(axis_circle_matrix_world)
        mat = axis_circle_matrix_world_np[:3, :3].T
        loc = axis_circle_matrix_world_np[:3, 3]
        axis_circle_vertices = axis_circle_vertices @ mat + loc
        axis_circle_vertices = axis_circle_vertices.tolist()

        self.axis_circle_batch = batch_for_shader(shader_3d, 'LINE_LOOP', {"pos": axis_circle_vertices})

        op_properties = self.properties.bl_rna.properties
        if (
            self.start_angle != op_properties["start_angle"].default
            or self.end_angle != op_properties["end_angle"].default
        ):
            # Build angle lines batch
            start_rot_matrix = Matrix.Rotation(self.start_angle, 4, spin_vec_spin)
            start_angle_co_spin = start_rot_matrix @ radius_vec_spin
            start_angle_co_world = spin_orientation_matrix_world @ start_angle_co_spin

            end_rot_matrix = Matrix.Rotation(self.end_angle, 4, spin_vec_spin)
            end_angle_co_spin = end_rot_matrix @ radius_vec_spin
            end_angle_co_world = spin_orientation_matrix_world @ end_angle_co_spin

            vertices = [pivot_point_co_world, start_angle_co_world,
                        pivot_point_co_world, end_angle_co_world]

            self.angle_lines_batch = batch_for_shader(shader_3d, 'LINES', {"pos": vertices})

            # Build angle fill stencil mask batch
            stencil_mask_vertices = axis_circle_vertices
            stencil_mask_vertices.append(axis_circle_vertices[0])
            stencil_mask_vertices.insert(0, pivot_point_co_world)

            self.angle_fill_stencil_mask_batch = batch_for_shader(shader_3d, 'TRI_FAN', {"pos": stencil_mask_vertices})

            # Build angle fill batch
            step_count = int(ceil(abs((self.end_angle - self.start_angle) / radians(90))))
            if step_count == 0:
                step_angle = 0
            else:
                step_angle = (self.end_angle - self.start_angle) / step_count

            fill_vertices = [pivot_point_co_world]
            for i in range(step_count + 1):
                step_rot_matrix = Matrix.Rotation(step_angle * i, 4, spin_vec_spin)
                step_co_spin = step_rot_matrix @ start_angle_co_spin * 2
                step_co_world = spin_orientation_matrix_world @ step_co_spin
                fill_vertices.append(step_co_world)

            self.angle_fill_batch = batch_for_shader(shader_3d, 'TRI_FAN', {"pos": fill_vertices})

    # noinspection PyTypeChecker
    def draw_3d_shaders(self, context):
        """Draw 3d shaders (angle lines and axis circle)."""
        axis_color = get_axis_color(context, self.spin_axis)

        shader_3d.bind()
        shader_3d.uniform_float("color", axis_color)

        glLineWidth(3)
        glEnable(GL_BLEND)
        glEnable(GL_LINE_SMOOTH)

        # Axis circle
        self.axis_circle_batch.draw(shader_3d)

        op_properties = self.properties.bl_rna.properties
        if (
            self.start_angle != op_properties["start_angle"].default
            or self.end_angle != op_properties["end_angle"].default
        ):
            # Angle lines
            self.angle_lines_batch.draw(shader_3d)

            # Angle fill stencil mask
            glClear(GL_STENCIL_BUFFER_BIT)
            glEnable(GL_STENCIL_TEST)
            glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
            glStencilFunc(GL_ALWAYS, 0, 1)
            glStencilOp(GL_KEEP, GL_KEEP, GL_INVERT)
            glStencilMask(1)

            shader_3d.uniform_float("color", (1, 1, 1, 1))
            self.angle_fill_stencil_mask_batch.draw(shader_3d)

            glStencilFunc(GL_EQUAL, 1, 1)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

            # Angle fill
            fill_color = (*list(axis_color)[:-1], 0.2)
            shader_3d.uniform_float("color", fill_color)
            self.angle_fill_batch.draw(shader_3d)

        glDisable(GL_LINE_SMOOTH)
        glDisable(GL_BLEND)
        glLineWidth(1)


classes = (
    RADDUPLICATOR_OT_radial_array_modal,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
