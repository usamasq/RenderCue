import bpy
import os
import json
import logging
import time
from .constants import (
    MANIFEST_JOBS, MANIFEST_GLOBAL_OUTPUT, MANIFEST_OUTPUT_LOCATION,
    JOB_SCENE_NAME, JOB_FRAME_START, JOB_FRAME_END, JOB_OVERRIDE_FRAME_RANGE,
    JOB_OVERRIDE_OUTPUT, JOB_OUTPUT_PATH, JOB_OVERRIDE_RESOLUTION,
    JOB_RESOLUTION_SCALE, JOB_OVERRIDE_SAMPLES, JOB_SAMPLES,
    JOB_OVERRIDE_FORMAT, JOB_RENDER_FORMAT, JOB_OVERRIDE_ENGINE,
    JOB_RENDER_ENGINE, JOB_OVERRIDE_VIEW_LAYER, JOB_VIEW_LAYER,
    JOB_OVERRIDE_CAMERA, JOB_CAMERA, JOB_OVERRIDE_FRAME_STEP, JOB_FRAME_STEP,
    JOB_OVERRIDE_TRANSPARENT, JOB_FILM_TRANSPARENT,
    JOB_OVERRIDE_COMPOSITOR, JOB_USE_COMPOSITOR,
    JOB_OVERRIDE_DENOISING, JOB_USE_DENOISING,
    JOB_OVERRIDE_DEVICE, JOB_DEVICE,
    JOB_OVERRIDE_TIME_LIMIT, JOB_TIME_LIMIT,
    JOB_OVERRIDE_PERSISTENT_DATA, JOB_USE_PERSISTENT_DATA,
    STATUS_MESSAGE, STATUS_ETR, STATUS_FINISHED, STATUS_ERROR,
    STATUS_JOB_INDEX, STATUS_TOTAL_JOBS, STATUS_TIMESTAMP,
    STATUS_FINISHED_FRAMES, STATUS_TOTAL_FRAMES, STATUS_LAST_FRAME,
    STATUS_JOB_STATUSES, STATUS_JOB_PROGRESS, STATUS_JOB_TIMINGS,
    DEFAULT_ETR, PAUSE_SIGNAL_FILENAME, PREVIEW_FILENAME_PREFIX,
    DEBUG_LOG_FILENAME, STATUS_PAUSED_DURATION
)

class RenderCueLogger:
    _logger = None

    @staticmethod
    def get_logger(output_dir):
        if RenderCueLogger._logger:
            return RenderCueLogger._logger
            
        log_file = os.path.join(output_dir, "rendercue.log")
        
        logger = logging.getLogger("RenderCue")
        logger.setLevel(logging.DEBUG)
        
        # File Handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        RenderCueLogger._logger = logger
        return logger

