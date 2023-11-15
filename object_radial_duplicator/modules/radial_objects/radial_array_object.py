from math import radians
from typing import Union, Optional

import bpy
import numpy as np
from bpy.types import ArrayModifier
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
from ..utils.object_data import get_data_center_co_world
from ..utils.object_data import get_mesh_selection_co_world
from ..radial_objects.radial_array_builder import new_nodes_mod
from ..radial_objects.radial_array_builder import new_center_empty
from ..radial_objects.radial_array_builder import RadialArrayDirector


class ObjectRadialArrays:
    """Class for getting or controlling RadialArrays on object"""
    def __init__(self, context: Context, ob: Object):
        self.context: Context = context
        self.object: Object = ob
        self.value: list["RadialArray"] = self._get_radial_arrays()

    def _get_radial_arrays(self) -> list["RadialArray"]:
        ob_mods = self.object.modifiers
        radial_array_modifier_names = [mod.name for mod in ob_mods if mod.type == 'ARRAY' and "Radial" in mod.name]
        radial_arrays = [RadialArray.from_modifier(self, name) for name in radial_array_modifier_names]
        return radial_arrays

    def __getitem__(self, key: Union[str, int]) -> Optional["RadialArray"]:
        """Get radial array from class dict or create it from modifier and add to class dict."""
        if type(key) is str:
            names = [radial_array.name for radial_array in self.value]
            if key in names:
                i = names.index(key)
                radial_array = self.value[i]
            else:
                radial_array = None

        elif type(key) is int:
            # https://stackoverflow.com/questions/2492087/how-to-get-the-nth-element-of-a-python-list-or-a-default-if-not-available # noqa
            radial_array = (
                self.value[key]
                if -len(self.value) <= key < len(self.value)
                else None
            )
        else:
            raise TypeError("key is invalid")

        return radial_array

    def new(self) -> "RadialArray":
        """Build new radial array and store it in class dict."""
        radial_array = RadialArray.new(self)

        self.value.append(radial_array)
        return radial_array

    def refresh_all(self) -> None:
        """Refresh all object radial arrays."""
        for radial_array in self.value:
            radial_array.refresh()

    def ensure_center_empties_of_child_radial_arrays(self) -> None:
        """Add center empty to non-top radial arrays if it's missing."""
        for radial_array in self.value[:-1]:
            radial_array.center_empty.ensure()

    def remove_center_empty_of_top_radial_array(self) -> None:
        """Remove center_empty of top radial array and set radial array pivot to object origin."""
        context = self.context
        ob = self.object

        if self.value:
            radial_array = self.value[-1]
            center_empty = radial_array.center_empty.value
            if center_empty is not None:
                co = center_empty.matrix_world.to_translation()
                radial_array.center_empty.remove()
                self.ensure_center_empties_of_child_radial_arrays()
                set_origin(context, ob, co)
                self.refresh_all()


