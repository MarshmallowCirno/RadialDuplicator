from math import ceil
from math import degrees
from math import radians
from typing import Optional, Union

import bpy
import gpu
import numpy as np
from bpy.types import Object
from gpu_extras.batch import batch_for_shader
from gpu.types import GPUBatch
from mathutils import Matrix
from mathutils import Vector

from ....package import get_preferences
from ...preferences.preferences import RADDUPLICATOR_preferences
from ...properties import ModalKeyMapItem
from ...radial_objects.radial_duplicates_object import RadialDuplicates
from ...utils.math import build_circle
from ...utils.math import flatten_vec
from ...utils.math import get_axis_vec
from ...utils.modal import event_match_kmi
from ...utils.modal import event_type_is_digit
from ...utils.modal import event_type_to_digit
from ...utils.modal import get_property_default
from ...utils.object_data import data_is_selected
from ...utils.gpu_draw import draw_bg
from ...utils.scene import get_unit
from ...utils.text import draw_text_block
from ...utils.text import get_text_block_dimensions
from ...utils.theme import get_axis_color
from ...utils.view3d import get_non_overlap_width
from ...utils.view3d import hide_sidebar
from ...utils.view3d import restore_sidebar

shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
shader_3d = gpu.shader.from_builtin('UNIFORM_COLOR')


