import bpy

class RENDERCUE_OT_sync_vse(bpy.types.Operator):
    bl_idname = "rendercue.sync_vse"
    bl_label = "Sync to VSE"
    bl_description = "Populate the VSE with scene strips from the queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.window_manager.rendercue
        
        if not settings.jobs:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}

        # 1. Create or Get "RenderCue VSE" Scene
        vse_scene_name = "RenderCue VSE"
        vse_scene = bpy.data.scenes.get(vse_scene_name)
        
        if not vse_scene:
            vse_scene = bpy.data.scenes.new(vse_scene_name)
        
        # 2. Switch to VSE Scene
        context.window.scene = vse_scene
        
        # 3. Switch to Video Editing Workspace (if available)
        # Try to find a workspace with "Video Editing" in the name
        vse_workspace = None
        for ws in bpy.data.workspaces:
            if "Video Editing" in ws.name:
                vse_workspace = ws
                break
        
        if vse_workspace:
            context.window.workspace = vse_workspace
        
        # 4. Setup VSE Scene Settings (Match first job)
        first_job = settings.jobs[0]
        if first_job.scene:
            vse_scene.render.resolution_x = first_job.scene.render.resolution_x
            vse_scene.render.resolution_y = first_job.scene.render.resolution_y
            vse_scene.render.resolution_percentage = first_job.scene.render.resolution_percentage
            vse_scene.render.fps = first_job.scene.render.fps
            vse_scene.render.fps_base = first_job.scene.render.fps_base
        
        # Ensure VSE exists
        if not vse_scene.sequence_editor:
            vse_scene.sequence_editor_create()
            
        vse = vse_scene.sequence_editor
        target_channel = settings.vse_channel
        
        # Clear existing strips in the target channel
        if hasattr(vse, "sequences"):
            seq_collection = vse.sequences
        else:
            seq_collection = vse.strips
            
        for strip in list(seq_collection):
            if strip.channel == target_channel:
                seq_collection.remove(strip)
                
        # 5. Add Strips Sequentially
        current_frame = 1
        vse_scene.frame_start = 1
        
        for job in settings.jobs:
            if not job.scene:
                continue
                
            # Determine duration
            start = job.scene.frame_start
            end = job.scene.frame_end
            
            if job.override_frame_range:
                start = job.frame_start
                end = job.frame_end
                
            duration = end - start + 1
            
            # Add Scene Strip
            try:
                strip = seq_collection.new_scene(
                    name=job.scene.name,
                    scene=job.scene,
                    channel=target_channel,
                    frame_start=current_frame
                )
                
                # Adjust strip range to match job override
                if job.override_frame_range:
                    strip.frame_final_duration = duration
                    
                    # Set the offset for the start frame
                    offset = job.frame_start - job.scene.frame_start
                    strip.animation_offset_start = offset
                    
                current_frame += duration
                
            except Exception as e:
                self.report({'WARNING'}, f"Could not add strip for {job.scene.name}: {e}")
        
        # Set Total Duration
        vse_scene.frame_end = current_frame - 1
        
        self.report({'INFO'}, "Synced to 'RenderCue VSE' scene")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RENDERCUE_OT_sync_vse)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_sync_vse)

