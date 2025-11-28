import bpy
import os
import json
import logging
import time

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
    @staticmethod
    def save_state(context, filepath):
        """Save the current render queue state to JSON"""
        settings = context.window_manager.rendercue
        data = {
            "timestamp": time.time(),
            "global_output_path": settings.global_output_path,
            "use_custom_output_path": settings.use_custom_output_path,
            "jobs": []
        }
        
        for job in settings.jobs:
            job_data = {
                "scene_name": job.scene.name if job.scene else None,
                
                "override_frame_range": job.override_frame_range,
                "frame_start": job.frame_start,
                "frame_end": job.frame_end,
                
                "override_output": job.override_output,
                "output_path": job.output_path,
                
                "override_resolution": job.override_resolution,
                "resolution_scale": job.resolution_scale,
                
                "override_samples": job.override_samples,
                "samples": job.samples,
                
                "override_format": job.override_format,
                "render_format": job.render_format,
                
                "override_engine": job.override_engine,
                "render_engine": job.render_engine,
                
                "override_view_layer": job.override_view_layer,
                "view_layer": job.view_layer
            }
            data["jobs"].append(job_data)
            
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            
    @staticmethod
    def load_state(context, filepath):
        """Load render queue state from JSON"""
        if not os.path.exists(filepath):
            return False
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            settings = context.window_manager.rendercue
            settings.jobs.clear()
            
            settings.global_output_path = data.get("global_output_path", settings.global_output_path)
            settings.use_custom_output_path = data.get("use_custom_output_path", False)
            
            for job_data in data.get("jobs", []):
                job = settings.jobs.add()
                
                if job_data.get("scene_name"):
                    job.scene = bpy.data.scenes.get(job_data["scene_name"])
                    
                job.override_frame_range = job_data.get("override_frame_range", False)
                job.frame_start = job_data.get("frame_start", 1)
                job.frame_end = job_data.get("frame_end", 250)
                
                job.override_output = job_data.get("override_output", False)
                job.output_path = job_data.get("output_path", "//")
                
                job.override_resolution = job_data.get("override_resolution", False)
                job.resolution_scale = job_data.get("resolution_scale", 100)
                
                job.override_samples = job_data.get("override_samples", False)
                job.samples = job_data.get("samples", 128)
                
                job.override_format = job_data.get("override_format", False)
                job.render_format = job_data.get("render_format", 'PNG')
                
                job.override_engine = job_data.get("override_engine", False)
                job.render_engine = job_data.get("render_engine", 'CYCLES')
                
                job.override_view_layer = job_data.get("override_view_layer", False)
                job.view_layer = job_data.get("view_layer", "")
                
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False

    @staticmethod
    def save_queue_to_text(context):
        """Save queue to internal Text Block"""
        settings = context.window_manager.rendercue
        data = {
            "global_output_path": settings.global_output_path,
            "use_custom_output_path": settings.use_custom_output_path,
            "jobs": []
        }
        
        for job in settings.jobs:
            job_data = {
                "scene_name": job.scene.name if job.scene else None,
                "override_frame_range": job.override_frame_range,
                "frame_start": job.frame_start,
                "frame_end": job.frame_end,
                "override_output": job.override_output,
                "output_path": job.output_path,
                "override_resolution": job.override_resolution,
                "resolution_scale": job.resolution_scale,
                "override_samples": job.override_samples,
                "samples": job.samples,
                "override_format": job.override_format,
                "render_format": job.render_format,
                "override_engine": job.override_engine,
                "render_engine": job.render_engine,
                "override_view_layer": job.override_view_layer,
                "view_layer": job.view_layer
            }
            data["jobs"].append(job_data)
            
        text_name = ".rendercue_data"
        text = bpy.data.texts.get(text_name)
        if not text:
            text = bpy.data.texts.new(text_name)
            
        text.clear()
        text.write(json.dumps(data, indent=4))

    @staticmethod
    def load_queue_from_text(context):
        """Load queue from internal Text Block"""
        text_name = ".rendercue_data"
        text = bpy.data.texts.get(text_name)
        if not text:
            return
            
        try:
            data = json.loads(text.as_string())
            settings = context.window_manager.rendercue
            settings.jobs.clear()
            
            settings.global_output_path = data.get("global_output_path", settings.global_output_path)
            settings.use_custom_output_path = data.get("use_custom_output_path", False)
            
            for job_data in data.get("jobs", []):
                job = settings.jobs.add()
                if job_data.get("scene_name"):
                    job.scene = bpy.data.scenes.get(job_data["scene_name"])
                    
                job.override_frame_range = job_data.get("override_frame_range", False)
                job.frame_start = job_data.get("frame_start", 1)
                job.frame_end = job_data.get("frame_end", 250)
                job.override_output = job_data.get("override_output", False)
                job.output_path = job_data.get("output_path", "//")
                job.override_resolution = job_data.get("override_resolution", False)
                job.resolution_scale = job_data.get("resolution_scale", 100)
                job.override_samples = job_data.get("override_samples", False)
                job.samples = job_data.get("samples", 128)
                job.override_format = job_data.get("override_format", False)
                job.render_format = job_data.get("render_format", 'PNG')
                job.override_engine = job_data.get("override_engine", False)
                job.render_engine = job_data.get("render_engine", 'CYCLES')
                job.override_view_layer = job_data.get("override_view_layer", False)
                job.view_layer = job_data.get("view_layer", "")
        except Exception as e:
            print(f"Error loading queue from text: {e}")

    @staticmethod
    def register_handlers():
        if not _save_pre_handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.append(_save_pre_handler)
        if not _load_post_handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(_load_post_handler)

    @staticmethod
    def unregister_handlers():
        if _save_pre_handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.remove(_save_pre_handler)
        if _load_post_handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(_load_post_handler)

from bpy.app.handlers import persistent

@persistent
def _save_pre_handler(dummy):
    # Only save if there are jobs
    if bpy.context.window_manager.rendercue.jobs:
        StateManager.save_queue_to_text(bpy.context)

@persistent
def _load_post_handler(dummy):
    # Use a timer to delay loading slightly to ensure context is ready
    bpy.app.timers.register(lambda: StateManager.load_queue_from_text(bpy.context) or None, first_interval=0.1)

def register():
    # Don't register handlers by default
    pass

def unregister():
    StateManager.unregister_handlers()
