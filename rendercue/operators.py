"""
RenderCue Operators Module

This module defines all the Blender Operators (actions) used in the addon.
Operators handle user interactions such as adding jobs, starting renders,
and managing the queue.
"""

import bpy
import logging
import os
import json
from .core import StateManager
from .constants import PAUSE_SIGNAL_FILENAME
from .properties import get_available_renderers
from . import ui_helpers
from . import version_compat

class RENDERCUE_OT_add_job(bpy.types.Operator):
    """Add the current active scene to the render queue."""
    bl_idname = "rendercue.add_job"
    bl_label = "Add Scene"
    bl_description = "Add the current active scene to the render queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        job = settings.jobs.add()
        job.scene = context.scene
        
        # Set default overrides to match scene? No, keep them disabled by default.
        settings.active_job_index = len(settings.jobs) - 1
        return {'FINISHED'}

class RENDERCUE_OT_remove_job(bpy.types.Operator):
    """Remove the currently selected job from the queue."""
    bl_idname = "rendercue.remove_job"
    bl_label = "Remove Job"
    bl_description = "Remove the currently selected job from the queue"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """Check if operator can run."""
        return context.window_manager.rendercue.jobs and context.window_manager.rendercue.active_job_index >= 0

    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        settings.jobs.remove(settings.active_job_index)
        
        if settings.active_job_index >= len(settings.jobs):
            settings.active_job_index = max(0, len(settings.jobs) - 1)
            
        return {'FINISHED'}

class RENDERCUE_OT_move_job(bpy.types.Operator):
    """Move the selected job up or down in the list."""
    bl_idname = "rendercue.move_job"
    bl_label = "Move Job"
    bl_description = "Move the selected job up or down in the list"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction: bpy.props.EnumProperty(items=[('UP', "Up", ""), ('DOWN', "Down", "")])

    @classmethod
    def poll(cls, context):
        """Check if operator can run."""
        return context.window_manager.rendercue.jobs and context.window_manager.rendercue.active_job_index >= 0

    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        idx = settings.active_job_index
        
        if self.direction == 'UP' and idx > 0:
            settings.jobs.move(idx, idx - 1)
            settings.active_job_index -= 1
        elif self.direction == 'DOWN' and idx < len(settings.jobs) - 1:
            settings.jobs.move(idx, idx + 1)
            settings.active_job_index += 1
            
        return {'FINISHED'}

class RENDERCUE_OT_populate_all(bpy.types.Operator):
    """Add all scenes in this .blend file to the render queue."""
    bl_idname = "rendercue.populate_all"
    bl_label = "Add All Scenes"
    bl_description = "Add all scenes in this .blend file to the render queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        existing_scenes = {job.scene for job in settings.jobs if job.scene}
        
        count = 0
        for scene in bpy.data.scenes:
            # Exclude existing scenes and scenes without cameras
            if scene not in existing_scenes and scene.camera:
                job = settings.jobs.add()
                job.scene = scene
                count += 1
                
        if count > 0:
            self.report({'INFO'}, f"Added {count} scenes to queue")
        else:
            self.report({'WARNING'}, "No new scenes with cameras found")
            
        return {'FINISHED'}

