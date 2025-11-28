import bpy
import bpy.utils.previews
import os

preview_collections = {}

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
                # Use template_icon with custom preview to show just the image
                # The preview is loaded into 'main' collection with key 'thumbnail'
                pcoll = preview_collections.get("main")
                if pcoll and "thumbnail" in pcoll:
                    # Scale 8.0 gives roughly 128px (16 * 8)
                    col.template_icon(icon_value=pcoll["thumbnail"].icon_id, scale=8.0)
                else:
                    col.label(text="No Preview Available")
            
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
        if not settings.jobs and bpy.data.texts.get(".rendercue_data"):
            box = layout.box()
            box.label(text="Found saved RenderCue data", icon='INFO')
            box.operator("rendercue.load_data", icon='IMPORT', text="Load Data")
            
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
        
        # Output Configuration Group
        box = layout.box()
        row = box.row()
        row.label(text="Output Configuration", icon='PREFERENCES')
        
        col = box.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        
        # Location Selector
        col.prop(settings, "output_location", expand=True)
        
        if settings.output_location == 'CUSTOM':
            # Custom Path Input
            row = col.row(align=True)
            row.prop(settings, "global_output_path", text="Path")
            # Browse Button
            op = row.operator("rendercue.browse_path", icon='FILE_FOLDER', text="")
            op.target_property = "global_output_path"
        else:
            # Informative Label for Default
            row = col.row()
            row.label(text="Base Path: // (Same as .blend file)", icon='FILE_BLEND')
            
        # Informative Label for Structure
        col.separator()
        row = col.row()
        row.label(text="Structure: [Base Path] / [Scene Name] /", icon='INFO')
        
        # Selected Job Settings (Overrides)
        if settings.jobs and settings.active_job_index >= 0 and len(settings.jobs) > settings.active_job_index:
            job = settings.jobs[settings.active_job_index]
            layout.separator()
            box = layout.box()
            
            # Header
            row = box.row()
            row.label(text=f"Overrides: {job.scene.name if job.scene else 'None'}", icon='MODIFIER')
            
            # Create parent column for all collapsible sections
            parent_col = box.column(align=True)
            parent_col.separator()
            
            # Helper for collapsible group styling
            def draw_collapsible_box(layout, settings, prop_name, title, icon, is_active=False):
                box = layout.box()
                row = box.row(align=True)
                
                # Toggle Icon
                is_expanded = getattr(settings, prop_name)
                icon_state = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
                
                # Header with toggle button
                row.prop(settings, prop_name, icon=icon_state, text=title, emboss=False)
                
                # Spacer to push icons to the right
                row.label(text="")
                
                # Active Indicator
                if is_active:
                    row.label(text="", icon='CHECKMARK')
                
                # Group Icon
                row.label(text="", icon=icon)
                
                if is_expanded:
                    # Add some padding inside the box
                    col = box.column(align=True)
                    col.separator()
                    return col
                return None

            # Group: Output
            col = draw_collapsible_box(parent_col, settings, "ui_show_output", "Output", 'FILE_FOLDER', is_active=job.override_output)
            
            if col:
                # Header Row (Checkbox + Apply Button)
                row = col.row(align=True)
                row.prop(job, "override_output", text="Output Path Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2 # Make button slightly wider for text
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_output"
                op.data_path_val = "output_path"
                
                col.separator() # Spacing
                
                # Content (Indented)
                if job.override_output:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    
                    row = sub_col.row(align=True)
                    row.prop(job, "output_path", text="Path")
                    # Browse Button
                    sub = row.row(align=True)
                    sub.scale_x = 1.0
                    op = sub.operator("rendercue.browse_path", icon='FILE_FOLDER', text="")
                    op.target_property = "job_output_path"
                    
                col.separator()

            # Group: Dimensions
            is_dim_active = job.override_frame_range or job.override_resolution
            col = draw_collapsible_box(parent_col, settings, "ui_show_dimensions", "Dimensions", 'CON_SIZELIKE', is_active=is_dim_active)

            if col:
                # Frame Range
                row = col.row(align=True)
                row.prop(job, "override_frame_range", text="Frame Range Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_frame_range"
                op.data_path_val = "frame_range"
                
                col.separator()
                
                if job.override_frame_range:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    
                    sub_col.prop(job, "frame_start", text="Start")
                    sub_col.prop(job, "frame_end", text="End")

                col.separator()

                # Resolution
                row = col.row(align=True)
                row.prop(job, "override_resolution", text="Resolution Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_resolution"
                op.data_path_val = "resolution_scale"
                
                col.separator()
                
                if job.override_resolution:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "resolution_scale", text="Scale %")
                    
                col.separator()

            # Group: Format
            col = draw_collapsible_box(parent_col, settings, "ui_show_format", "Format", 'IMAGE_DATA', is_active=job.override_format)
            
            if col:
                row = col.row(align=True)
                row.prop(job, "override_format", text="Format Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_format"
                op.data_path_val = "render_format"
                
                col.separator()
                
                if job.override_format:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "render_format", text="File Format")
                    
                col.separator()

            # Group: Render
            is_render_active = job.override_engine or job.override_samples or job.override_view_layer
            col = draw_collapsible_box(parent_col, settings, "ui_show_render", "Render", 'RESTRICT_RENDER_OFF', is_active=is_render_active)

            if col:
                # Engine
                row = col.row(align=True)
                row.prop(job, "override_engine", text="Engine Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_engine"
                op.data_path_val = "render_engine"
                
                col.separator()
                
                if job.override_engine:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "render_engine", text="Engine")

                col.separator()

                # Samples
                row = col.row(align=True)
                row.prop(job, "override_samples", text="Samples Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_samples"
                op.data_path_val = "samples"
                
                col.separator()
                
                if job.override_samples:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "samples", text="Samples")

                col.separator()

                # View Layer
                if job.scene and len(job.scene.view_layers) > 1:
                    row = col.row(align=True)
                    row.prop(job, "override_view_layer", text="View Layer Override")
                    
                    sub = row.row(align=True)
                    sub.scale_x = 1.2
                    op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                    op.data_path_bool = "override_view_layer"
                    op.data_path_val = "view_layer"
                    
                    col.separator()
                    
                    if job.override_view_layer:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop_search(job, "view_layer", job.scene, "view_layers", text="Layer")
                    
                    col.separator()
            
        layout.separator()
        
        # Start Render Button
        # Use a box to match width of other sections
        box = layout.box()
        row = box.row()
        row.scale_y = 2.0
        row.operator("rendercue.batch_render", icon='RENDER_ANIMATION', text="START RENDER QUEUE")

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

    # Register Previews
    pcoll = bpy.utils.previews.new()
    preview_collections["main"] = pcoll

def unregister():
    # Unregister Status Bar
    try:
        bpy.types.STATUSBAR_HT_header.remove(draw_status_bar)
    except (AttributeError, ValueError):
        pass
    
    # Unregister Previews
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
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