class RadialArray:
    @classmethod
    def from_modifier(cls, object_radial_arrays: ObjectRadialArrays, array_modifier_name: str = ""):
        return RadialArrayDirector(cls, object_radial_arrays).build_from_modifier(array_modifier_name)

    @classmethod
    def new(cls, object_radial_arrays: ObjectRadialArrays):
        return RadialArrayDirector(cls, object_radial_arrays).build_new()

    def __init__(
        self,
        siblings: "ObjectRadialArrays",
        name: str,
        array_modifier: ArrayModifier,
        nodes_modifier: Optional[NodesModifier],
        center_empty: Optional[Object],
        offset_empty: Object,
    ):
        self.siblings: "ObjectRadialArrays" = siblings
        self.name: str = name
        self.context: Context = siblings.context
        self.object: Object = siblings.object
        self.properties = RadialArrayProps(self)
        self.array_modifier = RadialArrayArrayMod(self, array_modifier)
        self.nodes_modifier = RadialArrayNodesMod(self, nodes_modifier)
        self.center_empty = RadialArrayCenterEmpty(self, center_empty)
        self.offset_empty = RadialArrayOffsetEmpty(self, offset_empty)
        self.pivot_point = RadialArrayPivotPoint(self)

    @property
    def spin_vec_object(self):
        ob = self.object
        props = self.properties

        # Get new spin orientation from operator attributes on properties update,
        # but use last spin orientation for refreshing.
        # Last orientation is stored in object space.
        # Storing it in global space wouldn't allow radial array to be properly
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
        count: int,
        radius_offset: float,
        start_angle: float,
        end_angle: float,
        height_offset: float,
        pivot_point: Optional[Union[str, Vector]] = None
    ) -> None:
        """Spin radial array and change pivot point.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        :param spin_axis: Axis along which spin will be performed in ['X', 'Y', 'Z'].
        :param count: Total number of duplicates to make in [1, inf].
        :param radius_offset: Moves each duplicate a user-defined distance from the pivot point in [-inf, inf].
        :param start_angle: Rotation placement for the first duplicated geometry in radians in [-inf, inf].
        :param end_angle: Rotation placement for the last duplicated geometry in radians in [-inf, inf].
        :param height_offset: Moves each successive duplicate a user-defined distance from the previous
        duplicate in [-inf, inf].
        :param pivot_point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector', None].
        """
        self.properties.update(spin_orientation, spin_axis, count, radius_offset, start_angle, end_angle, height_offset)
        if pivot_point is not None:
            self.set_pivot_point(pivot_point)
        else:
            self.refresh()

    def refresh(self) -> None:
        """Spin radial array not changing its parameters."""
        if self.object.type == 'MESH':
            self.nodes_modifier.refresh()
        self.array_modifier.refresh()
        self.offset_empty.refresh()

    def set_pivot_point(self, point: Union[str, Vector]) -> None:
        """Set pivot point and refresh radial array.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
        """
        RadialArrayPivotPoint(self).set(point)

    def apply(self) -> str:
        """Apply modifiers, remove empties and properties."""
        self.center_empty.remove()
        self.properties.remove()
        self.nodes_modifier.apply()
        success_msg = self.array_modifier.apply()
        self.offset_empty.remove()
        self.siblings.value.remove(self)
        self.siblings.remove_center_empty_of_top_radial_array()
        return success_msg

    def remove(self) -> None:
        """Remove modifiers, empties and properties."""
        self.center_empty.remove()
        self.properties.remove()
        self.nodes_modifier.remove()
        self.array_modifier.remove()
        self.offset_empty.remove()
        self.siblings.value.remove(self)
        self.siblings.remove_center_empty_of_top_radial_array()


class RadialArrayProps:
    def __init__(self, radial_array: RadialArray):
        self._radial_array = radial_array

    @property
    def value(self) -> "properties.RadialArrayPropsGroup":
        # Re-allocation can lead to crashes (e.g. if you add a lot of items to some Collection, this can lead
        # to re-allocating the underlying container’s memory, invalidating all previous references to existing items).
        # So, don't store collection item and retrieve it by a name instead.

        ob = self._radial_array.object
        name = self._radial_array.name

        return ob.radial_duplicator.arrays.get(name)

    def _get_spin_orientation_matrix(self, spin_orientation: str) -> Matrix:
        """Get spin orientation matrix in world space.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        """
        context = self._radial_array.context
        ob = self._radial_array.object

        return {
            'GLOBAL': lambda: Matrix.Identity(4),
            'LOCAL': lambda: ob.matrix_world.copy(),
            'VIEW': lambda: context.space_data.region_3d.view_matrix.inverted(),
            'NORMAL': lambda: get_normal_matrix(context, ob),
        }[spin_orientation]()

    def update(self,
               spin_orientation: str,
               spin_axis: str,
               count: int,
               radius_offset: float,
               start_angle: float,
               end_angle: float,
               height_offset: float) -> None:
        """Update property group."""
        ob = self._radial_array.object

        spin_orientation_enums = self.value.bl_rna.properties["spin_orientation"].enum_items
        self.value["spin_orientation"] = spin_orientation_enums.find(spin_orientation)
        spin_orientation_matrix = self._get_spin_orientation_matrix(spin_orientation)
        spin_orientation_matrix_object = ob.matrix_world.inverted() @ spin_orientation_matrix

        # noinspection PyTypeChecker
        self.value["spin_orientation_matrix_object"] = np.array(spin_orientation_matrix_object).T.ravel()
        spin_axis_enums = self.value.bl_rna.properties["spin_axis"].enum_items
        self.value["spin_axis"] = spin_axis_enums.find(spin_axis)
        self.value["count"] = count
        self.value["radius_offset"] = radius_offset
        self.value["start_angle"] = start_angle
        self.value["end_angle"] = end_angle
        self.value["height_offset"] = height_offset

    def remove(self) -> None:
        """Remove property group if it exists."""
        ob = self._radial_array.object
        name = self._radial_array.name

        props_id = ob.radial_duplicator.arrays.find(name)
        if props_id is not None:
            ob.radial_duplicator.arrays.remove(props_id)


