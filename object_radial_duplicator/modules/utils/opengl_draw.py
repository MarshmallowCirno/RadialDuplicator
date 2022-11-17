from gpu_extras.batch import batch_for_shader
from bgl import glDisable
from bgl import glEnable
from bgl import GL_BLEND


def draw_bg(shader, content_x_right, content_y_bottom, content_x_left, content_y_top, padding, color):
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

    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    glEnable(GL_BLEND)
    batch.draw(shader)
    glDisable(GL_BLEND)
