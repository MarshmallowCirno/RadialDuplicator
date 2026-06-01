from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self, cast

import bpy
import mathutils
import numpy as np

from ..radial_objects import radial_screw_builder
from ..utils import math_utils, object_data_utils, object_utils

if TYPE_CHECKING:
    from .. import properties


class ObjectRadialScrews:
    """Class for getting or controlling RadialScrews on object"""

    def __init__(self, context: bpy.types.Context, ob: bpy.types.Object) -> None:
        self.context: bpy.types.Context = context
        self.object: bpy.types.Object = ob
        self.value: list[RadialScrew] = self._get_radial_screws()

    def _get_radial_screws(self) -> list[RadialScrew]:
        ob_mods = self.object.modifiers
        radial_screw_modifier_names = [mod.name for mod in ob_mods if mod.type == 'SCREW' and "Radial" in mod.name]
        radial_screws = [
            cast(RadialScrew, RadialScrew.from_modifier(self, name)) for name in radial_screw_modifier_names
        ]
        return radial_screws

    def get_by_name(self, name: str) -> RadialScrew | None:
        """Get radial array from class dict or create it from modifier and add to class dict."""
        names = [radial_screw.name for radial_screw in self.value]
        if name in names:
            i = names.index(name)
            radial_screw = self.value[i]
        else:
            radial_screw = None
        return radial_screw

    def get_by_index(self, index: int) -> RadialScrew | None:
        """Get radial screw from class dict or create it from modifier and add to class dict."""
        # https://stackoverflow.com/questions/2492087/how-to-get-the-nth-element-of-a-python-list-or-a-default-if-not-available # noqa
        radial_screw = self.value[index] if -len(self.value) <= index < len(self.value) else None
        return radial_screw

    def new(self) -> RadialScrew:
        """Build new radial screw and store it in class dict."""
        radial_screw = RadialScrew.new(self)

        self.value.append(radial_screw)
        return radial_screw

    def refresh_all(self) -> None:
        """Refresh all object radial screws."""
        for radial_screw in self.value:
            radial_screw.refresh()


class RadialScrew:
    @classmethod
    def from_modifier(cls, object_radial_screws: ObjectRadialScrews, screw_modifier_name: str = "") -> Self | None:
        return radial_screw_builder.RadialScrewDirector(cls, object_radial_screws).build_from_modifier(
            screw_modifier_name
        )

    @classmethod
    def new(cls, object_radial_screws: ObjectRadialScrews) -> Self:
        return radial_screw_builder.RadialScrewDirector(cls, object_radial_screws).build_new()

    def __init__(
        self,
        siblings: ObjectRadialScrews,
        name: str,
        screw_modifier: bpy.types.ScrewModifier,
        nodes_modifier: bpy.types.NodesModifier | None,  # nodes_modifier is None when there is no offset or rotation
        axis_empty: bpy.types.Object,
    ) -> None:
        self.siblings: ObjectRadialScrews = siblings
        self.name: str = name
        self.context: bpy.types.Context = siblings.context
        self.object: bpy.types.Object = siblings.object
        self.properties = RadialScrewProps(self)
        self.screw_modifier = RadialScrewScrewMod(self, screw_modifier)
        self.nodes_modifier = RadialScrewNodesMod(self, nodes_modifier)
        self.axis_empty = RadialScrewAxisEmpty(self, axis_empty)
        self.pivot_point = RadialScrewPivotPoint(self)

    @property
    def spin_vec_object(self) -> mathutils.Vector:
        ob = self.object
        props = self.properties

        # Get new spin orientation from operator attributes on properties update,
        # but use last spin orientation for refreshing.
        # Last orientation is stored in object space.
        # Storing it in global space wouldn't allow radial screw to be properly
        # restored if object has been rotated since then.
        spin_orientation_matrix_world = ob.matrix_world @ props.value.spin_orientation_matrix_object
        spin_axis = props.value.spin_axis
        spin_vec_world = math_utils.get_axis_vec(spin_axis, spin_orientation_matrix_world)
        spin_vec_object = spin_vec_world @ ob.matrix_world

        return spin_vec_object

    def modify(
        self,
        spin_orientation: Literal['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'],
        spin_axis: Literal['X', 'Y', 'Z'],
        steps: int,
        radius_offset: float,
        start_angle: float,
        end_angle: float,
        screw_offset: float,
        iterations: int,
        pivot_point: Literal['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY']
        | mathutils.Vector
        | None = None,
    ) -> None:
        """Spin radial screw and change pivot point.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        :param spin_axis: Axis along which spin will be performed in ['X', 'Y', 'Z'].
        :param steps: Total number of duplicates to make in [1, inf].
        :param radius_offset: Moves each step a user-defined distance from the pivot point in [-inf, inf].
        :param screw_offset: Offset the revolution along its axis in [-inf, inf].
        :param start_angle: Rotation placement for the first duplicated geometry in radians in [-inf, inf].
        :param end_angle: Rotation placement for the last duplicated geometry in radians in [-inf, inf].
        :param iterations: Number of times to apply the screw operation in [1, inf].
        :param pivot_point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY', 'Vector', None].
        """
        self.properties.update(
            spin_orientation, spin_axis, steps, radius_offset, start_angle, end_angle, screw_offset, iterations
        )
        if pivot_point is not None:
            self.set_pivot_point(pivot_point)
        else:
            self.refresh()

    def refresh(self) -> None:
        """Spin radial screw not changing its parameters."""
        if self.object.type == 'MESH':
            self.nodes_modifier.refresh()
        self.screw_modifier.refresh()
        self.axis_empty.refresh()

    def set_pivot_point(
        self,
        point: Literal['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY'] | mathutils.Vector,
    ) -> None:
        """Set pivot point and refresh radial screw.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY', 'Vector'].
        """
        RadialScrewPivotPoint(self).set(point)

    def apply(self) -> str:
        """Apply modifiers, remove empties and properties."""
        self.axis_empty.remove()
        self.properties.remove()
        self.nodes_modifier.apply()
        success_msg = self.screw_modifier.apply()
        self.axis_empty.remove()
        self.siblings.value.remove(self)
        return success_msg

    def remove(self) -> None:
        """Remove modifiers, empties and properties."""
        self.axis_empty.remove()
        self.properties.remove()
        self.nodes_modifier.remove()
        self.screw_modifier.remove()
        self.axis_empty.remove()
        self.siblings.value.remove(self)


