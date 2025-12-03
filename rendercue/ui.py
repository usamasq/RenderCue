import bpy
import bpy.utils.previews
import os
import time
from .constants import (
    UI_RESOLUTION_PERCENTAGE_BASE, UI_BANNER_SCALE, UI_SPACER_SCALE,
    UI_QUEUE_PREVIEW_BEFORE, UI_QUEUE_PREVIEW_AFTER, UI_MAX_JOB_NAME_LENGTH,
    UI_PREVIEW_COLLECTION_KEY, UI_STATUS_ICONS
)

preview_collections = {}

class RENDER_UL_render_cue_jobs(bpy.types.UIList):
    """UI List for displaying render jobs."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # item is RenderCueJob
        if not item.scene:
            layout.label(text="<Missing Scene>", icon='ERROR')
            return

        # Status icon (from constant mapping)
        status_icon = UI_STATUS_ICONS.get(item.render_status, 'QUESTION')

        # Main row
        row = layout.row(align=True)
        
        # Use Blender's alert system for failed jobs
        if item.render_status == 'FAILED':
            row.alert = True
        elif item.render_status == 'COMPLETED':
            row.active = True  # Highlight completed
            
        # Status icon
        row.label(text="", icon=status_icon)
        
        # Scene Name
        row.label(text=item.scene.name, translate=False)
        
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
        elif r_engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
            icon_engine = 'LIGHT_SUN'
            engine_name = "Eevee"
        elif r_engine == 'BLENDER_WORKBENCH':
            icon_engine = 'SHADING_SOLID'
            engine_name = "Workbench"
            
        row.label(text=engine_name, icon=icon_engine)
        
        # Resolution (actual dimensions)
        res_x = item.scene.render.resolution_x
        res_y = item.scene.render.resolution_y
        scale = item.scene.render.resolution_percentage
        if item.override_resolution:
            scale = item.resolution_scale
        
        # Calculate final resolution
        # Guard against zero scale
        safe_scale = max(1, scale)
        final_x = int(res_x * safe_scale / UI_RESOLUTION_PERCENTAGE_BASE)
        final_y = int(res_y * safe_scale / UI_RESOLUTION_PERCENTAGE_BASE)
        
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
            elif r_engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
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
    """Mixin class for shared panel drawing logic."""
    bl_label = "RenderCue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw_summary_banner(self, layout, settings, context):
        """Draw render completion summary banner."""
        
        # Auto-dismiss check
        if settings.summary_auto_dismiss_seconds > 0:
            elapsed = time.time() - settings.summary_timestamp
            if elapsed > settings.summary_auto_dismiss_seconds:
                settings.show_summary_banner = False
                return
        
        # Main banner
        banner = layout.box()
        banner.scale_y = UI_BANNER_SCALE
        
        # Header with status and dismiss
        header = banner.row(align=True)
        
        # Status icon based on results
        if settings.summary_failed_jobs == 0:
            header.label(text="RENDER COMPLETE", icon='CHECKMARK')
        elif settings.summary_successful_jobs > 0:
            header.label(text="RENDER COMPLETE (WITH ERRORS)", icon='ERROR')
        else:
            header.label(text="RENDER FAILED", icon='CANCEL')
        
        # Spacer
        spacer = header.row()
        spacer.scale_x = UI_SPACER_SCALE
        
        # Dismiss button
        dismiss = header.row()
        dismiss.alignment = 'RIGHT'
        dismiss.scale_x = 0.7
        dismiss.operator("rendercue.dismiss_banner", text="", icon='X', emboss=False)
        
        # Stats grid
        stats = banner.grid_flow(row_major=True, columns=3, align=True)
        stats.scale_y = 0.85
        
        # Column 1: Jobs
        col1 = stats.column(align=True)
        col1.label(text="Jobs", icon='PRESET')
        jobs_row = col1.row(align=True)
        jobs_row.label(text=str(settings.summary_total_jobs))
        
        # Column 2: Results
        col2 = stats.column(align=True)
        col2.label(text="Results", icon='CHECKMARK')
        result_row = col2.row(align=True)
        result_row.label(text=f"{settings.summary_successful_jobs}", icon='CHECKMARK')
        if settings.summary_failed_jobs > 0:
            fail_part = result_row.row(align=True)
            fail_part.alert = True
            fail_part.label(text=f"{settings.summary_failed_jobs}", icon='ERROR')
        
        # Column 3: Duration
        col3 = stats.column(align=True)
        col3.label(text="Duration", icon='TIME')
        col3.label(text=settings.summary_render_time)
        
        # Details row
        banner.separator(factor=0.3)
        details = banner.row()
        details.scale_y = 0.7
        details.label(text=f"{settings.summary_blend_file} • {settings.summary_total_frames} frames", icon='FILE_FOLDER')
    
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        settings = context.window_manager.rendercue
        
        # Progress Indicator
        # Summary Banner (if exists)
        if settings.show_summary_banner:
            self.draw_summary_banner(layout, settings, context)
        
        # Rendering Progress
        if settings.is_rendering:
            self.draw_rendering_ui(layout, settings, context)
            
            # Show queue in read-only mode (collapsed by default could be better, but let's keep it visible)
            layout.separator()
            layout.label(text="Current Queue", icon='LOCKED')
            row = layout.row()
            row.enabled = False # Disable interaction
            row.template_list("RENDER_UL_render_cue_jobs", "", settings, "jobs", settings, "active_job_index")
            return
            
        # Main UI (when not rendering)
        self.draw_main_ui(layout, settings, context)
            
    def draw_rendering_ui(self, layout, settings, context):
        """Enhanced rendering progress UI."""
        
        # Main progress box
        box = layout.box()
        box.scale_y = 1.1
        
        # Header
        header = box.row()
        header.label(text="Rendering in Progress", icon='RENDER_ANIMATION')
        
        # Overall Stats
        stats_box = box.box()
        stats_box.scale_y = 0.9
        
        # Row 1: Job progress
        row1 = stats_box.row(align=True)
        col1a = row1.column(align=True)
        col1a.label(text="Job:")
        col1a.label(text=f"{settings.current_job_index + 1} / {settings.total_jobs_count}")
        
        col1b = row1.column(align=True)
        col1b.label(text="Time Left:")
        col1b.label(text=settings.etr)
        
        # Row 2: Frame progress
        if settings.total_frames_to_render > 0:
            row2 = stats_box.row(align=True)
            frames_pct = (settings.finished_frames_count / settings.total_frames_to_render) * 100
            
            col2a = row2.column(align=True)
            col2a.label(text="Frames:")
            col2a.label(text=f"{settings.finished_frames_count} / {settings.total_frames_to_render}")
            
            col2b = row2.column(align=True)
            col2b.label(text="Progress:")
            col2b.label(text=f"{frames_pct:.0f}%")
        
        # Status message
        box.separator(factor=0.5)
        msg_row = box.row()
        msg_row.scale_y = 0.8
        msg_row.label(text=settings.progress_message, icon='INFO')
        
        # Queue Preview (COLLAPSIBLE)
        box.separator()
        queue_header = box.row()
        queue_header.prop(settings, "show_queue_preview", 
                         text="Queue Status", 
                         icon='TRIA_DOWN' if settings.show_queue_preview else 'TRIA_RIGHT',
                         emboss=False)
        
        if settings.show_queue_preview:
            self.draw_queue_preview(box, settings, context)
        
        # Thumbnail
        if settings.has_preview_image:
            # box.separator() # Removed extra padding
            thumb_header = box.row()
            thumb_header.prop(settings, "show_preview_thumbnail",
                            text="Last Frame",
                            icon='TRIA_DOWN' if settings.show_preview_thumbnail else 'TRIA_RIGHT',
                            emboss=False)
            
            if settings.show_preview_thumbnail:
                # Use template_icon for display-only thumbnail
                # This uses the preview collection loaded in render.py
                if UI_PREVIEW_COLLECTION_KEY in preview_collections:
                    pcoll = preview_collections[UI_PREVIEW_COLLECTION_KEY]
                    # Use dynamic key from settings to ensure we get the latest icon
                    icon_key = settings.preview_icon_key
                    if icon_key in pcoll:
                        col = box.column()
                        col.template_icon(icon_value=pcoll[icon_key].icon_id, scale=8.0)
        
        # Controls
        box.separator()
        controls = box.row(align=True)
        controls.scale_y = 1.5
        
        if settings.is_paused:
            controls.operator("rendercue.resume_render", icon='PLAY', text="Resume")
        else:
            controls.operator("rendercue.pause_render", icon='PAUSE', text="Pause")
        
        controls.operator("rendercue.stop_render", icon='CANCEL', text="Stop")
    
    def draw_queue_preview(self, layout, settings, context):
        """Draw mini queue list (SMART TRUNCATION)."""
        queue_box = layout.box()
        queue_box.scale_y = 0.85
        
        current_idx = settings.current_job_index
        total_jobs = len(settings.jobs)
        
        # Show current + prev 1 + next 4 (max visible)
        start_idx = max(0, current_idx - UI_QUEUE_PREVIEW_BEFORE)
        end_idx = min(total_jobs, current_idx + UI_QUEUE_PREVIEW_AFTER)
        
        # Show "..." if truncated at start
        if start_idx > 0:
            row = queue_box.row()
            row.scale_y = 0.7
            row.label(text=f"... {start_idx} jobs before", icon='THREE_DOTS')
        
        # Show job range
        for idx in range(start_idx, end_idx):
            if idx >= total_jobs:
                break
            
            job = settings.jobs[idx]
            row = queue_box.row(align=True)
            
            # Status icon
            status_icon = UI_STATUS_ICONS.get(job.render_status, 'QUESTION')
            
            # Alert for failures
            if job.render_status == 'FAILED':
                row.alert = True
            
            # Highlight current job
            if idx == current_idx:
                row.active = True
            
            row.label(text="", icon=status_icon)
            
            # Job name (truncated)
            if job.scene:
                job_name = job.scene.name[:UI_MAX_JOB_NAME_LENGTH]
                if len(job.scene.name) > UI_MAX_JOB_NAME_LENGTH:
                    job_name += "..."
            else:
                job_name = "No Scene"
            row.label(text=job_name)
            
            # Progress/Status
            if job.render_status == 'RENDERING' and job.total_frames > 0:
                pct = (job.completed_frames / job.total_frames) * 100
                row.label(text=f"{pct:.0f}%")
            elif job.render_status == 'COMPLETED':
                row.label(text="", icon='CHECKMARK')
            elif job.render_status == 'FAILED':
                row.label(text="", icon='ERROR')
        
        # Show "..." if truncated at end
        remaining = total_jobs - end_idx
        if remaining > 0:
            row = queue_box.row()
            row.scale_y = 0.7
            row.label(text=f"... {remaining} jobs after", icon='THREE_DOTS')

    def draw_main_ui(self, layout, settings, context):
        """Draw the main configuration UI."""
        # Main List
        if not settings.jobs and bpy.data.texts.get(".rendercue_data"):
            box = layout.box()
            box.label(text="Saved queue available", icon='INFO')
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
        
        # Check for mixed engines
        if settings.jobs:
            engines = set()
            for job in settings.jobs:
                if job.scene:
                    engine = job.render_engine if job.override_engine else job.scene.render.engine
                    engines.add(engine)
            
            if len(engines) > 1:
                # Show warning
                warning_row = layout.row()
                warning_row.alert = True
                warning_row.label(text=f"Queue has {len(engines)} different render engines", icon='ERROR')

        row.menu("RENDERCUE_MT_presets_menu", icon='PRESET', text="Presets")
        
        layout.separator()
        
        # Output Configuration Group
        box = layout.box()
        row = box.row()
        row.label(text="Output Settings", icon='PREFERENCES')
        
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
        if settings.jobs:
            # Clamp index to valid range
            if settings.active_job_index >= len(settings.jobs):
                settings.active_job_index = max(0, len(settings.jobs) - 1)
            
            if settings.active_job_index >= 0:
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
                row.alignment = 'LEFT'
                row.prop(settings, prop_name, icon=icon_state, text=title, emboss=False)
                
                # Spacer to push icons to the right
                row.label(text="")
                
                # Active Indicator
                if is_active:
                    row.label(text="[Active]", icon='CHECKMARK')
                
                # Group Icon
                row.label(text="", icon=icon)
                
                if is_expanded:
                    # Add some padding inside the box
                    col = box.column(align=True)
                    col.separator()
                    return col
                return None
            
            # Group: Output Settings
            is_output_active = (job.override_output or job.override_camera or 
                               job.override_transparent or job.override_compositor)
            col = draw_collapsible_box(parent_col, settings, "ui_show_output", "Output Settings", 'FILE_FOLDER', is_active=is_output_active)
            
            if col:
                # Output Path
                row = col.row(align=True)
                row.prop(job, "override_output", text="Output Path Override")
                
                if job.override_output:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    
                    row = sub_col.row(align=True)
                    row.prop(job, "output_path", text="Path")
                    sub = row.row(align=True)
                    sub.scale_x = 1.0
                    op = sub.operator("rendercue.browse_path", icon='FILE_FOLDER', text="")
                    op.target_property = "job_output_path"
                
                col.separator()

                # Camera Override
                row = col.row(align=True)
                row.prop(job, "override_camera", text="Camera Override")
                
                if job.override_camera:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "camera", text="Camera")
                
                col.separator()

                # Transparent Background
                row = col.row(align=True)
                row.prop(job, "override_transparent", text="Override Transparency")
                
                if job.override_transparent:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "film_transparent", text="Transparent")
                
                col.separator()

                # Compositor
                row = col.row(align=True)
                row.prop(job, "override_compositor", text="Compositor Override")
                
                if job.override_compositor:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "use_compositor", text="Use Compositor")
                    
                col.separator()
            
            # Group: Range & Resolution
            is_dim_active = (job.override_frame_range or job.override_frame_step or 
                            job.override_resolution)
            col = draw_collapsible_box(parent_col, settings, "ui_show_dimensions", "Range & Resolution", 'SETTINGS', is_active=is_dim_active)

            if col:
                # Frame Range
                row = col.row(align=True)
                row.prop(job, "override_frame_range", text="Frame Range Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_frame_range"
                op.data_path_val = "frame_range"
                
                if job.override_frame_range:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    
                    sub_col.prop(job, "frame_start", text="Start")
                    sub_col.prop(job, "frame_end", text="End")

                col.separator()

                # Frame Step
                row = col.row(align=True)
                row.prop(job, "override_frame_step", text="Frame Step Override")
                
                if job.override_frame_step:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "frame_step", text="Step")
                    
                    # Show estimated frames
                    if job.frame_step > 1:
                        total_frames = job.frame_end - job.frame_start + 1
                        render_frames = (total_frames + job.frame_step - 1) // job.frame_step
                        sub_col.label(text=f"Renders approx. {render_frames} frames", icon='INFO')
                
                col.separator()

                # Resolution
                row = col.row(align=True)
                row.prop(job, "override_resolution", text="Resolution Override")
                
                sub = row.row(align=True)
                sub.scale_x = 1.2
                op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                op.data_path_bool = "override_resolution"
                op.data_path_val = "resolution_scale"
                
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
                op = sub.operator("rendercue.apply_override_to_all", text="Override All", icon='DUPLICATE')
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
            is_render_active = (job.override_engine or job.override_view_layer or
                               job.override_samples or job.override_denoising or
                               job.override_device or job.override_time_limit or
                               job.override_persistent_data)
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
                
                if job.override_engine:
                    sub_col = col.column(align=True)
                    sub_col.use_property_split = True
                    sub_col.use_property_decorate = False
                    sub_col.prop(job, "render_engine", text="Engine")

                col.separator()
                
                # Determine effective engine
                effective_engine = job.render_engine if job.override_engine else (job.scene.render.engine if job.scene else 'CYCLES')



                # Samples (Cycles/Eevee only)
                if effective_engine in ['CYCLES', 'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
                    row = col.row(align=True)
                    row.prop(job, "override_samples", text="Samples Override")
                    
                    sub = row.row(align=True)
                    sub.scale_x = 1.2
                    op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                    op.data_path_bool = "override_samples"
                    op.data_path_val = "samples"
                    
                    if job.override_samples:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "samples", text="Samples")
                    
                    col.separator()
                
                # === Cycles-Only Section ===
                if effective_engine == 'CYCLES':
                    col.separator()
                    col.label(text="Cycles Settings", icon='SETTINGS')
                    
                    # Denoising
                    row = col.row(align=True)
                    row.prop(job, "override_denoising", text="Denoising Override")
                    if job.override_denoising:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "use_denoising", text="Denoise")
                    col.separator()
                    
                    # Device
                    row = col.row(align=True)
                    row.prop(job, "override_device", text="Device Override")
                    if job.override_device:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "device", text="Device")
                    col.separator()
                    
                    # Time Limit
                    row = col.row(align=True)
                    row.prop(job, "override_time_limit", text="Time Limit Override")
                    if job.override_time_limit:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "time_limit", text="Time Limit")
                    col.separator()
                    
                    # Persistent Data
                    row = col.row(align=True)
                    row.prop(job, "override_persistent_data", text="Persistent Data Override")
                    if job.override_persistent_data:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "use_persistent_data", text="Persistent Data")
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
    """Menu for RenderCue presets."""
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
    """Main RenderCue panel in the Render properties tab."""
    bl_idname = "RENDER_PT_render_cue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

class RENDER_PT_render_cue_dashboard(RenderCuePanelMixin, bpy.types.Panel):
    """Dashboard panel for monitoring render progress."""
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

class VIEW3D_PT_render_cue(RenderCuePanelMixin, bpy.types.Panel):
    """RenderCue panel in the 3D Viewport sidebar."""
    bl_idname = "VIEW3D_PT_render_cue"
    bl_label = "RenderCue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "RenderCue"
    bl_context = "" 
    
    def draw(self, context):
        # Use the same draw method from the mixin
        RenderCuePanelMixin.draw(self, context)

class RENDERCUE_OT_clear_status(bpy.types.Operator):
    """Clear the last render status message."""
    bl_idname = "rendercue.clear_status"
    bl_label = "Clear Status"
    bl_description = "Clear the last render status message"
    
    def execute(self, context):
        context.window_manager.rendercue.last_render_status = 'NONE'
        context.window_manager.rendercue.last_render_message = ""
        return {'FINISHED'}

def draw_status_bar(self, context):
    """Draw RenderCue status in the Blender status bar."""
    settings = context.window_manager.rendercue
    if settings.is_rendering:
        self.layout.label(text=f"RenderCue: {settings.progress_message} | ETR: {settings.etr}", icon='RENDER_ANIMATION')

def register():
    bpy.utils.register_class(RENDER_UL_render_cue_jobs)
    bpy.utils.register_class(RENDER_PT_render_cue)
    bpy.utils.register_class(RENDERCUE_MT_presets_menu)
    bpy.utils.register_class(RENDER_PT_render_cue_dashboard)
    bpy.utils.register_class(VIEW3D_PT_render_cue)
    bpy.utils.register_class(RENDERCUE_OT_clear_status)
    
    # Register Status Bar
    bpy.types.STATUSBAR_HT_header.append(draw_status_bar)

    # Register Previews
    pcoll = bpy.utils.previews.new()
    preview_collections[UI_PREVIEW_COLLECTION_KEY] = pcoll

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
