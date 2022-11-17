import blf
from typing import TypeVar, Union, Any

LEFT = TypeVar('LEFT')
RIGHT = TypeVar('RIGHT')


def get_text_block_dimensions(text_lines: list[list[tuple[str, Any]]],
                              line_padding: int,
                              font_id: int,
                              font_size: int,
                              dpi: int):
    """Get dimensions of text lines."""
    blf.size(font_id, font_size, dpi)

    text_block_height = (blf.dimensions(font_id, "M")[1]
                         * (2 * len(text_lines) - 1)
                         + (len(text_lines) - 1) * line_padding)
    text_block_width = 0
    for text_line in text_lines:
        text_line_width = sum([blf.dimensions(font_id, text)[0] for text, _ in text_line])
        text_block_width = max(text_block_width, text_line_width)

    return text_block_width, text_block_height


def draw_text_block(text_lines: list[list[tuple[str, Any]]],
                    align_x: int,
                    top_y: int,
                    line_padding: int,
                    align: Union[LEFT, RIGHT],
                    font_id: int = 0,
                    font_size: int = 12,
                    dpi: int = 0):
    """Draw text lines from right top to bottom."""
    blf.size(font_id, font_size, dpi)
    blf.enable(font_id, blf.SHADOW)
    blf.shadow_offset(font_id, 1, -1)
    blf.shadow(font_id, 3, *(0, 0, 0, 1))

    text_height = blf.dimensions(font_id, "M")[1] * 2 + line_padding
    text_y = top_y - blf.dimensions(font_id, "M")[1]

    for text_line in text_lines:
        text_x = align_x

        if align == 'RIGHT':
            text_line = reversed(text_line)

        for text, color in text_line:
            blf.color(font_id, *color)
            text_width = blf.dimensions(font_id, text)[0]

            if align == 'RIGHT':
                blf.position(font_id, text_x - text_width, text_y, 0)
                blf.draw(font_id, text)
                text_x -= text_width
            else:
                blf.position(font_id, text_x, text_y, 0)
                blf.draw(font_id, text)
                text_x += text_width

        text_y -= text_height


def get_region_width(context):
    """Width of region that doesn't overlap with sidebar."""
    region_overlap = context.preferences.system.use_region_overlap
    sidebar_width = next((region.width for region in context.area.regions if region.type == 'UI'), 0)
    if context.space_data.show_region_ui and region_overlap:
        return context.region.width - sidebar_width
    else:
        return context.region.width
