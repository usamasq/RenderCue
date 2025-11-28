import bpy
import sys
import json
import os
import time
import argparse

# Import constants
# Since worker.py runs as a script, we need to handle imports carefully
# But since it's in the same package, we can try relative import if run as module,
# or add path if run as script.
# However, when run via -P, it's run as __main__.
# We might need to duplicate constants or adjust path.
# For now, let's assume we can import from .constants if we are in the package structure.
# But -P runs it as a standalone script.
# We should probably copy the constants or make sure the package is in path.
# A robust way for the worker script (which is run by Blender) is to add the current directory to sys.path.

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from constants import *
except ImportError:
    # Fallback or try relative import if it fails (though sys.path should fix it)
    try:
        from .constants import *
    except ImportError:
        print("Could not import constants")
        # Define critical constants to avoid crash if import fails completely
        STATUS_MESSAGE = "message"
        STATUS_ETR = "etr"
        STATUS_FINISHED = "finished"
        STATUS_ERROR = "error"
        STATUS_JOB_INDEX = "job_index"
        STATUS_TOTAL_JOBS = "total_jobs"
        STATUS_TIMESTAMP = "timestamp"
        STATUS_FINISHED_FRAMES = "finished_frames"
        STATUS_TOTAL_FRAMES = "total_frames"
        STATUS_LAST_FRAME = "last_frame"
        MANIFEST_JOBS = "jobs"
        MANIFEST_GLOBAL_OUTPUT = "global_output_path"
        MANIFEST_OUTPUT_LOCATION = "output_location"
        JOB_SCENE_NAME = "scene_name"
        JOB_FRAME_START = "frame_start"
        JOB_FRAME_END = "frame_end"
        JOB_OVERRIDE_FRAME_RANGE = "override_frame_range"
        JOB_OVERRIDE_OUTPUT = "override_output"
        JOB_OUTPUT_PATH = "output_path"
        JOB_OVERRIDE_ENGINE = "override_engine"
        JOB_RENDER_ENGINE = "render_engine"
        JOB_OVERRIDE_VIEW_LAYER = "override_view_layer"
        JOB_VIEW_LAYER = "view_layer"
        JOB_OVERRIDE_RESOLUTION = "override_resolution"
        JOB_RESOLUTION_SCALE = "resolution_scale"
        JOB_OVERRIDE_FORMAT = "override_format"
        JOB_RENDER_FORMAT = "render_format"
        JOB_OVERRIDE_SAMPLES = "override_samples"
        JOB_SAMPLES = "samples"
        PAUSE_SIGNAL_FILENAME = "rendercue_pause.signal"
        PREVIEW_FILENAME_PREFIX = ".rendercue_preview_"
        DEBUG_LOG_FILENAME = "worker_debug.log"
        DEFAULT_ETR = "--:--"


