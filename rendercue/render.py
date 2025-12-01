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
    DEFAULT_PROGRESS_MESSAGE, DEFAULT_ETR
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
                if self._background_process.poll() is not None:
                    # Process finished
                    self.finish(context)
                    return {'FINISHED'}
                
                # Read Status
                if self._status_file and os.path.exists(self._status_file):
                    try:
                        with open(self._status_file, 'r') as f:
                            status = json.load(f)
                            context.window_manager.rendercue.progress_message = status.get(STATUS_MESSAGE, DEFAULT_PROGRESS_MESSAGE)
                            context.window_manager.rendercue.etr = status.get(STATUS_ETR, DEFAULT_ETR)
                            context.window_manager.rendercue.current_job_index = status.get(STATUS_JOB_INDEX, 0)
                            context.window_manager.rendercue.finished_frames_count = status.get(STATUS_FINISHED_FRAMES, 0)
                            context.window_manager.rendercue.total_frames_to_render = status.get(STATUS_TOTAL_FRAMES, 0)
                            
                            # Handle preview updates
                            last_frame = status.get(STATUS_LAST_FRAME, "")
                            context.window_manager.rendercue.last_rendered_frame = last_frame
                            
                            if last_frame:
                                self.update_preview(context, last_frame)
                            
                            # Check for errors
                            if status.get(STATUS_ERROR):
                                self.report({'ERROR'}, f"Render Error: {status[STATUS_ERROR]}")
                                context.window_manager.rendercue.last_render_status = 'FAILED'
                                context.window_manager.rendercue.last_render_message = f"Error: {status[STATUS_ERROR]}"
                                
                                # Send error webhook
                                prefs = context.preferences.addons[__package__].preferences
                                if prefs.webhook_url:
                                    filename = os.path.basename(bpy.data.filepath) or "Untitled.blend"
                                    error_msg = f"**Project:** {filename}\n**Error:** {status[STATUS_ERROR]}"
                                    send_webhook(prefs.webhook_url, error_msg, title="❌ Render Failed", color=0xff0000)
                                
                                # Send desktop notification
                                if prefs.show_notifications:
                                    show_notification("RenderCue Error", status[STATUS_ERROR])
                                
                                self._stop = True
                    except (OSError, json.JSONDecodeError):
                        pass
                return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        """Initialize and start the background render process."""
        wm = context.window_manager
        if not context.window_manager.rendercue.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}
            
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Save the file before background rendering")
            return {'CANCELLED'}
            
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
        context.window_manager.rendercue.progress_message = "Starting Background Render..."
        
        # Track start time
        self._start_time = time.time()
        
        wm.modal_handler_add(self)
        self._timer = wm.event_timer_add(1.0, window=context.window)
        return {'RUNNING_MODAL'}

    def finish(self, context):
        """Clean up after rendering finishes (success or failure)."""
        wm = context.window_manager
        
        # Clean up progress bar
        wm.progress_end()
        
        # Remove timer
        if self._timer:
            wm.event_timer_remove(self._timer)
            
        self.report({'INFO'}, "Batch Render Complete")
        
        # Reset UI State
        context.window_manager.rendercue.is_rendering = False
        context.window_manager.rendercue.progress_message = "Done"
        context.window_manager.rendercue.etr = DEFAULT_ETR
        
        # Webhook Notification
        prefs = context.preferences.addons[__package__].preferences
        if prefs.webhook_url:
            # Build informative message
            filename = os.path.basename(bpy.data.filepath) or "Untitled.blend"
            total_jobs = context.window_manager.rendercue.total_jobs_count
            frames = context.window_manager.rendercue.finished_frames_count
            
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
            
            message = f"**Project:** {filename}\n**Jobs:** {total_jobs}\n**Frames:** {frames}\n**Duration:** {time_str}"
            send_webhook(prefs.webhook_url, message, title="✅ Render Complete", color=0x00ff00)

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
        if not img:
            try:
                img = bpy.data.images.load(filepath)
                img.name = image_name
            except RuntimeError:
                return
        else:
            if img.filepath != filepath:
                img.filepath = filepath
            img.reload()
        
        # Force update
        img.update()
        settings.preview_image = img
        
        # Update UI Preview Collection
        try:
            from . import ui
            if "main" in ui.preview_collections:
                pcoll = ui.preview_collections["main"]
                pcoll.clear()
                pcoll.load("thumbnail", filepath, 'IMAGE')
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
