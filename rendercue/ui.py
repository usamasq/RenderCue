import bpy
import bpy.utils.previews
import os
import time
from .constants import (
    UI_RESOLUTION_PERCENTAGE_BASE, UI_BANNER_SCALE, UI_SPACER_SCALE,
    UI_QUEUE_PREVIEW_BEFORE, UI_QUEUE_PREVIEW_AFTER, UI_MAX_JOB_NAME_LENGTH,
    UI_PREVIEW_COLLECTION_KEY, UI_STATUS_ICONS
)
from . import ui_helpers

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

def draw_queue_health_panel(layout, context):
    """Display queue validation status (HIG: Feedback)."""
    from . import ui_helpers
    
    settings = context.window_manager.rendercue
    if not settings.jobs:
        return  # No queue, no health to show
    
    validation = ui_helpers.get_queue_validation_summary(context)
    
    # Always create box to prevent layout shift
    health_box = layout.box()
    
    # Error State (Red)
    if validation['errors']:
        health_box.alert = True
        
        # Header
        header = health_box.row()
        header.scale_y = 0.9
        header.label(
            text=f"{len(validation['errors'])} Critical Issue(s)",
            icon='CANCEL'
        )
        
        # Show first 2 errors (HIG: Clarity)
        for error in validation['errors'][:2]:
            row = health_box.row()
            row.scale_y = 0.7
            row.label(text=f"• {error}")
        
        # "More" indicator
        if len(validation['errors']) > 2:
            row = health_box.row()
            row.scale_y = 0.7
            row.label(text=f"... +{len(validation['errors']) - 2} more")
        
        # Action button
        row = health_box.row()
        row.operator(
            "rendercue.validate_queue",
            icon='CHECKMARK',
            text="View All Issues"
        )
        
    # Warning State (Orange)
    elif validation['warnings']:
        header = health_box.row()
        header.scale_y = 0.9
        header.label(
            text=f"{len(validation['warnings'])} Warning(s)",
            icon='INFO'
        )
        # Orange tint for warnings
        sub = header.row()
        sub.alert = True
        sub.label(text="")
        
        # Show first 2 warnings
        for warning in validation['warnings'][:2]:
            row = health_box.row()
            row.scale_y = 0.7
            row.label(text=f"⚠ {warning}")
        
        if len(validation['warnings']) > 2:
            row = health_box.row()
            row.scale_y = 0.7
            row.label(text=f"... +{len(validation['warnings']) - 2} more")
            
    # Success State (Green/Dimmed)
    else:
        row = health_box.row()
        row.enabled = False
        row.label(text="Queue Ready", icon='CHECKMARK')

