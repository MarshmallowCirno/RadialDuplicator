from collections.abc import Sequence
from typing import Literal

import bmesh
import bpy
import mathutils

from ..utils import object_data_utils


def get_normal_matrix(context: bpy.types.Context, ob: bpy.types.Object) -> mathutils.Matrix:
    """Get normal matrix of selection."""
    assert isinstance(ob.data, (bpy.types.Mesh, bpy.types.Curve))

    if ob.mode == 'EDIT' and not object_data_utils.is_data_selected(ob.data):
        return ob.matrix_world.copy()
    else:
        active_slot = context.scene.transform_orientation_slots[0]
        if active_slot.custom_orientation is not None:
            bak_slot_name = active_slot.custom_orientation.name
        else:
            bak_slot_name = None
        bak_slot_type = active_slot.type
        bpy.ops.transform.create_orientation(name='RADIAL_DUPLICATOR', use=True, overwrite=True)
        custom_orientation = active_slot.custom_orientation
        assert custom_orientation is not None
        custom_orientation_mx = custom_orientation.matrix.copy().to_4x4()
        bpy.ops.transform.delete_orientation()
        if bak_slot_name != 'RADIAL_DUPLICATOR':
            active_slot.type = bak_slot_type
        return custom_orientation_mx


def copy_collections(master_ob: bpy.types.Object, ob: bpy.types.Object) -> None:
    """Copy collections from one object to another."""
    for collection in master_ob.users_collection:
        if collection not in ob.users_collection:
            collection.objects.link(ob)


def move_to_collection(collection_name: str, ob: bpy.types.Object) -> None:
    """Move object to collection."""
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        # Add collection to scene collection
        bpy.context.scene.collection.children.link(collection)
        collection.hide_viewport = True
    collection.objects.link(ob)


def copy_local_view_state(context: bpy.types.Context, ob: bpy.types.Object) -> None:
    """Copy local view state from context to object."""
    space = context.space_data
    if space.type == 'VIEW_3D':
        if space.local_view is not None:
            ob.local_view_set(space, True)


def set_origin(context: bpy.types.Context, ob: bpy.types.Object, co_world: mathutils.Vector) -> None:
    """Set object origin location."""

    if ob.mode == 'EDIT' and ob.type == 'MESH':
        assert isinstance(ob.data, bpy.types.Mesh)

        co_local = ob.matrix_world.inverted() @ co_world
        transform_mx = mathutils.Matrix.Translation((-co_local)[:])

        bm = bmesh.from_edit_mesh(ob.data)
        bm.transform(transform_mx)
        bmesh.update_edit_mesh(ob.data, loop_triangles=False, destructive=False)

        children = ob.children
        clear_children_parent_and_keep_mx(ob)
        ob.matrix_world.translation = co_world
        set_children_parent_and_keep_mx(children, ob)
        # for child in ob.children:
        #     child.matrix_parent_inverse = child.matrix_parent_inverse @ transform_mx

    elif ob.mode == 'OBJECT' and ob.type in {'CURVE', 'MESH'}:
        assert isinstance(ob.data, (bpy.types.Mesh, bpy.types.Curve))

        co_local = ob.matrix_world.inverted() @ co_world
        transform_mx = mathutils.Matrix.Translation((-co_local)[:])

        ob.data.transform(transform_mx)

        children = ob.children
        clear_children_parent_and_keep_mx(ob)
        ob.matrix_world.translation = co_world
        set_children_parent_and_keep_mx(children, ob)
        # for child in ob.children:
        #     child.matrix_parent_inverse = child.matrix_parent_inverse @ transform_mx

    else:
        bak_cursor_loc = context.scene.cursor.location.copy()
        context.scene.cursor.location = co_world
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        context.scene.cursor.location = bak_cursor_loc

    context.evaluated_depsgraph_get().update()


def get_modifier_index(current_index: int, reference_index: int, position: Literal['BEFORE', 'AFTER']) -> int:
    """Get new modifier index for moving modifier to it."""
    match position:
        case 'BEFORE':
            if current_index > reference_index:
                new_index = reference_index
            else:
                new_index = reference_index - 1
        case 'AFTER':
            if reference_index > current_index:
                new_index = reference_index
            else:
                new_index = reference_index + 1
    return new_index


def clear_parent_and_keep_mx(ob: bpy.types.Object) -> None:
    """Clear object parent and keep it transforms."""
    ob_mx = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world = ob_mx


def clear_children_parent_and_keep_mx(ob: bpy.types.Object) -> None:
    """Clear object children parent and keep their transforms."""
    children = ob.children
    for child in children:
        clear_parent_and_keep_mx(child)


def set_parent_and_keep_mx(ob: bpy.types.Object, parent: bpy.types.Object) -> None:
    """Set object parent and keep it transforms."""
    if ob.parent is not None:
        clear_parent_and_keep_mx(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()


def set_children_parent_and_keep_mx(children: Sequence[bpy.types.Object], parent: bpy.types.Object) -> None:
    """Set object children parent and keep their transforms."""
    for child in children:
        set_parent_and_keep_mx(child, parent)
