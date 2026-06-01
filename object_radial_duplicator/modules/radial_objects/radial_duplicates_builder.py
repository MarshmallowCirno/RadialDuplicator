from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

import bpy

from ... import addon_info
from .. import properties
from ..utils import object_utils

if TYPE_CHECKING:
    from . import radial_duplicates_object


def find_center_empty(props: properties.RadialDuplicatesPropsGroup) -> bpy.types.Object:
    """Find center empty from radial array properties."""
    center_empty = cast(bpy.types.Object, props.id_data)
    return center_empty


def find_starting_ob(props: properties.RadialDuplicatesPropsGroup) -> bpy.types.Object | None:
    """Find center empty from radial array properties."""
    starting_ob = props["starting_object"]
    return starting_ob


def new_center_empty(context: bpy.types.Context, starting_ob: bpy.types.Object) -> bpy.types.Object:
    """Add a new center empty and return it."""
    center_empty = bpy.data.objects.new(name="RadialDuplicatesEmpty", object_data=None)
    center_empty.empty_display_type = 'SPHERE'
    if addon_info.get_preferences().move_empties_to_collection:
        empties_collection = addon_info.get_preferences().empties_collection
        object_utils.move_to_collection(empties_collection, center_empty)
    else:
        object_utils.copy_collections(starting_ob, center_empty)
        object_utils.copy_local_view_state(context, center_empty)
    # matrix_world of the newly created object updates after updating depsgraph
    context.evaluated_depsgraph_get().update()
    return center_empty


def new_props(center_empty: bpy.types.Object, starting_ob: bpy.types.Object) -> properties.RadialDuplicatesPropsGroup:
    """Add a new radial array property group and return it."""
    props_collection = cast(properties.RadialCollections, center_empty.radial_duplicator)  # pyright: ignore[reportAttributeAccessIssue]

    props = props_collection.duplicates.add()
    props["starting_object"] = starting_ob
    return props


def fix_center_empty(starting_ob: bpy.types.Object, center_empty: bpy.types.Object | None) -> None:
    """Set correct center empty collections."""
    if center_empty is not None:
        if not center_empty.users_collection:
            if addon_info.get_preferences().move_empties_to_collection:
                empties_collection = addon_info.get_preferences().empties_collection
                object_utils.move_to_collection(empties_collection, center_empty)
            else:
                object_utils.copy_collections(starting_ob, center_empty)


def fix_starting_ob(starting_ob: bpy.types.Object, center_empty: bpy.types.Object) -> None:
    """Set correct starting object collections."""
    if not starting_ob.users_collection:
        object_utils.copy_collections(center_empty, starting_ob)


class ExistingRadialDuplicatesBuilder:
    @staticmethod
    def get_center_empty(props: properties.RadialDuplicatesPropsGroup) -> bpy.types.Object:
        return find_center_empty(props)

    @staticmethod
    def get_starting_ob(
        props: properties.RadialDuplicatesPropsGroup, children: Sequence[bpy.types.Object]
    ) -> bpy.types.Object:
        starting_ob = find_starting_ob(props)
        if starting_ob is None:
            starting_ob = children[0]
        return starting_ob


class NewRadialDuplicatesBuilder:
    @staticmethod
    def get_center_empty(context: bpy.types.Context, starting_ob: bpy.types.Object) -> bpy.types.Object:
        return new_center_empty(context, starting_ob)

    @staticmethod
    def get_props(
        center_empty: bpy.types.Object, starting_ob: bpy.types.Object
    ) -> properties.RadialDuplicatesPropsGroup:
        return new_props(center_empty, starting_ob)


class RadialDuplicatesDirector[T: "radial_duplicates_object.RadialDuplicates"]:
    def __init__(self, cls: type[T], context: bpy.types.Context) -> None:
        self.cls = cls
        self.context = context

    def build_from_props(self, props: properties.RadialDuplicatesPropsGroup) -> T:
        builder = ExistingRadialDuplicatesBuilder()

        center_empty = builder.get_center_empty(props)
        children = center_empty.children
        starting_ob = builder.get_starting_ob(props, children)
        dupli_obs = [ob for ob in center_empty.children if ob != starting_ob]

        fix_center_empty(starting_ob, center_empty)
        fix_starting_ob(starting_ob, center_empty)

        return self.cls(self.context, starting_ob, center_empty, dupli_obs)

    def build_new(self, starting_ob: bpy.types.Object) -> T:
        builder = NewRadialDuplicatesBuilder()

        center_empty = builder.get_center_empty(self.context, starting_ob)
        builder.get_props(center_empty, starting_ob)
        dupli_obs = center_empty.children

        return self.cls(self.context, starting_ob, center_empty, dupli_obs)
