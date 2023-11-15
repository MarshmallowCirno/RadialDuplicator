import re
from typing import Optional

import bpy
import numpy as np
from bpy.types import ArrayModifier
from bpy.types import Context
from bpy.types import NodesModifier
from bpy.types import NodeTree
from bpy.types import Object
from mathutils import Matrix
from mathutils import Vector

from .. import properties
from ...package import get_preferences
from ..utils.object import copy_collections
from ..utils.object import get_modifier_index
from ..utils.object import move_to_collection
from ..utils.object import copy_local_view_state


def find_array_mod(ob: Object, name: str) -> Optional[ArrayModifier]:
    """Find array modifier by name."""
    array_mod = ob.modifiers.get(name)
    return array_mod


def find_nodes_mod(ob: Object, name: str) -> Optional[NodesModifier]:
    """Find nodes modifier by name."""
    match = re.search(r"\.[0-9]+$", name)
    index = "" if match is None else match.group(0)
    base_name = name.removesuffix(index)
    nodes_mods = filter(lambda mod: mod.type == 'NODES' and mod.name == f"{base_name}Offset{index}", ob.modifiers)
    nodes_mod = next(nodes_mods, None)
    return nodes_mod


def find_offset_empty(array_mod: ArrayModifier) -> Optional[Object]:
    """Find offset empty of array modifier."""
    offset_empty = array_mod.offset_object
    return offset_empty


def find_props(ob: Object, name: str) -> Optional["properties.RadialArrayPropsGroup"]:
    """Find object radial array property group by name."""
    props = ob.radial_duplicator.arrays.get(name)
    return props


def find_center_empty(props: "properties.RadialArrayPropsGroup") -> Optional[Object]:
    """Find center empty from radial array properties."""
    center_empty = props.center_empty
    return center_empty


def new_array_mod(context: Context, ob: Object) -> ArrayModifier:
    """Add a new array modifier to object and sort it."""
    # noinspection PyTypeChecker
    array_mod: ArrayModifier = ob.modifiers.new(name="RadialArray", type='ARRAY')
    array_mod.use_object_offset = True
    array_mod.use_relative_offset = False
    array_mod.use_merge_vertices = True
    array_mod.use_merge_vertices_cap = True
    array_mod.show_expanded = False
    array_mod.merge_threshold = 0.0001 / context.scene.unit_settings.scale_length  # .1mm
    sort_array_mod(ob, array_mod)
    return array_mod


def new_nodes_mod(
    ob: Object, array_mod: ArrayModifier, props: "properties.RadialArrayPropsGroup", name: str
) -> NodesModifier:
    """Add new nodes modifier to object and sort it."""
    match = re.search(r"\.[0-9]+$", name)
    index = "" if match is None else match.group(0)
    base_name = array_mod.name.removesuffix(index)
    # noinspection PyTypeChecker
    nodes_mod: NodesModifier = ob.modifiers.new(name=f"{base_name}Offset{index}", type='NODES')
    nodes_mod.node_group = new_node_group()
    nodes_mod.show_expanded = False
    nodes_mod.show_viewport = props.show_viewport
    sort_nodes_mod(ob, nodes_mod, array_mod)
    return nodes_mod


def new_node_group() -> NodeTree:
    """Add a new node group and return it."""
    node_group = bpy.data.node_groups.new(name="RadialArrayNodes", type='GeometryNodeTree')

    group_input = node_group.nodes.new(type='NodeGroupInput')
    group_output = node_group.nodes.new(type='NodeGroupOutput')

    node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type="NodeSocketGeometry")
    node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type="NodeSocketGeometry")

    radius_offset = node_group.nodes.new(type='GeometryNodeTransform')
    radius_offset.name = "RadiusOffset"

    centering_pivot = node_group.nodes.new(type='GeometryNodeTransform')
    centering_pivot.name = "ObjectPivotToRadialArrayCenter"

    start_rotation = node_group.nodes.new(type='GeometryNodeTransform')
    start_rotation.name = "StartRotation"

    restore_pivot = node_group.nodes.new(type='GeometryNodeTransform')
    restore_pivot.name = "RestoreObjectPivot"

    radius_offset.location.x = 200
    centering_pivot.location.x = 400
    start_rotation.location.x = 600
    restore_pivot.location.x = 800
    group_output.location.x = 1000

    node_group.links.new(group_input.outputs[0], radius_offset.inputs[0])
    node_group.links.new(radius_offset.outputs[0], centering_pivot.inputs[0])
    node_group.links.new(centering_pivot.outputs[0], start_rotation.inputs[0])
    node_group.links.new(start_rotation.outputs[0], restore_pivot.inputs[0])
    node_group.links.new(restore_pivot.outputs[0], group_output.inputs[0])
    return node_group


