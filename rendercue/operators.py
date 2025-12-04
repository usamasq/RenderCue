import bpy
import os
import json
from .core import StateManager
from .constants import PAUSE_SIGNAL_FILENAME
from .properties import get_available_renderers

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
    apply_transparent: bpy.props.BoolProperty(name="Transparent")
    apply_compositor: bpy.props.BoolProperty(name="Compositor")
    apply_denoising: bpy.props.BoolProperty(name="Denoising")

    def invoke(self, context, event):
        """Show confirmation dialog with checkboxes."""
        settings = context.window_manager.rendercue
        if not settings.jobs:
            return {'CANCELLED'}
            
        source_job = settings.jobs[settings.active_job_index]
        
        # Reset all to False first
        for prop in self.__annotations__:
            if prop.startswith("apply_"):
                setattr(self, prop, False)
        
        # Enable the one that was clicked
        # Map data_path_bool (e.g. "override_resolution") to property name (e.g. "apply_resolution")
        clicked_prop = self.data_path_bool.replace("override_", "apply_")
        if hasattr(self, clicked_prop):
            setattr(self, clicked_prop, True)
            
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        source_job = settings.jobs[settings.active_job_index]
        
        layout.label(text="Select overrides to apply to all jobs:", icon='DUPLICATE')
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
            ("apply_transparent", "override_transparent", "Transparent"),
            ("apply_compositor", "override_compositor", "Compositor"),
            ("apply_denoising", "override_denoising", "Denoising"),
        ]
        
        has_options = False
        for apply_prop, source_bool, label in mappings:
            if getattr(source_job, source_bool, False):
                col.prop(self, apply_prop, text=label)
                has_options = True
                
        if not has_options:
            layout.label(text="No active overrides on this job.", icon='INFO')

    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        
        if not settings.jobs:
            return {'CANCELLED'}
            
        source_job = settings.jobs[settings.active_job_index]
        
        # Mapping: Apply Prop -> (Bool Prop, Value Prop)
        # Note: frame_range needs special handling
        mappings = {
            "apply_output": ("override_output", "output_path"),
            "apply_frame_range": ("override_frame_range", "frame_range"), # Special
            "apply_resolution": ("override_resolution", "resolution_scale"),
            "apply_samples": ("override_samples", "samples"),
            "apply_camera": ("override_camera", "camera"),
            "apply_engine": ("override_engine", "render_engine"),
            "apply_device": ("override_device", "device"),
            "apply_view_layer": ("override_view_layer", "view_layer"),
            "apply_frame_step": ("override_frame_step", "frame_step"),
            "apply_transparent": ("override_transparent", "use_transparent"),
            "apply_compositor": ("override_compositor", "use_compositor"),
            "apply_denoising": ("override_denoising", "use_denoising"),
        }
        
        applied_count = 0
        
        for apply_prop, (bool_prop, val_prop) in mappings.items():
            if getattr(self, apply_prop):
                applied_count += 1
                
                # Get value from source
                override_enabled = getattr(source_job, bool_prop)
                
                # Special case for frame_range
                if val_prop == "frame_range":
                    frame_start = source_job.frame_start
                    frame_end = source_job.frame_end
                    
                    for job in settings.jobs:
                        setattr(job, bool_prop, override_enabled)
                        if override_enabled:
                            job.frame_start = frame_start
                            job.frame_end = frame_end
                            if job.frame_end < job.frame_start:
                                job.frame_end = job.frame_start
                else:
                    override_value = getattr(source_job, val_prop)
                    for job in settings.jobs:
                        setattr(job, bool_prop, override_enabled)
                        if override_enabled:
                            setattr(job, val_prop, override_value)
        
        self.report({'INFO'}, f"Applied {applied_count} settings to {len(settings.jobs)} jobs")
        return {'FINISHED'}

class RENDERCUE_OT_open_output_folder(bpy.types.Operator):
    """Open the global output directory in the OS file explorer."""
    bl_idname = "rendercue.open_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Open the global output directory in your operating system's file explorer"
    
    def execute(self, context):
        """Execute the operator."""
        settings = context.window_manager.rendercue
        path = bpy.path.abspath(settings.global_output_path)
        
        if not os.path.exists(path):
            self.report({'WARNING'}, f"Directory does not exist: {path}")
            return {'CANCELLED'}
            
        bpy.ops.wm.path_open(filepath=path)
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
            print(f"Error clearing preview: {e}")
        
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

class RENDERCUE_OT_show_summary_popup(bpy.types.Operator):
    """Show a modal popup with render summary."""
    bl_idname = "rendercue.show_summary_popup"
    bl_label = "Render Complete"
    bl_description = "Show render summary"
    bl_options = {'INTERNAL'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
        
    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.rendercue
        
        # Title
        row = layout.row()
        row.label(text="Render Job Completed", icon='CHECKMARK')
        
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
            row.label(text=f"Failed: {settings.summary_failed_jobs}", icon='ERROR')
            
        layout.separator()
        
        # Actions
        row = layout.row()
        row.operator("rendercue.open_output_folder", icon='FILE_FOLDER', text="Open Output Folder")
        
    def execute(self, context):
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
