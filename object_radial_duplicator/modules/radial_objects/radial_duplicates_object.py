from typing import Union, Optional

import random
from math import radians

import bpy
import numpy as np
from bpy.types import Context
from bpy.types import Object
from mathutils import Matrix
from mathutils import Vector

from .. import properties
from ..utils.math import get_axis_vec
from ..utils.object import clear_children_parent_and_keep_mx
from ..utils.object import get_normal_matrix
from ..utils.object import set_children_parent_and_keep_mx, set_parent_and_keep_mx
from ..utils.object_data import get_mesh_selection_co_world
from ..radial_objects.radial_duplicates_builder import RadialDuplicatesDirector


class RadialDuplicates:
    @classmethod
    def from_props(cls, context: Context, props: "properties.RadialDuplicatesPropsGroup"):
        return RadialDuplicatesDirector(cls, context).build_from_props(props)

    @classmethod
    def new(cls, context: Context, starting_ob: Object):
        return RadialDuplicatesDirector(cls, context).build_new(starting_ob)

    def __init__(
            self,
            context: Context,
            starting_ob: Object,
            center_empty: Object,
            dupli_obs,
    ):
        self.context: Context = context
        self.starting_object = RadialDuplicatesStartingObject(self, starting_ob)
        self.duplicated_objects = RadialDuplicatesDuplicatedObjects(self, dupli_obs)
        self.properties = RadialDuplicatesProps(self)
        self.center_empty = RadialDuplicatesCenterEmpty(self, center_empty)
        self.pivot_point = RadialDuplicatesPivotPoint(self)

    @property
    def spin_vec_object(self):
        center_empty = self.center_empty.value
        props = self.properties

        # Get new spin orientation from operator attributes on properties update,
        # but use last spin orientation for refreshing.
        # Last orientation is stored in object space.
        # Storing it in global space wouldn't allow radial duplicates to be properly
        # restored if object has been rotated since then.
        spin_orientation_matrix_world = center_empty.matrix_world @ props.value.spin_orientation_matrix_object
        spin_axis = props.value.spin_axis
        spin_vec_world = get_axis_vec(spin_axis, spin_orientation_matrix_world)
        spin_vec_object = spin_vec_world @ center_empty.matrix_world

        return spin_vec_object

    def modify(
        self,
        spin_orientation: str,
        spin_axis: str,
        duplicates_rotation: str,
        count: int,
        end_angle: float,
        end_scale: float,
        height_offset: float,
        pivot_point: Optional[Union[str, Vector]] = None,
    ) -> None:
        """Spin radial duplicates and change pivot point.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        :param spin_axis: Axis along which spin will be performed in ['X', 'Y', 'Z'].
        :param duplicates_rotation: Rotation of duplicated objects around their own origin in
        ['FOLLOW', 'KEEP', 'RANDOM'].
        :param count: Total number of duplicates to make in [1, inf].
        :param end_angle: Rotation placement for the last duplicated geometry in radians in [-inf, inf].
        :param end_scale: Scale of the last duplicated geometry in [0.001, inf].
        :param height_offset: Moves each successive duplicate a user-defined distance from the previous
        duplicate in [-inf, inf].
        :param pivot_point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector', None].
        """
        self.properties.update(spin_orientation, spin_axis, duplicates_rotation, count, end_angle, end_scale,
                               height_offset)
        if pivot_point is not None:
            self.set_pivot_point(pivot_point)
        else:
            self.refresh()

    def refresh(self) -> None:
        """Spin radial duplicates not changing its parameters."""
        self.starting_object.refresh()
        self.duplicated_objects.refresh()

    def set_pivot_point(self, point: Union[str, Vector]) -> None:
        """Set pivot point and refresh radial duplicates.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
        """
        RadialDuplicatesPivotPoint(self).set(point)
        self.center_empty.refresh()

    def remove(self) -> None:
        """Remove modifiers, empties and properties."""
        self.duplicated_objects.remove()
        self.center_empty.remove()


