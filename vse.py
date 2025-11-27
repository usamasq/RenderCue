import bpy

class RENDERCUE_OT_sync_vse(bpy.types.Operator):
    bl_idname = "rendercue.sync_vse"
    bl_label = "Sync to VSE"
    bl_description = "Populate the VSE with scene strips from the queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.window_manager.rendercue
        
        # Ensure we are in a scene that has a VSE
        scene = context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()
            
        vse = scene.sequence_editor
        
        # Clear existing strips in the selected channel
        target_channel = settings.vse_channel
        
        # We must use vse.sequences for modification (adding/removing)
        # vse.sequences_all is read-only or does not support new_scene/remove
        if hasattr(vse, "sequences"):
            seq_collection = vse.sequences
        elif hasattr(vse, "strips"):
            seq_collection = vse.strips
        else:
            print(f"[RenderCue] VSE Attributes: {dir(vse)}")
            self.report({'ERROR'}, "Could not find VSE sequences collection (API mismatch)")
            return {'CANCELLED'}
            
        for strip in list(seq_collection):
            if strip.channel == target_channel:
                seq_collection.remove(strip)
                
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
        
        self.report({'INFO'}, "VSE Synced")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RENDERCUE_OT_sync_vse)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_sync_vse)

