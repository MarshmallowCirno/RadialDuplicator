import bpy
import bmesh
from bpy.types import Context
from bpy.types import Object
from bpy.types import Modifier
from mathutils import Matrix
from mathutils import Vector

from ..utils.object_data import data_is_selected


def get_normal_matrix(context: Context, ob: Object) -> Matrix:
    """Get normal matrix of selection."""
    if ob.mode == 'EDIT' and not data_is_selected(ob.data):
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
        custom_orientation_mx = custom_orientation.matrix.copy().to_4x4()
        bpy.ops.transform.delete_orientation()
        if bak_slot_name != 'RADIAL_DUPLICATOR':
            active_slot.type = bak_slot_type
        return custom_orientation_mx


def copy_collections(master_ob: Object, ob: Object) -> None:
    """Copy collections from one object to another."""
    for collection in master_ob.users_collection:
        if collection not in ob.users_collection:
            collection.objects.link(ob)


def move_to_collection(collection_name: str, ob: Object) -> None:
    """Move object to collection."""
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        # Add collection to scene collection
        bpy.context.scene.collection.children.link(collection)
        collection.hide_viewport = True
    collection.objects.link(ob)


def copy_local_view_state(context: Context, ob: Object) -> None:
    """Copy local view state from context to object."""
    space = context.space_data
    if space.type == 'VIEW_3D':
        if space.local_view is not None:
            ob.local_view_set(space, True)


def set_origin(context: Context, ob: Object, co_world: Vector) -> None:
    """Set object origin location."""
    if ob.mode == 'EDIT' and ob.type == 'MESH':
        co_local = ob.matrix_world.inverted() @ co_world
        transform_mx = Matrix.Translation(-co_local)

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
        co_local = ob.matrix_world.inverted() @ co_world
        transform_mx = Matrix.Translation(-co_local)

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


def move_modifier_up(ob: Object, mod: Modifier, iters: int) -> None:
    """Move modifier up in the stack."""
    for i in range(iters):
        # noinspection PyArgumentList
        bpy.ops.object.modifier_move_up({"object": ob}, modifier=mod.name)


def clear_parent_and_keep_mx(ob: Object) -> None:
    """Clear object parent and keep it transforms."""
    ob_mx = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world = ob_mx


def clear_children_parent_and_keep_mx(ob: Object) -> None:
    """Clear object children parent and keep their transforms."""
    children = ob.children
    if children is not None:
        for child in children:
            clear_parent_and_keep_mx(child)


def set_parent_and_keep_mx(ob: Object, parent: Object) -> None:
    """Set object parent and keep it transforms."""
    if ob.parent is not None:
        clear_parent_and_keep_mx(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()


def set_children_parent_and_keep_mx(children: list[Object], parent: Object) -> None:
    """Set object children parent and keep their transforms."""
    if children is not None:
        for child in children:
            set_parent_and_keep_mx(child, parent)
