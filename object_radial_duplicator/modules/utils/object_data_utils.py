from typing import Any

import bmesh
import bpy
import mathutils
import numpy as np


def get_mesh_selection_co_world(context: bpy.types.Context) -> mathutils.Vector:
    """Get median coordinate of mesh selection."""
    bak_cursor_loc = context.scene.cursor.location.copy()
    bpy.ops.view3d.snap_cursor_to_selected()
    co = context.scene.cursor.location.copy()
    context.scene.cursor.location = bak_cursor_loc
    return co


def is_data_selected(data: bpy.types.Mesh | bpy.types.Curve) -> bool:
    """Check if object data is selected."""
    match data:
        case bpy.types.Mesh():
            return mesh_is_selected(data)
        case bpy.types.Curve():
            return curve_is_selected(data)


def mesh_is_selected(mesh: bpy.types.Mesh) -> bool:
    """Check if mesh is selected."""
    bm = bmesh.from_edit_mesh(mesh)
    return bool(
        'VERT' in bm.select_mode
        and next((v for v in bm.verts if v.select), False)
        or 'EDGE' in bm.select_mode
        and next((e for e in bm.edges if e.select), False)
        or 'FACE' in bm.select_mode
        and next((f for f in bm.faces if f.select), False)
    )


def curve_is_selected(curve: bpy.types.Curve) -> bool:
    """Check if curve is selected."""
    splines = curve.splines
    total_selection: list[np.ndarray[tuple[int], np.dtype[np.bool]]] = []
    for spline in splines:
        if spline.type == 'BEZIER':
            points_count = len(spline.bezier_points)
            selection = np.empty(points_count, "?")
            spline.bezier_points.foreach_get("select_control_point", selection)
            total_selection.append(selection)
        else:
            points_count = len(spline.points)
            selection = np.empty(points_count, "?")
            spline.points.foreach_get("select", selection)
            total_selection.append(selection)
    total_selection_flat = np.array(total_selection).ravel()
    return bool(np.any(total_selection_flat))


def get_data_center_co_world(ob: bpy.types.Object) -> mathutils.Vector:
    """Get world space coordinates of object data center."""
    assert isinstance(ob.data, bpy.types.Mesh | bpy.types.Curve)
    match ob.data:
        case bpy.types.Mesh():
            return get_mesh_center_co_world(ob)
        case bpy.types.Curve():
            return get_curve_center_co_world(ob)


def get_mesh_center_co_world(ob: bpy.types.Object) -> mathutils.Vector:
    """Get world space coordinates of mesh center."""
    me = ob.data
    assert isinstance(me, bpy.types.Mesh)
    verts = me.vertices
    vert_count = len(verts)
    if vert_count > 0:
        vert_co_local = np.empty(vert_count * 3, "f")
        verts.foreach_get("co", vert_co_local)
        vert_co_local.shape = (vert_count, 3)

        amax = np.amax(vert_co_local, axis=0)
        amin = np.amin(vert_co_local, axis=0)

        center_co_local = (amax + amin) / 2
        center_co = ob.matrix_world @ mathutils.Vector(center_co_local)
    else:
        center_co = ob.matrix_world.to_translation()
    return center_co


def get_curve_center_co_world(ob: bpy.types.Object) -> mathutils.Vector:
    """Get world space coordinates of curve center."""
    curve = ob.data
    assert isinstance(curve, bpy.types.Curve)
    splines = curve.splines
    # Point coordinates
    points_co: list[np.ndarray[Any, np.dtype[np.float32]]] = []
    for spline in splines:
        if spline.type == 'BEZIER':
            points_count = len(spline.bezier_points)
            co = np.empty(points_count * 3, "f")
            spline.bezier_points.foreach_get("co", co)
            co.shape = (points_count, 3)
            points_co.append(co)
        elif spline.type == 'NURBS':
            points_count = len(spline.points)
            co = np.empty(points_count * 4, "f")
            spline.points.foreach_get("co", co)
            co.shape = (points_count, 4)
            co = co[:3]
            points_co.append(co)
        else:
            points_count = len(spline.points)
            co = np.empty(points_count * 3, "f")
            spline.points.foreach_get("co", co)
            co.shape = (points_count, 3)
            points_co.append(co)
    points_co_flat = np.array(points_co).ravel()
    # Median coordinate
    if points_co_flat.size > 0:
        points_co_flat.shape = (-1, 3)

        amax = np.amax(points_co_flat, axis=0)
        amin = np.amin(points_co_flat, axis=0)

        center_co_local = (amax + amin) / 2
        center_co = ob.matrix_world @ mathutils.Vector(center_co_local)
    else:
        center_co = ob.matrix_world.to_translation()
    return center_co
