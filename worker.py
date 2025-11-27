import bpy
import sys
import json
import os
import time
import argparse

# Add current directory to path to import local modules if needed
sys.path.append(os.path.dirname(__file__))

class BackgroundWorker:
    def __init__(self, manifest_path, status_path):
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
        
    def load_manifest(self):
        try:
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
            self.jobs = self.manifest.get("jobs", [])
            self.total_jobs = len(self.jobs)
            return True
        except Exception as e:
            print(f"Failed to load manifest: {e}")
            return False

    def log_status(self, message, etr="--:--", finished=False, error=None, **kwargs):
        data = {
            "job_index": self.current_job_index + 1, # 1-based for UI
            "total_jobs": self.total_jobs,
            "message": message,
            "etr": etr,
            "finished": finished,
            "error": error,
            "timestamp": time.time(),
            "finished_frames": self.finished_frames_count,
            "total_frames": self.total_frames_to_render,
            "last_frame": kwargs.get("last_frame", "")
        }
        try:
            with open(self.status_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to write status: {e}")

    def calculate_total_frames(self):
        self.total_frames_to_render = 0
        for job in self.jobs:
            # Note: This assumes scene data is available or passed in manifest.
            # Since we only have scene names in manifest, we rely on the blend file.
            scene_name = job.get("scene_name")
            if scene_name and scene_name in bpy.data.scenes:
                scene = bpy.data.scenes[scene_name]
                start = job.get("frame_start", scene.frame_start)
                end = job.get("frame_end", scene.frame_end)
                if job.get("override_frame_range"):
                    start = job["frame_start"]
                    end = job["frame_end"]
                self.total_frames_to_render += (end - start + 1)

    def on_render_post(self, scene, depsgraph=None):
        self.finished_frames_count += 1
        
        # Calculate ETR
        elapsed = time.time() - self.start_time
        etr = "--:--"
        
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
        # Use a hidden filename
        preview_path = os.path.join(os.path.dirname(self.status_path), ".rendercue_preview.jpg")
        
        # Debug Log
        debug_log_path = os.path.join(os.path.dirname(self.status_path), "worker_debug.log")
        def log_debug(msg):
            try:
                with open(debug_log_path, "a") as f:
                    f.write(f"{time.ctime()}: {msg}\n")
            except:
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
        # Check for Pause
        pause_file = os.path.join(os.path.dirname(self.status_path), "rendercue_pause.signal")
        if os.path.exists(pause_file):
            self.log_status("Paused", etr="Paused")
            print("Render Paused...")
            while os.path.exists(pause_file):
                time.sleep(1)
            print("Render Resumed")
            self.log_status("Resuming...", etr="Calculating...")

    def run(self):
        if not self.load_manifest():
            return

        print(f"Starting Background Render: {self.total_jobs} jobs")
        
        self.calculate_total_frames()
        self.start_time = time.time()
        
        # Register Handlers
        bpy.app.handlers.render_post.append(self.on_render_post)
        bpy.app.handlers.render_pre.append(self.on_render_pre)
        
        global_output = self.manifest.get("global_output_path", "//")
        output_structure = self.manifest.get("output_structure", "SEPARATE")

        for i, job in enumerate(self.jobs):
            self.current_job_index = i
            scene_name = job["scene_name"]
            
            if scene_name not in bpy.data.scenes:
                self.log_status(f"Scene {scene_name} not found", error=True)
                continue
                
            scene = bpy.data.scenes[scene_name]
            bpy.context.window.scene = scene
            
            # Apply Overrides
            if job["override_frame_range"]:
                scene.frame_start = job["frame_start"]
                scene.frame_end = job["frame_end"]
                
            # Output Path
            if job["override_output"]:
                base_path = job["output_path"]
            else:
                base_path = global_output
                
            if base_path.startswith("//"):
                base_path = bpy.path.abspath(base_path)
                
            if output_structure == 'SEPARATE':
                output_dir = os.path.join(base_path, scene_name)
            else:
                output_dir = base_path
                
            os.makedirs(output_dir, exist_ok=True)
            
            # Filename
            filename = scene_name.replace(" ", "_")
            render_format = job["render_format"] if job["override_format"] else scene.render.image_settings.file_format
            
            if render_format in ['FFMPEG', 'AVI_JPEG', 'AVI_RAW']:
                ext = ".mp4" if render_format == 'FFMPEG' else ".avi"
                filepath = os.path.join(output_dir, f"{filename}{ext}")
            else:
                filepath = os.path.join(output_dir, f"{filename}_")
                
            scene.render.filepath = filepath
            
            # Other Overrides
            if job.get("override_engine"):
                scene.render.engine = job["render_engine"]
                
            if job.get("override_view_layer"):
                vl_name = job["view_layer"]
                if vl_name and vl_name in scene.view_layers:
                    for vl in scene.view_layers:
                        vl.use = (vl.name == vl_name)

            if job["override_resolution"]:
                scene.render.resolution_percentage = job["resolution_scale"]
                
            if job["override_format"]:
                scene.render.image_settings.file_format = job["render_format"]
                
            if job["override_samples"]:
                if scene.render.engine == 'CYCLES':
                    scene.cycles.samples = job["samples"]
                elif scene.render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
                    try:
                        scene.eevee.taa_render_samples = job["samples"]
                    except AttributeError:
                        try:
                            scene.eevee.samples = job["samples"]
                        except AttributeError:
                            pass

            # Render
            try:
                self.log_status(f"Starting {scene_name}...", etr="Calculating...")
                print(f"Rendering {scene_name} to {filepath}")
                bpy.ops.render.render(animation=True, write_still=True)
            except Exception as e:
                msg = f"Error rendering {scene_name}: {str(e)}"
                print(msg)
                self.log_status(msg, error=str(e))
                return

        self.log_status("All Jobs Completed", finished=True)
        print("Background Render Complete")

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

if __name__ == "__main__":
    main()
