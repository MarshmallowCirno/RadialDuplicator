import re
from typing import Optional

import bpy
import numpy as np
from bpy.types import ScrewModifier
from bpy.types import Context
from bpy.types import NodesModifier
from bpy.types import NodeTree
from bpy.types import Object
from mathutils import Matrix
from mathutils import Vector

from .. import properties
from ..utils.object import copy_collections
from ..utils.object import copy_local_view_state
from ..utils.object import get_modifier_index


def find_screw_mod(ob: Object, name: str) -> Optional[ScrewModifier]:
    """Find screw modifier by name."""
    screw_mod = ob.modifiers.get(name)
    return screw_mod


def find_nodes_mod(ob: Object, name: str) -> Optional[NodesModifier]:
    """Find nodes modifier by name."""
    match = re.search(r"\.[0-9]+$", name)
    index = "" if match is None else match.group(0)
    base_name = name.removesuffix(index)
    nodes_mods = filter(lambda mod: mod.type == 'NODES' and mod.name == f"{base_name}Offset{index}", ob.modifiers)
    nodes_mod = next(nodes_mods, None)
    return nodes_mod


def find_axis_empty(screw_mod: ScrewModifier) -> Optional[Object]:
    """Find axis empty of screw modifier."""
    axis_empty = screw_mod.object
    return axis_empty


def find_props(ob: Object, name: str) -> Optional["properties.RadialScrewPropsGroup"]:
    """Find object radial screw property group by name."""
    props = ob.radial_duplicator.screws.get(name)
    return props


def new_screw_mod(context: Context, ob: Object) -> ScrewModifier:
    """Add a new screw modifier to object and sort it."""
    # noinspection PyTypeChecker
    screw_mod: ScrewModifier = ob.modifiers.new(name="RadialScrew", type='SCREW')
    screw_mod.use_merge_vertices = True
    screw_mod.show_expanded = False
    screw_mod.merge_threshold = 0.0001 / context.scene.unit_settings.scale_length  # .1mm
    if ob.type == 'MESH':
        screw_mod.use_normal_calculate = True
    sort_screw_mod(ob, screw_mod)
    return screw_mod


def new_nodes_mod(
    ob: Object, screw_mod: ScrewModifier, props: "properties.RadialScrewPropsGroup", name: str
) -> NodesModifier:
    """Add new nodes modifier to object and sort it."""
    match = re.search(r"\.[0-9]+$", name)
    index = "" if match is None else match.group(0)
    base_name = screw_mod.name.removesuffix(index)
    # noinspection PyTypeChecker
    nodes_mod: NodesModifier = ob.modifiers.new(name=f"{base_name}Offset{index}", type='NODES')
    nodes_mod.node_group = new_node_group()
    nodes_mod.show_expanded = False
    nodes_mod.show_viewport = props.show_viewport
    sort_nodes_mod(ob, nodes_mod, screw_mod)
    return nodes_mod


def new_node_group() -> NodeTree:
    """Add a new node group and return it."""
    node_group = bpy.data.node_groups.new(name="RadialScrewNodes", type='GeometryNodeTree')

    group_input = node_group.nodes.new(type='NodeGroupInput')
    group_output = node_group.nodes.new(type='NodeGroupOutput')

    node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type="NodeSocketGeometry")
    node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type="NodeSocketGeometry")

    radius_offset = node_group.nodes.new(type='GeometryNodeTransform')
    radius_offset.name = "RadiusOffset"

    centering_pivot = node_group.nodes.new(type='GeometryNodeTransform')
    centering_pivot.name = "ObjectPivotToRadialScrewCenter"

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


def new_props(ob: Object, screw_mod: ScrewModifier, name: str) -> "properties.RadialScrewPropsGroup":
    """Add a new radial screw property group and return it."""
    props = ob.radial_duplicator.screws.add()
    props["name"] = name
    mx = ob.matrix_world.inverted()
    props["spin_orientation_matrix_object"] = np.array(mx).ravel()
    props["show_viewport"] = screw_mod.show_viewport
    return props