def new_props(ob: Object, array_mod: ArrayModifier, name: str) -> "properties.RadialArrayPropsGroup":
    """Add a new radial array property group and return it."""
    props = ob.radial_duplicator.arrays.add()
    props["name"] = name
    mx = ob.matrix_world.inverted()
    props["spin_orientation_matrix_object"] = np.array(mx).ravel()
    props["show_viewport"] = array_mod.show_viewport
    return props


def new_center_empty(context: Context, ob: Object, props: "properties.RadialArrayPropsGroup") -> Object:
    """Add a new center empty to property group and return it."""
    center_empty = bpy.data.objects.new(name="RadialArrayEmpty", object_data=None)
    center_empty.empty_display_type = 'SPHERE'
    center_empty.empty_display_size = max(ob.dimensions) / 2
    if get_preferences().move_empties_to_collection:
        empties_collection = get_preferences().empties_collection
        move_to_collection(empties_collection, center_empty)
    else:
        copy_collections(ob, center_empty)
        copy_local_view_state(context, center_empty)
    if ob.type != 'CURVE':
        # center_empty.hide_viewport = True
        center_empty.parent = ob
        # matrix_world of the newly created object updates after updating depsgraph
        context.evaluated_depsgraph_get().update()
        center_empty.matrix_parent_inverse.identity()
        center_empty.matrix_basis.identity()
    else:
        # modifier will lag if its empty set to ob child
        center_empty.matrix_world = ob.matrix_world
    props["center_empty"] = center_empty
    return center_empty


def new_offset_empty(context: Context, ob: Object, array_mod: ArrayModifier) -> Object:
    """Add a new offset empty to array modifier and return it."""
    offset_empty = bpy.data.objects.new(name="RadialArrayEmpty", object_data=None)
    offset_empty.empty_display_type = 'SPHERE'
    offset_empty.empty_display_size = max(ob.dimensions) / 2
    if get_preferences().move_empties_to_collection:
        empties_collection = get_preferences().empties_collection
        move_to_collection(empties_collection, offset_empty)
    else:
        copy_collections(ob, offset_empty)
        copy_local_view_state(context, offset_empty)
    if ob.type != 'CURVE':
        # offset_empty.hide_viewport = True
        offset_empty.parent = ob
        # matrix_world of the newly created object updates after updating depsgraph
        context.evaluated_depsgraph_get().update()
        offset_empty.matrix_parent_inverse.identity()
        offset_empty.matrix_basis.identity()
    else:
        # modifier will lag if its empty set to ob child
        offset_empty.matrix_world = ob.matrix_world
    array_mod.offset_object = offset_empty
    return offset_empty


def sort_array_mod(ob: Object, array_mod: ArrayModifier) -> None:
    """Place array modifier after mirror, array or on the top."""
    array_mod_idx = ob.modifiers.find(array_mod.name)
    other_mods = [mod for mod in ob.modifiers if mod != array_mod]

    another_array_mods = filter(lambda mod: mod.type == 'ARRAY', reversed(other_mods))
    another_array_mod = next(another_array_mods, None)
    if another_array_mod is not None:
        another_array_mod_idx = ob.modifiers.find(another_array_mod.name)
        new_array_mod_idx = get_modifier_index(current_index=array_mod_idx,
                                               reference_index=another_array_mod_idx,
                                               position='AFTER')
    else:
        screw_mods = filter(lambda mod: mod.type == 'SCREW', reversed(other_mods))
        screw_mod = next(screw_mods, None)
        if screw_mod is not None:
            screw_mod_idx = ob.modifiers.find(screw_mod.name)
            new_array_mod_idx = get_modifier_index(current_index=array_mod_idx,
                                                   reference_index=screw_mod_idx,
                                                   position='AFTER')
        else:
            mirror_mods = filter(lambda mod: mod.type == 'MIRROR' and mod.mirror_object is None, reversed(other_mods))
            mirror_mod = next(mirror_mods, None)
            if mirror_mod is not None:
                mirror_mod_idx = ob.modifiers.find(mirror_mod.name)
                new_array_mod_idx = get_modifier_index(current_index=array_mod_idx,
                                                       reference_index=mirror_mod_idx,
                                                       position='AFTER')
            else:
                new_array_mod_idx = 0

    ob.modifiers.move(from_index=array_mod_idx, to_index=new_array_mod_idx)