class RADDUPLICATOR_OT_radial_duplicates_modal(bpy.types.Operator):
    bl_description = ("LMB: Edit radial duplicates or add a new one if they don't exist.\n"
                      "+ Shift: Add a new radial duplicates instead of trying to edit existing.\n"
                      "+ Ctrl: Set duplicates center to the 3D cursor instead of object pivot")
    bl_idname = "radial_duplicator.duplicates_modal"
    bl_label = "Radial Duplicates Modal"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    # noinspection PyTypeChecker
    spin_orientation: bpy.props.EnumProperty(
        name="Spin Orientation",
        description="Spin orientation",
        items=[
            ('GLOBAL', "Global", "Align the duplicates axes to world space", 'ORIENTATION_GLOBAL', 0),
            ('LOCAL', "Local", "Align the duplicates axes to selected objects' local space", 'ORIENTATION_LOCAL', 1),
            ('VIEW', "View", "Align the duplicates axes to the window", 'ORIENTATION_VIEW', 2),
        ],
        default='LOCAL',
        options={'SKIP_SAVE'},
    )
    # noinspection PyTypeChecker
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
    # noinspection PyTypeChecker
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
        description="Rotation placement for the last duplicated geometry as a number of degrees "
        "offset from 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(360),
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
    # noinspection PyTypeChecker
    pivot_point: bpy.props.EnumProperty(
        name="Center",
        description="Duplication center",
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
        name="Force New Duplicates",
        description="Add new radial duplicates instead of trying to pick up and edit existing",
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
                and ob.mode == 'OBJECT'
                and ob.library is None
                and not (ob.data is not None and ob.data.library is not None)
        )

    def __init__(self):
        self.master_ob: Optional[Object] = None   # active selected object
        self.slave_obs: Optional[list[Object]] = None  # nonactive selected objects

        self.radial_duplicates: Optional[RadialDuplicates] = None  # class from all radial duplicates of master_ob

        self.preferences: RADDUPLICATOR_preferences = get_preferences()
        self.keymap_items: ModalKeyMapItem = self.preferences.keymaps["modal"].keymap_items

        self.initial_sidebar_state: bool = False
        self.radial_duplicates_initial_attrs: Optional[dict[str:str]] = None
        self.last_set_pivot_point: Optional[str] = None

        self.is_new: bool = False
        self.is_modified: bool = False

        self.typed_string: Optional[str] = None
        self.count_before_typing: int = 0

        self.count_float: float = self.count
        self.end_angle_float: float = self.end_angle
        self.end_scale_float: float = self.end_scale
        self.height_offset_float: float = self.height_offset

        self.count_changing: bool = False
        self.end_angle_changing: bool = False
        self.end_scale_changing: bool = False
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
        # Store initial settings, build radial duplicates,
        self.initial_sidebar_state = context.space_data.show_region_ui
        self.build_radial_duplicates(context)
        if not self.is_new:
            self.set_operator_properties_from_radial_duplicates()
        self.set_operator_properties_from_event_and_context(context, event)
        self.last_mouse_co = (event.mouse_region_x, event.mouse_region_y)

        # Update duplicates
        self.modify_radial_duplicates()

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

    def build_radial_duplicates(self, context) -> None:
        """Build radial duplicates classes from properties and store initial attributes
        or build new radial duplicates classes."""
        if self.new:
            self.build_new_radial_duplicates(context)
        else:
            ob = context.object
            if len(ob.radial_duplicator.duplicates) > 0:
                props = ob.radial_duplicator.duplicates[0]
                self.build_radial_duplicates_from_props(context, props)
            elif ob.parent is not None and len(ob.parent.radial_duplicator.duplicates) > 0:
                props = ob.parent.radial_duplicator.duplicates[0]
                self.build_radial_duplicates_from_props(context, props)
            else:
                self.build_new_radial_duplicates(context)

    def build_radial_duplicates_from_props(self, context, props) -> None:
        """Try building radial duplicates classes from properties, then store their initial attributes."""
        self.radial_duplicates = RadialDuplicates.from_props(context, props)
        self.store_existing_radial_duplicates_attrs()

    def build_new_radial_duplicates(self, context) -> None:
        """Build new radial duplicates class."""
        self.radial_duplicates = RadialDuplicates.new(context, context.object)
        self.is_new = True

    def store_new_radial_duplicates_attrs(self) -> None:
        """Store initial pivot point value of newly created duplicates"""
        if self.radial_duplicates_initial_attrs is None:
            pivot_point_co_world = self.radial_duplicates.pivot_point.co_world
            self.radial_duplicates_initial_attrs = {
                "pivot_point": 'CENTER_EMPTY',
                "pivot_point_co_world": pivot_point_co_world
            }

    def store_existing_radial_duplicates_attrs(self) -> None:
        """Store radial duplicates class initial attributes."""
        props = self.radial_duplicates.properties.value
        pivot_point_co_world = self.radial_duplicates.pivot_point.co_world

        self.radial_duplicates_initial_attrs = {
            "spin_orientation": props.spin_orientation,
            "spin_orientation_matrix_object": props.spin_orientation_matrix_object.copy(),
            "spin_axis": props.spin_axis,
            "duplicates_rotation": props.duplicates_rotation,
            "count": props.count,
            "end_angle": props.end_angle,
            "end_scale": props.end_scale,
            "height_offset": props.height_offset,
            "pivot_point": 'CENTER_EMPTY',
            "pivot_point_co_world": pivot_point_co_world}

    def set_operator_properties_from_radial_duplicates(self) -> None:
        """Set operator properties to existing radial duplicates properties on initialization."""
        props = self.radial_duplicates.properties.value

        self.spin_orientation = props.spin_orientation
        self.spin_axis = props.spin_axis
        self.duplicates_rotation = props.duplicates_rotation
        self.count = self.count_float = props.count
        self.end_angle = self.end_angle_float = props.end_angle
        self.end_scale = props.end_scale
        self.height_offset = self.height_offset_float = props.height_offset
        self.pivot_point = 'CENTER_EMPTY'

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

    def modify_radial_duplicates(self) -> None:
        """Modify radial duplicates with operator properties."""

        # get initial Origin location, not current
        pivot_point = self.get_pivot_point()

        self.radial_duplicates.modify(
            self.spin_orientation,
            self.spin_axis,
            self.duplicates_rotation,
            self.count,
            self.end_angle,
            self.end_scale,
            self.height_offset,
            pivot_point,
        )

        self.is_modified = True

        # store pivot, so it can be retrieved after switching array
        self.last_set_pivot_point = self.pivot_point

    def get_pivot_point(self) -> Union[str, Vector]:
        """Get pivot point value taking into account changes of object origin. Allows toggling between stored initial
        pivot point."""
        initial_attrs = self.radial_duplicates_initial_attrs

        # Pivot point remains the same
        if self.last_set_pivot_point == self.pivot_point:
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
                    self.modify_radial_duplicates()
                    self.redraw_header(context)

            if self.end_angle_changing:
                divisor = 900 if event.shift else 100
                offset = event_mouse_offset_x / divisor
                self.end_angle_float += offset
                if event.ctrl or (context.scene.tool_settings.use_snap
                                  and context.scene.tool_settings.use_snap_rotate
                                  and context.scene.tool_settings.snap_elements == 'INCREMENT'
                                  and not event.ctrl):
                    rounded = radians(round(degrees(self.end_angle_float) / 10) * 10)
                    if self.end_angle != rounded:
                        self.end_angle = rounded
                        self.modify_radial_duplicates()
                        self.build_3d_shader_batches()
                        context.region.tag_redraw()
                else:
                    self.end_angle = self.end_angle_float
                    self.modify_radial_duplicates()
                    self.build_3d_shader_batches()
                    context.region.tag_redraw()

            if self.end_scale_changing:
                divisor = 1800 if event.shift else 200
                offset = event_mouse_offset_x / divisor
                self.end_scale_float = max(0.001, self.end_scale_float + offset)
                if event.ctrl or (context.scene.tool_settings.use_snap
                                  and context.scene.tool_settings.use_snap_rotate
                                  and context.scene.tool_settings.snap_elements == 'INCREMENT'
                                  and not event.ctrl):
                    rounded = round(self.end_scale_float / .1) * .1
                    if self.end_scale != rounded:
                        self.end_scale = rounded
                        self.modify_radial_duplicates()
                else:
                    self.end_scale = self.end_scale_float
                    self.modify_radial_duplicates()

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
                        self.modify_radial_duplicates()
                else:
                    self.height_offset = self.height_offset_float
                    self.modify_radial_duplicates()

            self.last_mouse_co = (event.mouse_region_x, event.mouse_region_y)

        if event.value == 'PRESS':
            if event.type == 'MIDDLEMOUSE':
                return {'PASS_THROUGH'}

            elif event.type == 'WHEELUPMOUSE':
                if self.use_wheelmouse:
                    self.cancel_typing(context)
                    self.count += 1
                    self.modify_radial_duplicates()
                    self.redraw_header(context)
                else:
                    return {'PASS_THROUGH'}

            elif event.type == 'WHEELDOWNMOUSE':
                if self.use_wheelmouse:
                    self.cancel_typing(context)
                    self.count = max(1, self.count - 1)
                    self.modify_radial_duplicates()
                    self.redraw_header(context)
                else:
                    return {'PASS_THROUGH'}

            elif event_type_is_digit(event.type):
                digit = event_type_to_digit(event.type)
                if self.typed_string is None:
                    if digit != 0:
                        self.count_before_typing = self.count
                        self.count = digit
                        self.typed_string = str(digit)
                        self.modify_radial_duplicates()
                else:
                    self.count = int(str(self.count) + str(digit))
                    self.typed_string += (str(digit))
                    self.modify_radial_duplicates()
                self.redraw_header(context)

            elif event.type == 'BACK_SPACE':
                if self.typed_string is not None:
                    if self.typed_string:
                        self.typed_string = self.typed_string[:-1]
                        self.count = int(self.typed_string) if self.typed_string else 1
                        self.modify_radial_duplicates()
                    else:
                        self.count = self.count_before_typing
                        self.typed_string = None
                        self.modify_radial_duplicates()
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
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()
                self.redraw_header(context)

            elif event_match_kmi(self, event, "spin_axis"):
                self.spin_axis = {
                    'X': 'Y',
                    'Y': 'Z',
                    'Z': 'X'
                }[self.spin_axis]
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()
                self.redraw_header(context)

            elif event_match_kmi(self, event, "x_axis"):
                self.spin_axis = 'X'
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()
                self.redraw_header(context)

            elif event_match_kmi(self, event, "y_axis"):
                self.spin_axis = 'Y'
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()
                self.redraw_header(context)

            elif event_match_kmi(self, event, "z_axis"):
                self.spin_axis = 'Z'
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()
                self.redraw_header(context)

            elif event_match_kmi(self, event, "duplicates_rotation"):
                self.set_next_duplicates_rotation()
                self.modify_radial_duplicates()

            elif event_match_kmi(self, event, "pivot_point"):
                self.set_next_pivot_point(context)
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "count_changing"):
                self.cancel_typing(context)
                self.count_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "end_angle_changing"):
                self.end_angle_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "end_scale_changing"):
                self.end_scale_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "height_offset_changing"):
                self.height_offset_changing = True
                context.window.cursor_modal_set('MOVE_X')

            elif event_match_kmi(self, event, "reset_count"):
                self.count = self.count_float = get_property_default(self, "count")
                self.modify_radial_duplicates()
                self.redraw_header(context)

            elif event_match_kmi(self, event, "reset_end_angle"):
                self.end_angle = self.end_angle_float = get_property_default(self, "end_angle")
                self.modify_radial_duplicates()
                self.build_3d_shader_batches()
                context.region.tag_redraw()

            elif event_match_kmi(self, event, "reset_end_scale"):
                self.end_scale = self.end_scale_float = get_property_default(self, "end_scale")
                self.modify_radial_duplicates()

            elif event_match_kmi(self, event, "reset_height_offset"):
                self.height_offset = self.height_offset_float = get_property_default(self, "height_offset")
                self.modify_radial_duplicates()

            elif event_match_kmi(self, event, "remove"):
                self.remove_radial_duplicates()
                self.finish_modal(context)
                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.restore_radial_duplicates()
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

            elif event_match_kmi(self, event, "end_angle_changing", release=True):
                self.end_angle_changing = False
                context.window.cursor_modal_restore()

            elif event_match_kmi(self, event, "end_scale_changing", release=True):
                self.end_scale_changing = False
                context.window.cursor_modal_restore()

            elif event_match_kmi(self, event, "height_offset_changing", release=True):
                self.height_offset_changing = False
                context.window.cursor_modal_restore()

        return {'RUNNING_MODAL'}

    def cancel_typing(self, context) -> None:
        if self.typed_string is not None:
            self.typed_string = None
            self.redraw_header(context)

    def set_next_duplicates_rotation(self) -> None:
        """Set next duplicates rotation from cycle."""
        self.duplicates_rotation = {
            'FOLLOW': 'KEEP',
            'KEEP': 'RANDOM',
            'RANDOM': 'FOLLOW'
        }[self.duplicates_rotation]

    def set_next_pivot_point(self, context) -> None:
        """Set next pivot point from cycle."""
        if context.mode == 'OBJECT':
            if self.is_new:
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
            if self.is_new:
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

    def restore_radial_duplicates(self) -> None:
        """Restore radial duplicates existed before invoking modal."""
        if self.is_new:
            self.remove_radial_duplicates()
        else:
            self.restore_radial_duplicates_attributes()

            if self.last_set_pivot_point is not None:
                co = self.radial_duplicates_initial_attrs["pivot_point_co_world"]
                self.radial_duplicates.set_pivot_point(co)
            else:
                self.radial_duplicates.refresh()

    def restore_radial_duplicates_attributes(self) -> None:
        """Fill radial duplicates properties with initial attributes."""
        props = self.radial_duplicates.properties.value
        attrs = self.radial_duplicates_initial_attrs

        props["spin_orientation_matrix_object"] = np.array(attrs["spin_orientation_matrix_object"]).T.ravel()
        spin_orientation_enums = props.bl_rna.properties["spin_orientation"].enum_items
        props["spin_orientation"] = spin_orientation_enums.find(attrs["spin_orientation"])
        spin_axis_enums = props.bl_rna.properties["spin_axis"].enum_items
        props["spin_axis"] = spin_axis_enums.find(attrs["spin_axis"])
        duplicates_rotation_enums = props.bl_rna.properties["duplicates_rotation"].enum_items
        props["duplicates_rotation"] = duplicates_rotation_enums.find(attrs["duplicates_rotation"])

        props["count"] = attrs["count"]
        props["end_angle"] = attrs["end_angle"]
        props["end_scale"] = attrs["end_scale"]
        props["height_offset"] = attrs["height_offset"]

    def remove_radial_duplicates(self) -> None:
        """Remove active radial duplicates."""
        self.radial_duplicates.remove()

    def finish_modal(self, context) -> None:
        """Remove status, header, sidebar, cursor, shaders."""
        restore_sidebar(context, self.initial_sidebar_state)
        context.area.header_text_set(text=None)
        context.workspace.status_text_set(text=None)
        context.window.cursor_modal_restore()
        context.space_data.draw_handler_remove(self.handler_2d, 'WINDOW')
        context.space_data.draw_handler_remove(self.handler_3d, 'WINDOW')
        context.region.tag_redraw()

    def redraw_header(self, context) -> None:
        """Draw count and spin axis in the header."""
        text = (
            f"count: {self.count}  Spin Axis: {self.spin_orientation.title()} {self.spin_axis.title()}"
            if self.typed_string is None
            else f"count: [{self.typed_string}|]  Spin Axis: {self.spin_orientation.title()} {self.spin_axis.title()}"
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
        remove_key = self.keymap_items["remove"].type

        status_text = (
            f"LMB, ENTER: Confirm | "
            f"RMB, ESC: Cancel | "
            f"{x_axis_key}{y_axis_key}{z_axis_key}: Axis | "
            f"{spin_orientation_key}: Cycle Orientation | "
            f"{spin_axis_key}: Cycle Axis | "
            f"{pivot_point_key}: Cycle Center | "
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

        duplicates_rotation_key = self.keymap_items["duplicates_rotation"].type
        duplicates_rotation = op_properties["duplicates_rotation"].enum_items[self.duplicates_rotation].name

        end_angle_key = self.keymap_items["end_angle_changing"].type
        end_angle = round(degrees(self.end_angle), 2)

        end_scale_key = self.keymap_items["end_scale_changing"].type
        end_scale = self.end_scale

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
        duplicates_rotation_line = [
            ("Rotation:", main_color),
            (f" ({duplicates_rotation_key})", key_color),
            (f" {duplicates_rotation}", val_color),
        ]
        end_angle_line = [
            ("End Angle:", main_color),
            (f" ({end_angle_key})", key_color),
            (f" {end_angle:.2f}°", val_color)
        ]
        end_scale_line = [
            ("End Scale:", main_color),
            (f" ({end_scale_key})", key_color),
            (f" {end_scale:.3f}", val_color)
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
            duplicates_rotation_line,
            end_angle_line,
            end_scale_line,
            height_offset_line,
            pivot_point_line,
        ]

        # Font
        font_id = 0
        font_size = int(13 * ui_scale)
        align = 'LEFT'

        # Text params
        bg_padding = 14
        line_padding = 5
        offset_x, offset_y = 100, 100  # offset of overlay box from 3d view borders

        # Calculate text dimensions
        props_text_block_width, props_text_block_height = \
            get_text_block_dimensions(props_text_lines, line_padding, font_id, font_size, dpi)

        # Calculate text coordinates
        props_text_block_x_right = get_non_overlap_width(context) - offset_x
        props_text_block_x_left = props_text_block_x_right - props_text_block_width
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

    def build_3d_shader_batches(self):
        """Build axis circle and angle lines shader batches."""
        properties = self.radial_duplicates.properties.value
        pivot_point_co_world = self.radial_duplicates.pivot_point.co_world
        center_empty = self.radial_duplicates.center_empty.value
        starting_ob = self.radial_duplicates.starting_object.value
        spin_orientation_matrix_world = center_empty.matrix_world @ properties.spin_orientation_matrix_object
        spin_orientation_matrix_world.translation = pivot_point_co_world
        spin_vec_world = get_axis_vec(self.spin_axis, spin_orientation_matrix_world)

        spin_vec_spin = spin_vec_world @ spin_orientation_matrix_world
        def_radius = 5

        ob_center_co_world = starting_ob.matrix_world.to_translation()
        ob_center_vec_spin = spin_orientation_matrix_world.inverted() @ ob_center_co_world
        ob_center_flat_vec_spin = flatten_vec(ob_center_vec_spin, self.spin_axis)

        # Radius vector of 1 unit length
        if ob_center_flat_vec_spin.length < 0.001:
            direction_base_vec_spin = flatten_vec(Vector((1, 1, 1)), self.spin_axis).normalized()
        else:
            direction_base_vec_spin = ob_center_flat_vec_spin.normalized()

        # Scaled radius vector
        if ob_center_flat_vec_spin.length < 0.001:
            radius_vec_spin = direction_base_vec_spin * def_radius
        else:
            radius_vec_spin = ob_center_flat_vec_spin / 2

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
        if self.end_angle != op_properties["end_angle"].default:
            start_angle = 0
            # Build angle lines batch
            start_rot_matrix = Matrix.Rotation(start_angle, 4, spin_vec_spin)
            start_angle_co_spin = start_rot_matrix @ radius_vec_spin
            start_angle_co_world = spin_orientation_matrix_world @ start_angle_co_spin

            end_rot_matrix = Matrix.Rotation(self.end_angle, 4, spin_vec_spin)
            end_angle_co_spin = end_rot_matrix @ radius_vec_spin
            end_angle_co_world = spin_orientation_matrix_world @ end_angle_co_spin

            vertices = [pivot_point_co_world, start_angle_co_world,
                        pivot_point_co_world, end_angle_co_world]

            self.angle_lines_batch = batch_for_shader(shader_3d, 'LINES', {"pos": vertices})

            # Build angle fill batch
            step_count = int(ceil(abs((self.end_angle - start_angle) / radians(5))))
            if step_count == 0:
                step_angle = 0
            else:
                step_angle = (self.end_angle - start_angle) / step_count

            fill_vertices = [pivot_point_co_world]
            for i in range(step_count + 1):
                step_rot_matrix = Matrix.Rotation(step_angle * i, 4, spin_vec_spin)
                step_co_spin = step_rot_matrix @ start_angle_co_spin
                step_co_world = spin_orientation_matrix_world @ step_co_spin
                fill_vertices.append(step_co_world)

            self.angle_fill_batch = batch_for_shader(shader_3d, 'TRI_FAN', {"pos": fill_vertices})

    def draw_3d_shaders(self, context):
        """Draw 3d shaders (angle lines and axis circle)."""
        axis_color = get_axis_color(context, self.spin_axis)

        shader_3d.bind()
        shader_3d.uniform_float("color", axis_color)

        gpu.state.line_width_set(3)
        gpu.state.blend_set('ALPHA')

        # Axis circle
        self.axis_circle_batch.draw(shader_3d)

        op_properties = self.properties.bl_rna.properties
        if self.end_angle != op_properties["end_angle"].default:
            # Angle lines
            self.angle_lines_batch.draw(shader_3d)

            # Angle fill
            fill_color = (*list(axis_color)[:-1], 0.2)
            shader_3d.uniform_float("color", fill_color)
            self.angle_fill_batch.draw(shader_3d)

        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1)


classes = (
    RADDUPLICATOR_OT_radial_duplicates_modal,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
