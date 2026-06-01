from collections.abc import Sequence

import gpu
import gpu_extras


def draw_bg(
    shader: gpu.types.GPUShader,
    content_x_right: int,
    content_y_bottom: int,
    content_x_left: int,
    content_y_top: int,
    padding: int,
    color: Sequence[float],
):
    bg_x_right = content_x_right + padding
    bg_x_left = content_x_left - padding
    bg_y_bottom = content_y_bottom - padding
    bg_y_top = content_y_top + padding

    top_left = (bg_x_left, bg_y_top)
    bottom_left = (bg_x_left, bg_y_bottom)
    top_right = (bg_x_right, bg_y_top)
    bottom_right = (bg_x_right, bg_y_bottom)

    radius = 3
    vertices = []

    # Top Left
    vertices.append((top_left[0] + radius, top_left[1]))
    vertices.append((top_left[0], top_left[1] - radius))

    # Bottom Left
    vertices.append((bottom_left[0], bottom_left[1] + radius))
    vertices.append((bottom_left[0] + radius, bottom_left[1]))

    # Bottom Right
    vertices.append((bottom_right[0] - radius, bottom_right[1]))
    vertices.append((bottom_right[0], bottom_right[1] + radius))

    # Top Right
    vertices.append((top_right[0], top_right[1] - radius))
    vertices.append((top_right[0] - radius, top_right[1]))

    # Make indices

    indices = [
        (0, 1, 2),
        (0, 2, 3),
        (0, 3, 4),
        (0, 4, 5),
        (0, 5, 6),
        (0, 6, 7),
    ]

    batch = gpu_extras.batch.batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)
    gpu.state.blend_set('NONE')