def sort_nodes_mod(ob: Object, nodes_mod: NodesModifier, array_mod: ArrayModifier) -> None:
    """Place nodes modifier before array modifier."""
    nodes_mod_idx = ob.modifiers.find(nodes_mod.name)
    array_mod_idx = ob.modifiers.find(array_mod.name)
    new_nodes_mod_idx = get_modifier_index(current_index=nodes_mod_idx,
                                           reference_index=array_mod_idx,
                                           position='BEFORE')
    ob.modifiers.move(from_index=nodes_mod_idx, to_index=new_nodes_mod_idx)


def restore_props(
    ob: Object, array_mod: ArrayModifier, offset_empty: Object, props: "properties.RadialArrayPropsGroup"
) -> None:
    """Calculate and set correct values to properties in property group.

    Calculate spin axis from offset empty rotation, get count from array modifier
    and replace them in radial array properties. Assume that array was rotated in local orientation.
    """
    if offset_empty is not None:
        spin_axis_enums = props.bl_rna.properties["spin_axis"].enum_items
        props["spin_axis"] = spin_axis_enums.find(get_spin_axis(ob, offset_empty))
    props["count"] = array_mod.count


def get_spin_axis(ob: Object, offset_empty: Object) -> str:
    """Calculate axis used for rotating offset_empty and return it.

    :return: Axis in ['X', 'Y', 'Z']

    Calculations are approximate and made by comparing the world space
    rotation of the offset_empty relative to the object.
    """
    ob_rot = ob.matrix_world.to_quaternion()
    offset_empty_rot = offset_empty.matrix_world.to_quaternion()
    vec = ob_rot.rotation_difference(offset_empty_rot).to_axis_angle()[0]
    max_axis = [vec[0], vec[1], vec[2]].index(max([vec[0], vec[1], vec[2]]))
    spin_axis = {0: "X", 1: "Y", 2: "Z"}[max_axis]
    return spin_axis


def get_pivot_co(ob: Object, offset_empty: Object) -> Vector:
    """Calculate coordinate of pivot point of offset empty rotation and return it.

    Calculations are approximate and made by comparing the world space
    rotation of the offset_empty relative to the object.
    Return one of the points lying on the spin axis.
    """
    transform_mx = offset_empty.matrix_world @ ob.matrix_world.inverted()
    a = Matrix.Identity(3) - transform_mx.to_3x3().normalized()
    b = transform_mx.to_translation()
    pivot_co = Vector(np.linalg.lstsq(a, b, rcond=None)[0])
    return pivot_co


def remove_junk_props(ob: Object) -> None:
    """Remove radial array properties with name that have no matching array modifier."""
    for props in reversed(ob.radial_duplicator.arrays):
        mod = ob.modifiers.get(props.name)
        if mod is None or mod.type != 'ARRAY' or "Radial" not in mod.name:
            index = ob.radial_duplicator.arrays.find(props.name)
            ob.radial_duplicator.arrays.remove(index)


def fix_nodes_mod(
    ob: Object, array_mod: ArrayModifier, nodes_mod: NodesModifier
) -> None:
    """Sort nodes modifier, set correct visibility and add nodes group if it's missing."""
    if nodes_mod is not None:
        if nodes_mod.node_group is None:
            nodes_mod.node_group = new_node_group()
        sort_nodes_mod(ob, nodes_mod, array_mod)


def fix_center_empty(ob: Object, center_empty: Optional[Object]) -> None:
    """Set correct center empty collections."""
    if center_empty is not None:
        if not center_empty.users_collection:
            if get_preferences().move_empties_to_collection:
                empties_collection = get_preferences().empties_collection
                move_to_collection(empties_collection, center_empty)
            else:
                copy_collections(ob, center_empty)


def fix_offset_empty(ob: Object, offset_empty: Optional[Object]) -> None:
    """Set correct offset empty collections."""
    if offset_empty is not None:
        if not offset_empty.users_collection:
            if get_preferences().move_empties_to_collection:
                empties_collection = get_preferences().empties_collection
                move_to_collection(empties_collection, offset_empty)
            else:
                copy_collections(ob, offset_empty)


