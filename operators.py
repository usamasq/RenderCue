import bpy

class RENDERCUE_OT_add_job(bpy.types.Operator):
    bl_idname = "rendercue.add_job"
    bl_label = "Add Scene"
    bl_description = "Add the current scene to the render queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wm = context.window_manager
        settings = wm.rendercue
        
        job = settings.jobs.add()
        job.scene = context.scene
        
        # Set default overrides to match scene? No, keep them disabled by default.
        settings.active_job_index = len(settings.jobs) - 1
        return {'FINISHED'}

class RENDERCUE_OT_remove_job(bpy.types.Operator):
    bl_idname = "rendercue.remove_job"
    bl_label = "Remove Job"
    bl_description = "Remove the selected job from the queue"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return wm.rendercue.jobs and wm.rendercue.active_job_index >= 0

    def execute(self, context):
        wm = context.window_manager
        settings = wm.rendercue
        
        settings.jobs.remove(settings.active_job_index)
        
        if settings.active_job_index >= len(settings.jobs):
            settings.active_job_index = max(0, len(settings.jobs) - 1)
            
        return {'FINISHED'}

class RENDERCUE_OT_move_job(bpy.types.Operator):
    bl_idname = "rendercue.move_job"
    bl_label = "Move Job"
    bl_description = "Move the selected job up or down"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction: bpy.props.EnumProperty(items=[('UP', "Up", ""), ('DOWN', "Down", "")])

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return wm.rendercue.jobs and wm.rendercue.active_job_index >= 0

    def execute(self, context):
        wm = context.window_manager
        settings = wm.rendercue
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
    bl_description = "Add all scenes in the file to the queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wm = context.window_manager
        settings = wm.rendercue
        
        existing_scenes = {job.scene for job in settings.jobs if job.scene}
        
        for scene in bpy.data.scenes:
            if scene not in existing_scenes:
                job = settings.jobs.add()
                job.scene = scene
                
        return {'FINISHED'}

class RENDERCUE_OT_apply_override_to_all(bpy.types.Operator):
    bl_idname = "rendercue.apply_override_to_all"
    bl_label = "Apply to All Jobs"
    bl_description = "Copy this override setting to all other jobs in the queue"
    bl_options = {'REGISTER', 'UNDO'}
    
    data_path_bool: bpy.props.StringProperty()
    data_path_val: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return wm.rendercue.jobs and wm.rendercue.active_job_index >= 0

    def execute(self, context):
        wm = context.window_manager
        settings = wm.rendercue
        
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

def register():
    bpy.utils.register_class(RENDERCUE_OT_add_job)
    bpy.utils.register_class(RENDERCUE_OT_remove_job)
    bpy.utils.register_class(RENDERCUE_OT_move_job)
    bpy.utils.register_class(RENDERCUE_OT_populate_all)
    bpy.utils.register_class(RENDERCUE_OT_apply_override_to_all)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_apply_override_to_all)
    bpy.utils.unregister_class(RENDERCUE_OT_populate_all)
    bpy.utils.unregister_class(RENDERCUE_OT_move_job)
    bpy.utils.unregister_class(RENDERCUE_OT_remove_job)
    bpy.utils.unregister_class(RENDERCUE_OT_add_job)
