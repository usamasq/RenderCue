import bpy
import os
import time
import json
import subprocess
import sys
from .core import StateManager, RenderCueLogger
from .notifications import send_webhook

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
    _total_frames_to_render = 0
    _background_process = None
    _status_file = None
    _manifest_file = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self._stop:
                if self._background_process:
                    self._background_process.kill()
                self.restore_settings()
                self.finish(context)
                return {'CANCELLED'}

            # Check Background Process
            if self._background_process:
                if self._background_process.poll() is not None:
                    # Process finished
                    self.finish(context)
                    return {'FINISHED'}
                
                # Read Status
                if self._status_file and os.path.exists(self._status_file):
                    try:
                        with open(self._status_file, 'r') as f:
                            status = json.load(f)
                            context.scene.rendercue.progress_message = status.get("message", "Rendering...")
                            context.scene.rendercue.etr = status.get("etr", "--:--")
                            context.scene.rendercue.current_job_index = status.get("job_index", 0)
                            context.scene.rendercue.finished_frames_count = status.get("finished_frames", 0)
                            context.scene.rendercue.total_frames_to_render = status.get("total_frames", 0)
                            last_frame = status.get("last_frame", "")
                            context.scene.rendercue.last_rendered_frame = last_frame
                            
                            if last_frame:
                                self.update_preview(context, last_frame)
                            
                            if status.get("error"):
                                self.report({'ERROR'}, status["error"])
                                self._stop = True
                    except:
                        pass
                return {'PASS_THROUGH'}

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
            
        # Check Render Mode
        render_mode = context.scene.rendercue.render_mode
        
        if render_mode == 'BACKGROUND':
            if not bpy.data.is_saved:
                self.report({'ERROR'}, "Save the file before background rendering")
                return {'CANCELLED'}
                
            # Setup Paths
            temp_dir = bpy.app.tempdir
            self._manifest_file = os.path.join(temp_dir, "rendercue_manifest.json")
            self._status_file = os.path.join(temp_dir, "rendercue_status.json")
            
            # Save Manifest
            StateManager.save_state(context, self._manifest_file)
            
            # Spawn Process
            worker_script = os.path.join(os.path.dirname(__file__), "worker.py")
            blend_file = bpy.data.filepath
            
            cmd = [
                bpy.app.binary_path,
                "-b", blend_file,
                "-P", worker_script,
                "--",
                "--manifest", self._manifest_file,
                "--status", self._status_file
            ]
            
            self._background_process = subprocess.Popen(cmd)
            
            context.scene.rendercue.is_rendering = True
            context.scene.rendercue.progress_message = "Starting Background Render..."
            
            wm.modal_handler_add(self)
            self._timer = wm.event_timer_add(1.0, window=context.window)
            return {'RUNNING_MODAL'}

        # FOREGROUND MODE (Existing Logic)
        self._job_index = 0
        self._rendering = False
        self._stop = False
        self._original_settings = {}
        self._current_job_scene = None
        self._total_jobs = len(context.scene.rendercue.jobs)
        
        # Update UI State
        context.scene.rendercue.is_rendering = True
        context.scene.rendercue.total_jobs_count = self._total_jobs
        context.scene.rendercue.current_job_index = 0
        context.scene.rendercue.progress_message = "Starting Batch Render..."
        context.scene.rendercue.start_time = time.time()
        context.scene.rendercue.finished_frames_count = 0
        context.scene.rendercue.etr = "Calculating..."
        
        # Calculate total frames (approximate)
        self._total_frames_to_render = 0
        for job in context.scene.rendercue.jobs:
            if job.scene:
                start = job.scene.frame_start
                end = job.scene.frame_end
                if job.override_frame_range:
                    start = job.frame_start
                    end = job.frame_end
                self._total_frames_to_render += (end - start + 1)
        
        context.scene.rendercue.total_frames_to_render = self._total_frames_to_render
        
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
        
        # Update UI State
        settings.current_job_index = self._job_index + 1
        settings.progress_message = progress_msg
        
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
        
        if render_format in ['FFMPEG', 'AVI_JPEG', 'AVI_RAW']:
            # Video format - no frame number needed
            ext = ".mp4" if render_format == 'FFMPEG' else ".avi"
            filepath = os.path.join(output_dir, f"{filename}{ext}")
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
        
        # Update ETR
        settings = scene.rendercue
        settings.finished_frames_count += 1
        
        elapsed = time.time() - settings.start_time
        if settings.finished_frames_count > 0 and self._total_frames_to_render > 0:
            avg_time_per_frame = elapsed / settings.finished_frames_count
            remaining_frames = self._total_frames_to_render - settings.finished_frames_count
            remaining_seconds = avg_time_per_frame * remaining_frames
            
            # Format ETR
            mins, secs = divmod(int(remaining_seconds), 60)
            hrs, mins = divmod(mins, 60)
            if hrs > 0:
                settings.etr = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            else:
                settings.etr = f"{mins:02d}:{secs:02d}"
                
        # Update Progress Message
        settings.progress_message = f"Rendering {self._job_index + 1}/{self._total_jobs}: {scene.name} (Frame {frame})"
        
        # Update Last Frame
        try:
            # Save Preview for Foreground Render
            preview_path = os.path.join(bpy.app.tempdir, ".rendercue_preview.jpg")
            if 'Render Result' in bpy.data.images:
                orig_format = scene.render.image_settings.file_format
                scene.render.image_settings.file_format = 'JPEG'
                bpy.data.images['Render Result'].save_render(filepath=preview_path)
                scene.render.image_settings.file_format = orig_format
                
                settings.last_rendered_frame = preview_path
                self.update_preview(bpy.context, preview_path)
        except Exception as e:
            print(f"Preview error: {e}")

    def on_render_complete(self, scene, depsgraph=None):
        """Called when render completes successfully"""
        print(f"[RenderCue] Render complete for {scene.name}")
        self._rendering = False

    def on_render_cancel(self, scene, depsgraph=None):
        """Called when render is cancelled"""
        print(f"[RenderCue] Render cancelled for {scene.name}")
        self._rendering = False
        self._stop = True
        scene.rendercue.is_rendering = False
        scene.rendercue.progress_message = "Cancelled"

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
        
        # Reset UI State
        context.scene.rendercue.is_rendering = False
        context.scene.rendercue.progress_message = "Done"
        context.scene.rendercue.etr = "--:--"
        
        # Sound Notification
        prefs = context.preferences.addons[__package__].preferences
        if prefs.play_sound_on_finish:
            try:
                import winsound
                winsound.MessageBeep()
            except:
                print('\a') # Fallback beep
            
        # Webhook Notification
        if prefs.webhook_url:
            send_webhook(prefs.webhook_url, "Batch Render Completed Successfully!")

    def update_preview(self, context, filepath):
        if not filepath or not os.path.exists(filepath):
            return
            
        settings = context.scene.rendercue
        image_name = "RenderCue Preview"
        
        img = bpy.data.images.get(image_name)
        if not img:
            try:
                img = bpy.data.images.load(filepath)
                img.name = image_name
            except:
                return
        else:
            img.filepath = filepath
            img.reload()
                
        settings.preview_image = img

def register():
    bpy.utils.register_class(RENDERCUE_OT_batch_render)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_batch_render)

