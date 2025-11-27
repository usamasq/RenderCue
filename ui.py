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
        
        # Switch Scene Button
        op = row.operator("rendercue.switch_to_job_scene", text="", icon='VIEW3D')
        op.index = index
        
        # Renderer Info with text
        r_engine = item.scene.render.engine
        icon_engine = 'SHADING_RENDERED'
        engine_name = r_engine
        
        if r_engine == 'CYCLES':
            icon_engine = 'PMARKER_ACT'
            engine_name = "Cycles"
        elif r_engine == 'BLENDER_EEVEE':
            icon_engine = 'LIGHT_SUN'
            engine_name = "Eevee"
        elif r_engine == 'BLENDER_EEVEE_NEXT':
            icon_engine = 'LIGHT_SUN'
            engine_name = "Eevee Next"
            
        row.label(text=engine_name, icon=icon_engine)
        
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
            
        # Samples with clearer label
        samples = 0
        if r_engine == 'CYCLES':
            samples = item.scene.cycles.samples
        elif r_engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
            # Blender 5.0 compatibility: try different property names
            try:
                samples = item.scene.eevee.taa_render_samples
            except AttributeError:
                # Fallback for Blender 5.0+
                try:
                    samples = item.scene.eevee.samples
                except AttributeError:
                    samples = 0
        
        if item.override_samples:
            row.label(text=f"Samples: {item.samples}", icon='MODIFIER')
        else:
            row.label(text=f"Samples: {samples}")

class RenderCuePanelMixin:
    bl_label = "RenderCue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        settings = context.window_manager.rendercue
        
        # Progress Indicator
        if settings.is_rendering:
            box = layout.box()
            box.label(text=settings.progress_message, icon='RENDER_ANIMATION')
            # Frame Progress
            if settings.total_frames_to_render > 0:
                percent = (settings.finished_frames_count / settings.total_frames_to_render) * 100
                box.label(text=f"Frames: {settings.finished_frames_count} / {settings.total_frames_to_render} ({int(percent)}%)")
            
            box.label(text=f"ETR: {settings.etr}", icon='TIME')
            
            # Thumbnail
            if settings.preview_image:
                col = box.column()
                col.template_image(settings, "preview_image", image_user=None, compact=True)
            
            # Draw a progress bar using a slider
            row = box.row()
            row.prop(settings, "current_job_index", text="Job Progress", slider=True)
            row.enabled = False # Make it read-only
            
            # Stop Button
            row = box.row()
            row.scale_y = 1.5
            row.operator("rendercue.stop_render", icon='CANCEL', text="Stop Render")
            
            # Disable the rest of the UI
            layout.enabled = False
            return

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
        layout.prop(settings, "render_mode")
        
        row = layout.row(align=True)
        row.prop(settings, "global_output_path")
        row.operator("rendercue.open_output_folder", icon='EXTERNAL_DRIVE', text="")
        
        row = layout.row(align=True)
        row.operator("rendercue.validate_queue", icon='CHECKMARK', text="Validate")
        row.menu("RENDERCUE_MT_presets_menu", icon='PRESET', text="Presets")
        
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
            
            op = row.operator("rendercue.apply_override_to_all", text="", icon='DUPLICATE')
            op.data_path_bool = "override_frame_range"
            op.data_path_val = "frame_range" # Special case

            # Resolution
            draw_override("override_resolution", "resolution_scale", "Resolution", "override_resolution", "resolution_scale")
            
            # Format
            draw_override("override_format", "render_format", "Format", "override_format", "render_format")
            
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("rendercue.batch_render", icon='RENDER_ANIMATION', text="Render Cue")

class RENDERCUE_MT_presets_menu(bpy.types.Menu):
    bl_label = "Presets"
    bl_idname = "RENDERCUE_MT_presets_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("rendercue.save_preset", icon='FILE_TICK')
        layout.operator("rendercue.load_preset", icon='FILE_FOLDER')

