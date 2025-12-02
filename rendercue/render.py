import bpy
import os
import time
import json
import subprocess
import sys
import atexit
from .core import StateManager, RenderCueLogger
from .notifications import send_webhook, show_notification
from .constants import (
    MANIFEST_FILENAME, STATUS_FILENAME, PAUSE_SIGNAL_FILENAME,
    STATUS_MESSAGE, STATUS_ETR, STATUS_JOB_INDEX, STATUS_FINISHED_FRAMES,
    STATUS_TOTAL_FRAMES, STATUS_LAST_FRAME, STATUS_ERROR,
    STATUS_JOB_STATUSES, STATUS_JOB_PROGRESS, STATUS_JOB_TIMINGS,
    STATUS_TOTAL_JOBS, DEFAULT_PROGRESS_MESSAGE, DEFAULT_ETR,
    STATUS_PAUSED_DURATION
)

# Global reference for atexit
_bg_process = None

def cleanup_process():
    global _bg_process
    if _bg_process:
        try:
            _bg_process.kill()
        except OSError:
            pass

atexit.register(cleanup_process)

class RENDERCUE_OT_batch_render(bpy.types.Operator):
    """Start background rendering of all jobs in the queue. Blender will remain responsive."""
    
    bl_idname = "rendercue.batch_render"
    bl_label = "Render Cue"
    bl_description = "Start background rendering of all jobs in the queue. Blender will remain responsive."
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
    _last_preview_path = None
    _last_finished_frames = -1

    def modal(self, context, event):
        """Handle modal events (timer ticks) to check render progress."""
        if event.type == 'TIMER':
            # Check for Stop Request
            if context.window_manager.rendercue.stop_requested:
                self._stop = True
                context.window_manager.rendercue.stop_requested = False # Reset flag
                
            if self._stop:
                if self._background_process:
                    self._background_process.kill()
                self.finish(context)
                return {'CANCELLED'}

            # Check Background Process
            if self._background_process:
                # Read Status first (to ensure we get the latest state even if it just finished)
                if self._status_file and os.path.exists(self._status_file):
                    try:
                        with open(self._status_file, 'r') as f:
                            status = json.load(f)
                            context.window_manager.rendercue.progress_message = status.get(STATUS_MESSAGE, DEFAULT_PROGRESS_MESSAGE)
                            
                            # Sync pause state from worker status
                            msg = status.get(STATUS_MESSAGE, "")
                            if "Paused" in msg:
                                context.window_manager.rendercue.is_paused = True
                            elif "Resuming" in msg or "Rendering" in msg:
                                context.window_manager.rendercue.is_paused = False

                            # Check for Error
                            if status.get(STATUS_ERROR):
                                # Send desktop notification
                                prefs = context.preferences.addons[__package__].preferences
                                if prefs.show_notifications:
                                    show_notification("RenderCue Error", status[STATUS_ERROR])
                                
                                self._stop = True

                            # Update Progress Stats
                            settings = context.window_manager.rendercue
                            
                            if STATUS_FINISHED_FRAMES in status:
                                settings.finished_frames_count = status[STATUS_FINISHED_FRAMES]
                            
                            if STATUS_TOTAL_FRAMES in status:
                                settings.total_frames_to_render = status[STATUS_TOTAL_FRAMES]
                                
                            if STATUS_ETR in status:
                                settings.etr = status[STATUS_ETR]
                                
                            if STATUS_JOB_INDEX in status:
                                # STATUS_JOB_INDEX is 1-based from worker, convert to 0-based
                                settings.current_job_index = status[STATUS_JOB_INDEX] - 1
                                
                            if STATUS_TOTAL_JOBS in status:
                                settings.total_jobs_count = status[STATUS_TOTAL_JOBS]

                            # Update job-level status and progress
                            job_statuses = status.get(STATUS_JOB_STATUSES, [])
                            job_progress = status.get(STATUS_JOB_PROGRESS, [])
                            job_timings = status.get(STATUS_JOB_TIMINGS, [])

                            for i, job in enumerate(settings.jobs):
                                if i < len(job_statuses):
                                    job.render_status = job_statuses[i]
                                
                                if i < len(job_progress):
                                    progress = job_progress[i]
                                    if isinstance(progress, dict):
                                        job.completed_frames = progress.get('done', 0)
                                        job.total_frames = progress.get('total', 0)
                                
                                if i < len(job_timings):
                                    timing = job_timings[i]
                                    if isinstance(timing, dict):
                                        if 'start' in timing and timing['start'] > 0:
                                            job.start_time = timing['start']
                                        if 'end' in timing and timing['end'] > 0:
                                            job.end_time = timing['end']
                            
                            # Update Preview
                            # Use finished_frames count to detect new frames because path is constant
                            current_finished = status.get(STATUS_FINISHED_FRAMES, 0)
                            last_frame_path = status.get(STATUS_LAST_FRAME)
                            
                            if last_frame_path and current_finished > self._last_finished_frames:
                                self._last_finished_frames = current_finished
                                self.update_preview(context, last_frame_path)
                    except (OSError, json.JSONDecodeError):
                        # File might be locked or partially written, just skip this update
                        pass

            if self._background_process.poll() is not None:
                # Process finished
                self.finish(context)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        """Initialize and start the background render process."""
        wm = context.window_manager
        if not context.window_manager.rendercue.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}
            
        # Reset state
        self._last_preview_path = None
        self._last_finished_frames = -1
            
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Save the file before background rendering")
            return {'CANCELLED'}
            
        # Clear completion data from previous render
        # (This gives fresh start when user clicks Render again)
        for job in context.window_manager.rendercue.jobs:
            job.completed_frames = 0
            job.total_frames = 0
        
        # Reset global progress counters
        context.window_manager.rendercue.finished_frames_count = 0

        # Clear Preview Thumbnail
        # This ensures we don't show the previous job's last frame
        
        # 1. Unlink from UI property first (Critical for releasing reference)
        context.window_manager.rendercue.preview_image = None
        
        # 2. Remove the data block
        image_name = "RenderCue Preview"
        if image_name in bpy.data.images:
            img = bpy.data.images[image_name]
            try:
                bpy.data.images.remove(img)
            except Exception as e:
                print(f"Warning: Could not remove preview image: {e}")
        
        # Clear UI Collection
        try:
            from . import ui
            if "main" in ui.preview_collections:
                pcoll = ui.preview_collections["main"]
                pcoll.clear()
        except Exception as e:
            print(f"Error clearing preview: {e}")
            
        # Setup Paths
        temp_dir = bpy.app.tempdir
        self._manifest_file = os.path.join(temp_dir, MANIFEST_FILENAME)
        self._status_file = os.path.join(temp_dir, STATUS_FILENAME)
        
        # Cleanup old pause signal
        pause_file = os.path.join(temp_dir, PAUSE_SIGNAL_FILENAME)
        if os.path.exists(pause_file):
            try:
                os.remove(pause_file)
            except OSError:
                pass
        
        # Reset Pause State
        context.window_manager.rendercue.is_paused = False
        
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
        
        global _bg_process
        self._background_process = subprocess.Popen(cmd)
        _bg_process = self._background_process
        
        context.window_manager.rendercue.is_rendering = True
        context.window_manager.rendercue.total_jobs_count = len(context.window_manager.rendercue.jobs)
        context.window_manager.rendercue.progress_message = "Starting Background Render..."
        
        # Track start time
        self._start_time = time.time()
        
        wm.modal_handler_add(self)
        self._timer = wm.event_timer_add(1.0, window=context.window)
        return {'RUNNING_MODAL'}

    def finish(self, context):
        """Clean up after rendering finishes (success or failure)."""
        wm = context.window_manager
        prefs = context.preferences.addons[__package__].preferences
        settings = context.window_manager.rendercue
        
        # Clean up timer and progress bar
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        wm.progress_end()
        
        # Reset rendering state
        settings.is_rendering = False
        # Generate summary (only if jobs were actually rendered)
        if len(settings.jobs) > 0:
            total_jobs = len(settings.jobs)
            successful = sum(1 for j in settings.jobs if j.render_status == 'COMPLETED')
            failed = sum(1 for j in settings.jobs if j.render_status == 'FAILED')
            cancelled = sum(1 for j in settings.jobs if j.render_status == 'CANCELLED')
            total_frames = sum(j.completed_frames for j in settings.jobs)
            
            # Calculate total render time
            duration = time.time() - getattr(self, '_start_time', time.time())
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours}h "
            if minutes > 0 or hours > 0:
                time_str += f"{minutes}m "
            time_str += f"{seconds}s"
            
            # Store summary
            settings.summary_total_jobs = total_jobs
            settings.summary_successful_jobs = successful
            settings.summary_failed_jobs = failed
            settings.summary_total_frames = total_frames
            settings.summary_render_time = time_str
            settings.summary_blend_file = os.path.basename(bpy.data.filepath) or "Untitled.blend"
            settings.summary_session_id = getattr(self, '_session_id', '')
            settings.summary_timestamp = time.time()
            
            # Show banner
            settings.show_summary_banner = True
            
            # Start auto-dismiss timer if configured
            prefs = context.preferences.addons[__package__].preferences
            if hasattr(prefs, 'banner_auto_dismiss') and prefs.banner_auto_dismiss > 0:
                settings.summary_auto_dismiss_seconds = prefs.banner_auto_dismiss

        # Desktop Notification
        if prefs.show_notifications:
            # Calculate duration
            duration = time.time() - getattr(self, '_start_time', time.time())
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours}h "
            if minutes > 0 or hours > 0:
                time_str += f"{minutes}m "
            time_str += f"{seconds}s"
            
            filename = os.path.basename(bpy.data.filepath) or "Untitled.blend"
            frames = context.window_manager.rendercue.finished_frames_count
            
            msg = f"File: {filename}\nFrames: {frames}\nTime: {time_str}"
            show_notification("RenderCue Complete", msg)
            
        # Update Status
        if not self._stop: # Only if not cancelled/error
            context.window_manager.rendercue.last_render_status = 'SUCCESS'
            context.window_manager.rendercue.last_render_message = "Finished successfully"

    def update_preview(self, context, filepath):
        """Update the preview image in the UI.

        Args:
            context (bpy.types.Context): Blender context.
            filepath (str): Path to the preview image file.
        """
        if not filepath or not os.path.exists(filepath):
            return
            
        settings = context.window_manager.rendercue
        image_name = "RenderCue Preview"
        
        img = bpy.data.images.get(image_name)
        
        if img:
            # CRITICAL FIX: Reload existing image instead of deleting
            # Deleting breaks the UI template_image binding
            try:
                img.filepath = filepath
                img.reload()
            except:
                # Fallback: recreate if reload fails
                bpy.data.images.remove(img)
                img = None
        
        if not img:
            # First time or reload failed: create new image
            try:
                img = bpy.data.images.load(filepath, check_existing=False)
                img.name = image_name
            except RuntimeError:
                return
        
        # Force update
        img.update()
        
        # CRITICAL: Re-assign property to trigger UI update
        # Even if it's the same object, this assignment notifies the UI system
        settings.preview_image = img
        
        # Update UI Preview Collection
        try:
            from . import ui
            if "main" in ui.preview_collections:
                pcoll = ui.preview_collections["main"]
                
                # Dynamic Key Strategy:
                # Force UI update by using a new key every time.
                # This defeats Blender's icon caching mechanism.
                old_key = settings.preview_icon_key
                new_key = f"thumbnail_{int(time.time() * 1000)}"
                print(f"DEBUG: Loading preview {new_key} from {filepath}")
                
                # Load new preview
                pcoll.load(new_key, filepath, 'IMAGE')
                
                # Update property so UI knows what to show
                settings.preview_icon_key = new_key
                print(f"DEBUG: Updated settings.preview_icon_key to {new_key}")
                
                # Cleanup old key to prevent memory leaks
                if old_key and old_key in pcoll and old_key != new_key:
                    del pcoll[old_key]
                    
        except Exception as e:
            print(f"Preview Collection Error: {e}")
        
        # Force UI redraw
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'PROPERTIES':
                    area.tag_redraw()

def register():
    bpy.utils.register_class(RENDERCUE_OT_batch_render)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_batch_render)
