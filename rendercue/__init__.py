"""
RenderCue Blender Addon

RenderCue is a powerful batch rendering and queue management tool for Blender.
It supports:
- Multi-scene queuing
- Job-specific overrides (resolution, samples, camera, etc.)
- Background rendering
- Progress monitoring
- Version compatibility (Blender 3.0 - 5.0+)

This module handles the registration of all addon components.
"""

import bpy
from . import properties
from . import ui
from . import operators
from . import render
from . import preferences


bl_info = {
    "name": "RenderCue",
    "author": "Usama Bin Shahid",
    "version": (1, 1, 1),
    "blender": (3, 0, 0),
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
    
    # Register handlers if auto-save is enabled
    # We need to delay this slightly to ensure preferences are loaded
    def register_handlers_delayed():
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
            if prefs.auto_save_queue:
                from .core import StateManager
                StateManager.register_handlers()
        except (AttributeError, KeyError):
            pass
            
    bpy.app.timers.register(register_handlers_delayed, first_interval=0.1)

def unregister():
    preferences.unregister()
    render.unregister()
    ui.unregister()
    operators.unregister()
    properties.unregister()