def new_axis_empty(context: Context, ob: Object, screw_mod: ScrewModifier) -> Object:
    """Add a new center empty to property group and return it."""
    axis_empty = bpy.data.objects.new(name="ScrewEmpty", object_data=None)
    axis_empty.empty_display_type = 'SPHERE'
    axis_empty.empty_display_size = max(ob.dimensions) / 2
    copy_collections(ob, axis_empty)
    copy_local_view_state(context, axis_empty)
    if ob.type != 'CURVE':
        # center_empty.hide_viewport = True
        axis_empty.parent = ob
        # matrix_world of the newly created object updates after updating depsgraph
        context.evaluated_depsgraph_get().update()
        axis_empty.matrix_parent_inverse.identity()
        axis_empty.matrix_basis.identity()
    else:
        # modifier will lag if its empty set to ob child
        axis_empty.matrix_world = ob.matrix_world
    screw_mod.object = axis_empty
    return axis_empty


def sort_screw_mod(ob: Object, screw_mod: ScrewModifier) -> None:
    """Place screw modifier after mirror, screw or on the top."""
    screw_mod_idx = ob.modifiers.find(screw_mod.name)
    other_mods = [mod for mod in ob.modifiers if mod != screw_mod]

    another_screw_mods = filter(lambda mod: mod.type == 'SCREW', reversed(other_mods))
    another_screw_mod = next(another_screw_mods, None)
    if another_screw_mod is not None:
        another_screw_mod_idx = ob.modifiers.find(another_screw_mod.name)
        new_screw_mod_idx = get_modifier_index(current_index=screw_mod_idx,
                                               reference_index=another_screw_mod_idx,
                                               position='AFTER')
    else:
        mirror_mods = filter(lambda mod: mod.type == 'MIRROR' and mod.mirror_object is None, reversed(other_mods))
        mirror_mod = next(mirror_mods, None)
        if mirror_mod is not None:
            mirror_mod_idx = ob.modifiers.find(mirror_mod.name)
            new_screw_mod_idx = get_modifier_index(current_index=screw_mod_idx,
                                                   reference_index=mirror_mod_idx,
                                                   position='AFTER')
        else:
            new_screw_mod_idx = 0

    ob.modifiers.move(from_index=screw_mod_idx, to_index=new_screw_mod_idx)


def sort_nodes_mod(ob: Object, nodes_mod: NodesModifier, screw_mod: ScrewModifier) -> None:
    """Place nodes modifier before screw modifier."""
    nodes_mod_idx = ob.modifiers.find(nodes_mod.name)
    screw_mod_idx = ob.modifiers.find(screw_mod.name)
    new_nodes_mod_idx = get_modifier_index(current_index=nodes_mod_idx,
                                           reference_index=screw_mod_idx,
                                           position='BEFORE')
    ob.modifiers.move(from_index=nodes_mod_idx, to_index=new_nodes_mod_idx)


def restore_props(
    ob: Object, screw_mod: ScrewModifier, axis_empty: Object, props: "properties.RadialScrewPropsGroup"
) -> None:
    """Calculate and set correct values to properties in property group.

    Calculate spin axis from axis empty rotation, get count from screw modifier
    and replace them in radial screw properties. Assume that screw was rotated in local orientation.
    """
    if axis_empty is not None:
        spin_axis_enums = props.bl_rna.properties["spin_axis"].enum_items
        props["spin_axis"] = spin_axis_enums.find(get_spin_axis(ob, axis_empty))
    props["steps"] = screw_mod.steps
    props["end_angle"] = screw_mod.angle
    props["screw_offset"] = screw_mod.screw_offset
    props["iterations"] = screw_mod.iterations


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
    """Remove radial screw properties with name that have no matching screw modifier."""
    for props in reversed(ob.radial_duplicator.screws):
        mod = ob.modifiers.get(props.name)
        if mod is None or mod.type != 'SCREW' or "Radial" not in mod.name:
            index = ob.radial_duplicator.screws.find(props.name)
            ob.radial_duplicator.screws.remove(index)


def fix_nodes_mod(
    ob: Object, screw_mod: ScrewModifier, nodes_mod: NodesModifier
) -> None:
    """Sort nodes modifier, set correct visibility and add nodes group if it's missing."""
    if nodes_mod is not None:
        if nodes_mod.node_group is None:
            nodes_mod.node_group = new_node_group()
        sort_nodes_mod(ob, nodes_mod, screw_mod)


