import gpu
import bpy
from gpu_extras.batch import batch_for_shader

point_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
segment_shader = gpu.shader.from_builtin('UNIFORM_COLOR')


def redraw_point_shader(context, points):
    dns = bpy.app.driver_namespace
    handler = dns.get("draw_xray_points_debug")
    if handler:
        context.space_data.draw_handler_remove(handler, 'WINDOW')
        del bpy.app.driver_namespace['draw_xray_points_debug']

    point_batch = batch_for_shader(point_shader, 'POINTS', {"pos": points})

    handler = context.space_data.draw_handler_add(draw_point_shader, (point_batch,), 'WINDOW', 'POST_VIEW')
    dns['draw_xray_points_debug'] = handler
    context.area.tag_redraw()


def draw_point_shader(point_batch):
    point_shader.bind()
    point_shader.uniform_float("color", (1.0, 0.0, 0.0, 1.0))
    point_batch.draw(point_shader)


def redraw_segment_shader(context, points, indices):
    dns = bpy.app.driver_namespace
    handler = dns.get("draw_xray_segment_debug")
    if handler:
        context.space_data.draw_handler_remove(handler, 'WINDOW')
        del bpy.app.driver_namespace['draw_xray_segment_debug']

    segment_batch = batch_for_shader(segment_shader, 'LINES', {"pos": points}, indices=indices)

    handler = context.space_data.draw_handler_add(draw_segment_shader, (segment_batch,), 'WINDOW', 'POST_VIEW')
    dns['draw_xray_segment_debug'] = handler
    context.area.tag_redraw()


def draw_segment_shader(segment_batch):
    gpu.state.blend_set('ALPHA')
    segment_shader.bind()
    segment_shader.uniform_float("color", (0.0, 1.0, 0.0, 0.2))
    segment_batch.draw(segment_shader)
    gpu.state.blend_set('NONE')


# from .. utils.debug_shader import redraw_segment_shader
# vec1 = self.ob.matrix_world @ pivot_point_co_local
# vec2 = self.ob.matrix_world @ non_flattened_displace_vec
# points = (vec1, vec2)
# indices = [(0, 1)]
# redraw_segment_shader(self.context, points, indices)