class RadialArrayArrayMod:
    def __init__(self, radial_array: RadialArray, value: ArrayModifier):
        self._radial_array = radial_array
        self.value = value

    def refresh(self) -> None:
        props = self._radial_array.properties.value
        spin_vec_object = self._radial_array.spin_vec_object

        self.value.count = props.count
        self.value.use_constant_offset = True
        height_offset_vec = spin_vec_object.normalized() * props.height_offset
        self.value.constant_offset_displace = height_offset_vec

    def apply(self) -> str:
        """Apply array modifier if it exists and return success message confirmation."""
        ob = self._radial_array.object
        context = self._radial_array.context

        message = (
            "Applied modifier was not first, result may not be as expected"
            if ob.modifiers.find(self.value.name) > 0
            else ""
        )
        with context.temp_override(object=ob):
            bpy.ops.object.modifier_apply(modifier=self.value.name)
        self.value = None
        return message

    def remove(self) -> None:
        """Remove array modifier if it exists."""
        ob = self._radial_array.object

        ob.modifiers.remove(self.value)
        self.value = None


class RadialArrayNodesMod:
    def __init__(self, radial_array: RadialArray, value: Optional[NodesModifier]):
        self._radial_array = radial_array
        self.value = value

    @property
    def displace_offset_vec_object(self) -> Vector:
        """Get displace vector in ob space."""
        ob = self._radial_array.object
        props = self._radial_array.properties.value
        pivot_point_co = self._radial_array.pivot_point.co_world
        spin_vec_object = self._radial_array.spin_vec_object

        if props.radius_offset == 0:
            return Vector((0, 0, 0))
        else:
            pivot_mx = ob.matrix_world.copy()
            pivot_mx.translation = pivot_point_co
            data_center_co_pivot = pivot_mx.inverted() @ get_data_center_co_world(ob)

            non_aligned_displace_vec = (
                Vector((1, 1, 1)) if data_center_co_pivot.length_squared < 0.001 else data_center_co_pivot
            )

            projection = non_aligned_displace_vec.project(spin_vec_object)
            rejection = non_aligned_displace_vec - projection

            aligned_displace_vec_local = rejection.normalized()
            displace_offset_vec = aligned_displace_vec_local * props.radius_offset
            return displace_offset_vec

    def _get_start_rotation_matrix(self) -> Euler:
        """Get object rotation to achieve radial array starting rotation."""
        props = self._radial_array.properties.value
        spin_vec_object = self._radial_array.spin_vec_object

        # noinspection PyArgumentList
        return (
            Euler((0, 0, 0))
            if props.start_angle == 0
            else Matrix.Rotation(props.start_angle, 4, spin_vec_object).to_euler()
        )

    def refresh(self) -> None:
        start_rotation = self._get_start_rotation_matrix()
        displace_offset_vec = self.displace_offset_vec_object
        ob = self._radial_array.object
        center_empty = self._radial_array.center_empty.value

        if start_rotation[:] != (0, 0, 0) or displace_offset_vec[:] != (0, 0, 0):

            if self.value is None:
                self.add()

            node_group = self.value.node_group
            node = node_group.nodes["StartRotation"]
            node.inputs["Rotation"].default_value = start_rotation[:]
            node = node_group.nodes["RadiusOffset"]
            node.inputs["Translation"].default_value = displace_offset_vec[:]

            if center_empty is not None:
                center_empty_mx = center_empty.matrix_world
                center_empty_mx_ob = ob.matrix_world.inverted() @ center_empty_mx

                node = node_group.nodes["ObjectPivotToRadialArrayCenter"]
                node.inputs["Translation"].default_value = center_empty_mx_ob.inverted().to_translation()

                node = node_group.nodes["RestoreObjectPivot"]
                node.inputs["Translation"].default_value = center_empty_mx_ob.to_translation()

            else:
                node = node_group.nodes["ObjectPivotToRadialArrayCenter"]
                node.inputs["Translation"].default_value = (0, 0, 0)

                node = node_group.nodes["RestoreObjectPivot"]
                node.inputs["Translation"].default_value = (0, 0, 0)
        else:
            self.remove()

    def add(self) -> None:
        """Add nodes modifier."""
        name = self._radial_array.name
        ob = self._radial_array.object
        array_mod = self._radial_array.array_modifier.value
        props = self._radial_array.properties.value

        self.value = new_nodes_mod(ob, array_mod, props, name)

    def apply(self) -> None:
        """Apply nodes modifier if it exists."""
        if self.value is not None:
            ob = self._radial_array.object
            context = self._radial_array.context

            with context.temp_override(object=ob):
                bpy.ops.object.modifier_apply(modifier=self.value.name)
            self.value = None

    def remove(self) -> None:
        """Remove nodes modifier if it exists."""
        if self.value is not None:
            ob = self._radial_array.object
            node_group = self.value.node_group
            if node_group is not None:
                bpy.data.node_groups.remove(node_group, do_unlink=True)
            ob.modifiers.remove(self.value)
            self.value = None
            self._radial_array.nodes_modifier.value = None


