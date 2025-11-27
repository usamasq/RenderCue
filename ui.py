import bpy

class RENDER_UL_render_cue_jobs(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # item is RenderCueJob
        if not item.scene:
            layout.label(text="<Missing Scene>", icon='ERROR')
            return

        # Main row
        row = layout.row(align=True)
        
        # Scene Name
        row.label(text=item.scene.name, icon='SCENE_DATA')
        
        # Renderer Info
        r_engine = item.scene.render.engine
        icon_engine = 'SHADING_RENDERED'
        if r_engine == 'CYCLES':
            icon_engine = 'PMARKER_ACT'
        elif r_engine == 'BLENDER_EEVEE' or r_engine == 'BLENDER_EEVEE_NEXT':
            icon_engine = 'LIGHT_SUN'
            
        row.label(text="", icon=icon_engine)
        
        # Resolution (actual dimensions)
        res_x = item.scene.render.resolution_x
        res_y = item.scene.render.resolution_y
        scale = item.scene.render.resolution_percentage
        if item.override_resolution:
            scale = item.resolution_scale
        
        # Calculate final resolution
        final_x = int(res_x * scale / 100)
        final_y = int(res_y * scale / 100)
        
        if item.override_resolution:
            row.label(text=f"{final_x}x{final_y}", icon='MODIFIER')
        else:
            row.label(text=f"{final_x}x{final_y}")
        
        # FPS
        fps = item.scene.render.fps
        row.label(text=f"{fps}fps")
            
        # Samples
        samples = 0
        if r_engine == 'CYCLES':
            samples = item.scene.cycles.samples
        elif r_engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
            samples = item.scene.eevee.taa_render_samples
        
        if item.override_samples:
            row.label(text=f"S:{item.samples}", icon='MODIFIER')
        else:
            row.label(text=f"S:{samples}")

class RenderCuePanelMixin:
    bl_label = "RenderCue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        settings = wm.rendercue
        
        # Main List
        row = layout.row()
        row.template_list("RENDER_UL_render_cue_jobs", "", settings, "jobs", settings, "active_job_index")
        
        # Side buttons for list
        col = row.column(align=True)
        col.operator("rendercue.add_job", icon='ADD', text="")
        col.operator("rendercue.remove_job", icon='REMOVE', text="")
        col.separator()
        col.operator("rendercue.move_job", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("rendercue.move_job", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        # Add All Scenes Helper
        layout.operator("rendercue.populate_all", icon='SCENE_DATA', text="Add All Scenes")
        
        # Global Settings
        layout.separator()
        layout.label(text="Batch Settings:")
        layout.prop(settings, "output_structure")
        layout.prop(settings, "global_output_path")
        
        # Selected Job Settings (Overrides)
        if settings.jobs and settings.active_job_index >= 0 and len(settings.jobs) > settings.active_job_index:
            job = settings.jobs[settings.active_job_index]
            box = layout.box()
            box.label(text=f"Overrides: {job.scene.name if job.scene else 'None'}")
            
            # Helper to draw override with "Apply to All"
            def draw_override(prop_bool, prop_val, name, data_path_bool, data_path_val):
                row = box.row(align=True)
                row.prop(job, prop_bool, text="")
                sub = row.row(align=True)
                sub.active = getattr(job, prop_bool)
                sub.prop(job, prop_val)
                
                # Apply to All Button
                op = row.operator("rendercue.apply_override_to_all", text="", icon='DUPLICATE')
                op.data_path_bool = data_path_bool
                op.data_path_val = data_path_val

            # Output
            draw_override("override_output", "output_path", "Output", "override_output", "output_path")
            
            # Frame Range
            row = box.row(align=True)
            row.prop(job, "override_frame_range", text="")
            sub = row.row(align=True)
            sub.active = job.override_frame_range
            sub.prop(job, "frame_start")
            sub.prop(job, "frame_end")
            # Apply to all for frame range is tricky as it has two values. 
            # We can make a specific operator or just skip for now.
            # Let's add a specific one for frame range.
            op = row.operator("rendercue.apply_override_to_all", text="", icon='DUPLICATE')
            op.data_path_bool = "override_frame_range"
            op.data_path_val = "frame_range" # Special case

            # Resolution
            draw_override("override_resolution", "resolution_scale", "Resolution", "override_resolution", "resolution_scale")
            
            # Format
            draw_override("override_format", "render_format", "Format", "override_format", "render_format")
            
            # Samples
            draw_override("override_samples", "samples", "Samples", "override_samples", "samples")

        # Actions
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("rendercue.sync_vse", icon='SEQUENCE', text="Sync to VSE")
        row.operator("rendercue.batch_render", icon='RENDER_ANIMATION', text="Render Cue")

class RENDER_PT_render_cue(RenderCuePanelMixin, bpy.types.Panel):
    bl_idname = "RENDER_PT_render_cue"
    # Inherits bl_space_type etc from Mixin

class VIEW3D_PT_render_cue(RenderCuePanelMixin, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_render_cue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "RenderCue"

def register():
    bpy.utils.register_class(RENDER_UL_render_cue_jobs)
    bpy.utils.register_class(RENDER_PT_render_cue)
    bpy.utils.register_class(VIEW3D_PT_render_cue)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_render_cue)
    bpy.utils.unregister_class(RENDER_PT_render_cue)
    bpy.utils.unregister_class(RENDER_UL_render_cue_jobs)
