import bpy
from . import properties, ui, operators, vse, render, preferences, vse_sync

bl_info = {
    "name": "RenderCue",
    "author": "RenderCue Team",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Render > RenderCue | Video Sequencer > RenderCue | 3D Viewport > RenderCue",
    "description": "Sequence. Queue. Render.",
    "warning": "",
    "doc_url": "",
    "category": "Render",
}

def register():
    properties.register()
    preferences.register()
    operators.register()
    ui.register()
    vse.register()
    vse_sync.register()
    render.register()

def unregister():
    render.unregister()
    vse_sync.unregister()
    vse.unregister()
    ui.unregister()
    operators.unregister()
    preferences.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()

