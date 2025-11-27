import bpy

class RenderCueJob(bpy.types.PropertyGroup):
    scene: bpy.props.PointerProperty(
        type=bpy.types.Scene,
        name="Scene",
        description="The scene to be rendered in this job"
    )
    
    # Overrides
    override_frame_range: bpy.props.BoolProperty(
        name="Override Frame Range", 
        default=False,
        description="Enable to render a custom frame range instead of the scene's default range"
    )
    frame_start: bpy.props.IntProperty(
        name="Start Frame", 
        default=1,
        description="First frame to render for this job"
    )
    frame_end: bpy.props.IntProperty(
        name="End Frame", 
        default=250,
        description="Last frame to render for this job"
    )
    
    override_output: bpy.props.BoolProperty(
        name="Override Output", 
        default=False,
        description="Enable to save this job's output to a custom location"
    )
    output_path: bpy.props.StringProperty(
        name="Output Path", 
        subtype='DIR_PATH', 
        default="//",
        description="Custom output directory for this job"
    )
    
    override_resolution: bpy.props.BoolProperty(
        name="Override Resolution", 
        default=False,
        description="Enable to scale the render resolution"
    )
    resolution_scale: bpy.props.IntProperty(
        name="Scale %", 
        default=100, 
        min=1, 
        max=200,
        description="Percentage of the scene's resolution to render (e.g., 50% for half size)"
    )
    
    override_samples: bpy.props.BoolProperty(
        name="Override Samples", 
        default=False,
        description="Enable to set a custom sample count for Cycles/Eevee"
    )
    samples: bpy.props.IntProperty(
        name="Samples", 
        default=128, 
        min=1,
        description="Number of samples to use for rendering (higher = better quality, slower)"
    )
    
    override_format: bpy.props.BoolProperty(
        name="Override Format", 
        default=False,
        description="Enable to change the output file format"
    )
    render_format: bpy.props.EnumProperty(
        name="Format",
        items=[
            ('PNG', "PNG", "Lossless image format"),
            ('JPEG', "JPEG", "Compressed image format"),
            ('BMP', "BMP", "Bitmap image format"),
            ('IRIS', "Iris", "SGI Iris image format"),
            ('JPEG2000', "JPEG 2000", "Advanced JPEG format"),
            ('TARGA', "Targa", "Truevision Targa image format"),
            ('TARGA_RAW', "Targa Raw", "Uncompressed Targa format"),
            ('CINEON', "Cineon", "Cineon image format"),
            ('DPX', "DPX", "Digital Moving-Picture Exchange"),
            ('OPEN_EXR', "OpenEXR", "High dynamic range format"),
            ('OPEN_EXR_MULTILAYER', "OpenEXR Multilayer", "Multilayer HDR format"),
            ('HDR', "Radiance HDR", "High dynamic range format"),
            ('TIFF', "TIFF", "Tagged Image File Format"),
            ('AVI_JPEG', "AVI JPEG", "AVI video with JPEG compression"),
            ('AVI_RAW', "AVI Raw", "Uncompressed AVI video"),
            ('FFMPEG', "FFmpeg Video", "Video file format"),
        ],
        default='PNG',
        description="File format for the rendered output"
    )

class RenderCueSettings(bpy.types.PropertyGroup):
    jobs: bpy.props.CollectionProperty(type=RenderCueJob)
    active_job_index: bpy.props.IntProperty(name="Active Job Index", default=0)
    
    output_structure: bpy.props.EnumProperty(
        name="Output Structure",
        items=[
            ('SEPARATE', "Separate Folders", "Create a subfolder for each scene (e.g. /output/SceneName/)"),
            ('SAME', "Same Folder", "Render all files directly into the global output directory"),
        ],
        default='SEPARATE',
        description="Determines how output files are organized in the global output directory"
    )
    
    global_output_path: bpy.props.StringProperty(
        name="Global Output",
        subtype='DIR_PATH',
        default="//render_cue_output/",
        description="Base directory for batch renders"
    )

    render_mode: bpy.props.EnumProperty(
        name="Render Mode",
        description="Choose between blocking foreground render or non-blocking background process",
        items=[
            ('FOREGROUND', "Foreground (Blocking)", "Render within the current Blender instance. Freezes UI."),
            ('BACKGROUND', "Background (Non-Blocking)", "Render in a separate process. Keeps UI responsive.")
        ],
        default='BACKGROUND'
    )
    
    presets_path: bpy.props.StringProperty(
        name="Presets Path",
        subtype='DIR_PATH',
        default="//presets/",
        description="Directory where render queue presets are saved and loaded from"
    )

    # VSE Integration
    vse_channel: bpy.props.IntProperty(
        name="VSE Channel",
        default=1,
        min=1,
        max=128,
        description="The Video Sequence Editor channel to use for syncing strips"
    )

    # Runtime State (Not saved)
    is_rendering: bpy.props.BoolProperty(
        name="Is Rendering",
        default=False,
        options={'SKIP_SAVE'}
    )
    
    current_job_index: bpy.props.IntProperty(
        name="Current Job Index",
        default=0,
        options={'SKIP_SAVE'}
    )
    
    total_jobs_count: bpy.props.IntProperty(
        name="Total Jobs",
        default=0,
        options={'SKIP_SAVE'}
    )
    
    progress_message: bpy.props.StringProperty(
        name="Progress Message",
        default="",
        options={'SKIP_SAVE'}
    )
    
    etr: bpy.props.StringProperty(
        name="Estimated Time Remaining",
        default="--:--",
        options={'SKIP_SAVE'}
    )
    
    start_time: bpy.props.FloatProperty(
        name="Start Time",
        default=0.0,
        options={'SKIP_SAVE'}
    )
    
    finished_frames_count: bpy.props.IntProperty(
        name="Finished Frames",
        default=0,
        options={'SKIP_SAVE'}
    )
    
    total_frames_to_render: bpy.props.IntProperty(
        name="Total Frames",
        default=0,
        options={'SKIP_SAVE'}
    )
    
    last_rendered_frame: bpy.props.StringProperty(
        name="Last Rendered Frame",
        subtype='FILE_PATH',
        default="",
        options={'SKIP_SAVE'}
    )
    
    preview_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Preview",
        options={'SKIP_SAVE'}
    )

def register():
    bpy.utils.register_class(RenderCueJob)
    bpy.utils.register_class(RenderCueSettings)
    # Store settings in Scene so they save with the .blend file
    # This makes the queue persistent across sessions
    bpy.types.Scene.rendercue = bpy.props.PointerProperty(type=RenderCueSettings)

def unregister():
    del bpy.types.Scene.rendercue
    bpy.utils.unregister_class(RenderCueSettings)
    bpy.utils.unregister_class(RenderCueJob)

