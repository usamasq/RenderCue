import bpy

class RenderCuePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    # Preference properties
    show_instructions: bpy.props.BoolProperty(
        name="Show Quick Start Instructions",
        description="Toggle the visibility of the Quick Start guide in the RenderCue panel header",
        default=True
    )
    
    auto_sync_vse: bpy.props.BoolProperty(
        name="Auto-Sync VSE After Queue Changes",
        description="Automatically update the Video Sequence Editor timeline whenever jobs are added, removed, or reordered",
        default=False
    )
    
    play_sound_on_finish: bpy.props.BoolProperty(
        name="Play Sound on Finish",
        description="Play a system notification sound when the entire batch render queue completes",
        default=True
    )
    
    webhook_url: bpy.props.StringProperty(
        name="Webhook URL",
        description="Enter a Discord or Slack Webhook URL to receive notifications when renders complete or fail",
        default=""
    )

    show_notifications: bpy.props.BoolProperty(
        name="Show Desktop Notifications",
        description="Show a system notification when a render batch completes or fails",
        default=True
    )
    
    check_updates_on_startup: bpy.props.BoolProperty(
        name="Check Updates on Startup",
        description="Automatically check GitHub for new versions of RenderCue when Blender starts",
        default=True
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Header
        layout.label(text="RenderCue Addon Settings", icon='SETTINGS')
        layout.separator()
        
        # Instructions Section
        if self.show_instructions:
            box = layout.box()
            box.label(text="Quick Start:", icon='INFO')
            col = box.column(align=True)
            col.label(text="1. Open RenderCue panel (Render Properties or 3D Viewport N-Panel)")
            col.label(text="2. Click 'Add Scene' or 'Add All Scenes' to build your queue")
            col.label(text="3. Select a job to configure overrides (resolution, samples, etc.)")
            col.label(text="4. Click 'Sync to VSE' to visualize your sequence")
            col.label(text="5. Click 'Render Cue' to batch render all scenes")
            layout.separator()
        
        # Preferences
        box = layout.box()
        box.label(text="Preferences:", icon='PREFERENCES')
        box.prop(self, "show_instructions")
        box.prop(self, "auto_sync_vse")
        box.prop(self, "play_sound_on_finish")
        
        layout.separator()
        layout.label(text="Notifications:")
        layout.prop(self, "show_notifications")
        layout.prop(self, "webhook_url")
        
        layout.separator()
        layout.label(text="Updates:")
        row = layout.row()
        row.prop(self, "check_updates_on_startup")
        row.operator("rendercue.check_updates", text="Check Now")
        
        layout.separator()
        
        # Tips
        box = layout.box()
        box.label(text="Tips:", icon='LIGHTPROBE_SPHERE')
        col = box.column(align=True)
        col.label(text="• Queue is saved with your .blend file - no need to rebuild!")
        col.label(text="• Use 'Sync from VSE' to import strip order from Video Editor")
        col.label(text="• Click the ⧉ icon next to any override to apply it to all jobs")
        col.label(text="• Access RenderCue from multiple locations for convenience")
        
        layout.separator()
        
        # Links
        row = layout.row()
        row.operator("wm.url_open", text="Documentation", icon='URL').url = "https://github.com/usamasq/RenderCue"
        row.operator("wm.url_open", text="Report Issue", icon='ERROR').url = "https://github.com/usamasq/RenderCue/issues"

def register():
    bpy.utils.register_class(RenderCuePreferences)

def unregister():
    bpy.utils.unregister_class(RenderCuePreferences)