class BackgroundWorker:
    """Handles background rendering processes independent of the main Blender UI thread.
    
    This class manages the render queue execution, progress tracking, and status reporting
    to the main Blender instance via status files.
    """
    
    def __init__(self, manifest_path, status_path):
        """Initialize the background worker.

        Args:
            manifest_path (str): Path to the JSON manifest file containing job details.
            status_path (str): Path where the worker should write status updates.
        """
        self.manifest_path = manifest_path
        self.status_path = status_path
        self.manifest = {}
        self.jobs = []
        self.total_jobs = 0
        self.current_job_index = 0
        
        # Progress Tracking
        self.start_time = 0
        self.total_frames_to_render = 0
        self.finished_frames_count = 0
        self.last_preview_path = ""
        
    def load_manifest(self):
        """Load the render job manifest from disk.

        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        try:
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
            self.jobs = self.manifest.get(MANIFEST_JOBS, [])
            self.total_jobs = len(self.jobs)
            return True
        except (OSError, json.JSONDecodeError) as e:
            print(f"Failed to load manifest: {e}")
            return False

    def log_status(self, message, etr=DEFAULT_ETR, finished=False, error=None, **kwargs):
        """Write current status to the status JSON file.

        Args:
            message (str): Status message to display in UI.
            etr (str): Estimated time remaining string.
            finished (bool): Whether the entire batch is complete.
            error (str, optional): Error message if an error occurred.
            **kwargs: Additional status fields (e.g., last_frame).
        """
        # Update last preview path if provided
        if STATUS_LAST_FRAME in kwargs:
            self.last_preview_path = kwargs[STATUS_LAST_FRAME]
            
        data = {
            STATUS_JOB_INDEX: self.current_job_index + 1, # 1-based for UI
            STATUS_TOTAL_JOBS: self.total_jobs,
            STATUS_MESSAGE: message,
            STATUS_ETR: etr,
            STATUS_FINISHED: finished,
            STATUS_ERROR: error,
            STATUS_TIMESTAMP: time.time(),
            STATUS_FINISHED_FRAMES: self.finished_frames_count,
            STATUS_TOTAL_FRAMES: self.total_frames_to_render,
            STATUS_LAST_FRAME: self.last_preview_path
        }
        try:
            with open(self.status_path, 'w') as f:
                json.dump(data, f)
        except OSError as e:
            print(f"Failed to write status: {e}")

    def calculate_total_frames(self):
        """Calculate total frames to be rendered across all jobs."""
        self.total_frames_to_render = 0
        for job in self.jobs:
            # Note: This assumes scene data is available or passed in manifest.
            # Since we only have scene names in manifest, we rely on the blend file.
            scene_name = job.get(JOB_SCENE_NAME)
            if scene_name and scene_name in bpy.data.scenes:
                scene = bpy.data.scenes[scene_name]
                start = job.get(JOB_FRAME_START, scene.frame_start)
                end = job.get(JOB_FRAME_END, scene.frame_end)
                if job.get(JOB_OVERRIDE_FRAME_RANGE):
                    start = job[JOB_FRAME_START]
                    end = job[JOB_FRAME_END]
                self.total_frames_to_render += (end - start + 1)

    def on_render_post(self, scene, depsgraph=None):
        """Handler called after each frame render to update progress and save preview.

        Args:
            scene (bpy.types.Scene): The scene that was rendered.
            depsgraph (bpy.types.Depsgraph, optional): Dependency graph.
        """
        self.finished_frames_count += 1
        
        # Calculate ETR
        elapsed = time.time() - self.start_time
        etr = DEFAULT_ETR
        
        if self.finished_frames_count > 0 and self.total_frames_to_render > 0:
            avg_time_per_frame = elapsed / self.finished_frames_count
            remaining_frames = self.total_frames_to_render - self.finished_frames_count
            remaining_seconds = avg_time_per_frame * remaining_frames
            
            if remaining_seconds > 0:
                mins, secs = divmod(int(remaining_seconds), 60)
                hrs, mins = divmod(mins, 60)
                if hrs > 0:
                    etr = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                else:
                    etr = f"{mins:02d}:{secs:02d}"
        
        # Save Preview Image
        # We save a separate JPEG for the preview to support all formats (including Video)
        # Use a unique filename with timestamp to force Blender to reload the image
        timestamp = int(time.time() * 1000)
        preview_path = os.path.join(os.path.dirname(self.status_path), f"{PREVIEW_FILENAME_PREFIX}{timestamp}.jpg")
        
        # Debug Log
        debug_log_path = os.path.join(os.path.dirname(self.status_path), DEBUG_LOG_FILENAME)
        def log_debug(msg):
            try:
                with open(debug_log_path, "a") as f:
                    f.write(f"{time.ctime()}: {msg}\n")
            except OSError:
                pass

        try:
            if 'Render Result' in bpy.data.images:
                # Store original settings
                orig_format = scene.render.image_settings.file_format
                
                # Set to JPEG for preview
                scene.render.image_settings.file_format = 'JPEG'
                
                # Save
                bpy.data.images['Render Result'].save_render(filepath=preview_path)
                log_debug(f"Saved preview to {preview_path}")
                
                # Restore
                scene.render.image_settings.file_format = orig_format
                
                # Clean up old previews to save space
                try:
                    dir_path = os.path.dirname(self.status_path)
                    current_name = os.path.basename(preview_path)
                    for f in os.listdir(dir_path):
                        if f.startswith(PREVIEW_FILENAME_PREFIX) and f.endswith(".jpg") and f != current_name:
                            try:
                                os.remove(os.path.join(dir_path, f))
                            except OSError:
                                pass
                except OSError:
                    pass
            else:
                log_debug("Render Result image not found")
                preview_path = ""
        except Exception as e:
            log_debug(f"Could not save preview: {e}")
            print(f"Could not save preview: {e}")
            preview_path = ""

        msg = f"Rendering {self.current_job_index + 1}/{self.total_jobs}: {scene.name} (Frame {scene.frame_current})"
        self.log_status(msg, etr=etr, last_frame=preview_path)

    def on_render_pre(self, scene, depsgraph=None):
        """Handler called before rendering starts to check for pause signals.

        Args:
            scene (bpy.types.Scene): The scene to be rendered.
            depsgraph (bpy.types.Depsgraph, optional): Dependency graph.
        """
        try:
            # Check for Pause
            pause_file = os.path.join(os.path.dirname(self.status_path), PAUSE_SIGNAL_FILENAME)
            if os.path.exists(pause_file):
                self.log_status("Paused", etr="Paused")
                print("Render Paused...")
                while os.path.exists(pause_file):
                    time.sleep(1)
                print("Render Resumed")
                self.log_status("Resuming...", etr="Calculating...")
        except OSError as e:
            print(f"Pause Handler Error: {e}")
            self.log_status(f"Pause Error: {e}", error=str(e))

    def run(self):
        """Main execution loop for the background worker."""
        if not self.load_manifest():
            return

        print(f"Starting Background Render: {self.total_jobs} jobs")
        
        self.calculate_total_frames()
        self.start_time = time.time()
        
        # Register Handlers (Only render_post for stats, render_pre is handled in loop)
        # Actually, with frame-by-frame, we can just call on_render_post manually or keep it.
        # But we need to be careful about when it's called. 
        # render(write_still=True) triggers handlers.
        bpy.app.handlers.render_post.append(self.on_render_post)
        
        global_output = self.manifest.get(MANIFEST_GLOBAL_OUTPUT, "//")
        output_location = self.manifest.get(MANIFEST_OUTPUT_LOCATION, "BLEND")
        
        # Pre-calculate scene usage for unique folder naming
        scene_usage_count = {}
        
        blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

        for i, job in enumerate(self.jobs):
            self.current_job_index = i
            scene_name = job[JOB_SCENE_NAME]
            
            if scene_name not in bpy.data.scenes:
                self.log_status(f"Scene {scene_name} not found", error=True)
                continue
                
            scene = bpy.data.scenes[scene_name]
            bpy.context.window.scene = scene
            
            # Track scene usage for naming
            if scene_name not in scene_usage_count:
                scene_usage_count[scene_name] = 0
            scene_usage_count[scene_name] += 1
            
            # Apply Overrides
            frame_start = scene.frame_start
            frame_end = scene.frame_end
            
            if job[JOB_OVERRIDE_FRAME_RANGE]:
                frame_start = job[JOB_FRAME_START]
                frame_end = job[JOB_FRAME_END]
                
            # Output Path Logic
            if job[JOB_OVERRIDE_OUTPUT]:
                # Job Override takes precedence
                output_dir = job[JOB_OUTPUT_PATH]
            else:
                # Determine Base Path
                if output_location == 'CUSTOM':
                    base_path = global_output
                else:
                    base_path = "//"
                    
                if base_path.startswith("//"):
                    base_path = bpy.path.abspath(base_path)
                    
                # Always Separate Folders
                folder_name = scene_name
                
                # Handle Duplicates
                if scene_usage_count[scene_name] > 1:
                    folder_name = f"{scene_name}_Job{i+1}"
                
                output_dir = os.path.join(base_path, folder_name)

            os.makedirs(output_dir, exist_ok=True)
            
            # Apply Render Settings Overrides
            if job.get(JOB_OVERRIDE_ENGINE):
                scene.render.engine = job[JOB_RENDER_ENGINE]
                
            if job.get(JOB_OVERRIDE_VIEW_LAYER):
                vl_name = job[JOB_VIEW_LAYER]
                if vl_name and vl_name in scene.view_layers:
                    for vl in scene.view_layers:
                        vl.use = (vl.name == vl_name)

            if job[JOB_OVERRIDE_RESOLUTION]:
                scene.render.resolution_percentage = job[JOB_RESOLUTION_SCALE]
                
            if job[JOB_OVERRIDE_FORMAT]:
                scene.render.image_settings.file_format = job[JOB_RENDER_FORMAT]
                
            if job[JOB_OVERRIDE_SAMPLES]:
                if scene.render.engine == 'CYCLES':
                    scene.cycles.samples = job[JOB_SAMPLES]
                elif scene.render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
                    try:
                        scene.eevee.taa_render_samples = job[JOB_SAMPLES]
                    except AttributeError:
                        try:
                            scene.eevee.samples = job[JOB_SAMPLES]
                        except AttributeError:
                            pass

            # Determine File Format Extension (for manual naming if needed)
            
            # Render Loop
            current_frame = frame_start
            while current_frame <= frame_end:
                # Check for Pause
                self.check_pause()
                
                # Set Frame
                scene.frame_set(current_frame)
                
                # Construct Filename
                # Standard naming: SceneName_0001...
                file_name = f"{scene_name}_{current_frame:04d}"
                
                full_path = os.path.join(output_dir, file_name)
                scene.render.filepath = full_path
                
                # Render Frame
                try:
                    self.log_status(f"Rendering {scene_name} (Frame {current_frame})", etr="Calculating...")
                    print(f"Rendering frame {current_frame} to {full_path}")
                    
                    bpy.ops.render.render(write_still=True)
                    
                except Exception as e:
                    msg = f"Error rendering {scene_name} frame {current_frame}: {str(e)}"
                    print(msg)
                    self.log_status(msg, error=str(e))
                
                current_frame += 1

        self.log_status("All Jobs Completed", finished=True)
        print("Background Render Complete")

    def check_pause(self):
        """Check for pause signal file and block execution if found."""
        try:
            pause_file = os.path.join(os.path.dirname(self.status_path), PAUSE_SIGNAL_FILENAME)
            if os.path.exists(pause_file):
                self.log_status("Paused", etr="Paused")
                print("Render Paused...")
                while os.path.exists(pause_file):
                    time.sleep(1)
                print("Render Resumed")
                self.log_status("Resuming...", etr="Calculating...")
        except OSError as e:
            print(f"Pause Check Error: {e}")

def main():
    argv = sys.argv
    if "--" not in argv:
        print("No arguments passed to worker")
        return
    
    args = argv[argv.index("--") + 1:]
    
    try:
        manifest_path = args[args.index("--manifest") + 1]
        status_path = args[args.index("--status") + 1]
    except (ValueError, IndexError):
        print("Missing arguments")
        return
        
    worker = BackgroundWorker(manifest_path, status_path)
    worker.run()

# Execute main function
main()