class RadialArrayCenterEmpty:
    def __init__(self, radial_array: RadialArray, value: Optional[Object]):
        self._radial_array = radial_array
        self.value = value

    def ensure(self) -> None:
        """Add center empty if it's missing."""
        context = self._radial_array.context
        ob = self._radial_array.object
        props = self._radial_array.properties.value

        if self.value is None:
            self.value = new_center_empty(context, ob, props)

    def remove(self) -> None:
        """Remove center empty if it exists."""
        if self.value is not None:
            props = self._radial_array.properties.value

            clear_children_parent_and_keep_mx(self.value)
            bpy.data.objects.remove(self.value, do_unlink=True)
            self.value = None

            if props is not None:
                props["center_empty"] = None


class RadialArrayOffsetEmpty:
    def __init__(self, radial_array: RadialArray, value: Optional[Object]):
        self._radial_array = radial_array
        self.value = value

    def refresh(self) -> None:
        """Rotate offset empty across pivot point."""
        ob = self._radial_array.object
        props = self._radial_array.properties.value
        pivot_point_co_world = self._radial_array.pivot_point.co_world
        spin_vec_object = self._radial_array.spin_vec_object
        spin_vec_world = spin_vec_object @ ob.matrix_world.inverted()

        if props.count > 1:
            # calculate angle
            full_circle = (
                round(props.end_angle, 5) == round(radians(360), 5)
                and props.start_angle == 0
                and props.height_offset == 0
            )
            if full_circle:
                spin_angle = props.end_angle / props.count - props.start_angle / (props.count - 1)
            else:
                spin_angle = props.end_angle / (props.count - 1) - props.start_angle / (props.count - 1)

            # transform
            children = self.value.children
            clear_children_parent_and_keep_mx(self.value)

            if self.value.parent == ob:
                # pivot point in object space
                pivot_point_co_object = ob.matrix_world.inverted() @ pivot_point_co_world
                # reset offset empty matrix
                self.value.matrix_parent_inverse.identity()
                self.value.matrix_basis.identity()
                # move offset empty to object origin
                tra = Matrix.Translation(Vector((0, 0, 0)))
                # rotation of offset empty around radial array pivot. offset empty starts in object origin
                rot = (
                    Matrix.Translation(pivot_point_co_object)
                    @ Matrix.Rotation(spin_angle, 4, spin_vec_object)
                    @ Matrix.Translation(-pivot_point_co_object)
                )
                # (1, 1, 1) scale
                sca = Matrix.Diagonal(Matrix.Identity(4).to_scale().to_4d())
                # compose matrix
                self.value.matrix_basis = tra @ rot @ sca
            else:
                # align with object
                self.value.matrix_world = ob.matrix_world
                # rotation of offset empty around radial array pivot. offset empty starts in object origin
                rot = (
                    Matrix.Translation(pivot_point_co_world)
                    @ Matrix.Rotation(spin_angle, 4, spin_vec_world)
                    @ Matrix.Translation(-pivot_point_co_world)
                )
                # apply rotation
                self.value.matrix_world = rot @ self.value.matrix_world

            set_children_parent_and_keep_mx(children, self.value)

    def remove(self) -> None:
        """Remove offset empty if it exists."""
        if self.value is not None:
            clear_children_parent_and_keep_mx(self.value)
            bpy.data.objects.remove(self.value, do_unlink=True)
            self.value = None


