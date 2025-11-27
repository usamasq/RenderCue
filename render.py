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
    _total_jobs = 0
    _start_time = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self._stop:
                self.restore_settings()
                self.finish(context)
                return {'CANCELLED'}

            if self._rendering:
                # Update progress display
                wm = context.window_manager
                wm.progress_update(self._job_index)
                return {'PASS_THROUGH'}
            
            # If we were rendering but now _rendering is False, it means we finished a job
            if self._current_job_scene:
                self.restore_settings()
                self._current_job_scene = None
                self._job_index += 1
            
            # Check if we have more jobs
            wm = context.window_manager
            if self._job_index < len(context.scene.rendercue.jobs):
                self.start_next_job(context)
            else:
                self.finish(context)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        if not context.scene.rendercue.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}
            
        self._job_index = 0
        self._rendering = False
        self._stop = False
        self._original_settings = {}
        self._current_job_scene = None
        self._total_jobs = len(context.scene.rendercue.jobs)
        
        # Setup progress bar
        wm.progress_begin(0, self._total_jobs)
        
        # Register handlers
        bpy.app.handlers.render_init.append(self.on_render_init)
        bpy.app.handlers.render_complete.append(self.on_render_complete)
        bpy.app.handlers.render_cancel.append(self.on_render_cancel)
        bpy.app.handlers.render_pre.append(self.on_render_pre)
        bpy.app.handlers.render_post.append(self.on_render_post)
        
        wm.modal_handler_add(self)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        
        self.report({'INFO'}, f"Starting Batch Render: {self._total_jobs} scenes")
        return {'RUNNING_MODAL'}

    def start_next_job(self, context):
        wm = context.window_manager
        settings = context.scene.rendercue
        job = settings.jobs[self._job_index]
        
        if not job.scene:
            self._job_index += 1
            return

        self._rendering = True
        self._current_job_scene = job.scene
        
        # Apply Overrides
        self.apply_overrides(job, settings)
        
        # Update progress message
        progress_msg = f"Rendering {self._job_index + 1}/{self._total_jobs}: {job.scene.name}"
        self.report({'INFO'}, progress_msg)
        print(f"[RenderCue] {progress_msg}")
        
        # Start Render
        # Use INVOKE_DEFAULT to show render window with progress
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
            base_path = job.output_path
        else:
            base_path = settings.global_output_path
        
        # Convert relative paths to absolute
        if base_path.startswith("//"):
            base_path = bpy.path.abspath(base_path)
            
        # Structure
        if settings.output_structure == 'SEPARATE':
            output_dir = os.path.join(base_path, scene.name)
        else:
            output_dir = base_path
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Set filepath with filename pattern
        # For image sequences: filename_####.ext
        # For videos: filename.ext
        filename = scene.name.replace(" ", "_")  # Remove spaces for safety
        
        # Check if rendering video or images
        render_format = job.render_format if job.override_format else scene.render.image_settings.file_format
        
        if render_format == 'FFMPEG':
            # Video format - no frame number needed
            filepath = os.path.join(output_dir, f"{filename}.mp4")
        else:
            # Image sequence - add frame number pattern
            filepath = os.path.join(output_dir, f"{filename}_")
        
        scene.render.filepath = filepath
        
        print(f"[RenderCue] Output path set to: {filepath}")
        
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
                # Blender 5.0 compatibility: try different property names
                try:
                    self._original_settings['eevee_samples'] = scene.eevee.taa_render_samples
                    scene.eevee.taa_render_samples = job.samples
                except AttributeError:
                    # Fallback for Blender 5.0+
                    try:
                        self._original_settings['eevee_samples'] = scene.eevee.samples
                        scene.eevee.samples = job.samples
                    except AttributeError:
                        pass  # Eevee samples not available

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
            try:
                scene.eevee.taa_render_samples = orig['eevee_samples']
            except AttributeError:
                try:
                    scene.eevee.samples = orig['eevee_samples']
                except AttributeError:
                    pass
            
        self._original_settings = {}

    def on_render_init(self, scene, depsgraph=None):
        """Called when render is initialized"""
        print(f"[RenderCue] Render init for {scene.name}")

    def on_render_pre(self, scene, depsgraph=None):
        """Called before each frame"""
        frame = scene.frame_current
        print(f"[RenderCue] Rendering frame {frame}")

    def on_render_post(self, scene, depsgraph=None):
        """Called after each frame"""
        frame = scene.frame_current
        print(f"[RenderCue] Completed frame {frame}")

    def on_render_complete(self, scene, depsgraph=None):
        """Called when render completes successfully"""
        print(f"[RenderCue] Render complete for {scene.name}")
        self._rendering = False

    def on_render_cancel(self, scene, depsgraph=None):
        """Called when render is cancelled"""
        print(f"[RenderCue] Render cancelled for {scene.name}")
        self._rendering = False
        self._stop = True

    def finish(self, context):
        wm = context.window_manager
        
        # Clean up progress bar
        wm.progress_end()
        
        # Remove timer
        if self._timer:
            wm.event_timer_remove(self._timer)
        
        # Remove all handlers
        if self.on_render_init in bpy.app.handlers.render_init:
            bpy.app.handlers.render_init.remove(self.on_render_init)
        if self.on_render_complete in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.on_render_complete)
        if self.on_render_cancel in bpy.app.handlers.render_cancel:
            bpy.app.handlers.render_cancel.remove(self.on_render_cancel)
        if self.on_render_pre in bpy.app.handlers.render_pre:
            bpy.app.handlers.render_pre.remove(self.on_render_pre)
        if self.on_render_post in bpy.app.handlers.render_post:
            bpy.app.handlers.render_post.remove(self.on_render_post)
            
        self.report({'INFO'}, f"Batch Render Complete: {self._job_index}/{self._total_jobs} scenes rendered")

def register():
    bpy.utils.register_class(RENDERCUE_OT_batch_render)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_batch_render)

