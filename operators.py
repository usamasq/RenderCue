import bpy
import os
import json
from .core import StateManager

class RENDERCUE_OT_add_job(bpy.types.Operator):
    bl_idname = "rendercue.add_job"
    bl_label = "Add Scene"
    bl_description = "Add the current active scene to the render queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.window_manager.rendercue
        
        job = settings.jobs.add()
        job.scene = context.scene
        
        # Set default overrides to match scene? No, keep them disabled by default.
        settings.active_job_index = len(settings.jobs) - 1
        return {'FINISHED'}

class RENDERCUE_OT_remove_job(bpy.types.Operator):
    bl_idname = "rendercue.remove_job"
    bl_label = "Remove Job"
    bl_description = "Remove the currently selected job from the queue"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.window_manager.rendercue.jobs and context.window_manager.rendercue.active_job_index >= 0

    def execute(self, context):
        settings = context.window_manager.rendercue
        
        settings.jobs.remove(settings.active_job_index)
        
        if settings.active_job_index >= len(settings.jobs):
            settings.active_job_index = max(0, len(settings.jobs) - 1)
            
        return {'FINISHED'}

class RENDERCUE_OT_move_job(bpy.types.Operator):
    bl_idname = "rendercue.move_job"
    bl_label = "Move Job"
    bl_description = "Move the selected job up or down in the list"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction: bpy.props.EnumProperty(items=[('UP', "Up", ""), ('DOWN', "Down", "")])

    @classmethod
    def poll(cls, context):
        return context.window_manager.rendercue.jobs and context.window_manager.rendercue.active_job_index >= 0

    def execute(self, context):
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
    bl_idname = "rendercue.populate_all"
    bl_label = "Add All Scenes"
    bl_description = "Add all scenes in this .blend file to the render queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.window_manager.rendercue
        
        existing_scenes = {job.scene for job in settings.jobs if job.scene}
        
        for scene in bpy.data.scenes:
            if scene not in existing_scenes:
                job = settings.jobs.add()
                job.scene = scene
                
        return {'FINISHED'}

class RENDERCUE_OT_apply_override_to_all(bpy.types.Operator):
    bl_idname = "rendercue.apply_override_to_all"
    bl_label = "Apply to All Jobs"
    bl_description = "Apply this specific override setting to all jobs in the queue"
    bl_options = {'REGISTER', 'UNDO'}
    
    data_path_bool: bpy.props.StringProperty()
    data_path_val: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return context.window_manager.rendercue.jobs and context.window_manager.rendercue.active_job_index >= 0

    def execute(self, context):
        settings = context.window_manager.rendercue
        
        if not settings.jobs:
            return {'CANCELLED'}
            
        source_job = settings.jobs[settings.active_job_index]
        
        # Get values from source
        override_enabled = getattr(source_job, self.data_path_bool)
        
        # Special case for frame_range (two values)
        if self.data_path_val == "frame_range":
            frame_start = source_job.frame_start
            frame_end = source_job.frame_end
            
            for job in settings.jobs:
                setattr(job, self.data_path_bool, override_enabled)
                if override_enabled:
                    job.frame_start = frame_start
                    job.frame_end = frame_end
        else:
            override_value = getattr(source_job, self.data_path_val)
            
            for job in settings.jobs:
                setattr(job, self.data_path_bool, override_enabled)
                if override_enabled:
                    setattr(job, self.data_path_val, override_value)
        
        self.report({'INFO'}, f"Applied override to {len(settings.jobs)} jobs")
        return {'FINISHED'}

class RENDERCUE_OT_open_output_folder(bpy.types.Operator):
    bl_idname = "rendercue.open_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Open the global output directory in your operating system's file explorer"
    
    def execute(self, context):
        settings = context.window_manager.rendercue
        path = bpy.path.abspath(settings.global_output_path)
        
        if not os.path.exists(path):
            self.report({'WARNING'}, f"Directory does not exist: {path}")
            return {'CANCELLED'}
            
        bpy.ops.wm.path_open(filepath=path)
        return {'FINISHED'}

class RENDERCUE_OT_validate_queue(bpy.types.Operator):
    bl_idname = "rendercue.validate_queue"
    bl_label = "Validate Queue"
    bl_description = "Check the queue for common errors (missing cameras, invalid paths, unsaved files) before rendering"
    
    def execute(self, context):
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
                except:
                    errors.append(f"Cannot create output directory: {path}")
        
        # Check Jobs
        if not settings.jobs:
            errors.append("Queue is empty")
            
        for i, job in enumerate(settings.jobs):
            if not job.scene:
                errors.append(f"Job {i+1}: No scene assigned")
            elif not job.scene.camera:
                errors.append(f"Job {i+1} ({job.scene.name}): No active camera")
                
        if errors:
            self.report({'ERROR'}, f"Validation Failed: {len(errors)} errors found")
            for err in errors:
                self.report({'ERROR'}, err)
            return {'CANCELLED'}
            
        self.report({'INFO'}, "Validation Passed! Queue is ready.")
        return {'FINISHED'}