class RadialScrewProps:
    def __init__(self, radial_screw: RadialScrew) -> None:
        self._radial_screw = radial_screw

    @property
    def value(self) -> properties.RadialScrewPropsGroup:
        # Re-allocation can lead to crashes (e.g. if you add a lot of items to some Collection, this can lead
        # to re-allocating the underlying container’s memory, invalidating all previous references to existing items).
        # So, don't store collection item and retrieve it by a name instead.
        ob = self._radial_screw.object
        name = self._radial_screw.name
        props_collection = cast("properties.RadialCollections", ob.radial_duplicator)  # pyright: ignore[reportAttributeAccessIssue]

        props = props_collection.screws.get(name)
        assert props is not None
        return props

    def _get_spin_orientation_matrix(
        self, spin_orientation: Literal['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL']
    ) -> mathutils.Matrix:
        """Get spin orientation matrix in world space.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        """
        context = self._radial_screw.context
        ob = self._radial_screw.object

        return {
            'GLOBAL': lambda: mathutils.Matrix.Identity(4),
            'LOCAL': lambda: ob.matrix_world.copy(),
            'VIEW': lambda: context.space_data.region_3d.view_matrix.inverted(),
            'NORMAL': lambda: object_utils.get_normal_matrix(context, ob),
        }[spin_orientation]()

    def update(
        self,
        spin_orientation: Literal['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'],
        spin_axis: Literal['X', 'Y', 'Z'],
        steps: int,
        radius_offset: float,
        start_angle: float,
        end_angle: float,
        screw_offset: float,
        iterations: int,
    ) -> None:
        """Update property group."""
        ob = self._radial_screw.object

        spin_orientation_enum = cast(bpy.types.EnumProperty, self.value.bl_rna.properties["spin_orientation"])
        spin_orientation_enum_items = spin_orientation_enum.enum_items
        self.value["spin_orientation"] = spin_orientation_enum_items.find(spin_orientation)
        spin_orientation_matrix = self._get_spin_orientation_matrix(spin_orientation)
        spin_orientation_matrix_object = ob.matrix_world.inverted() @ spin_orientation_matrix

        self.value["spin_orientation_matrix_object"] = np.array(spin_orientation_matrix_object).T.ravel()
        spin_axis_enum = cast(bpy.types.EnumProperty, self.value.bl_rna.properties["spin_axis"])
        spin_axis_enum_items = spin_axis_enum.enum_items
        self.value["spin_axis"] = spin_axis_enum_items.find(spin_axis)
        self.value["steps"] = steps
        self.value["radius_offset"] = radius_offset
        self.value["start_angle"] = start_angle
        self.value["end_angle"] = end_angle
        self.value["screw_offset"] = screw_offset
        self.value["iterations"] = iterations

    def remove(self) -> None:
        """Remove property group."""
        ob = self._radial_screw.object
        name = self._radial_screw.name
        props_collection = cast("properties.RadialCollections", ob.radial_duplicator)  # pyright: ignore[reportAttributeAccessIssue]

        props_id = props_collection.screws.find(name)
        props_collection.screws.remove(props_id)


