import bpy
import os

class RENDERCUE_OT_batch_render(bpy.types.Operator):
    bl_idname = "rendercue.batch_render"
    bl_label = "Render Cue"
    bl_description = "Process the render queue"
    bl_options = {'REGISTER'}

    _timer = None
    _job_index = 0
    _rendering = False
    _stop = False
    _original_settings = {}
    _current_job_scene = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self._stop:
                self.restore_settings()
                self.finish(context)
                return {'CANCELLED'}

            if self._rendering:
                return {'PASS_THROUGH'}
            
            # If we were rendering but now _rendering is False, it means we finished a job
            if self._current_job_scene:
                self.restore_settings()
                self._current_job_scene = None
                self._job_index += 1
            
            # Check if we have more jobs
            wm = context.window_manager
            if self._job_index < len(wm.rendercue.jobs):
                self.start_next_job(context)
            else:
                self.finish(context)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        if not wm.rendercue.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}
            
        self._job_index = 0
        self._rendering = False
        self._stop = False
        self._original_settings = {}
        self._current_job_scene = None
        
        # Register handlers
        # We bind the method to the instance
        bpy.app.handlers.render_complete.append(self.on_render_complete)
        bpy.app.handlers.render_cancel.append(self.on_render_cancel)
        
        wm.modal_handler_add(self)
        self._timer = wm.event_timer_add(0.5, window=context.window)
        
        self.report({'INFO'}, "Starting Batch Render...")
        return {'RUNNING_MODAL'}

    def start_next_job(self, context):
        wm = context.window_manager
        settings = wm.rendercue
        job = settings.jobs[self._job_index]
        
        if not job.scene:
            self._job_index += 1
            return

        self._rendering = True
        self._current_job_scene = job.scene
        
        # Apply Overrides
        self.apply_overrides(job, settings)
        
        self.report({'INFO'}, f"Rendering: {job.scene.name}")
        
        # Start Render
        # We use INVOKE_DEFAULT to ensure it runs properly, but for animation it might block?
        # If we use 'INVOKE_DEFAULT', it might spawn a new window.
        # If we use 'EXEC_DEFAULT', it blocks the UI.
        # Ideally we want 'INVOKE_DEFAULT' but we need to know when it finishes.
        # The handlers should work in both cases.
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True, write_still=True, scene=job.scene.name)

    def apply_overrides(self, job, settings):
        scene = job.scene
        
        # Store originals
        self._original_settings = {
            'filepath': scene.render.filepath,
            'frame_start': scene.frame_start,
            'frame_end': scene.frame_end,
            'resolution_x': scene.render.resolution_x,
            'resolution_y': scene.render.resolution_y,
            'resolution_percentage': scene.render.resolution_percentage,
            'file_format': scene.render.image_settings.file_format,
        }
        
        # Output Path
        if job.override_output:
            path = job.output_path
        else:
            path = settings.global_output_path
            
        # Structure
        if settings.output_structure == 'SEPARATE':
            path = os.path.join(path, scene.name, "")
        
        scene.render.filepath = path
        
        # Frame Range
        if job.override_frame_range:
            scene.frame_start = job.frame_start
            scene.frame_end = job.frame_end
            
        # Resolution
        if job.override_resolution:
            scene.render.resolution_percentage = job.resolution_scale
            
        # Format
        if job.override_format:
            scene.render.image_settings.file_format = job.render_format
            
        # Samples
        if job.override_samples:
            if scene.render.engine == 'CYCLES':
                self._original_settings['cycles_samples'] = scene.cycles.samples
                scene.cycles.samples = job.samples
            elif scene.render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
                self._original_settings['eevee_samples'] = scene.eevee.taa_render_samples
                scene.eevee.taa_render_samples = job.samples

    def restore_settings(self):
        if not self._current_job_scene:
            return
            
        scene = self._current_job_scene
        orig = self._original_settings
        
        if not orig:
            return

        scene.render.filepath = orig['filepath']
        scene.frame_start = orig['frame_start']
        scene.frame_end = orig['frame_end']
        scene.render.resolution_percentage = orig['resolution_percentage']
        scene.render.image_settings.file_format = orig['file_format']
        
        if 'cycles_samples' in orig:
            scene.cycles.samples = orig['cycles_samples']
        if 'eevee_samples' in orig:
            scene.eevee.taa_render_samples = orig['eevee_samples']
            
        self._original_settings = {}

    def on_render_complete(self, scene, layer=None):
        # We need to ensure this is the scene we are tracking?
        # For now assume yes as we render one by one.
        self._rendering = False

    def on_render_cancel(self, scene, layer=None):
        self._rendering = False
        self._stop = True

    def finish(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        
        if self.on_render_complete in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.on_render_complete)
        if self.on_render_cancel in bpy.app.handlers.render_cancel:
            bpy.app.handlers.render_cancel.remove(self.on_render_cancel)
            
        self.report({'INFO'}, "Batch Render Finished")

def register():
    bpy.utils.register_class(RENDERCUE_OT_batch_render)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_batch_render)
