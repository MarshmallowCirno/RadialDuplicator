from ...addon_info import get_preferences


def register_modal_keymap():
    modal_keymap = get_preferences().keymaps.get("modal")
    if modal_keymap is None:
        modal_keymap = get_preferences().keymaps.add()
        modal_keymap.name = "modal"

    keymap_items = modal_keymap.keymap_items

    if "spin_orientation" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "spin_orientation"
        kmi.label = "Cycle Spin Orientation"
        kmi.type = 'Q'
        kmi.tag = "Default"

    if "spin_axis" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "spin_axis"
        kmi.label = "Cycle Spin Axis"
        kmi.type = 'A'
        kmi.tag = "Default"

    if "x_axis" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "x_axis"
        kmi.label = "X Axis"
        kmi.type = 'X'
        kmi.tag = "Default"

    if "y_axis" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "y_axis"
        kmi.label = "Y Axis"
        kmi.type = 'Y'
        kmi.tag = "Default"

    if "z_axis" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "z_axis"
        kmi.label = "Z Axis"
        kmi.type = 'Z'
        kmi.tag = "Default"

    if "duplicates_rotation" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "duplicates_rotation"
        kmi.label = "Duplicates Rotation"
        kmi.type = 'T'
        kmi.tag = "Default"

    if "pivot_point" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "pivot_point"
        kmi.label = "Pivot Point"
        kmi.type = 'C'
        kmi.tag = "Default"

    if "add" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "add"
        kmi.label = "Add New"
        kmi.type = 'N'
        kmi.tag = "Default"

    if "apply" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "apply"
        kmi.label = "Apply"
        kmi.type = 'L'
        kmi.tag = "Default"

    if "remove" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "remove"
        kmi.label = "Remove"
        kmi.type = 'DEL'
        kmi.tag = "Default"

    if "count_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "count_changing"
        kmi.label = "Count Changing"
        kmi.type = 'S'
        kmi.tag = "Mode"

    if "radius_offset_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "radius_offset_changing"
        kmi.label = "Radius Changing"
        kmi.type = 'W'
        kmi.tag = "Mode"

    if "start_angle_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "start_angle_changing"
        kmi.label = "Start Angle Changing"
        kmi.type = 'R'
        kmi.tag = "Mode"

    if "end_angle_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "end_angle_changing"
        kmi.label = "End Angle Changing"
        kmi.type = 'E'
        kmi.tag = "Mode"

    if "end_scale_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "end_scale_changing"
        kmi.label = "End Scale Changing"
        kmi.type = 'B'
        kmi.tag = "Mode"

    if "height_offset_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "height_offset_changing"
        kmi.label = "Height Changing"
        kmi.type = 'H'
        kmi.tag = "Mode"

    if "iterations_changing" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "iterations_changing"
        kmi.label = "Iterations Changing"
        kmi.type = 'I'
        kmi.tag = "Mode"

    if "reset_count" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_count"
        kmi.label = "Count Reset"
        kmi.type = 'S'
        kmi.alt = True
        kmi.tag = "Reset"

    if "reset_radius_offset" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_radius_offset"
        kmi.label = "Radius Reset"
        kmi.type = 'W'
        kmi.alt = True
        kmi.tag = "Reset"

    if "reset_start_angle" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_start_angle"
        kmi.label = "Start Angle Reset"
        kmi.type = 'R'
        kmi.alt = True
        kmi.tag = "Reset"

    if "reset_end_angle" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_end_angle"
        kmi.label = "End Angle Reset"
        kmi.type = 'E'
        kmi.alt = True
        kmi.tag = "Reset"

    if "reset_end_scale" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_end_scale"
        kmi.label = "End Scale Reset"
        kmi.type = 'B'
        kmi.alt = True
        kmi.tag = "Reset"

    if "reset_height_offset" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_height_offset"
        kmi.label = "Height Reset"
        kmi.type = 'H'
        kmi.alt = True
        kmi.tag = "Reset"

    if "reset_iterations" not in keymap_items:
        kmi = keymap_items.add()
        kmi.name = "reset_iterations"
        kmi.label = "Iterations Reset"
        kmi.type = 'I'
        kmi.alt = True
        kmi.tag = "Reset"
