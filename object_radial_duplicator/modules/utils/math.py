import numpy as np
from mathutils import Matrix
from mathutils import Vector


def get_axis_vec(axis: str, matrix: Matrix) -> Vector:
    """Get axis vector from matrix.

    :param axis: Axis in ['X', 'Y', 'Z']
    :param matrix: Matrix
    """
    return {
        'X': Vector((matrix[0][0], matrix[1][0], matrix[2][0])),
        'Y': Vector((matrix[0][1], matrix[1][1], matrix[2][1])),
        'Z': Vector((matrix[0][2], matrix[1][2], matrix[2][2])),
    }[axis]


def flatten_vec(vec: Vector, axis: str) -> Vector:
    """Flatten vector in axis direction.

    :param vec: Vector
    :param axis: Axis in ['X', 'Y', 'Z']
    """
    if axis == 'X':
        vec[0] = 0
    elif axis == 'Y':
        vec[1] = 0
    elif axis == 'Z':
        vec[2] = 0
    return vec


def build_circle(radius: float, sides: int) -> np.array:
    """Build a circle and return its vertex coordinates."""
    # https://stackoverflow.com/questions/17258546/opengl-creating-a-circle-change-radius
    counts = np.arange(1, sides + 1, dtype="f")
    angles = np.multiply(counts, 2 * np.pi / sides)
    vert_x = np.multiply(np.sin(angles), radius)
    vert_y = np.multiply(np.cos(angles), radius)
    vert_z = np.zeros(sides, "f")
    vert_co = np.column_stack((vert_x, vert_y, vert_z))
    vert_co.shape = (sides, 3)
    return vert_co
