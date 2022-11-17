from math import radians

import bpy
from bpy.types import Object

from .radial_objects.radial_array_object import ObjectRadialArrays
from .radial_objects.radial_duplicates_object import RadialDuplicates
from .radial_objects.radial_screw_object import ObjectRadialScrews


modal_key_items = []
modal_key_names = {}
for i in bpy.types.Event.bl_rna.properties["type"].enum_items.values():
    modal_key_items.append((i.identifier, i.name, "", i.value))
    modal_key_names[i.identifier] = i.description or i.name


def update_array(self, context):
    ob = self.id_data
    radial_arrays = ObjectRadialArrays(context, ob)
    radial_array = radial_arrays[self.name]
    radial_array.modify(
        self.spin_orientation,
        self.spin_axis,
        self.count,
        self.radius_offset,
        self.start_angle,
        self.end_angle,
        self.height_offset
    )


def update_array_show_viewport(self, context):
    ob = self.id_data
    radial_arrays = ObjectRadialArrays(context, ob)
    radial_array = radial_arrays[self.name]
    array_modifier = radial_array.array_modifier.value
    nodes_modifier = radial_array.nodes_modifier.value

    if array_modifier is not None:
        array_modifier.show_viewport = self.show_viewport
    if nodes_modifier is not None:
        nodes_modifier.show_viewport = self.show_viewport


class RadialArrayPropsGroup(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
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
        update=update_array,
    )
    spin_orientation_matrix_object: bpy.props.FloatVectorProperty(
        name="Spin Orientation Matrix",
        description="Spin orientation matrix in object space",
        subtype='MATRIX',
        size=(4, 4),
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
        update=update_array,
    )
    center_empty: bpy.props.PointerProperty(
        name="Center Empty",
        description="Empty that act as a pivot point",
        type=bpy.types.Object,
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="Total number of duplicates to make",
        min=1,
        default=6,
        update=update_array,
    )
    radius_offset: bpy.props.FloatProperty(
        name="Radius Offset",
        description="Moves each duplicate a user-defined distance from the pivot point",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
        update=update_array,
    )
    start_angle: bpy.props.FloatProperty(
        name="Start Angle",
        description="Rotation placement for the first duplicated geometry as a number of degrees "
        "offset from the initial 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(0),
        update=update_array,
    )
    end_angle: bpy.props.FloatProperty(
        name="End Angle",
        description="Rotation placement for the last duplicated geometry as a number of degrees "
        "offset from 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(360),
        update=update_array,
    )
    height_offset: bpy.props.FloatProperty(
        name="Height Offset",
        description="Moves each successive duplicate a user-defined distance from the previous duplicate "
                    "along the defined Axis. This is useful when combined with an End Angle "
                    "greater than 360 degrees to create a spiral",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
        update=update_array,
    )
    show_viewport: bpy.props.BoolProperty(
        name="Display",
        description="Display in viewport",
        default=True,
        update=update_array_show_viewport,
    )


def update_screw(self, context):
    ob = self.id_data
    radial_screws = ObjectRadialScrews(context, ob)
    radial_screw = radial_screws[self.name]
    radial_screw.modify(
        self.spin_orientation,
        self.spin_axis,
        self.steps,
        self.radius_offset,
        self.start_angle,
        self.end_angle,
        self.screw_offset,
        self.iterations
    )


def update_screw_show_viewport(self, context):
    ob = self.id_data
    radial_screws = ObjectRadialScrews(context, ob)
    radial_screw = radial_screws[self.name]
    screw_modifier = radial_screw.screw_modifier.value
    nodes_modifier = radial_screw.nodes_modifier.value

    if screw_modifier is not None:
        screw_modifier.show_viewport = self.show_viewport
    if nodes_modifier is not None:
        nodes_modifier.show_viewport = self.show_viewport