class RENDERCUE_OT_apply_override_to_all(bpy.types.Operator):
    """Copy settings to all jobs in the queue."""
    bl_idname = "rendercue.apply_override_to_all"
    bl_label = "Apply to All"
    bl_description = "Copy selected settings to all jobs in the queue"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Internal props to know what was clicked
    data_path_bool: bpy.props.StringProperty()
    data_path_val: bpy.props.StringProperty()
    
    # Selection props
    apply_output: bpy.props.BoolProperty(name="Output Path")
    apply_frame_range: bpy.props.BoolProperty(name="Frame Range")
    apply_resolution: bpy.props.BoolProperty(name="Resolution")
    apply_samples: bpy.props.BoolProperty(name="Samples")
    apply_camera: bpy.props.BoolProperty(name="Camera")
    apply_engine: bpy.props.BoolProperty(name="Render Engine")
    apply_device: bpy.props.BoolProperty(name="Device")
    apply_view_layer: bpy.props.BoolProperty(name="View Layer")
    apply_frame_step: bpy.props.BoolProperty(name="Frame Step")
    apply_format: bpy.props.BoolProperty(name="Format")
    apply_transparent: bpy.props.BoolProperty(name="Transparent")
    apply_compositor: bpy.props.BoolProperty(name="Compositor")
    apply_denoising: bpy.props.BoolProperty(name="Denoising")
    apply_time_limit: bpy.props.BoolProperty(name="Time Limit")
    apply_persistent_data: bpy.props.BoolProperty(name="Persistent Data")

    def invoke(self, context, event):
        """Show confirmation dialog with checkboxes."""
        settings = context.window_manager.rendercue
        if not settings.jobs:
            return {'CANCELLED'}
            
        # Reset all to False first
        for prop in self.__annotations__:
            if prop.startswith("apply_"):
                setattr(self, prop, False)
            
        # If triggered from a specific button (data_path_bool set), pre-select ONLY that one
        if self.data_path_bool:
            clicked_prop = self.data_path_bool.replace("override_", "apply_")
            if hasattr(self, clicked_prop):
                setattr(self, clicked_prop, True)
        else:
            # Otherwise pre-select ALL active overrides (legacy behavior)
            source_job = settings.jobs[settings.active_job_index]
            
            # Mapping: (Apply Prop, Source Bool Prop)
            mappings = [
                ("apply_output", "override_output"),
                ("apply_frame_range", "override_frame_range"),
                ("apply_resolution", "override_resolution"),
                ("apply_samples", "override_samples"),
                ("apply_camera", "override_camera"),
                ("apply_engine", "override_engine"),
                ("apply_device", "override_device"),
                ("apply_view_layer", "override_view_layer"),
                ("apply_frame_step", "override_frame_step"),
                ("apply_format", "override_format"),
                ("apply_transparent", "override_transparent"),
                ("apply_compositor", "override_compositor"),
                ("apply_denoising", "override_denoising"),
                ("apply_time_limit", "override_time_limit"),
                ("apply_persistent_data", "override_persistent_data"),
            ]
            
            for apply_prop, source_bool in mappings:
                if getattr(source_job, source_bool, False):
                    setattr(self, apply_prop, True)
                
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        source_job = settings.jobs[settings.active_job_index]
        
        layout.label(text="Select overrides to apply to all jobs:", icon=version_compat.get_icon('DUPLICATE'))
        layout.separator()
        
        col = layout.column(align=True)
        
        # Only show options that are currently active on the source job
        # Mapping: (Apply Prop, Source Bool Prop, Label)
        mappings = [
            ("apply_output", "override_output", "Output Path"),
            ("apply_frame_range", "override_frame_range", "Frame Range"),
            ("apply_resolution", "override_resolution", "Resolution"),
            ("apply_samples", "override_samples", "Samples"),
            ("apply_camera", "override_camera", "Camera"),
            ("apply_engine", "override_engine", "Render Engine"),
            ("apply_device", "override_device", "Device"),
            ("apply_view_layer", "override_view_layer", "View Layer"),
            ("apply_frame_step", "override_frame_step", "Frame Step"),
            ("apply_format", "override_format", "Format"),
            ("apply_transparent", "override_transparent", "Transparent"),
            ("apply_compositor", "override_compositor", "Compositor"),
            ("apply_denoising", "override_denoising", "Denoising"),
            ("apply_time_limit", "override_time_limit", "Time Limit"),
            ("apply_persistent_data", "override_persistent_data", "Persistent Data"),
        ]
        
        has_options = False
        for apply_prop, source_bool, label in mappings:
            if getattr(source_job, source_bool, False):
                col.prop(self, apply_prop, text=label)
                has_options = True
                
        if not has_options:
            layout.label(text="No active overrides on this job.", icon=version_compat.get_icon('INFO'))

    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        if not settings.jobs:
            return {'CANCELLED'}
            
        source_job = settings.jobs[settings.active_job_index]
        
        # Mapping: Apply Prop -> (Bool Prop, Value Prop, Metadata Key)
        mappings = {
            "apply_output": ("override_output", "output_path", "output"),
            "apply_frame_range": ("override_frame_range", "frame_range", "frame_range"),
            "apply_resolution": ("override_resolution", "resolution_scale", "resolution"),
            "apply_samples": ("override_samples", "samples", "samples"),
            "apply_camera": ("override_camera", "camera", "camera"),
            "apply_engine": ("override_engine", "render_engine", "engine"),
            "apply_device": ("override_device", "device", "device"),
            "apply_view_layer": ("override_view_layer", "view_layer", "view_layer"),
            "apply_frame_step": ("override_frame_step", "frame_step", "frame_step"),
            "apply_format": ("override_format", "render_format", "format"),
            "apply_transparent": ("override_transparent", "film_transparent", "transparent"),
            "apply_compositor": ("override_compositor", "use_compositor", "compositor"),
            "apply_denoising": ("override_denoising", "use_denoising", "denoising"),
            "apply_time_limit": ("override_time_limit", "time_limit", "time_limit"),
            "apply_persistent_data": ("override_persistent_data", "use_persistent_data", "persistent_data"),
        }
        
        applied_count = 0
        skipped_count = 0
        
        for apply_prop, (bool_prop, val_prop, meta_key) in mappings.items():
            if getattr(self, apply_prop):
                
                # Get value from source
                override_enabled = getattr(source_job, bool_prop)
                
                # Check metadata for smart application
                meta = ui_helpers.OVERRIDE_METADATA.get(meta_key)
                apply_type = meta['apply'] if meta else 'universal'
                
                # Special case for frame_range (value copy)
                if meta_key == "frame_range":
                    frame_start = source_job.frame_start
                    frame_end = source_job.frame_end
                    
                    for job in settings.jobs:
                        setattr(job, bool_prop, override_enabled)
                        if override_enabled:
                            job.frame_start = frame_start
                            job.frame_end = frame_end
                            if job.frame_end < job.frame_start:
                                job.frame_end = job.frame_start
                            applied_count += 1
                else:
                    override_value = getattr(source_job, val_prop)
                    
                    for job in settings.jobs:
                        # Smart Check
                        should_apply = True
                        if apply_type == 'smart_camera' and override_enabled:
                            if not source_job.camera:
                                should_apply = False
                            elif job.scene and source_job.camera.name not in job.scene.objects:
                                should_apply = False
                                skipped_count += 1
                                
                        elif apply_type == 'smart_view_layer' and override_enabled:
                             if job.scene and source_job.view_layer not in [vl.name for vl in job.scene.view_layers]:
                                should_apply = False
                                skipped_count += 1

                        if should_apply:
                            setattr(job, bool_prop, override_enabled)
                            if override_enabled:
                                setattr(job, val_prop, override_value)
                            applied_count += 1
        
        msg = f"Applied settings to {applied_count} jobs"
        if skipped_count > 0:
            msg += f" (skipped {skipped_count} incompatible)"
            
        self.report({'INFO'}, msg)
        return {'FINISHED'}