class RENDER_PT_render_cue(RenderCuePanelMixin, bpy.types.Panel):
    bl_idname = "RENDER_PT_render_cue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

class RENDER_PT_render_cue_dashboard(RenderCuePanelMixin, bpy.types.Panel):
    bl_label = "Dashboard"
    bl_idname = "RENDER_PT_render_cue_dashboard"
    bl_parent_id = "RENDER_PT_render_cue"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        settings = context.window_manager.rendercue
        layout = self.layout
        
        if settings.is_rendering:
            box = layout.box()
            box.label(text="Status: RENDERING", icon='RENDER_ANIMATION')
            box.prop(settings, "progress_message", text="")
            
            row = box.row()
            row.label(text=f"Job: {settings.current_job_index + 1}/{settings.total_jobs_count}")
            row.label(text=f"ETR: {settings.etr}")
        else:
            # Status Indicator
            if settings.last_render_status != 'NONE':
                icon = 'INFO'
                if settings.last_render_status == 'SUCCESS':
                    icon = 'CHECKMARK'
                elif settings.last_render_status == 'FAILED':
                    icon = 'ERROR'
                elif settings.last_render_status == 'CANCELLED':
                    icon = 'CANCEL'
                
                box = layout.box()
                row = box.row()
                row.label(text=settings.last_render_message, icon=icon)
                # Clear button
                op = row.operator("rendercue.clear_status", text="", icon='X')
            else:
                layout.label(text="Idle", icon='SLEEP')

class VIEW3D_PT_render_cue(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_render_cue"
    bl_label = "RenderCue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "RenderCue"
    
    def draw(self, context):
        # Use the same draw method from the mixin
        RenderCuePanelMixin.draw(self, context)

class RENDERCUE_OT_clear_status(bpy.types.Operator):
    bl_idname = "rendercue.clear_status"
    bl_label = "Clear Status"
    bl_description = "Clear the last render status message"
    
    def execute(self, context):
        context.window_manager.rendercue.last_render_status = 'NONE'
        context.window_manager.rendercue.last_render_message = ""
        return {'FINISHED'}

class SEQUENCER_PT_render_cue(bpy.types.Panel):
    bl_idname = "SEQUENCER_PT_render_cue"
    bl_label = "RenderCue"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "RenderCue"
    
    def draw(self, context):
        # Use the same draw method from the mixin
        RenderCuePanelMixin.draw(self, context)

def draw_status_bar(self, context):
    settings = context.window_manager.rendercue
    if settings.is_rendering:
        self.layout.label(text=f"RenderCue: {settings.progress_message} | ETR: {settings.etr}", icon='RENDER_ANIMATION')

def register():
    bpy.utils.register_class(RENDER_UL_render_cue_jobs)
    bpy.utils.register_class(RENDER_PT_render_cue)
    bpy.utils.register_class(RENDERCUE_MT_presets_menu)
    bpy.utils.register_class(RENDER_PT_render_cue_dashboard)
    bpy.utils.register_class(VIEW3D_PT_render_cue)
    # bpy.utils.register_class(VIEW3D_PT_render_cue) # Duplicate removed
    bpy.utils.register_class(SEQUENCER_PT_render_cue)
    bpy.utils.register_class(RENDERCUE_OT_clear_status)
    
    # Register Status Bar
    bpy.types.WindowManager.draw_status.append(draw_status_bar)

def unregister():
    # Unregister Status Bar
    bpy.types.WindowManager.draw_status.remove(draw_status_bar)
    
    bpy.utils.unregister_class(RENDERCUE_OT_clear_status)
    bpy.utils.unregister_class(SEQUENCER_PT_render_cue)
    bpy.utils.unregister_class(VIEW3D_PT_render_cue)
    bpy.utils.unregister_class(RENDER_PT_render_cue_dashboard)
    bpy.utils.unregister_class(RENDERCUE_MT_presets_menu)
    bpy.utils.unregister_class(RENDER_PT_render_cue)
    bpy.utils.unregister_class(RENDER_UL_render_cue_jobs)