class RadialArrayPivotPoint:
    def __init__(self, radial_array: RadialArray):
        self._radial_array = radial_array

    @property
    def co_world(self) -> Vector:
        """Get current pivot point coordinates."""
        ob = self._radial_array.object
        center_empty = self._radial_array.center_empty.value

        return (
            center_empty.matrix_world.to_translation()
            if center_empty is not None
            else ob.matrix_world.to_translation()
        )

    def _get_point_co_world(self, point: Union[str, Vector]) -> Vector:
        """Get point coordinates.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
        """
        context = self._radial_array.context
        ob = self._radial_array.object
        center_empty = self._radial_array.center_empty.value

        if point == 'ORIGIN':
            return ob.matrix_world.to_translation()
        elif point == 'CURSOR':
            return Vector(context.scene.cursor.location.copy())
        elif point == 'MESH_SELECTION':
            return get_mesh_selection_co_world(context)
        elif point == 'ACTIVE_OBJECT':
            return context.view_layer.objects.active.matrix_world.to_translation()
        elif point == 'CENTER_EMPTY':
            return center_empty.matrix_world.to_translation()
        else:
            return point

    def set(self, point: Union[str, Vector]) -> None:
        """Change pivot point location.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
        """
        context = self._radial_array.context
        ob = self._radial_array.object
        siblings = self._radial_array.siblings

        if point == 'ORIGIN':
            self._radial_array.center_empty.remove()
            self._radial_array.refresh()
        else:
            point_co = self._get_point_co_world(point)

            if siblings.value:
                if siblings.value[-1] == self._radial_array:
                    self._set_top_radial_array_pivot_point(point_co)
                else:
                    self._set_child_radial_array_pivot_point(point_co)
            else:
                set_origin(context, ob, point_co)

    def _set_top_radial_array_pivot_point(self, point_co: Vector) -> None:
        """Set object origin location keeping pivot points of object radial arrays and refresh all radial arrays."""
        context = self._radial_array.context
        ob = self._radial_array.object
        siblings = self._radial_array.siblings

        self._radial_array.center_empty.remove()
        siblings.ensure_center_empties_of_child_radial_arrays()
        set_origin(context, ob, point_co)
        siblings.refresh_all()

    def _set_child_radial_array_pivot_point(self, point_co: Vector) -> None:
        """Set center empty location and refresh radial array."""
        self._radial_array.center_empty.ensure()
        self._radial_array.center_empty.value.matrix_world.translation = point_co
        self._radial_array.refresh()
