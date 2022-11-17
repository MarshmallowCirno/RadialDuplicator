from typing import Optional

import bpy
from bpy.types import Context
from bpy.types import Object

from .. import properties
from ..utils.object import copy_collections
from ..utils.object import copy_local_view_state


def find_center_empty(props: "properties.RadialDuplicatesPropsGroup") -> Optional[Object]:
    """Find center empty from radial array properties."""
    center_empty = props.id_data
    return center_empty


def find_starting_ob(props: "properties.RadialDuplicatesPropsGroup") -> Optional[Object]:
    """Find center empty from radial array properties."""
    starting_ob = props["starting_object"]
    return starting_ob


def new_center_empty(context: Context, starting_ob: Object) -> Object:
    """Add a new center empty and return it."""
    center_empty = bpy.data.objects.new("RadialDuplicatesEmpty", None)
    center_empty.empty_display_type = 'SPHERE'
    copy_collections(starting_ob, center_empty)
    copy_local_view_state(context, center_empty)
    # matrix_world of the newly created object updates after updating depsgraph
    context.evaluated_depsgraph_get().update()
    return center_empty


def new_props(center_empty: Object, starting_ob: Object) -> "properties.RadialDuplicatesPropsGroup":
    """Add a new radial array property group and return it."""
    props = center_empty.radial_duplicator.duplicates.add()
    props["starting_object"] = starting_ob
    return props


class ExistingRadialDuplicatesBuilder:
    @staticmethod
    def get_center_empty(props: "properties.RadialDuplicatesPropsGroup") -> Object:
        return find_center_empty(props)

    @staticmethod
    def get_starting_ob(props: "properties.RadialDuplicatesPropsGroup", children) -> Object:
        starting_ob = find_starting_ob(props)
        if starting_ob is None:
            starting_ob = children[0]
        return starting_ob


class NewRadialDuplicatesBuilder:
    @staticmethod
    def get_center_empty(context: Context, starting_ob: Object) -> Object:
        return new_center_empty(context, starting_ob)

    @staticmethod
    def get_props(center_empty: Object, starting_ob: Object) -> "properties.RadialDuplicatesPropsGroup":
        return new_props(center_empty, starting_ob)


class RadialDuplicatesDirector:
    def __init__(self, cls, context: Context):
        self.cls = cls
        self.context = context

    def build_from_props(self, props: "properties.RadialDuplicatesPropsGroup"):
        builder = ExistingRadialDuplicatesBuilder()

        context = self.context

        center_empty = builder.get_center_empty(props)
        starting_ob = builder.get_starting_ob(props, center_empty.children)
        dupli_obs = [ob for ob in center_empty.children if ob != starting_ob]

        return self.cls(context, starting_ob, center_empty, dupli_obs)

    def build_new(self, starting_ob: Object):
        builder = NewRadialDuplicatesBuilder()

        context = self.context

        center_empty = builder.get_center_empty(context, starting_ob)
        builder.get_props(center_empty, starting_ob)
        dupli_obs = center_empty.children

        return self.cls(context, starting_ob, center_empty, dupli_obs)