class RENDERCUE_OT_save_preset(bpy.types.Operator):
    bl_idname = "rendercue.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the current queue configuration (jobs and overrides) to a JSON preset file"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        if not self.filepath.endswith(".json"):
            self.filepath += ".json"
            
        StateManager.save_state(context, self.filepath)
        self.report({'INFO'}, f"Preset saved: {self.filepath}")
        return {'FINISHED'}

class RENDERCUE_OT_load_preset(bpy.types.Operator):
    bl_idname = "rendercue.load_preset"
    bl_label = "Load Preset"
    bl_description = "Load a queue configuration from a saved JSON preset file (replaces current queue)"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        if StateManager.load_state(context, self.filepath):
            self.report({'INFO'}, "Preset loaded successfully")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to load preset")
            return {'CANCELLED'}

class RENDERCUE_OT_switch_to_job_scene(bpy.types.Operator):
    bl_idname = "rendercue.switch_to_job_scene"
    bl_label = "Switch to Scene"
    bl_description = "Switch the current window to this job's scene"
    
    index: bpy.props.IntProperty()
    
    def execute(self, context):
        settings = context.window_manager.rendercue
        if self.index < 0 or self.index >= len(settings.jobs):
            return {'CANCELLED'}
            
        job = settings.jobs[self.index]
        if job.scene:
            context.window.scene = job.scene
            settings.active_job_index = self.index
            
        return {'FINISHED'}

class RENDERCUE_OT_stop_render(bpy.types.Operator):
    bl_idname = "rendercue.stop_render"
    bl_label = "Stop Render"
    bl_description = "Stop the current render process"
    
    def execute(self, context):
        context.window_manager.rendercue.stop_requested = True
        self.report({'INFO'}, "Stopping render...")
        return {'FINISHED'}

class RENDERCUE_OT_pause_render(bpy.types.Operator):
    bl_idname = "rendercue.pause_render"
    bl_label = "Pause Render"
    bl_description = "Pause the current render process"
    
    def execute(self, context):
        context.window_manager.rendercue.is_paused = True
        # Create pause signal file
        pause_file = os.path.join(bpy.app.tempdir, "rendercue_pause.signal")
        try:
            with open(pause_file, 'w') as f:
                f.write("PAUSE")
        except:
            pass
        return {'FINISHED'}

class RENDERCUE_OT_resume_render(bpy.types.Operator):
    bl_idname = "rendercue.resume_render"
    bl_label = "Resume Render"
    bl_description = "Resume the current render process"
    
    def execute(self, context):
        context.window_manager.rendercue.is_paused = False
        # Remove pause signal file
        pause_file = os.path.join(bpy.app.tempdir, "rendercue_pause.signal")
        if os.path.exists(pause_file):
            try:
                os.remove(pause_file)
            except:
                pass
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RENDERCUE_OT_add_job)
    bpy.utils.register_class(RENDERCUE_OT_remove_job)
    bpy.utils.register_class(RENDERCUE_OT_move_job)
    bpy.utils.register_class(RENDERCUE_OT_populate_all)
    bpy.utils.register_class(RENDERCUE_OT_apply_override_to_all)
    bpy.utils.register_class(RENDERCUE_OT_open_output_folder)
    bpy.utils.register_class(RENDERCUE_OT_validate_queue)
    bpy.utils.register_class(RENDERCUE_OT_save_preset)
    bpy.utils.register_class(RENDERCUE_OT_load_preset)
    bpy.utils.register_class(RENDERCUE_OT_switch_to_job_scene)
    bpy.utils.register_class(RENDERCUE_OT_stop_render)
    bpy.utils.register_class(RENDERCUE_OT_pause_render)
    bpy.utils.register_class(RENDERCUE_OT_resume_render)

def unregister():
    for cls in (
        RENDERCUE_OT_resume_render,
        RENDERCUE_OT_pause_render,
        RENDERCUE_OT_stop_render,
        RENDERCUE_OT_switch_to_job_scene,
        RENDERCUE_OT_load_preset,
        RENDERCUE_OT_save_preset,
        RENDERCUE_OT_validate_queue,
        RENDERCUE_OT_open_output_folder,
        RENDERCUE_OT_apply_override_to_all,
        RENDERCUE_OT_populate_all,
        RENDERCUE_OT_move_job,
        RENDERCUE_OT_remove_job,
        RENDERCUE_OT_add_job,
    ):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