class RadialDuplicatesProps:
    def __init__(self, radial_duplicates: RadialDuplicates):
        self._radial_duplicates = radial_duplicates

    @property
    def value(self) -> "properties.RadialDuplicatesPropsGroup":
        # Re-allocation can lead to crashes (e.g. if you add a lot of items to some Collection, this can lead
        # to re-allocating the underlying container’s memory, invalidating all previous references to existing items).
        # So, don't store collection item and retrieve it by a name instead

        center_empty = self._radial_duplicates.center_empty.value
        return center_empty.radial_duplicator.duplicates[0]

    def _get_spin_orientation_matrix(self, spin_orientation: str) -> Matrix:
        """Get spin orientation matrix in world space.

        :param spin_orientation: Spin orientation in ['GLOBAL', 'LOCAL', 'VIEW', 'NORMAL'].
        """
        context = self._radial_duplicates.context
        starting_object = self._radial_duplicates.starting_object.value

        return {
            'GLOBAL': lambda: Matrix.Identity(4),
            'LOCAL': lambda: starting_object.matrix_world.copy(),
            'VIEW': lambda: context.space_data.region_3d.view_matrix.inverted(),
            'NORMAL': lambda: get_normal_matrix(context, starting_object),
        }[spin_orientation]()

    def update(self,
               spin_orientation: str,
               spin_axis: str,
               duplicates_rotation: str,
               count: int,
               end_angle: float,
               end_scale: float,
               height_offset: float) -> None:
        """Update property group."""
        center_empty = self._radial_duplicates.center_empty.value

        spin_orientation_enums = self.value.bl_rna.properties["spin_orientation"].enum_items
        self.value["spin_orientation"] = spin_orientation_enums.find(spin_orientation)
        spin_orientation_matrix = self._get_spin_orientation_matrix(spin_orientation)
        spin_orientation_matrix_object = center_empty.matrix_world.inverted() @ spin_orientation_matrix

        self.value["spin_orientation_matrix_object"] = np.array(spin_orientation_matrix_object).T.ravel()
        spin_axis_enums = self.value.bl_rna.properties["spin_axis"].enum_items
        self.value["spin_axis"] = spin_axis_enums.find(spin_axis)
        duplicates_rotation_enums = self.value.bl_rna.properties["duplicates_rotation"].enum_items
        self.value["duplicates_rotation"] = duplicates_rotation_enums.find(duplicates_rotation)
        self.value["count"] = count
        self.value["end_angle"] = end_angle
        self.value["end_scale"] = end_scale
        self.value["height_offset"] = height_offset

    def remove(self) -> None:
        """Remove property group if it exists."""
        ob = self._radial_duplicates.starting_object.value

        ob.radial_duplicator.duplicates.clear()


class RadialDuplicatesStartingObject:
    def __init__(self, radial_duplicates: RadialDuplicates, value: Optional[Object]):
        self._radial_duplicates = radial_duplicates
        self.value = value

    def _set_parent(self):
        center_empty = self._radial_duplicates.center_empty.value

        set_parent_and_keep_mx(self.value, center_empty)

    def refresh(self) -> None:
        self._set_parent()


