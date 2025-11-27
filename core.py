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
        settings = context.scene.rendercue
        data = {
            "timestamp": time.time(),
            "global_output_path": settings.global_output_path,
            "output_structure": settings.output_structure,
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
                "render_format": job.render_format
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
                
            settings = context.scene.rendercue
            settings.jobs.clear()
            
            settings.global_output_path = data.get("global_output_path", settings.global_output_path)
            settings.output_structure = data.get("output_structure", settings.output_structure)
            
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
                
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False
