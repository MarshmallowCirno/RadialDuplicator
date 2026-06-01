import bpy

from ...addon_info import get_preferences


def hide_sidebar(context: bpy.types.Context) -> None:
    if get_preferences().hide_sidebar:
        if context.space_data.show_region_ui and context.preferences.system.use_region_overlap:
            context.space_data.show_region_ui = False


def restore_sidebar(context: bpy.types.Context, initial_state: bool) -> None:
    if get_preferences().hide_sidebar:
        context.space_data.show_region_ui = initial_state


def get_non_overlap_width(context: bpy.types.Context) -> int:
    """Get width of ui that doesn't overlap width sidebar"""
    region_overlap = context.preferences.system.use_region_overlap
    offset_width = 0
    if context.space_data.show_region_ui and region_overlap:
        for region in context.area.regions:
            if region.type == 'UI':
                offset_width = region.width  # area of 3d view covered by sidebar
                break

    safe_x = context.region.width - offset_width
    return safe_x