class RadialScrewPropsGroup(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    # noinspection PyTypeChecker
    spin_orientation: bpy.props.EnumProperty(
        name="Spin Orientation",
        description="Spin orientation",
        items=[
            ('GLOBAL', "Global", "Align the screw axes to world space", 'ORIENTATION_GLOBAL', 0),
            ('LOCAL', "Local", "Align the screw axes to selected objects' local space", 'ORIENTATION_LOCAL', 1),
            ('VIEW', "View", "Align the screw to the window", 'ORIENTATION_VIEW', 2),
            ('NORMAL', "Normal", "Align the screw axes to average normal of selected mesh elements",
             'ORIENTATION_NORMAL', 3),
        ],
        default='LOCAL',
        update=update_screw,
    )
    spin_orientation_matrix_object: bpy.props.FloatVectorProperty(
        name="Spin Orientation Matrix",
        description="Spin orientation matrix in object space",
        subtype='MATRIX',
        size=(4, 4),
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
        update=update_screw,
    )
    axis_empty: bpy.props.PointerProperty(
        name="Axis Empty",
        description="Empty that act as a pivot point",
        type=bpy.types.Object,
    )
    steps: bpy.props.IntProperty(
        name="Steps",
        description="Number of steps in the revolution",
        min=1,
        default=16,
        update=update_screw,
    )
    radius_offset: bpy.props.FloatProperty(
        name="Radius Offset",
        description="Moves each step a user-defined distance from the pivot point",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
        update=update_screw,
    )
    start_angle: bpy.props.FloatProperty(
        name="Start Angle",
        description="Rotation placement for the first step geometry as a number of degrees "
        "offset from the initial 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(0),
        update=update_screw,
    )
    end_angle: bpy.props.FloatProperty(
        name="End Angle",
        description="Rotation placement for the last step geometry as a number of degrees "
        "offset from 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(360),
        update=update_screw,
    )
    screw_offset: bpy.props.FloatProperty(
        name="Screw Offset",
        description="Offset the revolution along its axis",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
        update=update_screw,
    )
    iterations: bpy.props.IntProperty(
        name="Count",
        description="Number of times to apply the screw operation",
        min=1,
        default=1,
        update=update_screw,
    )
    show_viewport: bpy.props.BoolProperty(
        name="Display",
        description="Display in viewport",
        default=True,
        update=update_screw_show_viewport,
    )


def update_duplicates(self, context):
    radial_duplicate = RadialDuplicates.from_props(context, self)
    radial_duplicate.modify(
        self.spin_orientation,
        self.spin_axis,
        self.count,
        self.end_angle,
        self.height_offset
    )


def update_duplicates_show_viewport(self, context):
    radial_duplicate = RadialDuplicates.from_props(context, self)
    dupli_obs = radial_duplicate.duplicated_objects.value

    for ob in dupli_obs:
        ob.hide_viewport = not self.show_viewport


class RadialDuplicatesPropsGroup(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    # noinspection PyTypeChecker
    spin_orientation: bpy.props.EnumProperty(
        name="Spin Orientation",
        description="Spin orientation",
        items=[
            ('GLOBAL', "Global", "Align the duplication axes to world space", 'ORIENTATION_GLOBAL', 0),
            ('LOCAL', "Local", "Align the duplication axes to selected objects' local space", 'ORIENTATION_LOCAL', 1),
            ('VIEW', "View", "Align the duplication axes to the window", 'ORIENTATION_VIEW', 2),
        ],
        default='LOCAL',
        update=update_duplicates,
    )
    spin_orientation_matrix_object: bpy.props.FloatVectorProperty(
        name="Spin Orientation Matrix",
        description="Spin orientation matrix in object space",
        subtype='MATRIX',
        size=(4, 4),
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
        update=update_duplicates,
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="Total number of duplicates to make",
        min=1,
        default=6,
        update=update_duplicates,
    )
    end_angle: bpy.props.FloatProperty(
        name="End Angle",
        description="Rotation placement for the last duplicated geometry as a number of degrees "
        "offset from 0 degrees",
        subtype='ANGLE',
        unit='ROTATION',
        step=100,
        default=radians(360),
        update=update_duplicates,
    )
    height_offset: bpy.props.FloatProperty(
        name="Height Offset",
        description="Moves each successive duplicate a user-defined distance from the previous duplicate "
                    "along the defined Axis. This is useful when combined with an End Angle "
                    "greater than 360 degrees to create a spiral",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
        update=update_duplicates,
    )
    starting_object: bpy.props.PointerProperty(
        name="Starting Object",
        description="Original object",
        type=Object,
        update=update_duplicates,
    )
    show_viewport: bpy.props.BoolProperty(
        name="Display",
        description="Display in viewport",
        default=True,
        update=update_duplicates_show_viewport,
    )


class RadialCollections(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    arrays: bpy.props.CollectionProperty(type=RadialArrayPropsGroup, name="Radial Arrays")
    duplicates: bpy.props.CollectionProperty(type=RadialDuplicatesPropsGroup, name="Radial Duplicates")
    screws: bpy.props.CollectionProperty(type=RadialScrewPropsGroup, name="Screws")


def get_color_from_theme(color_name):
    theme = bpy.context.preferences.themes[0]
    # theme.properties.space.back
    # theme.user_interface.wcol_num.inner
    return {
        "main": (1.0, 1.0, 1.0, 1.0),
        "key": (0.5, 0.5, 0.5, 1.0),
        "val": (*theme.view_3d.object_active, 1),
        "bg": (*theme.user_interface.wcol_box.inner[:-1], 0.6),
    }[color_name]


def fill_colors_from_theme(self, _):
    self.main = get_color_from_theme("main")
    self.key = get_color_from_theme("key")
    self.val = get_color_from_theme("val")
    self.bg = get_color_from_theme("bg")


def get_main_color(self):
    return get_color_from_theme("main") if self.use_from_theme else self["main"]


def get_key_color(self):
    return get_color_from_theme("key") if self.use_from_theme else self["key"]


def get_val_color(self):
    return get_color_from_theme("val") if self.use_from_theme else self["val"]


def get_bg_color(self):
    return get_color_from_theme("bg") if self.use_from_theme else self["bg"]


def set_main_color(self, value):
    self["main"] = value


def set_key_color(self, value):
    self["key"] = value


def set_val_color(self, value):
    self["val"] = value


def set_bg_color(self, value):
    self["bg"] = value


class OverlayColors(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    use_from_theme: bpy.props.BoolProperty(
        name="Use Colors from Theme",
        description="Use overlay colors from the current blender theme colors",
        default=True,
        update=fill_colors_from_theme,
    )
    main: bpy.props.FloatVectorProperty(
        name="Font Color",
        description="Overlay main text color",
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        size=4,
        get=get_main_color,
        set=set_main_color,
    )
    key: bpy.props.FloatVectorProperty(
        name="Key Color",
        description="Overlay hotkeys text color",
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        size=4,
        get=get_key_color,
        set=set_key_color,
    )
    val: bpy.props.FloatVectorProperty(
        name="Value Color",
        description="Overlay values text color",
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        size=4,
        get=get_val_color,
        set=set_val_color,
    )
    bg: bpy.props.FloatVectorProperty(
        name="Background Color",
        description="Overlay background color",
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        size=4,
        get=get_bg_color,
        set=set_bg_color,
    )


class ModalKeyMapItem(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    label: bpy.props.StringProperty()
    tag: bpy.props.StringProperty()
    type: bpy.props.EnumProperty(
        name="Type",
        description="Type of event",
        items=modal_key_items,
    )

    alt: bpy.props.BoolProperty(description="Alt key pressed", name="Alt", default=False)
    ctrl: bpy.props.BoolProperty(description="Control key pressed", name="Ctrl", default=False)
    shift: bpy.props.BoolProperty(description="Shift key pressed", name="Shift", default=False)


class AddonKeyMap(bpy.types.PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    keymap_items: bpy.props.CollectionProperty(type=ModalKeyMapItem)


classes = (
    RadialArrayPropsGroup,
    RadialDuplicatesPropsGroup,
    RadialScrewPropsGroup,
    RadialCollections,
    OverlayColors,
    ModalKeyMapItem,
    AddonKeyMap,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Object.radial_duplicator = bpy.props.PointerProperty(
        type=RadialCollections, name="RadialDuplicator"
    )


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
