import bpy
import os

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
        
        # Override Indicators (Visual feedback)
        sub = row.row(align=True)
        sub.scale_x = 0.8
        
        if item.override_output:
            sub.label(icon='FILE_FOLDER')
        if item.override_frame_range:
            sub.label(icon='TIME')
        if item.override_format:
            sub.label(icon='IMAGE_DATA')
        if item.override_view_layer:
            sub.label(icon='RENDERLAYERS')
            
        # Renderer Info
        # Check for override first
        if item.override_engine:
            r_engine = item.render_engine
        else:
            r_engine = item.scene.render.engine
            
        icon_engine = 'SHADING_RENDERED'
        engine_name = r_engine
        
        if r_engine == 'CYCLES':
            icon_engine = 'PMARKER_ACT'
            engine_name = "Cycles"
        elif r_engine == 'BLENDER_EEVEE':
            icon_engine = 'LIGHT_SUN'
            engine_name = "Eevee"
            
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
            
        # Samples with clearer label
        samples = 0
        
        # Determine samples based on engine (override or scene)
        if item.override_samples:
            samples = item.samples
        else:
            # Get scene samples
            if r_engine == 'CYCLES':
                samples = item.scene.cycles.samples
            elif r_engine == 'BLENDER_EEVEE':
                try:
                    samples = item.scene.eevee.taa_render_samples
                except AttributeError:
                    try:
                        samples = item.scene.eevee.samples
                    except AttributeError:
                        samples = 0
        
        if item.override_samples:
            row.label(text=f"Samples: {samples}", icon='MODIFIER')
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
        
        # Banner
        if not settings.banner_image:
            # Try to load banner
            banner_name = "RenderCue.jpg"
            if banner_name in bpy.data.images:
                settings.banner_image = bpy.data.images[banner_name]
            else:
                addon_dir = os.path.dirname(__file__)
                banner_path = os.path.join(addon_dir, banner_name)
                if os.path.exists(banner_path):
                    try:
                        img = bpy.data.images.load(banner_path, check_existing=True)
                        img.name = banner_name
                        settings.banner_image = img
                    except:
                        pass
        
        if settings.banner_image:
            row = layout.row()
            row.scale_y = 0.5 # Adjust if needed, but template_image handles aspect ratio usually
            # Use template_ID_preview for a cleaner look without open/new buttons if possible, 
            # but template_image is standard. compact=True hides some controls.
            layout.template_image(settings, "banner_image", image_user=None, compact=True)
            layout.separator()
        
        
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
                box.separator()
                box.label(text="Last Rendered Frame:", icon='IMAGE_DATA')
                col = box.column()
                # Use template_ID_preview instead of template_image for dynamic images
                col.template_ID_preview(settings, "preview_image", rows=4, cols=6)
            
            # Control Buttons - IMPORTANT: Draw these BEFORE disabling layout!
            box.separator()
            row = box.row(align=True)
            row.scale_y = 1.5
            
            if settings.is_paused:
                row.operator("rendercue.resume_render", icon='PLAY', text="Resume")
            else:
                row.operator("rendercue.pause_render", icon='PAUSE', text="Pause")
                
            row.operator("rendercue.stop_render", icon='CANCEL', text="Stop")
            
            
            # Return early - don't draw the job queue UI below
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
        
        # Queue Tools
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("rendercue.populate_all", icon='SCENE_DATA', text="Add All Scenes")
        row.menu("RENDERCUE_MT_presets_menu", icon='PRESET', text="Presets")
        
        layout.separator()
        
        # Batch Settings Group
        box = layout.box()
        box.label(text="Batch Settings", icon='PREFERENCES')
        col = box.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        
        col.prop(settings, "output_structure", text="Structure")
        
        row = col.row(align=True)
        row.prop(settings, "global_output_path", text="Output Path")
        row.operator("rendercue.open_output_folder", icon='EXTERNAL_DRIVE', text="")
        
        # Selected Job Settings (Overrides)
        if settings.jobs and settings.active_job_index >= 0 and len(settings.jobs) > settings.active_job_index:
            job = settings.jobs[settings.active_job_index]
            layout.separator()
            box = layout.box()
            
            # Header
            row = box.row()
            row.label(text=f"Overrides: {job.scene.name if job.scene else 'None'}", icon='MODIFIER')
            
            # Use a cleaner layout for overrides
            col = box.column(align=True)
            col.use_property_split = False
            col.use_property_decorate = False
            
            # Helper to draw override with "Apply to All"
            def draw_override_row(prop_bool, prop_val, name, data_path_bool, data_path_val):
                row = col.row(align=True)
                # Checkbox
                row.prop(job, prop_bool, text=name)
                
                # Value (only if enabled)
                sub = row.row(align=True)
                sub.active = getattr(job, prop_bool)
                sub.prop(job, prop_val, text="")
                
                # Apply to All Button
                op = row.operator("rendercue.apply_override_to_all", text="", icon='DUPLICATE')
                op.data_path_bool = data_path_bool
                op.data_path_val = data_path_val

            # Output
            draw_override_row("override_output", "output_path", "Output", "override_output", "output_path")
            
            # Frame Range (Special handling)
            row = col.row(align=True)
            row.prop(job, "override_frame_range", text="Frame Range")
            sub = row.row(align=True)
            sub.active = job.override_frame_range
            sub.prop(job, "frame_start", text="Start")
            sub.prop(job, "frame_end", text="End")
            
            op = row.operator("rendercue.apply_override_to_all", text="", icon='DUPLICATE')
            op.data_path_bool = "override_frame_range"
            op.data_path_val = "frame_range"

            # Resolution
            draw_override_row("override_resolution", "resolution_scale", "Resolution %", "override_resolution", "resolution_scale")
            
            # Format
            draw_override_row("override_format", "render_format", "Format", "override_format", "render_format")
            
            # Samples
            draw_override_row("override_samples", "samples", "Samples", "override_samples", "samples")

            # Render Engine
            draw_override_row("override_engine", "render_engine", "Engine", "override_engine", "render_engine")

            # View Layer (Smart Dropdown)
            if job.scene and len(job.scene.view_layers) > 1:
                row = col.row(align=True)
                row.prop(job, "override_view_layer", text="View Layer")
                
                sub = row.row(align=True)
                sub.active = job.override_view_layer
                # Use prop_search to create a dropdown from the scene's view layers
                sub.prop_search(job, "view_layer", job.scene, "view_layers", text="")
                
                op = row.operator("rendercue.apply_override_to_all", text="", icon='DUPLICATE')
                op.data_path_bool = "override_view_layer"
                op.data_path_val = "view_layer"
            
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0 # Make Render button very prominent
        row.operator("rendercue.batch_render", icon='RENDER_ANIMATION', text="Render Cue")

class RENDERCUE_MT_presets_menu(bpy.types.Menu):
    bl_label = "Presets"
    bl_idname = "RENDERCUE_MT_presets_menu"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Quick Settings")
        layout.operator("rendercue.quick_preset", text="Draft (50%, Low Samples)").preset_type = 'DRAFT'
        layout.operator("rendercue.quick_preset", text="Production (100%, High Samples)").preset_type = 'PRODUCTION'
        layout.separator()
        layout.label(text="Queue Presets")
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
    bpy.utils.register_class(RENDERCUE_OT_clear_status)
    
    # Register Status Bar
    bpy.types.STATUSBAR_HT_header.append(draw_status_bar)

def unregister():
    # Unregister Status Bar
    try:
        bpy.types.STATUSBAR_HT_header.remove(draw_status_bar)
    except (AttributeError, ValueError):
        pass
    
    for cls in (
        RENDERCUE_OT_clear_status,
        VIEW3D_PT_render_cue,
        RENDER_PT_render_cue_dashboard,
        RENDERCUE_MT_presets_menu,
        RENDER_PT_render_cue,
        RENDER_UL_render_cue_jobs,
    ):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

