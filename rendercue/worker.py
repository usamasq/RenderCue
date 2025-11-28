import bpy
import sys
import json
import os
import time
import argparse



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
        # Use a unique filename with timestamp to force Blender to reload the image
        timestamp = int(time.time() * 1000)
        preview_path = os.path.join(os.path.dirname(self.status_path), f".rendercue_preview_{timestamp}.jpg")
        
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
                
                # Clean up old previews to save space
                try:
                    dir_path = os.path.dirname(self.status_path)
                    current_name = os.path.basename(preview_path)
                    for f in os.listdir(dir_path):
                        if f.startswith(".rendercue_preview_") and f.endswith(".jpg") and f != current_name:
                            try:
                                os.remove(os.path.join(dir_path, f))
                            except:
                                pass
                except:
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
        try:
            # Check for Pause
            pause_file = os.path.join(os.path.dirname(self.status_path), "rendercue_pause.signal")
            if os.path.exists(pause_file):
                self.log_status("Paused", etr="Paused")
                print("Render Paused...")
                while os.path.exists(pause_file):
                    time.sleep(1)
                print("Render Resumed")
                self.log_status("Resuming...", etr="Calculating...")
        except Exception as e:
            print(f"Pause Handler Error: {e}")
            self.log_status(f"Pause Error: {e}", error=str(e))

    def run(self):
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
        
        global_output = self.manifest.get("global_output_path", "//")
        output_structure = self.manifest.get("output_structure", "SEPARATE")
        
        # Pre-calculate scene usage for unique folder naming in SEPARATE mode
        scene_usage_count = {}
        
        # Global frame counter for SAME FOLDER mode
        global_frame_counter = 1
        blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

        for i, job in enumerate(self.jobs):
            self.current_job_index = i
            scene_name = job["scene_name"]
            
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
            
            if job["override_frame_range"]:
                frame_start = job["frame_start"]
                frame_end = job["frame_end"]
                
            # Output Path Logic
            if job["override_output"]:
                base_path = job["output_path"]
                # If overriding output, we treat it as a separate destination usually, 
                # but let's respect the structure if it's not absolute? 
                # Actually, override output usually implies a specific folder.
                # Let's assume override output is the final folder for that job.
                output_dir = base_path
            else:
                base_path = global_output
                if base_path.startswith("//"):
                    base_path = bpy.path.abspath(base_path)
                    
                if output_structure == 'SEPARATE':
                    folder_name = scene_name
                    # If this scene is used multiple times, append index to subsequent ones
                    # Or always append index if it appears multiple times in the queue?
                    # User said: "how are folders named if we queue a scene multiple times... Need to fix that"
                    # Let's append _Job<Index> if it's not the first time OR if we want to be explicit.
                    # To be safe and consistent: If a scene appears > 1 time in TOTAL list, we might want to suffix.
                    # But simpler: Just check if we've seen it before in this run?
                    # Better: If we have duplicates, suffix.
                    # Let's use the usage count we are tracking.
                    if scene_usage_count[scene_name] > 1:
                        folder_name = f"{scene_name}_Job{i+1}"
                    
                    output_dir = os.path.join(base_path, folder_name)
                else:
                    # SAME FOLDER
                    output_dir = base_path

            os.makedirs(output_dir, exist_ok=True)
            
            # Apply Render Settings Overrides
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

            # Determine File Format Extension (for manual naming if needed)
            # Actually, Blender handles extension if we don't provide it, but we want control.
            
            # Render Loop
            # We iterate frames manually
            current_frame = frame_start
            while current_frame <= frame_end:
                # Check for Pause
                self.check_pause()
                
                # Set Frame
                scene.frame_set(current_frame)
                
                # Construct Filename
                if output_structure == 'SAME_FOLDER' and not job["override_output"]:
                    # Continuous numbering: BlendName_0001, BlendName_0002...
                    # We use global_frame_counter
                    file_name = f"{blend_name}_{global_frame_counter:04d}"
                    global_frame_counter += 1
                else:
                    # Standard naming: SceneName_0001...
                    # Or if override output, just standard frame number
                    # We use the scene's frame number
                    file_name = f"{scene_name}_{current_frame:04d}"
                
                # Set Filepath
                # We need to strip extension from file_name if Blender adds it, 
                # but render(write_still=True) expects the path without extension usually?
                # Actually, if we provide extension, Blender uses it.
                # Let's let Blender handle extension by not providing it in the name, 
                # BUT we need to ensure the frame number is what we want.
                # If we set filepath to "path/to/file_0001", Blender might add "0001" again if use_file_extension is True?
                # No, if we set filepath, Blender uses it. 
                # If we want exact control, we should probably disable 'use_overwrite' or similar?
                
                # Wait, if we set scene.render.filepath = "/path/to/image", Blender appends frame number.
                # If we want to FORCE a specific name (like for continuous sequence), we must include the number in the path
                # AND tell Blender NOT to append frame number.
                # The way to do that is to use the '#' characters or just set the path and render single frame?
                # When rendering a single frame (write_still=True), Blender usually appends frame number 
                # UNLESS we are not in animation mode?
                # Actually, for single frame render, if we set filepath to "/tmp/img.png", it writes to "/tmp/img.png".
                # It does NOT append frame number automatically if we don't ask it to (unlike animation render).
                
                full_path = os.path.join(output_dir, file_name)
                scene.render.filepath = full_path
                
                # Render Frame
                try:
                    self.log_status(f"Rendering {scene_name} (Frame {current_frame})", etr="Calculating...")
                    print(f"Rendering frame {current_frame} to {full_path}")
                    
                    # Redirect stdout to suppress Blender noise if needed, but we want logs.
                    bpy.ops.render.render(write_still=True)
                    
                except Exception as e:
                    msg = f"Error rendering {scene_name} frame {current_frame}: {str(e)}"
                    print(msg)
                    self.log_status(msg, error=str(e))
                    # We might want to continue or abort? Let's continue to next frame/job.
                    # But if it's a persistent error, maybe abort job?
                    # For now, let's try next frame.
                
                current_frame += 1

        self.log_status("All Jobs Completed", finished=True)
        print("Background Render Complete")

    def check_pause(self):
        try:
            pause_file = os.path.join(os.path.dirname(self.status_path), "rendercue_pause.signal")
            if os.path.exists(pause_file):
                self.log_status("Paused", etr="Paused")
                print("Render Paused...")
                while os.path.exists(pause_file):
                    time.sleep(1)
                print("Render Resumed")
                self.log_status("Resuming...", etr="Calculating...")
        except Exception as e:
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
