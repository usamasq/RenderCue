import bpy

class RENDERCUE_OT_sync_vse(bpy.types.Operator):
    bl_idname = "rendercue.sync_vse"
    bl_label = "Sync to VSE"
    bl_description = "Populate the VSE with scene strips from the queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wm = context.window_manager
        settings = wm.rendercue
        
        # Ensure we are in a scene that has a VSE
        # Usually we want to do this in the current scene or a dedicated "Master" scene.
        # For now, let's use the current scene.
        scene = context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()
            
        vse = scene.sequence_editor
        
        # Clear existing strips in a specific channel (e.g., Channel 1)
        # Or maybe we should tag them? For simplicity, let's clear channel 1.
        target_channel = 1
        for strip in list(vse.sequences):
            if strip.channel == target_channel:
                vse.sequences.remove(strip)
                
        current_frame = 1
        
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
                strip = vse.sequences.new_scene(
                    name=job.scene.name,
                    scene=job.scene,
                    channel=target_channel,
                    frame_start=current_frame
                )
                
                # Adjust strip range to match job override
                # Scene strips by default take the scene's frame range.
                # We need to adjust the strip's internal start/end if overridden.
                
                # strip.scene_input.frame_start/end controls what part of the scene is shown
                # strip.frame_start/end controls where it is on the timeline
                
                # By default new_scene uses the scene's start/end.
                # If we override, we need to change the input.
                
                if job.override_frame_range:
                    # The strip length is already set by frame_start (placement)
                    # We need to set the length.
                    strip.frame_final_duration = duration
                    
                    # Now set the offset if the start frame is different
                    # scene_camera uses the scene's frame range.
                    # If we want frame 10-20 of the scene to play at frame 1 of timeline:
                    # strip.animation_offset_start = 10 - scene.frame_start
                    
                    # Actually, for Scene strips:
                    # strip.scene_input.frame_start is not directly exposed like that for all versions.
                    # Usually it's just mapped 1:1.
                    # We might need to adjust 'animation_offset_start'.
                    
                    offset = job.frame_start - job.scene.frame_start
                    strip.animation_offset_start = offset
                    
                current_frame += duration
                
            except Exception as e:
                self.report({'WARNING'}, f"Could not add strip for {job.scene.name}: {e}")
        
        self.report({'INFO'}, "VSE Synced")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RENDERCUE_OT_sync_vse)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_sync_vse)
