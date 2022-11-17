from typing import Union, Optional

import bpy
import numpy as np
from bpy.types import ScrewModifier
from bpy.types import Context
from bpy.types import NodesModifier
from bpy.types import Object
from mathutils import Euler
from mathutils import Matrix
from mathutils import Vector

from .. import properties
from ..utils.math import get_axis_vec
from ..utils.object import clear_children_parent_and_keep_mx
from ..utils.object import get_normal_matrix
from ..utils.object import set_children_parent_and_keep_mx
from ..utils.object import set_origin
from ..utils.object_data import get_mesh_center_co_world
from ..utils.object_data import get_mesh_selection_co_world
from ..radial_objects.radial_screw_builder import new_nodes_mod
from ..radial_objects.radial_screw_builder import RadialScrewDirector


class ObjectRadialScrews:
    """Class for getting or controlling RadialScrews on object"""
    def __init__(self, context: Context, ob: Object):
        self.context: Context = context
        self.object: Object = ob
        self.value: list["RadialScrew"] = self._get_radial_screws()

    def _get_radial_screws(self) -> list["RadialScrew"]:
        ob_mods = self.object.modifiers
        radial_screw_modifier_names = [mod.name for mod in ob_mods if mod.type == 'SCREW' and "Radial" in mod.name]
        radial_screws = [RadialScrew.from_modifier(self, name) for name in radial_screw_modifier_names]
        return radial_screws

    def __getitem__(self, key: Union[str, int]) -> Optional["RadialScrew"]:
        """Get radial screw from class dict or create it from modifier and add to class dict."""
        if type(key) is str:
            names = [radial_screw.name for radial_screw in self.value]
            if key in names:
                i = names.index(key)
                radial_screw = self.value[i]
            else:
                radial_screw = None

        elif type(key) is int:
            # https://stackoverflow.com/questions/2492087/how-to-get-the-nth-element-of-a-python-list-or-a-default-if-not-available # noqa
            radial_screw = (
                self.value[key]
                if -len(self.value) <= key < len(self.value)
                else None
            )
        else:
            raise TypeError("key is invalid")

        return radial_screw

    def new(self) -> "RadialScrew":
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
    def from_modifier(cls, object_radial_screws: ObjectRadialScrews, screw_modifier_name: str = ""):
        return RadialScrewDirector(cls, object_radial_screws).build_from_modifier(screw_modifier_name)

    @classmethod
    def new(cls, object_radial_screws: ObjectRadialScrews):
        return RadialScrewDirector(cls, object_radial_screws).build_new()

    def __init__(
        self,
        siblings: "ObjectRadialScrews",
        name: str,
        screw_modifier: ScrewModifier,
        nodes_modifier: Optional[NodesModifier],
        axis_empty: Optional[Object],
    ):
        self.siblings: "ObjectRadialScrews" = siblings
        self.name: str = name
        self.context: Context = siblings.context
        self.object: Object = siblings.object
        self.properties = RadialScrewProps(self)
        self.screw_modifier = RadialScrewScrewMod(self, screw_modifier)
        self.nodes_modifier = RadialScrewNodesMod(self, nodes_modifier)
        self.axis_empty = RadialScrewAxisEmpty(self, axis_empty)
        self.pivot_point = RadialScrewPivotPoint(self)

    @property
    def spin_vec_object(self):
        ob = self.object
        props = self.properties

        # Get new spin orientation from operator attributes on properties update,
        # but use last spin orientation for refreshing.
        # Last orientation is stored in object space.
        # Storing it in global space wouldn't allow radial screw to be properly
        # restored if object has been rotated since then.
        spin_orientation_matrix_world = ob.matrix_world @ props.value.spin_orientation_matrix_object
        spin_axis = props.value.spin_axis
        spin_vec_world = get_axis_vec(spin_axis, spin_orientation_matrix_world)
        spin_vec_object = spin_vec_world @ ob.matrix_world

        return spin_vec_object

    def modify(
        self,
        spin_orientation: str,
        spin_axis: str,
        steps: int,
        radius_offset: float,
        start_angle: float,
        end_angle: float,
        screw_offset: float,
        iterations: int,
        pivot_point: Optional[Union[str, Vector]] = None,
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
        :param pivot_point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector', None].
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

    def set_pivot_point(self, point: Union[str, Vector]) -> None:
        """Set pivot point and refresh radial screw.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
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
    def __init__(self, radial_screw: RadialScrew):
        self._radial_screw = radial_screw

    @property
    def value(self) -> "properties.RadialScrewPropsGroup":
        # Re-allocation can lead to crashes (e.g. if you add a lot of items to some Collection, this can lead
        # to re-allocating the underlying container’s memory, invalidating all previous references to existing items).
        # So, don't store collection item and retrieve it by a name instead.

        ob = self._radial_screw.object
        name = self._radial_screw.name

        return ob.radial_duplicator.screws.get(name)

    def _get_spin_orientation_matrix(self, spin_orientation: str) -> Matrix:
        """Get spin orientation matrix in world space.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        """
        context = self._radial_screw.context
        ob = self._radial_screw.object

        return {
            'GLOBAL': lambda: Matrix.Identity(4),
            'LOCAL': lambda: ob.matrix_world.copy(),
            'VIEW': lambda: context.space_data.region_3d.view_matrix.inverted(),
            'NORMAL': lambda: get_normal_matrix(context, ob),
        }[spin_orientation]()

    def update(self,
               spin_orientation: str,
               spin_axis: str,
               steps: int,
               radius_offset: float,
               start_angle: float,
               end_angle: float,
               screw_offset: float,
               iterations: int) -> None:
        """Update property group."""
        ob = self._radial_screw.object

        spin_orientation_enums = self.value.bl_rna.properties["spin_orientation"].enum_items
        self.value["spin_orientation"] = spin_orientation_enums.find(spin_orientation)
        spin_orientation_matrix = self._get_spin_orientation_matrix(spin_orientation)
        spin_orientation_matrix_object = ob.matrix_world.inverted() @ spin_orientation_matrix

        # noinspection PyTypeChecker
        self.value["spin_orientation_matrix_object"] = np.array(spin_orientation_matrix_object).T.ravel()
        spin_axis_enums = self.value.bl_rna.properties["spin_axis"].enum_items
        self.value["spin_axis"] = spin_axis_enums.find(spin_axis)
        self.value["steps"] = steps
        self.value["radius_offset"] = radius_offset
        self.value["start_angle"] = start_angle
        self.value["end_angle"] = end_angle
        self.value["screw_offset"] = screw_offset
        self.value["iterations"] = iterations

    def remove(self) -> None:
        """Remove property group if it exists."""
        ob = self._radial_screw.object
        name = self._radial_screw.name

        props_id = ob.radial_duplicator.screws.find(name)
        if props_id is not None:
            ob.radial_duplicator.screws.remove(props_id)


class RadialScrewScrewMod:
    def __init__(self, radial_screw: RadialScrew, value: ScrewModifier):
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
        """Apply screw modifier if it exists and return success message confirmation."""
        ob = self._radial_screw.object

        message = (
            "Applied modifier was not first, result may not be as expected"
            if ob.modifiers.find(self.value.name) > 0
            else ""
        )
        # noinspection PyArgumentList
        bpy.ops.object.modifier_apply({"object": ob}, modifier=self.value.name)
        self.value = None
        return message

    def remove(self) -> None:
        """Remove screw modifier if it exists."""
        ob = self._radial_screw.object

        ob.modifiers.remove(self.value)
        self.value = None


class RadialScrewNodesMod:
    def __init__(self, radial_screw: RadialScrew, value: Optional[NodesModifier]):
        self._radial_screw = radial_screw
        self.value = value

    @property
    def displace_offset_vec_object(self) -> Vector:
        """Get displace vector in ob space."""
        ob = self._radial_screw.object
        props = self._radial_screw.properties.value
        pivot_point_co = self._radial_screw.pivot_point.co_world
        spin_vec_object = self._radial_screw.spin_vec_object

        if props.radius_offset == 0:
            return Vector((0, 0, 0))
        else:
            pivot_mx = ob.matrix_world.copy()
            pivot_mx.translation = pivot_point_co
            mesh_center_co_pivot = pivot_mx.inverted() @ get_mesh_center_co_world(ob)

            non_aligned_displace_vec = (
                Vector((1, 1, 1)) if mesh_center_co_pivot.length_squared < 0.001 else mesh_center_co_pivot
            )

            projection = non_aligned_displace_vec.project(spin_vec_object)
            rejection = non_aligned_displace_vec - projection

            aligned_displace_vec_local = rejection.normalized()
            displace_offset_vec = aligned_displace_vec_local * props.radius_offset
            return displace_offset_vec

    def _get_start_rotation_matrix(self) -> Euler:
        """Get object rotation to achieve radial screw starting rotation."""
        props = self._radial_screw.properties.value
        spin_vec_object = self._radial_screw.spin_vec_object

        # noinspection PyArgumentList
        return (
            Euler((0, 0, 0))
            if props.start_angle == 0
            else Matrix.Rotation(props.start_angle, 4, spin_vec_object).to_euler()
        )

    def refresh(self) -> None:
        start_rotation = self._get_start_rotation_matrix()
        displace_offset_vec = self.displace_offset_vec_object
        ob = self._radial_screw.object
        axis_empty = self._radial_screw.axis_empty.value

        if start_rotation[:] != (0, 0, 0) or displace_offset_vec[:] != (0, 0, 0):

            if self.value is None:
                self.add()

            node_group = self.value.node_group
            node = node_group.nodes["StartRotation"]
            node.inputs["Rotation"].default_value = start_rotation[:]
            node = node_group.nodes["RadiusOffset"]
            node.inputs["Translation"].default_value = displace_offset_vec[:]

            axis_empty_mx = axis_empty.matrix_world
            axis_empty_mx_ob = ob.matrix_world.inverted() @ axis_empty_mx

            node = node_group.nodes["ObjectPivotToRadialScrewCenter"]
            node.inputs["Translation"].default_value = axis_empty_mx_ob.inverted().to_translation()

            node = node_group.nodes["RestoreObjectPivot"]
            node.inputs["Translation"].default_value = axis_empty_mx_ob.to_translation()

        else:
            self.remove()

    def add(self) -> None:
        """Add nodes modifier."""
        name = self._radial_screw.name
        ob = self._radial_screw.object
        screw_mod = self._radial_screw.screw_modifier.value
        props = self._radial_screw.properties.value

        self.value = new_nodes_mod(ob, screw_mod, props, name)

    def apply(self) -> None:
        """Apply nodes modifier if it exists."""
        if self.value is not None:
            ob = self._radial_screw.object

            # noinspection PyArgumentList
            bpy.ops.object.modifier_apply({"object": ob}, modifier=self.value.name)
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
    def __init__(self, radial_screw: RadialScrew, value: Optional[Object]):
        self._radial_screw = radial_screw
        self.value = value

    def refresh(self) -> None:
        """Rotate offset empty across pivot point."""
        ob = self._radial_screw.object
        props = self._radial_screw.properties.value
        pivot_point_co_world = self._radial_screw.pivot_point.co_world
        spin_orientation_matrix_world = ob.matrix_world @ props.spin_orientation_matrix_object

        # transform
        children = self.value.children
        clear_children_parent_and_keep_mx(self.value)

        self.value.matrix_world = spin_orientation_matrix_world
        self.value.matrix_world.translation = pivot_point_co_world

        set_children_parent_and_keep_mx(children, self.value)

    def remove(self) -> None:
        """Remove offset empty if it exists."""
        if self.value is not None:
            clear_children_parent_and_keep_mx(self.value)
            bpy.data.objects.remove(self.value, do_unlink=True)
            self.value = None


class RadialScrewPivotPoint:
    def __init__(self, radial_screw: RadialScrew):
        self._radial_screw = radial_screw

    @property
    def co_world(self) -> Vector:
        """Get current pivot point coordinates."""
        axis_empty = self._radial_screw.axis_empty.value

        return axis_empty.matrix_world.to_translation()

    def _get_point_co_world(self, point: Union[str, Vector]) -> Vector:
        """Get point coordinates.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
        """
        context = self._radial_screw.context
        ob = self._radial_screw.object
        axis_empty = self._radial_screw.axis_empty.value

        if point == 'ORIGIN':
            return ob.matrix_world.to_translation()
        elif point == 'CURSOR':
            return Vector(context.scene.cursor.location.copy())
        elif point == 'MESH_SELECTION':
            return get_mesh_selection_co_world(context)
        elif point == 'ACTIVE_OBJECT':
            return context.view_layer.objects.active.matrix_world.to_translation()
        elif point == 'AXIS_EMPTY':
            return axis_empty.matrix_world.to_translation()
        else:
            return point

    def set(self, point: Union[str, Vector]) -> None:
        """Change pivot point location.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
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
            set_origin(context, ob, point_co)

    def _set_top_radial_screw_pivot_point(self, point_co: Vector) -> None:
        """Set object origin location keeping pivot points of object radial screws and refresh all radial screws."""
        context = self._radial_screw.context
        ob = self._radial_screw.object
        axis_empty = self._radial_screw.axis_empty.value

        if ob.parent == axis_empty:
            axis_empty.matrix_world.translation = point_co
            set_origin(context, ob, point_co)
        else:
            set_origin(context, ob, point_co)
            axis_empty.matrix_world.translation = point_co

        self._radial_screw.refresh()

    def _set_child_radial_screw_pivot_point(self, point_co: Vector) -> None:
        """Set center empty location and refresh radial screw."""
        axis_empty = self._radial_screw.axis_empty.value

        axis_empty.matrix_world.translation = point_co
        self._radial_screw.refresh()