class StateManager:
    """Manages the saving and loading of the RenderCue queue state."""
    
    @staticmethod
    def save_state(context, filepath):
        """Save the current render queue state to an external JSON file.

        Args:
            context (bpy.types.Context): Blender context.
            filepath (str): Path to save the JSON file.
        """
        settings = context.window_manager.rendercue
        data = {
            "timestamp": time.time(),
            MANIFEST_GLOBAL_OUTPUT: settings.global_output_path,
            MANIFEST_OUTPUT_LOCATION: settings.output_location,
            MANIFEST_JOBS: []
        }
        
        for job in settings.jobs:
            job_data = {
                JOB_SCENE_NAME: job.scene.name if job.scene else None,
                
                JOB_OVERRIDE_FRAME_RANGE: job.override_frame_range,
                JOB_FRAME_START: job.frame_start,
                JOB_FRAME_END: job.frame_end,
                
                JOB_OVERRIDE_OUTPUT: job.override_output,
                JOB_OUTPUT_PATH: job.output_path,
                
                JOB_OVERRIDE_RESOLUTION: job.override_resolution,
                JOB_RESOLUTION_SCALE: job.resolution_scale,
                
                JOB_OVERRIDE_SAMPLES: job.override_samples,
                JOB_SAMPLES: job.samples,
                
                JOB_OVERRIDE_FORMAT: job.override_format,
                JOB_RENDER_FORMAT: job.render_format,
                
                JOB_OVERRIDE_ENGINE: job.override_engine,
                JOB_RENDER_ENGINE: job.render_engine,
                
                JOB_OVERRIDE_VIEW_LAYER: job.override_view_layer,
                JOB_VIEW_LAYER: job.view_layer,
                
                # New Overrides
                JOB_OVERRIDE_CAMERA: job.override_camera,
                JOB_CAMERA: job.camera.name if job.camera else None,
                JOB_OVERRIDE_FRAME_STEP: job.override_frame_step,
                JOB_FRAME_STEP: job.frame_step,
                JOB_OVERRIDE_TRANSPARENT: job.override_transparent,
                JOB_FILM_TRANSPARENT: job.film_transparent,
                JOB_OVERRIDE_COMPOSITOR: job.override_compositor,
                JOB_USE_COMPOSITOR: job.use_compositor,
                JOB_OVERRIDE_DENOISING: job.override_denoising,
                JOB_USE_DENOISING: job.use_denoising,
                JOB_OVERRIDE_DEVICE: job.override_device,
                JOB_DEVICE: job.device,
                JOB_OVERRIDE_TIME_LIMIT: job.override_time_limit,
                JOB_TIME_LIMIT: job.time_limit,
                JOB_OVERRIDE_PERSISTENT_DATA: job.override_persistent_data,
                JOB_USE_PERSISTENT_DATA: job.use_persistent_data
            }
            data[MANIFEST_JOBS].append(job_data)
            
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except OSError as e:
            print(f"Error saving state to {filepath}: {e}")
            
    @staticmethod
    def load_state(context, filepath):
        """Load render queue state from an external JSON file.

        Args:
            context (bpy.types.Context): Blender context.
            filepath (str): Path to the JSON file.

        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        if not os.path.exists(filepath):
            return False
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            settings = context.window_manager.rendercue
            settings.jobs.clear()
            
            settings.global_output_path = data.get(MANIFEST_GLOBAL_OUTPUT, settings.global_output_path)
            settings.output_location = data.get(MANIFEST_OUTPUT_LOCATION, 'BLEND')
            
            for job_data in data.get(MANIFEST_JOBS, []):
                job = settings.jobs.add()
                
                if job_data.get(JOB_SCENE_NAME):
                    job.scene = bpy.data.scenes.get(job_data[JOB_SCENE_NAME])
                    
                job.override_frame_range = job_data.get(JOB_OVERRIDE_FRAME_RANGE, False)
                job.frame_start = job_data.get(JOB_FRAME_START, 1)
                job.frame_end = job_data.get(JOB_FRAME_END, 250)
                
                # Enforce frame_end >= frame_start (bypassed by direct setattr)
                if job.frame_end < job.frame_start:
                    job.frame_end = job.frame_start
                
                job.override_output = job_data.get(JOB_OVERRIDE_OUTPUT, False)
                job.output_path = job_data.get(JOB_OUTPUT_PATH, "//")
                
                job.override_resolution = job_data.get(JOB_OVERRIDE_RESOLUTION, False)
                job.resolution_scale = job_data.get(JOB_RESOLUTION_SCALE, 100)
                
                job.override_samples = job_data.get(JOB_OVERRIDE_SAMPLES, False)
                job.samples = job_data.get(JOB_SAMPLES, 128)
                
                job.override_format = job_data.get(JOB_OVERRIDE_FORMAT, False)
                job.render_format = job_data.get(JOB_RENDER_FORMAT, 'PNG')
                
                job.override_engine = job_data.get(JOB_OVERRIDE_ENGINE, False)
                job.render_engine = job_data.get(JOB_RENDER_ENGINE, 'CYCLES')
                
                job.override_view_layer = job_data.get(JOB_OVERRIDE_VIEW_LAYER, False)
                job.view_layer = job_data.get(JOB_VIEW_LAYER, "")
                
                # New Overrides
                job.override_camera = job_data.get(JOB_OVERRIDE_CAMERA, False)
                camera_name = job_data.get(JOB_CAMERA)
                if camera_name and camera_name in bpy.data.objects:
                    job.camera = bpy.data.objects[camera_name]
                    
                job.override_frame_step = job_data.get(JOB_OVERRIDE_FRAME_STEP, False)
                job.frame_step = job_data.get(JOB_FRAME_STEP, 1)
                
                job.override_transparent = job_data.get(JOB_OVERRIDE_TRANSPARENT, False)
                job.film_transparent = job_data.get(JOB_FILM_TRANSPARENT, False)
                
                job.override_compositor = job_data.get(JOB_OVERRIDE_COMPOSITOR, False)
                job.use_compositor = job_data.get(JOB_USE_COMPOSITOR, True)
                
                job.override_denoising = job_data.get(JOB_OVERRIDE_DENOISING, False)
                job.use_denoising = job_data.get(JOB_USE_DENOISING, True)
                
                job.override_device = job_data.get(JOB_OVERRIDE_DEVICE, False)
                job.device = job_data.get(JOB_DEVICE, 'GPU')
                
                job.override_time_limit = job_data.get(JOB_OVERRIDE_TIME_LIMIT, False)
                job.time_limit = job_data.get(JOB_TIME_LIMIT, 0.0)
                
                job.override_persistent_data = job_data.get(JOB_OVERRIDE_PERSISTENT_DATA, False)
                job.use_persistent_data = job_data.get(JOB_USE_PERSISTENT_DATA, False)
                
            return True
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error loading state: {e}")
            return False

    @staticmethod
    def save_queue_to_text(context):
        """Save the current queue to an internal Blender Text Block.
        
        This allows the queue to be saved within the .blend file itself.

        Args:
            context (bpy.types.Context): Blender context.
        """
        settings = context.window_manager.rendercue
        data = {
            MANIFEST_GLOBAL_OUTPUT: settings.global_output_path,
            MANIFEST_OUTPUT_LOCATION: settings.output_location,
            MANIFEST_JOBS: []
        }
        
        for job in settings.jobs:
            job_data = {
                JOB_SCENE_NAME: job.scene.name if job.scene else None,
                JOB_OVERRIDE_FRAME_RANGE: job.override_frame_range,
                JOB_FRAME_START: job.frame_start,
                JOB_FRAME_END: job.frame_end,
                JOB_OVERRIDE_OUTPUT: job.override_output,
                JOB_OUTPUT_PATH: job.output_path,
                JOB_OVERRIDE_RESOLUTION: job.override_resolution,
                JOB_RESOLUTION_SCALE: job.resolution_scale,
                JOB_OVERRIDE_SAMPLES: job.override_samples,
                JOB_SAMPLES: job.samples,
                JOB_OVERRIDE_FORMAT: job.override_format,
                JOB_RENDER_FORMAT: job.render_format,
                JOB_OVERRIDE_ENGINE: job.override_engine,
                JOB_RENDER_ENGINE: job.render_engine,
                JOB_OVERRIDE_VIEW_LAYER: job.override_view_layer,
                JOB_VIEW_LAYER: job.view_layer,
                
                # New Overrides
                JOB_OVERRIDE_CAMERA: job.override_camera,
                JOB_CAMERA: job.camera.name if job.camera else None,
                JOB_OVERRIDE_FRAME_STEP: job.override_frame_step,
                JOB_FRAME_STEP: job.frame_step,
                JOB_OVERRIDE_TRANSPARENT: job.override_transparent,
                JOB_FILM_TRANSPARENT: job.film_transparent,
                JOB_OVERRIDE_COMPOSITOR: job.override_compositor,
                JOB_USE_COMPOSITOR: job.use_compositor,
                JOB_OVERRIDE_DENOISING: job.override_denoising,
                JOB_USE_DENOISING: job.use_denoising,
                JOB_OVERRIDE_DEVICE: job.override_device,
                JOB_DEVICE: job.device,
                JOB_OVERRIDE_TIME_LIMIT: job.override_time_limit,
                JOB_TIME_LIMIT: job.time_limit,
                JOB_OVERRIDE_PERSISTENT_DATA: job.override_persistent_data,
                JOB_USE_PERSISTENT_DATA: job.use_persistent_data
            }
            data[MANIFEST_JOBS].append(job_data)
            
        text_name = ".rendercue_data"
        text = bpy.data.texts.get(text_name)
        if not text:
            text = bpy.data.texts.new(text_name)
            
        text.clear()
        text.write(json.dumps(data, indent=4))

    @staticmethod
    def load_queue_from_text(context):
        """Load the queue from an internal Blender Text Block.

        Args:
            context (bpy.types.Context): Blender context.
        """
        text_name = ".rendercue_data"
        text = bpy.data.texts.get(text_name)
        if not text:
            return
            
        try:
            data = json.loads(text.as_string())
            settings = context.window_manager.rendercue
            settings.jobs.clear()
            
            settings.global_output_path = data.get(MANIFEST_GLOBAL_OUTPUT, settings.global_output_path)
            settings.output_location = data.get(MANIFEST_OUTPUT_LOCATION, 'BLEND')
            
            for job_data in data.get(MANIFEST_JOBS, []):
                job = settings.jobs.add()
                if job_data.get(JOB_SCENE_NAME):
                    job.scene = bpy.data.scenes.get(job_data[JOB_SCENE_NAME])
                    
                job.override_frame_range = job_data.get(JOB_OVERRIDE_FRAME_RANGE, False)
                job.frame_start = job_data.get(JOB_FRAME_START, 1)
                job.frame_end = job_data.get(JOB_FRAME_END, 250)

                # Enforce frame_end >= frame_start
                if job.frame_end < job.frame_start:
                    job.frame_end = job.frame_start
                job.override_output = job_data.get(JOB_OVERRIDE_OUTPUT, False)
                job.output_path = job_data.get(JOB_OUTPUT_PATH, "//")
                job.override_resolution = job_data.get(JOB_OVERRIDE_RESOLUTION, False)
                job.resolution_scale = job_data.get(JOB_RESOLUTION_SCALE, 100)
                job.override_samples = job_data.get(JOB_OVERRIDE_SAMPLES, False)
                job.samples = job_data.get(JOB_SAMPLES, 128)
                job.override_format = job_data.get(JOB_OVERRIDE_FORMAT, False)
                job.render_format = job_data.get(JOB_RENDER_FORMAT, 'PNG')
                job.override_engine = job_data.get(JOB_OVERRIDE_ENGINE, False)
                job.render_engine = job_data.get(JOB_RENDER_ENGINE, 'CYCLES')
                job.override_view_layer = job_data.get(JOB_OVERRIDE_VIEW_LAYER, False)
                job.view_layer = job_data.get(JOB_VIEW_LAYER, "")
                
                # New Overrides
                job.override_camera = job_data.get(JOB_OVERRIDE_CAMERA, False)
                camera_name = job_data.get(JOB_CAMERA)
                if camera_name and camera_name in bpy.data.objects:
                    job.camera = bpy.data.objects[camera_name]
                    
                job.override_frame_step = job_data.get(JOB_OVERRIDE_FRAME_STEP, False)
                job.frame_step = job_data.get(JOB_FRAME_STEP, 1)
                
                job.override_transparent = job_data.get(JOB_OVERRIDE_TRANSPARENT, False)
                job.film_transparent = job_data.get(JOB_FILM_TRANSPARENT, False)
                
                job.override_compositor = job_data.get(JOB_OVERRIDE_COMPOSITOR, False)
                job.use_compositor = job_data.get(JOB_USE_COMPOSITOR, True)
                
                job.override_denoising = job_data.get(JOB_OVERRIDE_DENOISING, False)
                job.use_denoising = job_data.get(JOB_USE_DENOISING, True)
                
                job.override_device = job_data.get(JOB_OVERRIDE_DEVICE, False)
                job.device = job_data.get(JOB_DEVICE, 'GPU')
                
                job.override_time_limit = job_data.get(JOB_OVERRIDE_TIME_LIMIT, False)
                job.time_limit = job_data.get(JOB_TIME_LIMIT, 0.0)
                
                job.override_persistent_data = job_data.get(JOB_OVERRIDE_PERSISTENT_DATA, False)
                job.use_persistent_data = job_data.get(JOB_USE_PERSISTENT_DATA, False)
        except json.JSONDecodeError as e:
            print(f"Error loading queue from text: {e}")

    @staticmethod
    def register_handlers():
        """Register auto-save/load handlers."""
        if not _save_pre_handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.append(_save_pre_handler)
        if not _load_post_handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(_load_post_handler)

    @staticmethod
    def unregister_handlers():
        """Unregister auto-save/load handlers."""
        if _save_pre_handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.remove(_save_pre_handler)
        if _load_post_handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(_load_post_handler)

from bpy.app.handlers import persistent

@persistent
def _save_pre_handler(dummy):
    """Handler called before saving the blend file."""
    # Only save if there are jobs
    if bpy.context.window_manager.rendercue.jobs:
        StateManager.save_queue_to_text(bpy.context)

@persistent
def _load_post_handler(dummy):
    """Handler called after loading a blend file."""
    # Use a timer to delay loading slightly to ensure context is ready
    bpy.app.timers.register(lambda: StateManager.load_queue_from_text(bpy.context) or None, first_interval=0.1)


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
        self.total_paused_duration = 0
        
        # Job Status Tracking
        self.job_statuses = []
        self.job_progress = []
        self.job_timings = []
        
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
            
            # Initialize tracking lists
            self.job_statuses = ['PENDING'] * self.total_jobs
            self.job_progress = [{'done': 0, 'total': 0} for _ in range(self.total_jobs)]
            self.job_timings = [{'start': 0.0, 'end': 0.0} for _ in range(self.total_jobs)]
            
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
            STATUS_LAST_FRAME: self.last_preview_path,
            STATUS_PAUSED_DURATION: self.total_paused_duration,
            STATUS_JOB_STATUSES: self.job_statuses,
            STATUS_JOB_PROGRESS: self.job_progress,
            STATUS_JOB_TIMINGS: self.job_timings
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
                
                # Determine step
                step = scene.frame_step
                if job.get(JOB_OVERRIDE_FRAME_STEP):
                    step = job.get(JOB_FRAME_STEP, 1)
                
                # Calculate frame count
                if start > end:
                    job_frames = 0
                else:
                    job_frames = (end - start) // step + 1
                
                self.total_frames_to_render += job_frames
                
                # Update total frames for this job in tracking
                idx = self.jobs.index(job)
                if idx < len(self.job_progress):
                    self.job_progress[idx]['total'] = job_frames

    def on_render_post(self, scene, depsgraph=None):
        """Handler called after each frame render to update progress and save preview.

        Args:
            scene (bpy.types.Scene): The scene that was rendered.
            depsgraph (bpy.types.Depsgraph, optional): Dependency graph.
        """

        self.finished_frames_count += 1
        
        # Update job progress
        if self.current_job_index < len(self.job_progress):
            self.job_progress[self.current_job_index]['done'] += 1
        
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
        # We save a separate JPEG for the preview
        # Use a fixed filename so Blender can reload it reliably
        preview_path = os.path.join(os.path.dirname(self.status_path), f"{PREVIEW_FILENAME_PREFIX}latest.jpg")
        
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
                
                # Save to temp file first, then atomic rename
                temp_preview_path = preview_path + ".tmp"
                bpy.data.images['Render Result'].save_render(filepath=temp_preview_path)
                
                try:
                    os.replace(temp_preview_path, preview_path)
                    log_debug(f"Saved preview to {preview_path}")
                except OSError as e:
                    log_debug(f"Atomic rename failed: {e}")
                    # Fallback
                    if os.path.exists(temp_preview_path):
                        os.remove(temp_preview_path)
                
                # Restore
                scene.render.image_settings.file_format = orig_format
            else:
                log_debug("Render Result image not found")
                preview_path = ""
        except Exception as e:
            log_debug(f"Could not save preview: {e}")
            print(f"Could not save preview: {e}")
            preview_path = ""

        msg = f"Rendering {self.current_job_index + 1}/{self.total_jobs}: {scene.name} (Frame {scene.frame_current})"

        self.log_status(msg, etr=etr, last_frame=preview_path)


    def run(self):
        """Main execution loop for the background worker."""
        if not self.load_manifest():
            return

        # Initialize Logger
        logger = RenderCueLogger.get_logger(os.path.dirname(self.status_path))
        logger.info(f"Starting Background Render: {self.total_jobs} jobs")
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
            
            # Update Job Status
            self.job_statuses[i] = 'RENDERING'
            self.job_timings[i]['start'] = time.time()
            self.log_status(f"Starting Job {i+1}: {scene_name}", etr="Calculating...")
            
            # Apply Overrides
            frame_start = scene.frame_start
            frame_end = scene.frame_end
            
            if job[JOB_OVERRIDE_FRAME_RANGE]:
                frame_start = job[JOB_FRAME_START]
                frame_end = job[JOB_FRAME_END]
                
            # Output Path Logic
            if job[JOB_OVERRIDE_OUTPUT] and job.get(JOB_OUTPUT_PATH):
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
                target_engine = job[JOB_RENDER_ENGINE]
                try:
                    current_engine = scene.render.engine
                    scene.render.engine = target_engine
                except (AttributeError, TypeError) as e:
                    error_msg = f"Error: Cannot set render engine to '{target_engine}': {e}. Using scene default '{current_engine}'"
                    print(error_msg)
                    self.log_status(error_msg, error=str(e))
            
            # Camera Override (Universal)
            if job.get(JOB_OVERRIDE_CAMERA, False):
                camera_name = job.get(JOB_CAMERA)
                if camera_name and camera_name in bpy.data.objects:
                    camera_obj = bpy.data.objects[camera_name]
                    if camera_obj and camera_obj.type == 'CAMERA':
                        scene.camera = camera_obj
                    else:
                        print(f"Warning: Overridden camera '{camera_name}' is invalid or not a camera.")
                else:
                    print(f"Warning: Overridden camera '{camera_name}' not found.")
            
            # Frame Step (Universal)
            if job.get(JOB_OVERRIDE_FRAME_STEP, False):
                frame_step = job.get(JOB_FRAME_STEP, 1)
            else:
                frame_step = scene.frame_step
            
            # Transparent Background (Universal)
            if job.get(JOB_OVERRIDE_TRANSPARENT, False):
                scene.render.film_transparent = job[JOB_FILM_TRANSPARENT]
            
            # Compositor (Universal)
            if job.get(JOB_OVERRIDE_COMPOSITOR, False):
                scene.render.use_compositing = job[JOB_USE_COMPOSITOR]
                
            if job.get(JOB_OVERRIDE_VIEW_LAYER):
                vl_name = job[JOB_VIEW_LAYER]
                if vl_name and vl_name in scene.view_layers:
                    for vl in scene.view_layers:
                        vl.use = (vl.name == vl_name)
                elif vl_name:
                     available_layers = [vl.name for vl in scene.view_layers]
                     error_msg = f"Warning: View layer '{vl_name}' not found in scene '{scene.name}'. Available layers: {', '.join(available_layers)}"
                     print(error_msg)

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
            
            # Cycles-Only Overrides
            if scene.render.engine == 'CYCLES':
                # Denoising (Risk #7: API Compatibility)
                if job.get(JOB_OVERRIDE_DENOISING, False):
                    try:
                        # Blender 3.0+
                        scene.cycles.use_denoising = job[JOB_USE_DENOISING]
                    except AttributeError:
                        try:
                            # Older versions might use different property or location
                            # For now, we log if it fails but don't crash
                            pass
                        except Exception as e:
                            print(f"Failed to set denoising: {e}")
                
                # Device (Risk #8: API Complexity)
                if job.get(JOB_OVERRIDE_DEVICE, False):
                    target_device = job[JOB_DEVICE] # 'CPU' or 'GPU'
                    scene.cycles.device = target_device
                    
                    # If GPU is selected, we might need to ensure preferences are set correctly
                    # But changing system preferences from a background job is risky/complex.
                    # Setting scene.cycles.device is usually enough for the scene to *request* it.
                    # However, if no GPU is configured in preferences, it might fall back to CPU.
                    # We'll stick to setting the scene property as it's the safest per-job override.
                
                # Time Limit
                if job.get(JOB_OVERRIDE_TIME_LIMIT, False):
                    try:
                        scene.cycles.time_limit = job[JOB_TIME_LIMIT]
                    except AttributeError:
                        pass
                
                # Persistent Data
                if job.get(JOB_OVERRIDE_PERSISTENT_DATA, False):
                    try:
                        scene.render.use_persistent_data = job[JOB_USE_PERSISTENT_DATA]
                    except AttributeError:
                        pass

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
                    self.job_statuses[i] = 'FAILED'
                
                current_frame += frame_step

            # Job Finished
            self.job_statuses[i] = 'COMPLETED'
            self.job_timings[i]['end'] = time.time()

        self.log_status("All Jobs Completed", finished=True)
        print("Background Render Complete")

    def check_pause(self):
        """Check for pause signal file and block execution if found."""
        try:
            pause_file = os.path.join(os.path.dirname(self.status_path), PAUSE_SIGNAL_FILENAME)
            if os.path.exists(pause_file):
                self.log_status("Paused", etr="Paused")
                print("Render Paused...")
                
                pause_start = time.time()
                while os.path.exists(pause_file):
                    time.sleep(1)
                
                pause_duration = time.time() - pause_start
                self.total_paused_duration += pause_duration
                
                print(f"Render Resumed (Paused for {pause_duration:.1f}s)")
                self.log_status("Resuming...", etr="Calculating...")
        except OSError as e:
            print(f"Pause Check Error: {e}")

def register():
    # Don't register handlers by default
    pass

def unregister():
    StateManager.unregister_handlers()