class RenderCuePanelMixin:
    """Mixin class for shared panel drawing logic."""
    bl_label = "RenderCue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    

    
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        settings = context.window_manager.rendercue
        
        # Progress Indicator

        
        # Rendering Progress
        if settings.is_rendering:
            self.draw_rendering_ui(layout, settings, context)
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
            # Subtle notification row instead of box
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(text="Saved queue data found", icon='INFO')
            row.operator("rendercue.load_data", icon='IMPORT', text="Load")
            
        row = layout.row()
        row.template_list("RENDER_UL_render_cue_jobs", "", settings, "jobs", settings, "active_job_index")
        
        # Side buttons for list
        col = row.column(align=True)
        col.operator("rendercue.add_job", icon='ADD', text="")
        col.operator("rendercue.remove_job", icon='REMOVE', text="")
        col.separator()
        col.operator("rendercue.move_job", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("rendercue.move_job", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        if not settings.jobs:
            # Helper message for empty state
            row = layout.row()
            row.alignment = 'CENTER'
            row.enabled = False
            row.label(text="No jobs. Click + or 'Add All Scenes' to start.")
        
        layout.separator()
        draw_queue_health_panel(layout, context)
        layout.separator()
        
        # Queue Tools
        
        # Scene Availability Info
        stats = ui_helpers.get_scene_statistics(context)
        
        # Always show info row
        info_row = layout.row()
        info_row.scale_y = 0.75
        
        if stats['total'] == 0:
            info_row.enabled = False
            info_row.label(text="No scenes in file", icon='INFO')
        elif stats['available'] > 0:
            info_row.label(text=f"{stats['available']} scene(s) can be added", icon='ADD')
        elif stats['with_cameras'] == 0:
            info_row.alert = True
            info_row.label(text="No scenes have cameras assigned", icon='ERROR')
        else:
            info_row.enabled = False
            info_row.label(text="All scenes with cameras in queue", icon='CHECKMARK')

        row = layout.row(align=True)
        row.scale_y = 1.2
        
        btn_text = "Add All Scenes"
        if stats['available'] > 0:
            btn_text = f"Add All Scenes ({stats['available']})"
            
        row.operator("rendercue.populate_all", icon='SCENE_DATA', text=btn_text)
        
        # Check for mixed engines
        warning = ui_helpers.get_mixed_engine_warning(settings)
        
        warn_row = layout.row()
        warn_row.scale_y = 0.8
        
        if warning:
            # Informational only - mixed engines is a valid choice
            warn_row.label(text=warning, icon='INFO')
        else:
            warn_row.enabled = False
            warn_row.label(text="All jobs use same engine", icon='CHECKMARK')

        row.menu("RENDERCUE_MT_presets_menu", icon='PRESET', text="Presets")
        
        layout.separator()
        
        # Output Configuration Group
        box = layout.box()
        row = box.row(align=True)
        
        # Split Header: Title (Left) | Icon (Right)
        split = row.split(factor=0.6)
        
        # Left: Toggle
        left = split.row(align=True)
        left.alignment = 'LEFT'
        left.prop(
            settings, 
            "ui_show_output", 
            icon='TRIA_DOWN' if settings.ui_show_output else 'TRIA_RIGHT',
            text="Global Output",
            emboss=False
        )
        
        # Right: Icon
        right = split.row(align=True)
        right.alignment = 'RIGHT'
        right.label(text="", icon='FILE_FOLDER')
        
        if settings.ui_show_output:
            col = box.column(align=True)
            col.use_property_split = True
            col.use_property_decorate = False
            
            # Location Selector (Segmented)
            col.prop(settings, "output_location", expand=True)
            
            if settings.output_location == 'CUSTOM':
                # Custom Path Input
                row = col.row(align=True)
                row.prop(settings, "global_output_path", text="Path")
                # Browse Button
                op = row.operator("rendercue.browse_path", icon='FILE_FOLDER', text="")
                op.target_property = "global_output_path"
                
            # Visual Path Preview
            col.separator()
            preview_box = box.box()
            preview_box.scale_y = 0.8
            
            row = preview_box.row()
            row.alignment = 'LEFT'
            
            if settings.output_location == 'DEFAULT':
                row.label(text="Path: // [Scene Name] /", icon='FILE_BLEND')
            else:
                row.label(text="Path: [Custom] / [Scene Name] /", icon='FILE_FOLDER')
        
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
            override_info = ui_helpers.get_override_summary(job)
            row = box.row(align=True)
            
            # Split Header
            split = row.split(factor=0.7)
            
            # Left: Title
            left = split.row(align=True)
            left.alignment = 'LEFT'
            
            header_text = f"Overrides: {job.scene.name if job.scene else 'None'}"
            if override_info['count'] > 0:
                header_text += f" ({override_info['count']} active)"
                
            left.prop(
                settings,
                "ui_show_overrides_main",
                icon='TRIA_DOWN' if settings.ui_show_overrides_main else 'TRIA_RIGHT',
                text=header_text,
                emboss=False
            )
            
            # Right: Icon
            right = split.row(align=True)
            right.alignment = 'RIGHT'
            right.label(text="", icon='MODIFIER')

            if settings.ui_show_overrides_main:
                # Collapsible Summary (Dashboard)
                # Always show summary box to prevent layout shift
                summary_box = box.box()
                summary_header = summary_box.row()
                
                if override_info['count'] > 0:
                    summary_header.prop(
                        settings,
                        "ui_show_override_summary",
                        icon='TRIA_DOWN' if settings.ui_show_override_summary else 'TRIA_RIGHT',
                        text=f"Active Overrides ({override_info['count']})",
                        emboss=False
                    )
                    
                    if settings.ui_show_override_summary:
                        summary_col = summary_box.column(align=True)
                        # Removed scale_y reduction for better spacing
                        
                        for name, value, bool_prop, val_prop in override_info['overrides']:
                            row = summary_col.row(align=True)
                            
                            # Split Layout: Label (40%) | Value (30%) | Button (30%)
                            split = row.split(factor=0.4)
                            split.label(text=name, icon='DOT')
                            
                            sub = split.split(factor=0.5)
                            sub.label(text=value)
                            
                            # Apply to All Button
                            op = sub.operator("rendercue.apply_override_to_all", text="Apply to All", icon='DUPLICATE')
                            op.data_path_bool = bool_prop
                            op.data_path_val = val_prop
                else:
                    # Show empty state (dimmed, no collapse icon)
                    row = summary_header.row()
                    row.enabled = False
                    row.label(text="No Active Overrides", icon='INFO')
                
                # Create parent column for all collapsible sections
                parent_col = box.column(align=True)
                parent_col.separator()
                
                # Helper for collapsible group styling
                def draw_collapsible_box(layout, settings, prop_name, title, icon, is_active=False):
                    box = layout.box()
                    row = box.row(align=True)
                    
                    # Split Header: Title (Left) | Status & Icon (Right)
                    split = row.split(factor=0.6)
                    
                    # Left: Toggle
                    left = split.row(align=True)
                    left.alignment = 'LEFT'
                    
                    is_expanded = getattr(settings, prop_name)
                    icon_state = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
                    
                    left.prop(settings, prop_name, icon=icon_state, text=title, emboss=False)
                    
                    # Right: Status + Icon
                    right = split.row(align=True)
                    right.alignment = 'RIGHT'
                    
                    if is_active:
                        right.label(text="[Active]", icon='CHECKMARK')
                        right.separator()
                    
                    right.label(text="", icon=icon)
                    
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
                    row.prop(job, "override_output", text="Output Path")
                    
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
                    


                    # Camera Override
                    row = col.row(align=True)
                    row.prop(job, "override_camera", text="Camera")
                    
                    if job.override_camera:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "camera", text="Camera")
                    


                    # Transparent Background
                    row = col.row(align=True)
                    row.prop(job, "override_transparent", text="Transparent Background")
                    
                    if job.override_transparent:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "film_transparent", text="Transparent")
                    


                    # Compositor
                    row = col.row(align=True)
                    row.prop(job, "override_compositor", text="Compositor")
                    
                    if job.override_compositor:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "use_compositor", text="Enable")
                        

                
                # Group: Range & Resolution
                is_dim_active = (job.override_frame_range or job.override_frame_step or 
                                job.override_resolution)
                col = draw_collapsible_box(parent_col, settings, "ui_show_dimensions", "Range & Resolution", 'SETTINGS', is_active=is_dim_active)

                if col:
                    # Frame Range
                    row = col.row(align=True)
                    row.prop(job, "override_frame_range", text="Frame Range")
                    

                    
                    if job.override_frame_range:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        
                        sub_col.prop(job, "frame_start", text="Start")
                        sub_col.prop(job, "frame_end", text="End")



                    # Frame Step
                    row = col.row(align=True)
                    row.prop(job, "override_frame_step", text="Frame Step")
                    
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
                    


                    # Resolution
                    row = col.row(align=True)
                    row.prop(job, "override_resolution", text="Resolution")
                    

                    
                    if job.override_resolution:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "resolution_scale", text="Scale %")
                        

                
                # Group: Format
                col = draw_collapsible_box(parent_col, settings, "ui_show_format", "Format", 'IMAGE_DATA', is_active=job.override_format)
                
                if col:
                    row = col.row(align=True)
                    row.prop(job, "override_format", text="Format")
                    

                    
                    col.separator()
                    
                    if job.override_format:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "render_format", text="File Format")
                        

                
                # Group: Render
                is_render_active = (job.override_engine or job.override_view_layer or
                                   job.override_samples or job.override_denoising or
                                   job.override_device or job.override_time_limit or
                                   job.override_persistent_data)
                col = draw_collapsible_box(parent_col, settings, "ui_show_render", "Render", 'RESTRICT_RENDER_OFF', is_active=is_render_active)

                if col:
                    # Engine
                    row = col.row(align=True)
                    row.prop(job, "override_engine", text="Engine")
                    

                    
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
                        row.prop(job, "override_samples", text="Samples")
                        

                        
                        if job.override_samples:
                            sub_col = col.column(align=True)
                            sub_col.use_property_split = True
                            sub_col.use_property_decorate = False
                            sub_col.prop(job, "samples", text="Samples")
                        

                    
                    # === Cycles-Only Section ===
                    if effective_engine == 'CYCLES':
                        col.separator()
                        col.label(text="Cycles Settings", icon='SETTINGS')
                        
                        # Denoising
                        row = col.row(align=True)
                        row.prop(job, "override_denoising", text="Denoising")
                        if job.override_denoising:
                            sub_col = col.column(align=True)
                            sub_col.use_property_split = True
                            sub_col.use_property_decorate = False
                            sub_col.prop(job, "use_denoising", text="Denoise")

                        
                        # Device
                        row = col.row(align=True)
                        row.prop(job, "override_device", text="Device")
                        if job.override_device:
                            sub_col = col.column(align=True)
                            sub_col.use_property_split = True
                            sub_col.use_property_decorate = False
                            sub_col.prop(job, "device", text="Device")

                        
                        # Time Limit
                        row = col.row(align=True)
                        row.prop(job, "override_time_limit", text="Time Limit")
                        if job.override_time_limit:
                            sub_col = col.column(align=True)
                            sub_col.use_property_split = True
                            sub_col.use_property_decorate = False
                            sub_col.prop(job, "time_limit", text="Time Limit")

                        
                        # Persistent Data
                        row = col.row(align=True)
                        row.prop(job, "override_persistent_data", text="Persistent Data")
                        if job.override_persistent_data:
                            sub_col = col.column(align=True)
                            sub_col.use_property_split = True
                            sub_col.use_property_decorate = False
                            sub_col.prop(job, "use_persistent_data", text="Persistent Data")

                    



                    # View Layer
                    if job.scene and len(job.scene.view_layers) > 1:
                        row = col.row(align=True)
                        row.prop(job, "override_view_layer", text="View Layer")
                        

                        
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

