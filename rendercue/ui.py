"""
RenderCue UI Module

This module defines the user interface for the RenderCue addon, including:
- Panels (Render Properties, 3D Viewport)
- UI Lists (Job Queue)
- Menus (Presets, Context Menus)
- Drawing functions for custom UI elements (Dashboard, Status Bar)
"""

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
from . import version_compat

preview_collections = {}

class RENDER_UL_render_cue_jobs(bpy.types.UIList):
    """UI List for displaying render jobs."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # item is RenderCueJob
        if not item.scene:
            layout.label(text="<Missing Scene>", icon=version_compat.get_icon('ERROR'))
            return

        # Check if job is valid (has camera)
        has_camera = item.scene.camera is not None
        has_camera_override = item.override_camera and item.camera is not None
        is_valid = has_camera or has_camera_override

        # Status icon (from constant mapping)
        status_icon = UI_STATUS_ICONS.get(item.render_status, 'QUESTION')
        
        # Override status icon for invalid jobs
        if not is_valid:
            status_icon = 'ERROR'

        # === CLEAN DESIGN: Status | Name | Switch | Frames ===
        row = layout.row(align=True)
        
        # Visual styling based on status
        if not is_valid:
            row.alert = True  # Red highlight for invalid
        elif item.render_status == 'FAILED':
            row.alert = True
        elif item.render_status == 'COMPLETED':
            row.active = False  # Muted for completed
            
        # 1. Status Icon
        row.label(text="", icon=version_compat.get_icon(status_icon))
        
        # 2. Scene Name (with "no camera" suffix if invalid)
        name_text = item.scene.name
        if not is_valid:
            name_text += " (no camera)"
        row.label(text=name_text, translate=False)
        
        # 3. Switch Scene Button (quick action)
        op = row.operator("rendercue.switch_to_job_scene", text="", icon=version_compat.get_icon('RESTRICT_VIEW_OFF'))
        op.index = index
        
        # 4. Frame Range (right-aligned, compact)
        if item.override_frame_range:
            start = item.frame_start
            end = item.frame_end
        else:
            start = item.scene.frame_start
            end = item.scene.frame_end
        
        # Determine step
        if item.override_frame_step:
            step = item.frame_step
        else:
            step = item.scene.frame_step
        
        # Calculate frame count
        if step > 0:
            frame_count = ((end - start) // step) + 1
        else:
            frame_count = end - start + 1
        
        # Compact frame display
        sub = row.row()
        sub.alignment = 'RIGHT'
        if start == end:
            sub.label(text=f"{start}")
        else:
            sub.label(text=f"{start}-{end} ({frame_count}f)")



def draw_queue_health_panel(layout, context):
    """Deprecated - issues now shown in Scene Summary."""
    pass  # Issues displayed in Scene Summary card instead

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
        header.label(text="Rendering in Progress", icon=version_compat.get_icon('RENDER_ANIMATION'))
        
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
        msg_row.label(text=settings.progress_message, icon=version_compat.get_icon('INFO'))
        
        # Queue Preview (COLLAPSIBLE)
        box.separator()
        queue_header = box.row()
        queue_header.prop(settings, "show_queue_preview", 
                         text="Queue Status", 
                         icon=version_compat.get_icon('TRIA_DOWN') if settings.show_queue_preview else version_compat.get_icon('TRIA_RIGHT'),
                         emboss=False)
        
        if settings.show_queue_preview:
            self.draw_queue_preview(box, settings, context)
        
        # Thumbnail
        if settings.has_preview_image:
            # box.separator() # Removed extra padding
            thumb_header = box.row()
            thumb_header.prop(settings, "show_preview_thumbnail",
                            text="Last Frame",
                            icon=version_compat.get_icon('TRIA_DOWN') if settings.show_preview_thumbnail else version_compat.get_icon('TRIA_RIGHT'),
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
            controls.operator("rendercue.resume_render", icon=version_compat.get_icon('PLAY'), text="Resume")
        else:
            controls.operator("rendercue.pause_render", icon=version_compat.get_icon('PAUSE'), text="Pause")
        
        controls.operator("rendercue.stop_render", icon=version_compat.get_icon('CANCEL'), text="Stop")
    
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
            row.label(text=f"... {start_idx} jobs before", icon=version_compat.get_icon('THREE_DOTS'))
        
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
            
            row.label(text="", icon=version_compat.get_icon(status_icon))
            
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
                row.label(text="", icon=version_compat.get_icon('CHECKMARK'))
            elif job.render_status == 'FAILED':
                row.label(text="", icon=version_compat.get_icon('ERROR'))
        
        # Show "..." if truncated at end
        remaining = total_jobs - end_idx
        if remaining > 0:
            row = queue_box.row()
            row.scale_y = 0.7
            row.label(text=f"... {remaining} jobs after", icon=version_compat.get_icon('THREE_DOTS'))

    def draw_main_ui(self, layout, settings, context):
        """Draw the main configuration UI."""
        # Main List
        if not settings.jobs and bpy.data.texts.get(".rendercue_data"):
            # Subtle notification row instead of box
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(text="Saved queue data found", icon=version_compat.get_icon('INFO'))
            row.operator("rendercue.load_data", icon=version_compat.get_icon('IMPORT'), text="Load")
            
        row = layout.row()
        row.template_list("RENDER_UL_render_cue_jobs", "", settings, "jobs", settings, "active_job_index")
        
        # Side buttons for list
        col = row.column(align=True)
        col.operator("rendercue.add_job", icon=version_compat.get_icon('ADD'), text="")
        col.operator("rendercue.remove_job", icon=version_compat.get_icon('REMOVE'), text="")
        col.separator()
        col.operator("rendercue.move_job", icon=version_compat.get_icon('TRIA_UP'), text="").direction = 'UP'
        col.operator("rendercue.move_job", icon=version_compat.get_icon('TRIA_DOWN'), text="").direction = 'DOWN'
        
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
        
        # Show warning if jobs have invalid scenes (no camera)
        if stats['invalid_jobs'] > 0:
            warn_row = layout.row()
            warn_row.alert = True
            if stats['invalid_jobs'] == 1:
                warn_row.label(
                    text=f"'{stats['invalid_job_names'][0]}' has no camera",
                    icon=version_compat.get_icon('ERROR')
                )
            else:
                warn_row.label(
                    text=f"{stats['invalid_jobs']} jobs have no camera",
                    icon=version_compat.get_icon('ERROR')
                )
        
        # Info row for available scenes
        if stats['available'] > 0:
            info_row = layout.row()
            info_row.scale_y = 0.75
            info_row.label(text=f"{stats['available']} scene(s) can be added", icon=version_compat.get_icon('ADD'))

        row = layout.row(align=True)
        row.scale_y = 1.2
        
        btn_text = "Add All Scenes"
        if stats['available'] > 0:
            btn_text = f"Add All Scenes ({stats['available']})"
            
        row.operator("rendercue.populate_all", icon=version_compat.get_icon('SCENE_DATA'), text=btn_text)
        row.menu("RENDERCUE_MT_presets_menu", icon=version_compat.get_icon('PRESET'), text="Presets")
        
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
            "ui_show_global_output", 
            icon=version_compat.get_icon('TRIA_DOWN') if settings.ui_show_global_output else version_compat.get_icon('TRIA_RIGHT'),
            text="Global Output",
            emboss=False
        )
        
        # Right: Icon
        right = split.row(align=True)
        right.alignment = 'RIGHT'
        right.label(text="", icon=version_compat.get_icon('FILE_FOLDER'))
        
        if settings.ui_show_global_output:
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
                op = row.operator("rendercue.browse_path", icon=version_compat.get_icon('FILE_FOLDER'), text="")
                op.target_property = "global_output_path"
                
            # Visual Path Preview
            col.separator()
            preview_box = box.box()
            preview_box.scale_y = 0.8
            
            row = preview_box.row()
            row.alignment = 'LEFT'
            
            if settings.output_location == 'DEFAULT':
                row.label(text="Path: // [Scene Name] /", icon=version_compat.get_icon('FILE_BLEND'))
            else:
                row.label(text="Path: [Custom] / [Scene Name] /", icon=version_compat.get_icon('FILE_FOLDER'))
        
        # Selected Job Settings (Overrides)
        if settings.jobs:
            # Clamp index to valid range
            if settings.active_job_index >= len(settings.jobs):
                settings.active_job_index = max(0, len(settings.jobs) - 1)
            
            if settings.active_job_index >= 0:
                job = settings.jobs[settings.active_job_index]
            
            # === SCENE SUMMARY ===
            layout.separator()
            summary_box = layout.box()
            
            # Scene Title + Switch Button
            title_row = summary_box.row()
            title_row.label(text=job.scene.name if job.scene else "No Scene", icon=version_compat.get_icon('SCENE_DATA'))
            op = title_row.operator("rendercue.switch_to_job_scene", text="", icon=version_compat.get_icon('RESTRICT_VIEW_OFF'))
            op.index = settings.active_job_index
            
            if job.scene:
                # Settings Row: Engine • Resolution • Samples
                info_row = summary_box.row()
                info_row.scale_y = 0.8
                
                # Engine
                if job.override_engine:
                    engine = job.render_engine
                    engine_text = f"⚡ {version_compat.get_engine_display_name(engine)}"
                else:
                    engine = job.scene.render.engine
                    engine_text = version_compat.get_engine_display_name(engine)
                
                # Resolution  
                res_x = job.scene.render.resolution_x
                res_y = job.scene.render.resolution_y
                if job.override_resolution:
                    scale = job.resolution_scale
                    res_text = f"⚡ {int(res_x * scale / 100)}×{int(res_y * scale / 100)}"
                else:
                    scale = job.scene.render.resolution_percentage
                    res_text = f"{int(res_x * scale / 100)}×{int(res_y * scale / 100)}"
                
                # Samples
                if job.override_samples:
                    samples_text = f"⚡ {job.samples} samples"
                elif engine == 'CYCLES':
                    samples_text = f"{job.scene.cycles.samples} samples"
                else:
                    samples_text = f"{version_compat.get_eevee_samples(job.scene)} samples"
                
                info_row.label(text=f"{engine_text} • {res_text} • {samples_text}")
                
                # Show other active overrides if any
                override_info = ui_helpers.get_override_summary(context, job)
                other_overrides = []
                if job.override_frame_range:
                    other_overrides.append("Frame Range")
                if job.override_output:
                    other_overrides.append("Output")
                if job.override_format:
                    other_overrides.append("Format")
                if job.override_view_layer:
                    other_overrides.append("View Layer")
                if job.override_camera:
                    other_overrides.append("Camera")
                
                if other_overrides:
                    ov_row = summary_box.row()
                    ov_row.scale_y = 0.7
                    ov_row.label(text=f"⚡ {', '.join(other_overrides)}", icon=version_compat.get_icon('MODIFIER'))
            
            # Inline Error (if file not saved)
            validation = ui_helpers.get_queue_validation_summary(context)
            if validation['errors']:
                err_row = summary_box.row()
                err_row.alert = True
                err_row.label(text=validation['errors'][0], icon=version_compat.get_icon('ERROR'))
            
            # === OVERRIDES SECTION (Collapsible) ===
            layout.separator()
            box = layout.box()
            
            # Get override info for header
            override_info = ui_helpers.get_override_summary(context, job)
            
            # Header
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
                icon=version_compat.get_icon('TRIA_DOWN') if settings.ui_show_overrides_main else version_compat.get_icon('TRIA_RIGHT'),
                text=header_text,
                emboss=False
            )
            
            # Right: Icon
            right = split.row(align=True)
            right.alignment = 'RIGHT'
            right.label(text="", icon=version_compat.get_icon('MODIFIER'))

            if settings.ui_show_overrides_main:
                # Collapsible Summary (Dashboard)
                if override_info['count'] > 0:
                    summary_box = box.box()
                    summary_header = summary_box.row(align=True)
                    
                    # Split Header: Toggle (Left) | Apply Button (Right)
                    split = summary_header.split(factor=0.65)
                
                    # Left: Toggle
                    left = split.row(align=True)
                    left.alignment = 'LEFT'
                    left.prop(
                        settings,
                        "ui_show_override_summary",
                        icon=version_compat.get_icon('TRIA_DOWN') if settings.ui_show_override_summary else version_compat.get_icon('TRIA_RIGHT'),
                        text=f"Active Overrides ({override_info['count']})",
                        emboss=False
                    )
                    
                    # Right: Apply to All Button
                    right = split.row(align=True)
                    right.alignment = 'RIGHT'
                    right.operator("rendercue.apply_override_to_all", text="Apply to All", icon=version_compat.get_icon('DUPLICATE'))
                    
                    if settings.ui_show_override_summary:
                        summary_col = summary_box.column(align=True)
                        
                        for group in override_info['groups']:
                            # Add spacing before each group (except first)
                            if group != override_info['groups'][0]:
                                summary_col.separator(factor=1.5)

                            # Group Header
                            group_row = summary_col.row(align=True)
                            group_row.label(text=group['name'], icon=version_compat.get_icon(group['icon']))
                            
                            # Group Items
                            for override in group['overrides']:
                                row = summary_col.row(align=True)
                                
                                # Split Layout: Close (10%) | Label (35%) | Value (30%) | Apply (25%)
                                # Close button first
                                close_split = row.split(factor=0.1, align=True)
                                
                                # Remove Button (leftmost)
                                op = close_split.operator("rendercue.remove_override", text="", icon=version_compat.get_icon('X'))
                                op.data_path_bool = override['bool_prop']
                                
                                # Rest of the content
                                content_split = close_split.split(factor=0.35, align=True)
                                
                                # Label with slight indent
                                sub = content_split.row()
                                sub.separator(factor=0.5)
                                sub.label(text=override['display_name'])
                                
                                # Value & Apply Button
                                value_apply_split = content_split.split(factor=0.5, align=True)
                                value_apply_split.label(text=override['value'])
                                
                                # Apply Button (rightmost)
                                btns = value_apply_split.row(align=True)
                                btns.alignment = 'RIGHT'
                                
                                if override['can_apply']:
                                    applicable, total = override['apply_stats']
                                    if applicable == total:
                                        btn_text = "Apply to All"
                                    else:
                                        btn_text = f"Apply ({applicable}/{total})"
                                        
                                    op = btns.operator("rendercue.apply_override_to_all", text=btn_text, icon=version_compat.get_icon('DUPLICATE'))
                                    op.data_path_bool = override['bool_prop']
                                    op.data_path_val = override['val_prop']
                                    
                        # Queue Health Integration
                        validation = ui_helpers.get_queue_validation_summary(context)
                        if validation['errors'] or validation['warnings']:
                            summary_col.separator()
                            health_row = summary_col.row()
                            health_row.scale_y = 0.8
                            
                            if validation['errors']:
                                health_row.alert = True
                                health_row.label(
                                    text=f"⚠ {len(validation['errors'])} error(s) in queue",
                                    icon=version_compat.get_icon('ERROR')
                                )
                            elif validation['warnings']:
                                health_row.label(
                                    text=f"⚠ {len(validation['warnings'])} warning(s)",
                                    icon=version_compat.get_icon('INFO')
                                )
                
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
                    icon_state = version_compat.get_icon('TRIA_DOWN') if is_expanded else version_compat.get_icon('TRIA_RIGHT')
                    
                    left.prop(settings, prop_name, icon=icon_state, text=title, emboss=False)
                    
                    # Right: Status + Icon
                    right = split.row(align=True)
                    right.alignment = 'RIGHT'
                    
                    if is_active:
                        right.label(text="[Active]", icon=version_compat.get_icon('CHECKMARK'))
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
                col = draw_collapsible_box(parent_col, settings, "ui_show_job_output", "Output Settings", version_compat.get_icon('FILE_FOLDER'), is_active=is_output_active)
                
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
                        op = sub.operator("rendercue.browse_path", icon=version_compat.get_icon('FILE_FOLDER'), text="")
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
                col = draw_collapsible_box(parent_col, settings, "ui_show_dimensions", "Range & Resolution", version_compat.get_icon('SETTINGS'), is_active=is_dim_active)

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
                            sub_col.label(text=f"Renders approx. {render_frames} frames", icon=version_compat.get_icon('INFO'))
                    


                    # Resolution
                    row = col.row(align=True)
                    row.prop(job, "override_resolution", text="Resolution")
                    

                    
                    if job.override_resolution:
                        sub_col = col.column(align=True)
                        sub_col.use_property_split = True
                        sub_col.use_property_decorate = False
                        sub_col.prop(job, "resolution_scale", text="Scale %")
                        

                
                # Group: Format
                col = draw_collapsible_box(parent_col, settings, "ui_show_format", "Format", version_compat.get_icon('IMAGE_DATA'), is_active=job.override_format)
                
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
                col = draw_collapsible_box(parent_col, settings, "ui_show_render", "Render", version_compat.get_icon('RESTRICT_RENDER_OFF'), is_active=is_render_active)

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
                    if effective_engine == 'CYCLES' or version_compat.is_eevee_engine(effective_engine):
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
                        col.label(text="Cycles Settings", icon=version_compat.get_icon('SETTINGS'))
                        
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
        row = layout.row()
        row.scale_y = 2.0
        row.operator("rendercue.confirm_render", icon=version_compat.get_icon('RENDER_ANIMATION'), text="START RENDER QUEUE")

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

class RENDERCUE_MT_job_context_menu(bpy.types.Menu):
    """Right-click context menu for job list items."""
    bl_label = "Job Options"
    bl_idname = "RENDERCUE_MT_job_context_menu"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        
        # Move operations
        layout.operator("rendercue.move_job_to_top", icon=version_compat.get_icon('TRIA_UP_BAR'))
        layout.operator("rendercue.move_job", text="Move Up", icon=version_compat.get_icon('TRIA_UP')).direction = 'UP'
        layout.operator("rendercue.move_job", text="Move Down", icon=version_compat.get_icon('TRIA_DOWN')).direction = 'DOWN'
        layout.operator("rendercue.move_job_to_bottom", icon=version_compat.get_icon('TRIA_DOWN_BAR'))
        
        layout.separator()
        
        # Scene operations
        if settings.active_job_index >= 0 and settings.active_job_index < len(settings.jobs):
            op = layout.operator("rendercue.switch_to_job_scene", text="Switch to Scene", icon=version_compat.get_icon('VIEW3D'))
            op.index = settings.active_job_index
        
        layout.separator()
        
        # Remove
        layout.operator("rendercue.remove_job", text="Remove Job", icon=version_compat.get_icon('TRASH'))

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
        layout.operator("rendercue.save_preset", icon=version_compat.get_icon('FILE_TICK'))
        layout.operator("rendercue.load_preset", icon=version_compat.get_icon('FILE_FOLDER'))

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
            box.label(text="Status: RENDERING", icon=version_compat.get_icon('RENDER_ANIMATION'))
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
            row.label(text=settings.last_render_message, icon=version_compat.get_icon(icon))
            # Clear button
            op = row.operator("rendercue.clear_status", text="", icon=version_compat.get_icon('X'))
            
        else:
            # Idle state
            box.label(text="Status: Idle", icon=version_compat.get_icon('PAUSE'))

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

def draw_status_bar(self, context):
    """Draw RenderCue status in the Blender status bar."""
    settings = context.window_manager.rendercue
    
    if settings.is_rendering:
        self.layout.label(text=f"RenderCue: {settings.progress_message} | ETR: {settings.etr}", icon=version_compat.get_icon('RENDER_ANIMATION'))
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
                        self.layout.label(text=msg, icon=version_compat.get_icon(icon))
        except Exception:
            pass # Fail silently in status bar draw

def register():
    bpy.utils.register_class(RENDER_UL_render_cue_jobs)
    bpy.utils.register_class(RENDER_PT_render_cue)
    bpy.utils.register_class(RENDERCUE_MT_apply_to_all_menu)
    bpy.utils.register_class(RENDERCUE_MT_job_context_menu)
    bpy.utils.register_class(RENDERCUE_MT_presets_menu)
    bpy.utils.register_class(RENDER_PT_render_cue_dashboard)
    bpy.utils.register_class(VIEW3D_PT_render_cue)
    
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
        VIEW3D_PT_render_cue,
        RENDER_PT_render_cue_dashboard,
        RENDERCUE_MT_presets_menu,
        RENDERCUE_MT_job_context_menu,
        RENDERCUE_MT_apply_to_all_menu,
        RENDER_PT_render_cue,
        RENDER_UL_render_cue_jobs,
    ):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
