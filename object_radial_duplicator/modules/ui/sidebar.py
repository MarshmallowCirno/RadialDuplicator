import bpy

from ...package import get_preferences


class RADDUPLCIATOR_PT_sidebar(bpy.types.Panel):
    bl_label = "Radial Duplicator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (
            context.area.type == 'VIEW_3D'
            and ob is not None
            and ob.mode in {'OBJECT', 'EDIT'}
            and ob.library is None
            and not (ob.data is not None and ob.data.library is not None)
        )

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        if get_preferences().modal_buttons:
            col.operator("radial_duplicator.array_modal",
                         text="Add Radial Array",
                         icon='PHYSICS').from_button = True
            col.operator("radial_duplicator.screw_modal",
                         text="Add Screw",
                         icon='MOD_SCREW').from_button = True
            col.operator("radial_duplicator.duplicates_modal",
                         text="Duplicate Radially",
                         icon='CURVE_NCIRCLE').from_button = True
        else:
            col.operator("radial_duplicator.array_add",
                         text="Add Radial Array",
                         icon='PHYSICS').from_button = True
            col.operator("radial_duplicator.screw_add",
                         text="Add Screw",
                         icon='MOD_SCREW').from_button = True
            col.operator("radial_duplicator.duplicates_add",
                         text="Duplicate Radially",
                         icon='CURVE_NCIRCLE').from_button = True

        ob = context.object
        if ob.type in {'MESH', 'EMPTY', 'CURVE', 'SURFACE', 'FONT'}:
            self.draw_radial_arrays(layout, context)
        if ob.type in {'MESH', 'EMPTY', 'CURVE', 'SURFACE', 'FONT'}:
            self.draw_radial_screws(layout, context)
        if ob.type in {'MESH', 'EMPTY', 'CURVE', 'SURFACE', 'FONT', 'EMPTY'}:
            self.draw_radial_duplicates(layout, context)

    def draw_radial_arrays(self, layout, context):
        ob = context.object

        array_mods = [mod for mod in ob.modifiers if mod.type == 'ARRAY' and "Radial" in mod.name]
        if array_mods:
            col = layout.column(align=True)

            for array_mod in array_mods:
                radial_array_name = array_mod.name
                props = ob.radial_duplicator.arrays.get(radial_array_name)
                box = col.box()

                # Top row
                row = box.row()
                row.label(text="", icon='PHYSICS')
                row.label(text=radial_array_name)

                # Buttons
                sub = row.row(align=True)
                if props is not None:
                    icon = 'RESTRICT_VIEW_OFF' if props.show_viewport else 'RESTRICT_VIEW_ON'
                    sub.prop(props, "show_viewport", text="", emboss=False, icon=icon)
                sub.operator("radial_duplicator.array_apply", text="", emboss=False,
                             icon='CHECKMARK').name = radial_array_name
                sub.operator("radial_duplicator.array_remove", text="", emboss=False,
                             icon='PANEL_CLOSE').name = radial_array_name

                # Corrupted array
                if props is None or array_mod.offset_object is None:
                    box.operator("radial_duplicator.array_refresh", text="Refresh",
                                 icon='FILE_REFRESH').name = radial_array_name
                # Working array
                else:
                    sub = box.column()
                    sub.use_property_split = True
                    sub.use_property_decorate = False

                    # Orientation row
                    sub.prop(props, "spin_orientation", text="Orientation")

                    # Axis row
                    row = sub.row()
                    row.prop(props, "spin_axis", text="Axis", expand=True)

                    # Sliders
                    sub = box.column(align=True)
                    sub.prop(props, "count", text="Count")
                    if ob.type == 'MESH':
                        sub.prop(props, "radius_offset", text="Radius Offset")
                    sub.prop(props, "start_angle", text="Start Angle")
                    sub.prop(props, "end_angle", text="End Angle")
                    sub.prop(props, "height_offset", text="Height Offset")

                    # Pivot
                    op = sub.operator("radial_duplicator.array_set_pivot_point", text="Pivot to 3D Cursor",
                                      icon='PIVOT_CURSOR')
                    op.name = array_mod.name
                    op.pivot_point = 'CURSOR'

    def draw_radial_duplicates(self, layout, context):
        ob = context.object

        props = None
        if ob.children is not None and len(ob.radial_duplicator.duplicates) > 0:
            props = ob.radial_duplicator.duplicates[0]
        elif ob.parent is not None and len(ob.parent.radial_duplicator.duplicates) > 0:
            props = ob.parent.radial_duplicator.duplicates[0]

        if props is not None:
            box = layout.box()

            if ob.mode != 'OBJECT':
                box.enabled = False

            # Top row
            row = box.row()
            row.label(text="", icon='PHYSICS')
            row.label(text="RadialDuplicates")

            sub = row.row(align=True)
            if props is not None:
                icon = 'RESTRICT_VIEW_OFF' if props.show_viewport else 'RESTRICT_VIEW_ON'
                sub.prop(props, "show_viewport", text="", emboss=False, icon=icon)
            sub.operator("radial_duplicator.duplicates_remove", text="", emboss=False,
                         icon='PANEL_CLOSE')

            sub = box.column()
            sub.use_property_split = True
            sub.use_property_decorate = False

            # Orientation row
            sub.prop(props, "spin_orientation", text="Orientation")

            # Axis row
            row = sub.row()
            row.prop(props, "spin_axis", text="Axis", expand=True)

            # Sliders
            sub = box.column(align=True)
            sub.prop(props, "count", text="Count")
            sub.prop(props, "end_angle", text="End Angle")
            sub.prop(props, "height_offset", text="Height Offset")

            # Pivot
            op = sub.operator("radial_duplicator.duplicates_set_pivot_point", text="Pivot to 3D Cursor",
                              icon='PIVOT_CURSOR')
            op.pivot_point = 'CURSOR'

    def draw_radial_screws(self, layout, context):
        ob = context.object

        screw_mods = [mod for mod in ob.modifiers if mod.type == 'SCREW' and "Radial" in mod.name]
        if screw_mods:
            col = layout.column(align=True)

            for screw_mod in screw_mods:
                radial_screw_name = screw_mod.name
                props = ob.radial_duplicator.screws.get(radial_screw_name)
                box = col.box()

                # Top row
                row = box.row()
                row.label(text="", icon='PHYSICS')
                row.label(text=radial_screw_name)

                # Buttons
                sub = row.row(align=True)
                if props is not None:
                    icon = 'RESTRICT_VIEW_OFF' if props.show_viewport else 'RESTRICT_VIEW_ON'
                    sub.prop(props, "show_viewport", text="", emboss=False, icon=icon)
                sub.operator("radial_duplicator.screw_apply", text="", emboss=False,
                             icon='CHECKMARK').name = radial_screw_name
                sub.operator("radial_duplicator.screw_remove", text="", emboss=False,
                             icon='PANEL_CLOSE').name = radial_screw_name

                # Corrupted screw
                if props is None or screw_mod.object is None:
                    box.operator("radial_duplicator.screw_refresh", text="Refresh",
                                 icon='FILE_REFRESH').name = radial_screw_name
                # Working screw
                else:
                    sub = box.column()
                    sub.use_property_split = True
                    sub.use_property_decorate = False

                    # Orientation row
                    sub.prop(props, "spin_orientation", text="Orientation")

                    # Axis row
                    row = sub.row()
                    row.prop(props, "spin_axis", text="Axis", expand=True)

                    # Sliders
                    sub = box.column(align=True)
                    sub.prop(props, "steps", text="Steps")
                    if ob.type == 'MESH':
                        sub.prop(props, "radius_offset", text="Radius Offset")
                    sub.prop(props, "start_angle", text="Start Angle")
                    sub.prop(props, "end_angle", text="End Angle")
                    sub.prop(props, "screw_offset", text="Screw Offset")
                    sub.prop(props, "iterations", text="Iterations")

                    # Pivot
                    op = sub.operator("radial_duplicator.screw_set_pivot_point", text="Pivot to 3D Cursor",
                                      icon='PIVOT_CURSOR')
                    op.name = screw_mod.name
                    op.pivot_point = 'CURSOR'


classes = (
    RADDUPLCIATOR_PT_sidebar,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