class RENDERCUE_OT_remove_override(bpy.types.Operator):
    """Remove a specific override from the active job."""
    bl_idname = "rendercue.remove_override"
    bl_label = "Remove Override"
    bl_description = "Remove this override from the active job"
    bl_options = {'REGISTER', 'UNDO'}

    data_path_bool: bpy.props.StringProperty(name="Boolean Property Path")

    def execute(self, context):
        settings = context.window_manager.rendercue
        if not settings.jobs or settings.active_job_index < 0:
            return {'CANCELLED'}
            
        job = settings.jobs[settings.active_job_index]
        
        if hasattr(job, self.data_path_bool):
            setattr(job, self.data_path_bool, False)
            self.report({'INFO'}, "Override removed")
            return {'FINISHED'}
            
        return {'CANCELLED'}

class RENDERCUE_OT_open_output_folder(bpy.types.Operator):
    """Open the global output directory in the OS file explorer."""
    bl_idname = "rendercue.open_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Open the global output directory in your operating system's file explorer"
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        # Default to global path
        target_path = bpy.path.abspath(settings.global_output_path)
        
        # Smart Behavior: If only one job, try to open its specific folder
        if len(settings.jobs) == 1:
            job = settings.jobs[0]
            if job.scene:
                # Replicate logic from core.py
                if job.override_output and job.output_path:
                    target_path = bpy.path.abspath(job.output_path)
                else:
                    # Standard structure: Base/SceneName
                    if settings.output_location == 'CUSTOM':
                        base = bpy.path.abspath(settings.global_output_path)
                    else:
                        # Match core.py logic: //BlendName_RenderCue
                        blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                        if not blend_name:
                            blend_name = "Untitled"
                        base = bpy.path.abspath(f"//{blend_name}_RenderCue")
                        
                    target_path = os.path.join(base, job.scene.name)
        
        target_path = os.path.normpath(target_path)
        
        if not os.path.exists(target_path):
            self.report({'WARNING'}, f"Directory does not exist: {target_path}")
            
            # Fallback 1: Try the base path (parent of the scene folder)
            # This handles cases where the scene folder wasn't created but the parent was
            if settings.output_location == 'CUSTOM':
                base_fallback = bpy.path.abspath(settings.global_output_path)
            else:
                # Re-calculate base for BLEND mode
                blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "Untitled"
                base_fallback = bpy.path.abspath(f"//{blend_name}_RenderCue")

            if os.path.exists(base_fallback) and base_fallback != target_path:
                 bpy.ops.wm.path_open(filepath=base_fallback)
                 return {'FINISHED'}
                 
            # Fallback 2: Try the legacy/simple path (//SceneName) just in case
            # This helps if the user is seeing "folder named after scene" in the root
            legacy_path = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else "", job.scene.name if job.scene else "")
            if os.path.exists(legacy_path):
                bpy.ops.wm.path_open(filepath=legacy_path)
                return {'FINISHED'}

            return {'CANCELLED'}
            
        bpy.ops.wm.path_open(filepath=target_path)
        return {'FINISHED'}