class RadialScrewScrewMod:
    def __init__(self, radial_screw: RadialScrew, value: bpy.types.ScrewModifier) -> None:
        self._radial_screw = radial_screw
        self.value = value

    def refresh(self) -> None:
        props = self._radial_screw.properties.value
        axis_empty = self._radial_screw.axis_empty.value

        self.value.steps = props.steps
        self.value.iterations = props.iterations
        self.value.axis = props.spin_axis
        self.value.screw_offset = props.screw_offset
        self.value.angle = props.end_angle - props.start_angle
        self.value.object = axis_empty

    def apply(self) -> str:
        """Apply screw modifier and return success message confirmation."""
        ob = self._radial_screw.object
        context = self._radial_screw.context

        message = (
            "Applied modifier was not first, result may not be as expected"
            if ob.modifiers.find(self.value.name) > 0
            else ""
        )

        with context.temp_override(object=ob):
            bpy.ops.object.modifier_apply(modifier=self.value.name)
        return message

    def remove(self) -> None:
        """Remove screw modifier."""
        ob = self._radial_screw.object

        ob.modifiers.remove(self.value)


class RadialScrewNodesMod:
    def __init__(self, radial_screw: RadialScrew, value: bpy.types.NodesModifier | None) -> None:
        self._radial_screw = radial_screw
        self.value = value

    @property
    def displace_offset_vec_object(self) -> mathutils.Vector:
        """Get displace vector in ob space."""
        ob = self._radial_screw.object
        props = self._radial_screw.properties.value
        pivot_point_co = self._radial_screw.pivot_point.co_world
        spin_vec_object = self._radial_screw.spin_vec_object

        if props.radius_offset == 0:
            return mathutils.Vector((0, 0, 0))
        else:
            pivot_mx = ob.matrix_world.copy()
            pivot_mx.translation = pivot_point_co
            mesh_center_co_pivot = pivot_mx.inverted() @ object_data_utils.get_mesh_center_co_world(ob)

            non_aligned_displace_vec = (
                mathutils.Vector((1, 1, 1)) if mesh_center_co_pivot.length_squared < 0.001 else mesh_center_co_pivot
            )

            projection = non_aligned_displace_vec.project(spin_vec_object)
            rejection = non_aligned_displace_vec - projection

            aligned_displace_vec_local = rejection.normalized()
            displace_offset_vec = aligned_displace_vec_local * props.radius_offset
            return displace_offset_vec

    def _get_start_rotation_matrix(self) -> mathutils.Euler:
        """Get object rotation to achieve radial screw starting rotation."""
        props = self._radial_screw.properties.value
        spin_vec_object = self._radial_screw.spin_vec_object

        return (
            mathutils.Euler((0, 0, 0))
            if props.start_angle == 0
            else mathutils.Matrix.Rotation(props.start_angle, 4, spin_vec_object[:]).to_euler()
        )

    def refresh(self) -> None:
        start_rotation = self._get_start_rotation_matrix()
        displace_offset_vec = self.displace_offset_vec_object
        ob = self._radial_screw.object
        axis_empty = self._radial_screw.axis_empty.value

        if start_rotation[:] != (0, 0, 0) or displace_offset_vec[:] != (0, 0, 0):
            if self.value is None:
                self.add()
            assert self.value is not None

            node_group = self.value.node_group
            assert node_group is not None
            node = node_group.nodes["StartRotation"]
            cast(bpy.types.NodeSocketRotation, node.inputs["Rotation"]).default_value = start_rotation[:]
            node = node_group.nodes["RadiusOffset"]
            cast(bpy.types.NodeSocketVectorTranslation, node.inputs["Translation"]).default_value = displace_offset_vec[
                :
            ]

            axis_empty_mx = axis_empty.matrix_world
            axis_empty_mx_ob = ob.matrix_world.inverted() @ axis_empty_mx

            node = node_group.nodes["ObjectPivotToRadialScrewCenter"]
            cast(
                bpy.types.NodeSocketVectorTranslation, node.inputs["Translation"]
            ).default_value = axis_empty_mx_ob.inverted().to_translation()

            node = node_group.nodes["RestoreObjectPivot"]
            cast(
                bpy.types.NodeSocketVectorTranslation, node.inputs["Translation"]
            ).default_value = axis_empty_mx_ob.to_translation()

        else:
            self.remove()

    def add(self) -> None:
        """Add nodes modifier."""
        name = self._radial_screw.name
        ob = self._radial_screw.object
        screw_mod = self._radial_screw.screw_modifier.value
        props = self._radial_screw.properties.value

        self.value = radial_screw_builder.new_nodes_mod(ob, screw_mod, props, name)

    def apply(self) -> None:
        """Apply nodes modifier if it exists."""
        if self.value is not None:
            ob = self._radial_screw.object
            context = self._radial_screw.context

            with context.temp_override(object=ob):
                bpy.ops.object.modifier_apply(modifier=self.value.name)
            self.value = None

    def remove(self) -> None:
        """Remove nodes modifier if it exists."""
        if self.value is not None:
            ob = self._radial_screw.object
            node_group = self.value.node_group
            if node_group is not None:
                bpy.data.node_groups.remove(node_group, do_unlink=True)
            ob.modifiers.remove(self.value)
            self.value = None
            self._radial_screw.nodes_modifier.value = None


