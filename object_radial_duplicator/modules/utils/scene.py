def get_unit(context) -> str:
    unit = {
        'METRIC': " m",
        'IMPERIAL': " '",
        'NONE': ""
    }[context.scene.unit_settings.system]
    return unit