class RENDERCUE_OT_validate_queue(bpy.types.Operator):
    """Check the queue for common errors before rendering."""
    bl_idname = "rendercue.validate_queue"
    bl_label = "Validate Queue"
    bl_description = "Check for missing cameras, invalid paths, and other errors before rendering"
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        errors = []
        
        # Check File Status
        if not bpy.data.filepath:
            errors.append("Blender file has not been saved. Please save first.")
        elif bpy.data.is_dirty:
            self.report({'WARNING'}, "File has unsaved changes. Background render uses saved file.")

        # Check Output Path
        if not settings.global_output_path:
            errors.append("Global Output Path is empty")
        else:
            path = bpy.path.abspath(settings.global_output_path)
            if not os.path.exists(path):
                try:
                    os.makedirs(path)
                except OSError:
                    errors.append(f"Cannot create output directory: {path}")
        
        # Check Jobs
        if not settings.jobs:
            errors.append("Queue is empty")
            
        for i, job in enumerate(settings.jobs):
            if not job.scene:
                errors.append(f"Job {i+1}: No scene assigned")
            elif not job.scene.camera:
                errors.append(f"Job {i+1} ({job.scene.name}): No active camera")
            
            # Validate Overrides
            if job.override_camera:
                if not job.camera:
                    errors.append(f"Job {i+1}: Camera override enabled but no camera selected")
                elif job.camera.name not in bpy.data.objects: # Should be handled by PointerProperty but good to check
                     errors.append(f"Job {i+1}: Overridden camera '{job.camera.name}' not found")
            
            if job.override_frame_step:
                if job.frame_step < 1:
                    errors.append(f"Job {i+1}: Frame step must be at least 1")
                elif job.frame_step > (job.frame_end - job.frame_start + 1):
                     errors.append(f"Job {i+1}: Frame step ({job.frame_step}) is larger than frame range")

            if job.override_device and job.device == 'GPU':
                # Basic check if GPU is available (this is a rough check)
                try:
                    preferences = context.preferences.addons['cycles'].preferences
                    has_devices = False
                    for device_type in preferences.get_device_types(context):
                        preferences.get_devices_for_type(device_type[0])
                        if preferences.devices:
                             has_devices = True
                             break
                    if not has_devices:
                         errors.append(f"Job {i+1}: GPU override selected but no GPU devices found")
                except:
                    pass # Ignore if we can't check preferences

            # Validate Render Engine Availability
            if job.override_engine:
                available_engines = [e[0] for e in get_available_renderers(None, context)]
                if job.render_engine not in available_engines:
                    errors.append(f"Job {i+1}: Render engine '{job.render_engine}' is not available (addon disabled or removed)")

            # Validate Camera Linkage
            if job.override_camera and job.camera and job.scene:
                if job.camera.name not in job.scene.objects:
                    errors.append(f"Job {i+1}: Camera '{job.camera.name}' is not linked to scene '{job.scene.name}'")

            # Validate View Layer
            if job.override_view_layer and job.view_layer and job.scene:
                if job.view_layer not in [vl.name for vl in job.scene.view_layers]:
                    errors.append(f"Job {i+1}: View layer '{job.view_layer}' not found in scene '{job.scene.name}'")

            # Warn about extreme resolutions
            if job.override_resolution:
                res_x = job.scene.render.resolution_x if job.scene else 1920
                res_y = job.scene.render.resolution_y if job.scene else 1080
                final_x = int(res_x * job.resolution_scale / 100)
                final_y = int(res_y * job.resolution_scale / 100)
                
                if final_x > 8192 or final_y > 8192:
                    errors.append(f"Job {i+1}: Resolution {final_x}x{final_y} exceeds 8K (may cause GPU memory errors)")
                
        if errors:
            self.report({'ERROR'}, f"Validation Failed: {len(errors)} errors found")
            for err in errors:
                self.report({'ERROR'}, err)
            return {'CANCELLED'}
            
        self.report({'INFO'}, "Queue validated. Ready to render.")
        return {'FINISHED'}