class RadialDuplicatesDuplicatedObjects:
    def __init__(self, radial_duplicates: RadialDuplicates, value: Optional[Object]):
        self._radial_duplicates = radial_duplicates
        self.value = value

    def _set_count(self):
        starting_ob = self._radial_duplicates.starting_object.value
        props = self._radial_duplicates.properties.value
        context = self._radial_duplicates.context

        if context.view_layer.objects.active in self.value:
            context.view_layer.objects.active = starting_ob
            for ob in context.selected_objects:
                ob.select_set(False)
            starting_ob.select_set(True)
            context.view_layer.objects.active = starting_ob

        for ob in self.value:
            if ob != starting_ob:
                clear_children_parent_and_keep_mx(ob)
                bpy.data.objects.remove(ob, do_unlink=True)
        self.value = []

        dupli_obs = []
        for i in range(props.count - 1):
            dupli_ob = starting_ob.copy()
            starting_ob.users_collection[0].objects.link(dupli_ob)
            dupli_obs.append(dupli_ob)

        # matrix_world of the newly created object updates after updating depsgraph
        context.evaluated_depsgraph_get().update()
        self.value = dupli_obs

    @property
    def displace_offset_vec_object(self) -> Vector:
        """Get displace vector in ob space."""
        props = self._radial_duplicates.properties.value
        pivot_point_co = self._radial_duplicates.pivot_point.co_world
        spin_vec_object = self._radial_duplicates.spin_vec_object
        starting_ob = self._radial_duplicates.starting_object.value
        center_empty = self._radial_duplicates.center_empty.value

        if props["radius"] == 0:
            return Vector((0, 0, 0))
        else:
            pivot_mx = center_empty.matrix_world.copy()
            pivot_mx.translation = pivot_point_co
            starting_ob_co_pivot = pivot_mx.inverted() @ starting_ob.matrix_world.to_translation()

            non_aligned_displace_vec = starting_ob_co_pivot

            projection = non_aligned_displace_vec.project(spin_vec_object)
            rejection = non_aligned_displace_vec - projection

            aligned_displace_vec_local = rejection.normalized()
            displace_offset_vec = aligned_displace_vec_local * props["radius"]
            return displace_offset_vec

    def _set_transforms(self):
        starting_ob = self._radial_duplicates.starting_object.value
        center_empty = self._radial_duplicates.center_empty.value
        props = self._radial_duplicates.properties.value
        pivot_point_co_world = self._radial_duplicates.pivot_point.co_world
        spin_vec_object = self._radial_duplicates.spin_vec_object
        spin_vec_world = spin_vec_object @ center_empty.matrix_world.inverted()

        if props.count > 1:
            # calculate angle
            full_circle = round(props.end_angle, 5) == round(radians(360), 5) and props.height_offset == 0
            if full_circle:
                step_angle = props.end_angle / props.count
            else:
                step_angle = props.end_angle / (props.count - 1)

            # calculate scale
            spaced_scale = np.linspace(1.0, props.end_scale, props.count)

            # transform
            for i, dupli_ob in enumerate(self.value, start=1):
                children = dupli_ob.children
                clear_children_parent_and_keep_mx(dupli_ob)

                # align with starting object
                dupli_ob.matrix_world = starting_ob.matrix_world
                dupli_ob.matrix_world.translation = (
                    dupli_ob.matrix_world.to_translation() + spin_vec_object.normalized() * props.height_offset * i
                )
                # rotation around spin axis
                rot = (
                    Matrix.Translation(pivot_point_co_world)
                    @ Matrix.Rotation(i * step_angle, 4, spin_vec_world)
                    @ Matrix.Translation(-pivot_point_co_world)
                )
                dupli_ob.matrix_world = rot @ dupli_ob.matrix_world

                # rotation around own axis
                match props.duplicates_rotation:
                    case 'KEEP':
                        R = starting_ob.matrix_world.to_3x3().normalized().to_4x4()
                        T = Matrix.Translation(dupli_ob.matrix_world.to_translation())
                        S = Matrix.Diagonal(dupli_ob.matrix_world.to_scale().to_4d())
                        dupli_ob.matrix_world = T @ R @ S
                    case 'RANDOM':
                        R = Matrix.Rotation(random.randrange(0, 360), 4, spin_vec_world)
                        T = Matrix.Translation(dupli_ob.matrix_world.to_translation())
                        S = Matrix.Diagonal(dupli_ob.matrix_world.to_scale().to_4d())
                        dupli_ob.matrix_world = T @ R @ S

                # scale
                scale_vec = Vector((spaced_scale[i],) * 3)
                sca = (
                    Matrix.Translation(dupli_ob.matrix_world.to_translation())
                    @ Matrix.Diagonal(scale_vec).to_4x4()
                    @ Matrix.Translation(-dupli_ob.matrix_world.to_translation())
                )
                dupli_ob.matrix_world = sca @ dupli_ob.matrix_world

                set_children_parent_and_keep_mx(children, dupli_ob)

    def _set_parent(self):
        center_empty = self._radial_duplicates.center_empty.value

        for ob in self.value:
            set_parent_and_keep_mx(ob, center_empty)

    def refresh(self) -> None:
        self._set_count()
        self._set_transforms()
        self._set_parent()

    def remove(self) -> None:
        for ob in self.value:
            clear_children_parent_and_keep_mx(ob)
            bpy.data.objects.remove(ob, do_unlink=True)
        self.value = []


class RadialDuplicatesCenterEmpty:
    def __init__(self, radial_duplicates: RadialDuplicates, value: Optional[Object]):
        self._radial_duplicates = radial_duplicates
        self.value = value

    def refresh(self) -> None:
        pivot_point_co_world = self._radial_duplicates.pivot_point.co_world
        self.value.matrix_world.translation = pivot_point_co_world

    def remove(self) -> None:
        """Remove center empty."""
        clear_children_parent_and_keep_mx(self.value)
        bpy.data.objects.remove(self.value, do_unlink=True)
        self.value = None


class RadialDuplicatesPivotPoint:
    def __init__(self, radial_duplicates: RadialDuplicates):
        self._radial_duplicates = radial_duplicates

    @property
    def co_world(self) -> Vector:
        """Get current pivot point coordinates."""
        center_empty = self._radial_duplicates.center_empty.value

        return center_empty.matrix_world.to_translation()

    def _get_point_co_world(self, point: Union[str, Vector]) -> Vector:
        """Get point coordinates.

        :param point: Point in ['ORIGIN', 'CURSOR', 'MESH_SELECTION', 'ACTIVE_OBJECT', 'Vector'].
        """
        context = self._radial_duplicates.context
        starting_ob = self._radial_duplicates.starting_object.value
        center_empty = self._radial_duplicates.center_empty.value

        if point == 'ORIGIN':
            return starting_ob.matrix_world.to_translation()
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
        center_empty = self._radial_duplicates.center_empty.value

        children = center_empty.children
        clear_children_parent_and_keep_mx(center_empty)

        point_co = self._get_point_co_world(point)
        center_empty.matrix_world.translation = point_co

        set_children_parent_and_keep_mx(children, center_empty)
        self._radial_duplicates.refresh()
