import bpy

class RenderCuePreferences(bpy.types.AddonPreferences):
    bl_idname = "rendercue"
    
    # Preference properties
    show_instructions: bpy.props.BoolProperty(
        name="Show Quick Start Instructions",
        description="Display quick start guide in the panel header",
        default=True
    )
    
    auto_sync_vse: bpy.props.BoolProperty(
        name="Auto-Sync VSE After Queue Changes",
        description="Automatically update VSE when the render queue is modified",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Header
        layout.label(text="RenderCue Addon Settings", icon='SETTINGS')
        layout.separator()
        
        # Instructions Section
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
        row.operator("wm.url_open", text="Documentation", icon='URL').url = "https://github.com/rendercue/rendercue"
        row.operator("wm.url_open", text="Report Issue", icon='ERROR').url = "https://github.com/rendercue/rendercue/issues"

def register():
    bpy.utils.register_class(RenderCuePreferences)

def unregister():
    bpy.utils.unregister_class(RenderCuePreferences)
