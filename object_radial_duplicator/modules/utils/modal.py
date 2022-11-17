def event_match_kmi(operator, event, idname: str, release: bool = False) -> bool:
    """Return match between event type and keymap item type."""
    if release:
        return event.type == operator.keymap_items[idname].type
    else:
        return (event.type == (kmi := operator.keymap_items[idname]).type
                and event.alt == kmi.alt
                and event.ctrl == kmi.ctrl
                and event.shift == kmi.shift)


def get_property_default(operator, idname):
    op_properties = operator.properties.bl_rna.properties
    return op_properties[idname].default


def event_type_to_digit(event_type):
    event_type_digit = {
        'ZERO': 0,
        'ONE': 1,
        'TWO': 2,
        'THREE': 3,
        'FOUR': 4,
        'FIVE': 5,
        'SIX': 6,
        'SEVEN': 7,
        'EIGHT': 8,
        'NINE': 9,
        'NUMPAD_0': 0,
        'NUMPAD_1': 1,
        'NUMPAD_2': 2,
        'NUMPAD_3': 3,
        'NUMPAD_4': 4,
        'NUMPAD_5': 5,
        'NUMPAD_6': 6,
        'NUMPAD_7': 7,
        'NUMPAD_8': 8,
        'NUMPAD_9': 9,
    }
    return event_type_digit[event_type]


def event_type_is_digit(event_type):
    digits = {
        'ZERO',
        'ONE',
        'TWO',
        'THREE',
        'FOUR',
        'FIVE',
        'SIX',
        'SEVEN',
        'EIGHT',
        'NINE',
        'NUMPAD_0',
        'NUMPAD_1',
        'NUMPAD_2',
        'NUMPAD_3',
        'NUMPAD_4',
        'NUMPAD_5',
        'NUMPAD_6',
        'NUMPAD_7',
        'NUMPAD_8',
        'NUMPAD_9',
    }
    return event_type in digits
