import bpy


def get_unit(context: bpy.types.Context) -> str:
    unit = {'METRIC': " m", 'IMPERIAL': " '", 'NONE': ""}[context.scene.unit_settings.system]
    return unit
