import bpy
from .core import StateManager
from . import version_compat

class RenderCuePreferences(bpy.types.AddonPreferences):
    """Addon preferences for RenderCue."""
    bl_idname = __package__
    
    # Preference properties
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

    renumber_frame_step_output: bpy.props.BoolProperty(
        name="Auto-Renumber Frame Step Output",
        description="Automatically renumber output files sequentially when using Frame Step > 1 (for video editor compatibility)",
        default=False
    )

    def update_auto_save(self, context):
        if self.auto_save_queue:
            StateManager.register_handlers()
        else:
            StateManager.unregister_handlers()

    auto_save_queue: bpy.props.BoolProperty(
        name="Auto-Save Queue State",
        description="Automatically save and restore render queue when saving/loading .blend files",
        default=False,
        update=update_auto_save
    )

    # Completion Feedback Preferences
    
    show_completion_statusbar: bpy.props.BoolProperty(
        name="Show Completion in Status Bar",
        description="Show render completion message in status bar",
        default=True
    )
    
    statusbar_display_seconds: bpy.props.IntProperty(
        name="Status Bar Display Time",
        description="Show status bar message for this many seconds",
        default=30,
        min=5,
        max=120
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Header
        layout.label(text="RenderCue Addon Settings", icon=version_compat.get_icon('SETTINGS'))
        layout.separator()
        
        # Instructions Section
        box = layout.box()
        box.label(text="Quick Start:", icon=version_compat.get_icon('INFO'))
        col = box.column(align=True)
        col.label(text="1. Open RenderCue panel (Render Properties or 3D Viewport N-Panel)")
        col.label(text="2. Click 'Add Scene' or 'Add All Scenes' to build your queue")
        col.label(text="3. Select a job to configure overrides (resolution, samples, etc.)")
        col.label(text="4. Click 'Render Cue' to batch render all scenes")
        layout.separator()
        
        # Preferences
        layout.separator()
        layout.label(text="General:")
        layout.prop(self, "auto_save_queue")
        layout.prop(self, "renumber_frame_step_output")
        
        layout.separator()
        layout.label(text="Notifications:")
        layout.prop(self, "show_notifications")
        layout.prop(self, "webhook_url")
        
        layout.separator()
        layout.label(text="Completion Feedback:")
        
        # Status Bar Settings
        row = layout.row()
        row.prop(self, "show_completion_statusbar")
        if self.show_completion_statusbar:
            row.prop(self, "statusbar_display_seconds", text="Duration (s)")
        
        layout.separator()
        layout.separator()
        
        # Tips
        box = layout.box()
        box.label(text="Tips:", icon=version_compat.get_icon('LIGHTPROBE_SPHERE'))
        col = box.column(align=True)
        col.label(text="• Enable 'Auto-Save Queue' in preferences to persist queue in .blend files")
        col.label(text="• Use 'Override All' button to apply settings to all jobs in queue")
        col.label(text="• Access RenderCue from multiple locations for convenience")
        
        layout.separator()
        
        # Links
        row = layout.row()
        row.operator("wm.url_open", text="Documentation", icon=version_compat.get_icon('URL')).url = "https://github.com/usamasq/RenderCue"
        row.operator("wm.url_open", text="Report Issue", icon=version_compat.get_icon('ERROR')).url = "https://github.com/usamasq/RenderCue/issues"

def register():
    bpy.utils.register_class(RenderCuePreferences)

def unregister():
    bpy.utils.unregister_class(RenderCuePreferences)
