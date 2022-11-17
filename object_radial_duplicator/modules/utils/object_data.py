from typing import Union

import bpy
import bmesh
import numpy as np
from bpy.types import Context
from bpy.types import Curve
from bpy.types import Mesh
from bpy.types import Object
from mathutils import Vector


def get_mesh_selection_co_world(context: Context) -> Vector:
    """Get median coordinate of mesh selection."""
    bak_cursor_loc = context.scene.cursor.location.copy()
    bpy.ops.view3d.snap_cursor_to_selected()
    co = context.scene.cursor.location.copy()
    context.scene.cursor.location = bak_cursor_loc
    return co


def data_is_selected(data: Union[Curve, Mesh]) -> bool:
    """Check if object data is selected."""
    idname = data.rna_type.name
    if idname == "Mesh":
        return mesh_is_selected(data)
    elif idname in {"Curve", "Text Curve", "Surface Curve"}:
        return curve_is_selected(data)


def mesh_is_selected(mesh: Mesh) -> bool:
    """Check if mesh is selected."""
    bm = bmesh.from_edit_mesh(mesh)
    return ('VERT' in bm.select_mode and next((v for v in bm.verts if v.select), False) or
            'EDGE' in bm.select_mode and next((e for e in bm.edges if e.select), False) or
            'FACE' in bm.select_mode and next((f for f in bm.faces if f.select), False))


def curve_is_selected(curve: Curve) -> bool:
    """Check if curve is selected."""
    splines = curve.splines
    total_selection = []
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
    total_selection = np.array(total_selection).ravel()
    return np.any(total_selection)


def get_data_center_co_world(ob: Object) -> Vector:
    """Get world space coordinates of object data center."""
    idname = ob.data.rna_type.name
    if idname == "Mesh":
        return get_mesh_center_co_world(ob)
    elif idname in {"Curve", "Text Curve", "Surface Curve"}:
        return get_curve_center_co_world(ob)


def get_mesh_center_co_world(ob: Object) -> Vector:
    """Get world space coordinates of mesh center."""
    me = ob.data
    verts = me.vertices
    vert_count = len(verts)
    if vert_count > 0:
        vert_co_local = np.empty(vert_count * 3, "f")
        verts.foreach_get("co", vert_co_local)
        vert_co_local.shape = (vert_count, 3)

        amax = np.amax(vert_co_local, axis=0)
        amin = np.amin(vert_co_local, axis=0)

        center_co_local = (amax + amin) / 2
        center_co = ob.matrix_world @ Vector(center_co_local)
    else:
        center_co = ob.matrix_world.to_translation()
    return center_co


def get_curve_center_co_world(ob: Object) -> Vector:
    """Get world space coordinates of curve center."""
    curve = ob.data
    splines = curve.splines
    # Point coordinates
    points_co = []
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
    points_co = np.array(points_co).ravel()
    # Median coordinate
    if points_co.size > 0:
        points_co.shape = (-1, 3)

        amax = np.amax(points_co, axis=0)
        amin = np.amin(points_co, axis=0)

        center_co_local = (amax + amin) / 2
        center_co = ob.matrix_world @ Vector(center_co_local)
    else:
        center_co = ob.matrix_world.to_translation()
    return center_co