def fix_axis_empty(ob: Object, axis_empty: Optional[Object]) -> None:
    """Set correct axis empty collections."""
    if axis_empty is not None:
        if not axis_empty.users_collection:
            copy_collections(ob, axis_empty)


class ExistingRadialScrewBuilder:
    @staticmethod
    def get_screw_mod(ob: Object, name: str) -> Optional[ScrewModifier]:
        return find_screw_mod(ob, name)

    @staticmethod
    def get_name(screw_mod: Optional[ScrewModifier]) -> str:
        return "" if screw_mod is None else screw_mod.name

    @staticmethod
    def get_axis_empty(screw_mod: Optional[ScrewModifier]) -> Optional[Object]:
        return None if screw_mod is None else find_axis_empty(screw_mod)

    @staticmethod
    def get_props(ob: Object, screw_mod: Optional[ScrewModifier], name: str) -> \
            Optional["properties.RadialScrewPropsGroup"]:
        return None if screw_mod is None else find_props(ob, name)

    @staticmethod
    def get_nodes_mod(ob: Object, screw_mod: Optional[ScrewModifier], name: str) -> Optional[NodesModifier]:
        return None if screw_mod is None else find_nodes_mod(ob, name)


class NewRadialScrewBuilder:
    @staticmethod
    def get_screw_mod(context: Context, ob: Object) -> ScrewModifier:
        return new_screw_mod(context, ob)

    @staticmethod
    def get_name(screw_mod: ScrewModifier) -> str:
        return screw_mod.name

    @staticmethod
    def get_axis_empty(context: Context, ob: Object, screw_mod: ScrewModifier) -> Object:
        return new_axis_empty(context, ob, screw_mod)

    @staticmethod
    def get_props(ob: Object, screw_mod: ScrewModifier, name: str) -> "properties.RadialScrewPropsGroup":
        props = find_props(ob, name)
        if props is None:
            props = new_props(ob, screw_mod, name)
        return props

    @staticmethod
    def get_nodes_mod(ob: Object, name: str) -> Optional[NodesModifier]:
        return find_nodes_mod(ob, name)


class RadialScrewDirector:
    def __init__(self, cls, object_radial_screws):
        self.cls = cls
        self.object_radial_screws = object_radial_screws

    def build_from_modifier(self, screw_mod_name=""):
        builder = ExistingRadialScrewBuilder

        context = self.object_radial_screws.context
        ob = self.object_radial_screws.object

        screw_mod = builder.get_screw_mod(ob, screw_mod_name)
        if screw_mod is None:
            return None

        radial_screw_name = builder.get_name(screw_mod)
        axis_empty = builder.get_axis_empty(screw_mod)
        props = builder.get_props(ob, screw_mod, radial_screw_name)

        if props is None:
            props = NewRadialScrewBuilder.get_props(ob, screw_mod, radial_screw_name)
            restore_props(ob, screw_mod, axis_empty, props)
        if axis_empty is None:
            axis_empty = NewRadialScrewBuilder.get_axis_empty(context, ob, screw_mod)

        nodes_mod = builder.get_nodes_mod(ob, screw_mod, radial_screw_name)

        remove_junk_props(ob)
        fix_nodes_mod(ob, screw_mod, nodes_mod)
        fix_axis_empty(ob, axis_empty)

        return self.cls(self.object_radial_screws,
                        radial_screw_name,
                        screw_mod,
                        nodes_mod,
                        axis_empty)

    def build_new(self):
        builder = NewRadialScrewBuilder()

        context = self.object_radial_screws.context
        ob = self.object_radial_screws.object
        screw_mod = builder.get_screw_mod(context, ob)
        radial_screw_name = builder.get_name(screw_mod)

        axis_empty = builder.get_axis_empty(context, ob, screw_mod)
        builder.get_props(ob, screw_mod, radial_screw_name)
        nodes_mod = builder.get_nodes_mod(ob, radial_screw_name)

        remove_junk_props(ob)
        fix_nodes_mod(ob, screw_mod, nodes_mod)
        fix_axis_empty(ob, axis_empty)

        return self.cls(self.object_radial_screws,
                        radial_screw_name,
                        screw_mod,
                        nodes_mod,
                        axis_empty)
