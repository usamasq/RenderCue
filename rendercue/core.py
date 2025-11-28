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
    JOB_RENDER_ENGINE, JOB_OVERRIDE_VIEW_LAYER, JOB_VIEW_LAYER
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
                JOB_VIEW_LAYER: job.view_layer
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
                JOB_VIEW_LAYER: job.view_layer
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

def register():
    # Don't register handlers by default
    pass

def unregister():
    StateManager.unregister_handlers()
