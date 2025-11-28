import bpy

class RenderCueJob(bpy.types.PropertyGroup):
    scene: bpy.props.PointerProperty(
        type=bpy.types.Scene,
        name="Scene",
        description="The scene to be rendered in this job"
    )
    
    # Overrides
    override_engine: bpy.props.BoolProperty(
        name="Override Engine", 
        default=False,
        description="Enable to render with a specific engine",
        options={'SKIP_SAVE'}
    )
    render_engine: bpy.props.EnumProperty(
        name="Engine",
        items=[
            ('CYCLES', "Cycles", "Cycles Render Engine"),
            ('BLENDER_EEVEE', "Eevee", "Eevee Render Engine"),
        ],
        default='CYCLES',
        description="Render Engine to use",
        options={'SKIP_SAVE'}
    )
    
    override_view_layer: bpy.props.BoolProperty(
        name="Override View Layer", 
        default=False,
        description="Enable to render a specific view layer",
        options={'SKIP_SAVE'}
    )
    view_layer: bpy.props.StringProperty(
        name="View Layer",
        default="",
        description="Name of the View Layer to render (leave empty for active)",
        options={'SKIP_SAVE'}
    )

    override_frame_range: bpy.props.BoolProperty(
        name="Override Frame Range", 
        default=False,
        description="Enable to render a custom frame range instead of the scene's default range",
        options={'SKIP_SAVE'}
    )
    frame_start: bpy.props.IntProperty(
        name="Start Frame", 
        default=1,
        description="First frame to render for this job",
        options={'SKIP_SAVE'}
    )
    frame_end: bpy.props.IntProperty(
        name="End Frame", 
        default=250,
        description="Last frame to render for this job",
        options={'SKIP_SAVE'}
    )
    
    override_output: bpy.props.BoolProperty(
        name="Override Output", 
        default=False,
        description="Enable to save this job's output to a custom location",
        options={'SKIP_SAVE'}
    )
    output_path: bpy.props.StringProperty(
        name="Output Path", 
        # subtype='DIR_PATH', # Removed to prevent red highlight
        default="//",
        description="Custom output directory for this job",
        options={'SKIP_SAVE'}
    )
    
    override_resolution: bpy.props.BoolProperty(
        name="Override Resolution", 
        default=False,
        description="Enable to scale the render resolution",
        options={'SKIP_SAVE'}
    )
    resolution_scale: bpy.props.IntProperty(
        name="Scale %", 
        default=100, 
        min=1, 
        max=200,
        description="Percentage of the scene's resolution to render (e.g., 50% for half size)",
        options={'SKIP_SAVE'}
    )
    
    override_samples: bpy.props.BoolProperty(
        name="Override Samples", 
        default=False,
        description="Enable to set a custom sample count for Cycles/Eevee",
        options={'SKIP_SAVE'}
    )
    samples: bpy.props.IntProperty(
        name="Samples", 
        default=128, 
        min=1,
        description="Number of samples to use for rendering (higher = better quality, slower)",
        options={'SKIP_SAVE'}
    )
    
    override_format: bpy.props.BoolProperty(
        name="Override Format", 
        default=False,
        description="Enable to change the output file format",
        options={'SKIP_SAVE'}
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
        description="File format for the rendered output",
        options={'SKIP_SAVE'}
    )

class RenderCueSettings(bpy.types.PropertyGroup):
    jobs: bpy.props.CollectionProperty(type=RenderCueJob, options={'SKIP_SAVE'})
    active_job_index: bpy.props.IntProperty(name="Active Job Index", default=0, options={'SKIP_SAVE'})
    
    output_structure: bpy.props.EnumProperty(
        name="Output Structure",
        items=[
            ('SEPARATE', "Separate Folders", "Create a subfolder for each scene (e.g. /output/SceneName/)"),
            ('SAME', "Same Folder", "Render all files directly into the global output directory"),
        ],
        default='SEPARATE',
        description="Determines how output files are organized in the global output directory",
        options={'SKIP_SAVE'}
    )
    
    global_output_path: bpy.props.StringProperty(
        name="Global Output",
        # subtype='DIR_PATH', # Removed to prevent red highlight
        default="//render_cue_output/",
        description="Base directory for batch renders",
        options={'SKIP_SAVE'}
    )


    
    presets_path: bpy.props.StringProperty(
        name="Presets Path",
        subtype='DIR_PATH',
        default="//presets/",
        description="Directory where render queue presets are saved and loaded from",
        options={'SKIP_SAVE'}
    )

    presets_path: bpy.props.StringProperty(
        name="Presets Path",
        subtype='DIR_PATH',
        default="//presets/",
        description="Directory where render queue presets are saved and loaded from",
        options={'SKIP_SAVE'}
    )

    # Runtime State (Not saved)
    is_rendering: bpy.props.BoolProperty(
        name="Is Rendering",
        default=False,
        options={'SKIP_SAVE'}
    )

    is_paused: bpy.props.BoolProperty(
        name="Is Paused",
        default=False,
        options={'SKIP_SAVE'}
    )

    stop_requested: bpy.props.BoolProperty(
        name="Stop Requested",
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
    


    last_render_status: bpy.props.EnumProperty(
        name="Last Render Status",
        items=[
            ('NONE', "None", ""),
            ('SUCCESS', "Success", ""),
            ('FAILED', "Failed", ""),
            ('CANCELLED', "Cancelled", "")
        ],
        default='NONE',
        options={'SKIP_SAVE'}
    )

    last_render_message: bpy.props.StringProperty(
        name="Last Render Message",
        default="",
        options={'SKIP_SAVE'}
    )

def register():
    try:
        bpy.utils.register_class(RenderCueJob)
    except ValueError:
        pass
        
    try:
        bpy.utils.register_class(RenderCueSettings)
    except ValueError:
        pass
        
    # Store settings in WindowManager so they are global across scenes
    # We handle persistence manually via Text Block
    try:
        bpy.types.WindowManager.rendercue = bpy.props.PointerProperty(type=RenderCueSettings)
    except Exception:
        pass

def unregister():
    try:
        del bpy.types.WindowManager.rendercue
    except AttributeError:
        pass
        
    try:
        bpy.utils.unregister_class(RenderCueSettings)
    except RuntimeError:
        pass
        
    try:
        bpy.utils.unregister_class(RenderCueJob)
    except RuntimeError:
        pass

