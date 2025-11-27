import bpy

class RENDERCUE_OT_sync_from_vse(bpy.types.Operator):
    bl_idname = "rendercue.sync_from_vse"
    bl_label = "Sync from VSE"
    bl_description = "Import scene strip order from VSE Channel 1 into the render queue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.rendercue
        scene = context.scene
        
        if not scene.sequence_editor:
            self.report({'WARNING'}, "No Video Sequence Editor in this scene")
            return {'CANCELLED'}
            
        vse = scene.sequence_editor
        target_channel = settings.vse_channel
        
        # Find all scene strips in channel 1
        scene_strips = []
        # Blender 5.0 compatibility: sequences_all is the new API
        if hasattr(vse, 'sequences_all'):
            all_strips = vse.sequences_all
        else:
            all_strips = vse.sequences
        for strip in all_strips:
            if strip.channel == target_channel and strip.type == 'SCENE':
                scene_strips.append(strip)
        
        if not scene_strips:
            self.report({'WARNING'}, f"No scene strips found in VSE Channel {target_channel}")
            return {'CANCELLED'}
        
        # Sort strips by start frame
        scene_strips.sort(key=lambda s: s.frame_start)
        
        # Clear existing queue
        settings.jobs.clear()
        
        # Add jobs based on strip order
        for strip in scene_strips:
            if strip.scene:
                job = settings.jobs.add()
                job.scene = strip.scene
                
                # Try to detect overrides from strip properties
                # Frame range override based on strip duration vs scene duration
                scene_duration = strip.scene.frame_end - strip.scene.frame_start + 1
                strip_duration = strip.frame_final_duration
                
                if strip_duration != scene_duration:
                    job.override_frame_range = True
                    # Calculate actual frame range from strip offset
                    job.frame_start = strip.scene.frame_start + int(strip.animation_offset_start)
                    job.frame_end = job.frame_start + strip_duration - 1
        
        self.report({'INFO'}, f"Synced {len(scene_strips)} scenes from VSE")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RENDERCUE_OT_sync_from_vse)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_sync_from_vse)
