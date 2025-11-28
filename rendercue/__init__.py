import bpy
from . import properties
from . import ui
from . import operators
from . import render
from . import preferences


bl_info = {
    "name": "RenderCue",
    "author": "Usama Bin Shahid",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Render > RenderCue | Video Sequencer > RenderCue | 3D Viewport > RenderCue",
    "description": "Sequence. Queue. Render. Support development: https://www.patreon.com/c/usamasq",
    "warning": "",
    "doc_url": "",
    "category": "Render",
}

def register():
    properties.register()
    operators.register()
    ui.register()
    render.register()
    preferences.register()

def unregister():
    preferences.unregister()
    render.unregister()
    ui.unregister()
    operators.unregister()
    properties.unregister()