class RENDERCUE_OT_save_preset(bpy.types.Operator):
    """Save the current queue configuration to a JSON preset file."""
    bl_idname = "rendercue.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the current queue configuration (jobs and overrides) to a JSON preset file"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})
    
    def invoke(self, context, event):
        """Invoke the file selector."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        """Execute the operator."""
        if not self.filepath.endswith(".json"):
            self.filepath += ".json"
            
        StateManager.save_state(context, self.filepath)
        self.report({'INFO'}, f"Preset saved: {self.filepath}")
        return {'FINISHED'}

class RENDERCUE_OT_load_preset(bpy.types.Operator):
    """Load a queue configuration from a JSON preset file."""
    bl_idname = "rendercue.load_preset"
    bl_label = "Load Preset"
    bl_description = "Load a queue configuration from a saved JSON preset file (replaces current queue)"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})
    
    def invoke(self, context, event):
        """Invoke the file selector."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        """Execute the operator."""
        if StateManager.load_state(context, self.filepath):
            self.report({'INFO'}, "Preset loaded successfully")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to load preset")
            return {'CANCELLED'}

class RENDERCUE_OT_quick_preset(bpy.types.Operator):
    """Apply a quick quality preset to all jobs."""
    bl_idname = "rendercue.quick_preset"
    bl_label = "Quick Preset"
    bl_description = "Apply a quick quality preset to all jobs"
    
    preset_type: bpy.props.EnumProperty(
        items=[
            ('DRAFT', "Draft (50%, Low Samples)", "Fast render for checking animation"),
            ('PRODUCTION', "Production (100%, High Samples)", "Final quality render")
        ]
    )
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        if not settings.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}
            
        for job in settings.jobs:
            if self.preset_type == 'DRAFT':
                # Resolution
                job.override_resolution = True
                job.resolution_scale = 50
                # Samples
                job.override_samples = True
                job.samples = 32
                # Frame Step (Render every 2nd frame)
                job.override_frame_step = True
                job.frame_step = 2
                # Disable Denoising (Faster)
                job.override_denoising = True
                job.use_denoising = False
                
            elif self.preset_type == 'PRODUCTION':
                # Resolution
                job.override_resolution = True
                job.resolution_scale = 100
                # Samples
                job.override_samples = True
                job.samples = 512 # Increased for production
                # Frame Step (All frames)
                job.override_frame_step = True
                job.frame_step = 1
                # Enable Denoising
                job.override_denoising = True
                job.use_denoising = True
                # Use GPU if possible
                job.override_device = True
                job.device = 'GPU'
                
        self.report({'INFO'}, f"Applied '{self.preset_type}' preset to all jobs")
        return {'FINISHED'}

class RENDERCUE_OT_switch_to_job_scene(bpy.types.Operator):
    """Switch the current window to the selected job's scene."""
    bl_idname = "rendercue.switch_to_job_scene"
    bl_label = "Switch to Scene"
    
    index: bpy.props.IntProperty()
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        if self.index < 0 or self.index >= len(settings.jobs):
            return {'CANCELLED'}
            
        job = settings.jobs[self.index]
        if job.scene:
            context.window.scene = job.scene
            settings.active_job_index = self.index
            
            # Auto-switch to Layout workspace
            layout_ws = None
            # Try to find "Layout" or "General"
            for ws in bpy.data.workspaces:
                if ws.name == "Layout" or ws.name == "General":
                    layout_ws = ws
                    break
            
            # If not found, just pick the first one that isn't Video Editing
            if not layout_ws:
                for ws in bpy.data.workspaces:
                    if "Video Editing" not in ws.name:
                        layout_ws = ws
                        break
            
            if layout_ws:
                context.window.workspace = layout_ws
            
        return {'FINISHED'}

