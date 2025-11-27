import bpy
from . import properties, ui, operators, vse, render

bl_info = {
    "name": "RenderCue",
    "author": "RenderCue Team",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Render > RenderCue",
    "description": "Sequence. Queue. Render.",
    "warning": "",
    "doc_url": "",
    "category": "Render",
}

def register():
    properties.register()
    operators.register()
    ui.register()
    vse.register()
    render.register()

def unregister():
    render.unregister()
    vse.unregister()
    ui.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()
