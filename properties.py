import bpy

class RenderCueJob(bpy.types.PropertyGroup):
    scene: bpy.props.PointerProperty(
        type=bpy.types.Scene,
        name="Scene",
        description="Scene to render"
    )
    
    # Overrides
    override_output: bpy.props.BoolProperty(name="Override Output", default=False)
    output_path: bpy.props.StringProperty(name="Output Path", subtype='DIR_PATH', default="//render/")
    
    override_frame_range: bpy.props.BoolProperty(name="Override Frame Range", default=False)
    frame_start: bpy.props.IntProperty(name="Start", default=1)
    frame_end: bpy.props.IntProperty(name="End", default=250)
    
    override_resolution: bpy.props.BoolProperty(name="Override Resolution", default=False)
    resolution_scale: bpy.props.IntProperty(name="Scale %", default=50, min=1, max=1000)
    
    override_format: bpy.props.BoolProperty(name="Override Format", default=False)
    render_format: bpy.props.EnumProperty(
        name="Format",
        items=[
            ('PNG', "PNG", ""),
            ('JPEG', "JPEG", ""),
            ('OPEN_EXR', "OpenEXR", ""),
            ('FFMPEG', "FFmpeg Video", ""),
        ],
        default='PNG'
    )
    
    override_samples: bpy.props.BoolProperty(name="Override Samples", default=False)
    samples: bpy.props.IntProperty(name="Samples", default=128, min=1)

class RenderCueSettings(bpy.types.PropertyGroup):
    jobs: bpy.props.CollectionProperty(type=RenderCueJob)
    active_job_index: bpy.props.IntProperty(name="Active Job Index", default=0)
    
    output_structure: bpy.props.EnumProperty(
        name="Output Structure",
        items=[
            ('SEPARATE', "Separate Folders", "Create a subfolder for each scene (e.g. /output/SceneName/)"),
            ('SAME', "Same Folder", "Render all to the same directory"),
        ],
        default='SEPARATE'
    )
    
    global_output_path: bpy.props.StringProperty(
        name="Global Output",
        subtype='DIR_PATH',
        default="//render_cue_output/",
        description="Base directory for batch renders"
    )

def register():
    bpy.utils.register_class(RenderCueJob)
    bpy.utils.register_class(RenderCueSettings)
    # Store settings in WindowManager to be global across scenes in the session/file
    bpy.types.WindowManager.rendercue = bpy.props.PointerProperty(type=RenderCueSettings)

def unregister():
    del bpy.types.WindowManager.rendercue
    bpy.utils.unregister_class(RenderCueSettings)
    bpy.utils.unregister_class(RenderCueJob)