class RENDERCUE_OT_stop_render(bpy.types.Operator):
    """Stop the current render process and clear all progress."""
    bl_idname = "rendercue.stop_render"
    bl_label = "Stop & Clear Progress"
    bl_description = "Stop rendering and clear all progress. Jobs will restart from beginning. Use PAUSE if you want to resume later."
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        # Signal stop to background worker
        settings.stop_requested = True
        
        # Reset ONLY visual queue state (preserve completion data for summary)
        for job in settings.jobs:
            job.render_status = 'PENDING'
            # Do NOT clear completed_frames or total_frames
            # (needed for summary banner and notifications)
        
        # Reset current render pointer
        settings.current_job_index = 0
        
        # Clear Preview State
        settings.has_preview_image = False
        
        # Clear UI Collection
        try:
            from . import ui
            if "main" in ui.preview_collections:
                pcoll = ui.preview_collections["main"]
                pcoll.clear()
        except Exception as e:
            logging.getLogger("RenderCue").warning(f"Error clearing preview: {e}")
        
        self.report({'INFO'}, "Stopping render... (Progress will be cleared on next render)")
        return {'FINISHED'}

class RENDERCUE_OT_pause_render(bpy.types.Operator):
    """Pause the current render process."""
    bl_idname = "rendercue.pause_render"
    bl_label = "Pause Render"
    bl_description = "Pause the current render process"
    
    def execute(self, context):
        """Execute the operator."""
        context.window_manager.rendercue.is_paused = True
        # Create pause signal file
        pause_file = os.path.join(bpy.app.tempdir, PAUSE_SIGNAL_FILENAME)
        try:
            with open(pause_file, 'w') as f:
                f.write("PAUSE")
        except OSError:
            pass
        return {'FINISHED'}

class RENDERCUE_OT_resume_render(bpy.types.Operator):
    """Resume the current render process."""
    bl_idname = "rendercue.resume_render"
    bl_label = "Resume Render"
    bl_description = "Resume the current render process"
    
    def execute(self, context):
        """Execute the operator."""
        context.window_manager.rendercue.is_paused = False
        # Remove pause signal file
        pause_file = os.path.join(bpy.app.tempdir, PAUSE_SIGNAL_FILENAME)
        if os.path.exists(pause_file):
            try:
                os.remove(pause_file)
            except OSError:
                pass
        return {'FINISHED'}