class ExistingRadialArrayBuilder:
    @staticmethod
    def get_array_mod(ob: Object, name: str) -> Optional[ArrayModifier]:
        return find_array_mod(ob, name)

    @staticmethod
    def get_name(array_mod: Optional[ArrayModifier]) -> str:
        return "" if array_mod is None else array_mod.name

    @staticmethod
    def get_offset_empty(array_mod: Optional[ArrayModifier]) -> Optional[Object]:
        return None if array_mod is None else find_offset_empty(array_mod)

    @staticmethod
    def get_props(ob: Object, array_mod: Optional[ArrayModifier], name: str) -> \
            Optional["properties.RadialArrayPropsGroup"]:
        return None if array_mod is None else find_props(ob, name)

    @staticmethod
    def get_nodes_mod(ob: Object, array_mod: Optional[ArrayModifier], name: str) -> Optional[NodesModifier]:
        return None if array_mod is None else find_nodes_mod(ob, name)

    @staticmethod
    def get_center_empty(
        array_mod: Optional[ArrayModifier], props: Optional["properties.RadialArrayPropsGroup"]
    ) -> Optional[Object]:
        return find_center_empty(props) if array_mod is not None and props is not None else None


class NewRadialArrayBuilder:
    @staticmethod
    def get_array_mod(context: Context, ob: Object) -> ArrayModifier:
        return new_array_mod(context, ob)

    @staticmethod
    def get_name(array_mod: ArrayModifier) -> str:
        return array_mod.name

    @staticmethod
    def get_offset_empty(context: Context, ob: Object, array_mod: ArrayModifier) -> Object:
        return new_offset_empty(context, ob, array_mod)

    @staticmethod
    def get_props(ob: Object, array_mod: ArrayModifier, name: str) -> "properties.RadialArrayPropsGroup":
        props = find_props(ob, name)
        if props is None:
            props = new_props(ob, array_mod, name)
        return props

    @staticmethod
    def get_nodes_mod(ob: Object, name: str) -> Optional[NodesModifier]:
        return find_nodes_mod(ob, name)

    @staticmethod
    def get_center_empty() -> None:
        return None


class RadialArrayDirector:
    def __init__(self, cls, object_radial_arrays):
        self.cls = cls
        self.object_radial_arrays = object_radial_arrays

    def build_from_modifier(self, array_mod_name=""):
        builder = ExistingRadialArrayBuilder

        context = self.object_radial_arrays.context
        ob = self.object_radial_arrays.object

        array_mod = builder.get_array_mod(ob, array_mod_name)
        if array_mod is None:
            return None

        radial_array_name = builder.get_name(array_mod)
        offset_empty = builder.get_offset_empty(array_mod)
        props = builder.get_props(ob, array_mod, radial_array_name)

        if props is None:
            props = NewRadialArrayBuilder.get_props(ob, array_mod, radial_array_name)
            restore_props(ob, array_mod, offset_empty, props)
        if offset_empty is None:
            offset_empty = NewRadialArrayBuilder.get_offset_empty(context, ob, array_mod)

        nodes_mod = builder.get_nodes_mod(ob, array_mod, radial_array_name)
        center_empty = builder.get_center_empty(array_mod, props)

        remove_junk_props(ob)
        fix_nodes_mod(ob, array_mod, nodes_mod)
        fix_center_empty(ob, center_empty)
        fix_offset_empty(ob, offset_empty)

        return self.cls(self.object_radial_arrays,
                        radial_array_name,
                        array_mod,
                        nodes_mod,
                        center_empty,
                        offset_empty)

    def build_new(self):
        builder = NewRadialArrayBuilder()

        context = self.object_radial_arrays.context
        ob = self.object_radial_arrays.object
        array_mod = builder.get_array_mod(context, ob)
        radial_array_name = builder.get_name(array_mod)

        offset_empty = builder.get_offset_empty(context, ob, array_mod)
        builder.get_props(ob, array_mod, radial_array_name)
        nodes_mod = builder.get_nodes_mod(ob, radial_array_name)
        center_empty = None

        remove_junk_props(ob)
        fix_nodes_mod(ob, array_mod, nodes_mod)
        fix_center_empty(ob, center_empty)
        fix_offset_empty(ob, offset_empty)

        return self.cls(self.object_radial_arrays,
                        radial_array_name,
                        array_mod,
                        nodes_mod,
                        center_empty,
                        offset_empty)
