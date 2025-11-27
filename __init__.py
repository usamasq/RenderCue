import bpy
from . import properties
from . import ui
from . import operators
from . import vse
from . import render
from . import preferences
from . import vse_sync
from . import updater

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
    updater.register()
    operators.register()
    ui.register()
    vse.register()
    render.register()
    preferences.register()
    vse_sync.register()

def unregister():
    vse_sync.unregister()
    preferences.unregister()
    render.unregister()
    vse.unregister()
    ui.unregister()
    operators.unregister()
    updater.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()