class RadialScrewAxisEmpty:
    def __init__(self, radial_screw: RadialScrew, value: bpy.types.Object):
        self._radial_screw = radial_screw
        self.value = value

    def refresh(self) -> None:
        """Rotate offset empty across pivot point."""
        ob = self._radial_screw.object
        props = self._radial_screw.properties.value
        pivot_point_co_world = self._radial_screw.pivot_point.co_world
        spin_orientation_matrix_world = ob.matrix_world @ props.spin_orientation_matrix_object

        # Transform
        children = self.value.children
        object_utils.clear_children_parent_and_keep_mx(self.value)

        self.value.matrix_world = spin_orientation_matrix_world
        self.value.matrix_world.translation = pivot_point_co_world

        object_utils.set_children_parent_and_keep_mx(children, self.value)

    def remove(self) -> None:
        """Remove offset empty."""
        object_utils.clear_children_parent_and_keep_mx(self.value)
        bpy.data.objects.remove(self.value, do_unlink=True)


class RadialScrewPivotPoint:
    def __init__(self, radial_screw: RadialScrew) -> None:
        self._radial_screw = radial_screw

    @property
    def co_world(self) -> mathutils.Vector:
        """Get current pivot point coordinates."""
        axis_empty = self._radial_screw.axis_empty.value

        return axis_empty.matrix_world.to_translation()

    def _get_point_co_world(
        self, point: Literal['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY'] | mathutils.Vector
    ) -> mathutils.Vector:
        """Get point coordinates.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY', 'Vector'].
        """
        context = self._radial_screw.context
        ob = self._radial_screw.object
        axis_empty = self._radial_screw.axis_empty.value

        if point == 'ORIGIN':
            return ob.matrix_world.to_translation()
        elif point == 'CURSOR':
            return mathutils.Vector(context.scene.cursor.location.copy())
        elif point == 'MESH_SELECTION':
            return object_data_utils.get_mesh_selection_co_world(context)
        elif point == 'ACTIVE_OBJECT':
            return context.view_layer.objects.active.matrix_world.to_translation()
        elif point == 'AXIS_EMPTY':
            return axis_empty.matrix_world.to_translation()
        else:
            return point

    def set(
        self, point: Literal['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY'] | mathutils.Vector
    ) -> None:
        """Change pivot point location.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'AXIS_EMPTY', 'Vector'].
        """
        context = self._radial_screw.context
        ob = self._radial_screw.object
        siblings = self._radial_screw.siblings

        point_co = self._get_point_co_world(point)

        if siblings.value:
            if siblings.value[-1] == self._radial_screw:
                self._set_top_radial_screw_pivot_point(point_co)
            else:
                self._set_child_radial_screw_pivot_point(point_co)
        else:
            object_utils.set_origin(context, ob, point_co)

    def _set_top_radial_screw_pivot_point(self, point_co: mathutils.Vector) -> None:
        """Set object origin location keeping pivot points of object radial screws and refresh all radial screws."""
        context = self._radial_screw.context
        ob = self._radial_screw.object
        axis_empty = self._radial_screw.axis_empty.value

        if ob.parent == axis_empty:
            axis_empty.matrix_world.translation = point_co
            object_utils.set_origin(context, ob, point_co)
        else:
            object_utils.set_origin(context, ob, point_co)
            axis_empty.matrix_world.translation = point_co

        self._radial_screw.refresh()

    def _set_child_radial_screw_pivot_point(self, point_co: mathutils.Vector) -> None:
        """Set center empty location and refresh radial screw."""
        axis_empty = self._radial_screw.axis_empty.value
        axis_empty.matrix_world.translation = point_co
        self._radial_screw.refresh()