class RENDERCUE_MT_apply_to_all_menu(bpy.types.Menu):
    bl_label = "Apply to All Jobs"
    bl_idname = "RENDERCUE_MT_apply_to_all_menu"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        if not settings.jobs or settings.active_job_index < 0:
            return
            
        job = settings.jobs[settings.active_job_index]
        
        # Helper to add item
        def add_item(prop_bool, prop_val, text):
            if getattr(job, prop_bool):
                op = layout.operator("rendercue.apply_override_to_all", text=text)
                op.data_path_bool = prop_bool
                op.data_path_val = prop_val

        # Add items based on active overrides
        add_item("override_output", "output_path", "Output Path")
        add_item("override_camera", "camera", "Camera")
        add_item("override_transparent", "film_transparent", "Transparent Background")
        add_item("override_compositor", "use_compositor", "Compositor")
        add_item("override_frame_range", "frame_range", "Frame Range")
        add_item("override_frame_step", "frame_step", "Frame Step")
        add_item("override_resolution", "resolution_scale", "Resolution")
        add_item("override_format", "render_format", "Format")
        add_item("override_engine", "render_engine", "Engine")
        add_item("override_samples", "samples", "Samples")
        add_item("override_denoising", "use_denoising", "Denoising")
        add_item("override_device", "device", "Device")
        add_item("override_time_limit", "time_limit", "Time Limit")
        add_item("override_persistent_data", "use_persistent_data", "Persistent Data")
        add_item("override_view_layer", "view_layer", "View Layer")

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
        
        # Always use a box for consistent layout
        box = layout.box()
        
        if settings.is_rendering:
            box.label(text="Status: RENDERING", icon='RENDER_ANIMATION')
            box.prop(settings, "progress_message", text="")
            
            row = box.row()
            row.label(text=f"Job: {settings.current_job_index + 1}/{settings.total_jobs_count}")
            row.label(text=f"ETR: {settings.etr}")
        
        elif settings.last_render_status != 'NONE':
            icon = 'INFO'
            if settings.last_render_status == 'SUCCESS':
                icon = 'CHECKMARK'
            elif settings.last_render_status == 'FAILED':
                icon = 'ERROR'
            elif settings.last_render_status == 'CANCELLED':
                icon = 'CANCEL'
            
            row = box.row()
            row.label(text=settings.last_render_message, icon=icon)
            # Clear button
            op = row.operator("rendercue.clear_status", text="", icon='X')
            
        else:
            # Idle state
            box.label(text="Status: Idle", icon='PAUSE')

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
    else:
        # Check for completion message
        try:
            # We need to access preferences safely
            addon_name = __package__ if __package__ else "RenderCue"
            if addon_name in context.preferences.addons:
                prefs = context.preferences.addons[addon_name].preferences
                
                if prefs.show_completion_statusbar and settings.completion_statusbar_timestamp > 0:
                    import time
                    elapsed = time.time() - settings.completion_statusbar_timestamp
                    if elapsed < prefs.statusbar_display_seconds:
                        # Show completion message
                        icon = 'CHECKMARK' if settings.summary_failed_jobs == 0 else 'ERROR'
                        msg = f"RenderCue: Completed {settings.summary_successful_jobs}/{settings.summary_total_jobs} jobs ({settings.summary_total_frames} frames) in {settings.summary_render_time}"
                        if settings.summary_failed_jobs > 0:
                            msg += f" | {settings.summary_failed_jobs} Failed"
                        self.layout.label(text=msg, icon=icon)
        except Exception:
            pass # Fail silently in status bar draw

def register():
    bpy.utils.register_class(RENDER_UL_render_cue_jobs)
    bpy.utils.register_class(RENDER_PT_render_cue)
    bpy.utils.register_class(RENDERCUE_MT_apply_to_all_menu)
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
        RENDERCUE_MT_apply_to_all_menu,
        RENDER_PT_render_cue,
        RENDER_UL_render_cue_jobs,
    ):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