class RENDERCUE_OT_browse_path(bpy.types.Operator):
    """Browse for a directory path."""
    bl_idname = "rendercue.browse_path"
    bl_label = "Browse"
    bl_description = "Browse for directory"
    
    filepath: bpy.props.StringProperty(subtype="DIR_PATH")
    target_property: bpy.props.StringProperty()
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        if self.filepath:
            if self.target_property == "global_output_path":
                settings.global_output_path = self.filepath
            elif self.target_property == "job_output_path":
                if settings.jobs and settings.active_job_index >= 0:
                     settings.jobs[settings.active_job_index].output_path = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        """Invoke the file selector."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}



class RENDERCUE_OT_confirm_render(bpy.types.Operator):
    """Show pre-render confirmation dialog with job details and validation"""
    bl_idname = "rendercue.confirm_render"
    bl_label = "Confirm Render Queue"
    bl_options = {'INTERNAL'}
    
    # Store validation results
    warnings = []
    errors = []
    
    def invoke(self, context, event):
        settings = context.window_manager.rendercue
        if not settings.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}
            
        # Run validation first
        self.warnings, self.errors = ui_helpers.validate_queue_for_render(context)
        
        # Show dialog (wide width for better readability)
        return context.window_manager.invoke_props_dialog(self, width=650)
    
    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        
        # === HEADER: Queue Summary ===
        summary = ui_helpers.get_queue_summary(context)
        
        # Clean summary box
        box = layout.box()
        
        # Title & File Status
        row = box.row()
        row.label(text="Queue Summary", icon=version_compat.get_icon('PROPERTIES'))
        
        file_icon = 'FILE_TICK' if summary['is_saved'] and not summary['is_dirty'] else 'FILE_BACKUP'
        sub = row.row()
        sub.alignment = 'RIGHT'
        sub.label(text=summary['filename'], icon=version_compat.get_icon(file_icon))
        
        # Stats Split
        split = box.split(factor=0.5)
        
        col = split.column()
        col.label(text=f"Total Jobs: {summary['total_jobs']}")
        
        col = split.column()
        col.label(text=f"Est. Frames: {summary['total_frames']}")
        
        if summary['is_dirty']:
            row = box.row()
            row.alert = True
            row.label(text="File has unsaved changes (will be saved automatically)", icon=version_compat.get_icon('INFO'))
            
        layout.separator()
        
        # === JOB LIST ===
        layout.label(text="Jobs to Render:", icon=version_compat.get_icon('OUTLINER_COLLECTION'))
        
        jobs_box = layout.box()
        
        if not settings.jobs:
             jobs_box.label(text="Queue is empty!", icon=version_compat.get_icon('ERROR'))
        
        for i, job in enumerate(settings.jobs):
            details = ui_helpers.get_job_confirmation_details(job)
            
            # Job Container
            job_col = jobs_box.column(align=True)
            job_box = job_col.box()
            
            # Header
            header = job_box.row()
            icon = 'CHECKMARK' if details['is_valid'] else 'ERROR'
            if job.render_status == 'COMPLETED': icon = 'FILE_TICK'
            
            header.label(text=f"{i+1}. {details['scene_name']}", icon=version_compat.get_icon(icon))
            
            # Details Column
            content = job_box.column(align=True)
            content.scale_y = 0.9 # Slightly compact
            
            # Row 1: Camera & Engine
            row = content.row()
            row.label(text=f"Camera: {details['camera_display']}")
            row.label(text=f"Engine: {details['engine_display']}")
            
            # Row 2: Resolution & Range
            row = content.row()
            row.label(text=f"Res: {details['resolution_display']}")
            row.label(text=f"Frames: {details['range_display']} ({details['frames_display']})")
            
            # Overrides Indicator
            if details['has_overrides']:
                row = content.row()
                row.label(text=f"Overrides: {', '.join(details['override_names'])}", icon=version_compat.get_icon('MODIFIER'))

        layout.separator()
        
        # === VALIDATION STATUS ===
        if self.errors or self.warnings:
            val_box = layout.box()
            
            if self.errors:
                row = val_box.row()
                row.alert = True
                row.label(text=f"{len(self.errors)} Errors (Must Fix):", icon=version_compat.get_icon('ERROR'))
                
                col = val_box.column()
                col.alert = True
                for err in self.errors:
                    col.label(text=f"• {err}")
                val_box.separator()
                
            if self.warnings:
                val_box.label(text="Warnings:", icon=version_compat.get_icon('INFO'))
                col = val_box.column()
                for warn in self.warnings:
                    col.label(text=f"• {warn}")
        else:
            row = layout.row()
            row.alignment = 'CENTER'
            row.label(text="All checks passed. Ready to render.", icon=version_compat.get_icon('CHECKMARK'))
            
        layout.separator()
        

    
    def execute(self, context):
        if self.errors:
             self.report({'ERROR'}, "Cannot start render with errors")
             return {'CANCELLED'}

        # Save file if dirty
        if bpy.data.is_dirty:
            try:
                bpy.ops.wm.save_mainfile()
                self.report({'INFO'}, "File saved")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to save: {e}")
                return {'CANCELLED'}
        
        # Call the actual render operator
        bpy.ops.rendercue.batch_render('INVOKE_DEFAULT')
        return {'FINISHED'}


class RENDERCUE_OT_show_summary_popup(bpy.types.Operator):
    """Show a modal popup with render summary."""
    bl_idname = "rendercue.show_summary_popup"
    bl_label = "Render Complete"
    bl_description = "Show render summary"
    bl_options = {'INTERNAL'}
    
    def invoke(self, context, event):
        # Use invoke_props_dialog for proper dialog closure
        return context.window_manager.invoke_props_dialog(self, width=400)
        
    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        
        # Title
        row = layout.row()
        row.label(text="Render Job Completed", icon=version_compat.get_icon('CHECKMARK'))
        
        layout.separator()
        
        # Stats
        box = layout.box()
        col = box.column(align=True)
        
        row = col.row()
        row.alignment = 'LEFT'
        row.label(text=f"Total Time: {settings.summary_render_time}")
        
        row = col.row()
        row.alignment = 'LEFT'
        row.label(text=f"Frames: {settings.summary_total_frames}")
        
        row = col.row()
        row.alignment = 'LEFT'
        row.label(text=f"Jobs: {settings.summary_successful_jobs} / {settings.summary_total_jobs}")
        
        if settings.summary_failed_jobs > 0:
            row = col.row()
            row.alert = True
            row.label(text=f"Failed: {settings.summary_failed_jobs}", icon=version_compat.get_icon('ERROR'))
            
        layout.separator()
        
        # Prompt
        row = layout.row()
        row.alignment = 'CENTER'
        row.label(text="Open output folder?", icon=version_compat.get_icon('FILE_FOLDER'))
        
    def execute(self, context):
        settings = context.window_manager.rendercue
        output_path = settings.summary_output_path
        
        if output_path and os.path.exists(output_path):
            bpy.ops.wm.path_open(filepath=output_path)
        else:
            # Fallback to the open_output_folder operator if path is invalid
            bpy.ops.rendercue.open_output_folder()
        
        return {'FINISHED'}

class RENDERCUE_OT_clear_status(bpy.types.Operator):
    """Clear the last render status message."""
    bl_idname = "rendercue.clear_status"
    bl_label = "Clear Status"
    bl_description = "Clear the last render status message"
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        settings.last_render_status = 'NONE'
        settings.last_render_message = ""
        return {'FINISHED'}

class RENDERCUE_OT_load_data(bpy.types.Operator):
    """Load saved RenderCue data from this blend file."""
    bl_idname = "rendercue.load_data"
    bl_label = "Load RenderCue Data"
    bl_description = "Load saved RenderCue data from this blend file"
    def execute(self, context):
        """Execute the operator."""
        StateManager.load_queue_from_text(context)
        self.report({'INFO'}, "RenderCue data loaded")
        return {'FINISHED'}

classes = (
    RENDERCUE_OT_add_job,
    RENDERCUE_OT_remove_job,
    RENDERCUE_OT_move_job,
    RENDERCUE_OT_populate_all,
    RENDERCUE_OT_apply_override_to_all,
    RENDERCUE_OT_remove_override,
    RENDERCUE_OT_open_output_folder,
    RENDERCUE_OT_validate_queue,
    RENDERCUE_OT_save_preset,
    RENDERCUE_OT_load_preset,
    RENDERCUE_OT_quick_preset,
    RENDERCUE_OT_switch_to_job_scene,
    RENDERCUE_OT_stop_render,
    RENDERCUE_OT_pause_render,
    RENDERCUE_OT_resume_render,
    RENDERCUE_OT_browse_path,
    RENDERCUE_OT_load_data,
    RENDERCUE_OT_show_summary_popup,

    RENDERCUE_OT_clear_status,
    RENDERCUE_OT_confirm_render,

)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
