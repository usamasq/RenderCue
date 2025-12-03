import bpy

def update_frame_range(self, context):
    """Validate frame range to ensure start <= end."""
    if self.frame_end < self.frame_start:
        # If user moved start past end, push end
        if self.frame_start > self.frame_end: 
             self.frame_end = self.frame_start
        # If user moved end before start, push start (but this callback is on both)
        # It's tricky with one callback. Let's just enforce end >= start
        if self.frame_end < self.frame_start:
             self.frame_end = self.frame_start

# ==================== UPDATE CALLBACKS FOR DYNAMIC DEFAULTS ====================

def update_override_engine(self, context):
    if self.override_engine and self.scene:
        self.render_engine = self.scene.render.engine

def update_override_view_layer(self, context):
    if self.override_view_layer and self.scene and self.scene.view_layers:
        # Default to the first one as we can't know the "active" one easily from here
        self.view_layer = self.scene.view_layers[0].name

def update_override_camera(self, context):
    if self.override_camera and self.scene and self.scene.camera:
        self.camera = self.scene.camera

def update_override_frame_step(self, context):
    if self.override_frame_step and self.scene:
        self.frame_step = self.scene.frame_step

def update_override_transparent(self, context):
    if self.override_transparent and self.scene:
        self.film_transparent = self.scene.render.film_transparent

def update_override_compositor(self, context):
    if self.override_compositor and self.scene:
        self.use_compositor = self.scene.render.use_compositing

def update_override_frame_range(self, context):
    if self.override_frame_range and self.scene:
        self.frame_start = self.scene.frame_start
        self.frame_end = self.scene.frame_end

def update_override_resolution(self, context):
    if self.override_resolution and self.scene:
        self.resolution_scale = self.scene.render.resolution_percentage

def update_override_samples(self, context):
    if self.override_samples and self.scene:
        # Determine effective engine
        engine = self.scene.render.engine
        if self.override_engine:
            engine = self.render_engine
            
        if engine == 'CYCLES':
            self.samples = self.scene.cycles.samples
        elif engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
            try:
                self.samples = self.scene.eevee.taa_render_samples
            except AttributeError:
                try:
                    self.samples = self.scene.eevee.samples
                except AttributeError:
                    pass

def update_override_format(self, context):
    if self.override_format and self.scene:
        self.render_format = self.scene.render.image_settings.file_format

def update_override_denoising(self, context):
    if self.override_denoising and self.scene:
        # Only relevant for Cycles usually, but check effective engine
        engine = self.scene.render.engine
        if self.override_engine:
            engine = self.render_engine
            
        if engine == 'CYCLES':
            try:
                self.use_denoising = self.scene.cycles.use_denoising
            except AttributeError:
                pass

def update_override_device(self, context):
    if self.override_device and self.scene:
        engine = self.scene.render.engine
        if self.override_engine:
            engine = self.render_engine
            
        if engine == 'CYCLES':
            try:
                self.device = self.scene.cycles.device
            except AttributeError:
                pass

def update_override_time_limit(self, context):
    if self.override_time_limit and self.scene:
        engine = self.scene.render.engine
        if self.override_engine:
            engine = self.render_engine
            
        if engine == 'CYCLES':
            try:
                self.time_limit = self.scene.cycles.time_limit
            except AttributeError:
                pass

def update_override_persistent_data(self, context):
    if self.override_persistent_data and self.scene:
        # This is a general render setting but often associated with Cycles performance
        try:
            self.use_persistent_data = self.scene.render.use_persistent_data
        except AttributeError:
            pass

def get_available_renderers(self, context):
    """Dynamically enumerate all available render engines using robust detection."""
    items = []
    
    # Use __subclasses__ for efficient detection
    for engine in bpy.types.RenderEngine.__subclasses__():
        if hasattr(engine, 'bl_idname') and hasattr(engine, 'bl_label'):
            items.append((
                engine.bl_idname,
                engine.bl_label,
                f"Use {engine.bl_label}"
            ))
    
    # Ensure standard engines are present
    standard_engines = {
        'BLENDER_WORKBENCH': ("Workbench", "Workbench render engine"),
        'BLENDER_EEVEE': ("Eevee", "Eevee render engine"),
        'BLENDER_EEVEE_NEXT': ("Eevee Next", "Eevee Next render engine"),
        'CYCLES': ("Cycles", "Cycles render engine"),
    }
    
    existing_ids = {item[0] for item in items}
    for eng_id, (label, desc) in standard_engines.items():
        if eng_id not in existing_ids:
            # Check if engine exists in bpy.types (safer than iterating dir)
            if hasattr(bpy.types, f"{eng_id}_RenderEngine") or \
               (eng_id == 'BLENDER_EEVEE_NEXT' and hasattr(bpy.types, 'EEVEE_NEXT_RenderEngine')): # Handle naming variations if any
                items.append((eng_id, label, desc))
            # Fallback for standard engines that should be there
            elif eng_id in ['BLENDER_EEVEE', 'CYCLES', 'BLENDER_WORKBENCH']:
                 items.append((eng_id, label, desc))

    # Remove duplicates and sort
    items = list(set(items))
    items.sort(key=lambda x: x[1])
    
    return items

class RenderCueJob(bpy.types.PropertyGroup):
    """Property group defining a single render job."""
    scene: bpy.props.PointerProperty(
        type=bpy.types.Scene,
        name="Scene",
        description="The scene to be rendered in this job"
    )
    
    # Overrides
    override_engine: bpy.props.BoolProperty(
        name="Override Engine", 
        default=False,
        description="Use a specific render engine for this job",
        update=update_override_engine,
        options={'SKIP_SAVE'}
    )
    render_engine: bpy.props.EnumProperty(
        name="Engine",
        items=get_available_renderers,
        description="Render Engine to use",
        options={'SKIP_SAVE'}
    )
    
    override_view_layer: bpy.props.BoolProperty(
        name="Override View Layer", 
        default=False,
        description="Render only a specific view layer for this job",
        update=update_override_view_layer,
        options={'SKIP_SAVE'}
    )
    view_layer: bpy.props.StringProperty(
        name="View Layer",
        default="",
        description="Name of the View Layer to render (leave empty for active)",
        options={'SKIP_SAVE'}
    )

    # ==================== UNIVERSAL OVERRIDES ====================
    
    # Camera Override
    override_camera: bpy.props.BoolProperty(
        name="Override Camera",
        default=False,
        description="Use a specific camera for this job",
        update=update_override_camera,
        options={'SKIP_SAVE'}
    )
    camera: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Camera",
        description="Camera object to use for rendering",
        poll=lambda self, obj: obj.type == 'CAMERA' and (not self.scene or self.scene in obj.users_scene),
        options={'SKIP_SAVE'}
    )
    
    # Frame Step Override
    override_frame_step: bpy.props.BoolProperty(
        name="Override Frame Step",
        default=False,
        description="Render every Nth frame for this job",
        update=update_override_frame_step,
        options={'SKIP_SAVE'}
    )
    frame_step: bpy.props.IntProperty(
        name="Step",
        default=1,
        min=1,
        description="Number of frames to skip forward while rendering",
        options={'SKIP_SAVE'}
    )
    
    # Transparent Background Override
    override_transparent: bpy.props.BoolProperty(
        name="Override Transparency",
        default=False,
        description="Override transparent background setting",
        update=update_override_transparent,
        options={'SKIP_SAVE'}
    )
    film_transparent: bpy.props.BoolProperty(
        name="Transparent",
        default=False,
        description="World background is transparent, for compositing over another background",
        options={'SKIP_SAVE'}
    )

    # Compositor Override
    override_compositor: bpy.props.BoolProperty(
        name="Override Compositor",
        default=False,
        description="Enable/disable compositor for this job",
        update=update_override_compositor,
        options={'SKIP_SAVE'}
    )
    use_compositor: bpy.props.BoolProperty(
        name="Use Compositor",
        default=True,
        description="Enable/disable compositor nodes during rendering",
        options={'SKIP_SAVE'}
    )

    override_frame_range: bpy.props.BoolProperty(
        name="Override Frame Range", 
        default=False,
        description="Use a custom frame range for this job",
        update=update_override_frame_range,
        options={'SKIP_SAVE'}
    )
    frame_start: bpy.props.IntProperty(
        name="Start Frame", 
        default=1,
        min=0,
        soft_min=1,
        description="First frame to render",
        update=update_frame_range,
        options={'SKIP_SAVE'}
    )
    frame_end: bpy.props.IntProperty(
        name="End Frame", 
        default=250,
        min=0,
        soft_min=1,
        description="Last frame to render",
        update=update_frame_range,
        options={'SKIP_SAVE'}
    )
    
    override_output: bpy.props.BoolProperty(
        name="Override Output", 
        default=False,
        description="Save output to a custom location for this job",
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
        description="Use a custom resolution scale for this job",
        update=update_override_resolution,
        options={'SKIP_SAVE'}
    )
    resolution_scale: bpy.props.IntProperty(
        name="Scale %", 
        default=100, 
        min=1, 
        soft_max=200,
        max=10000,
        description="Resolution scale (100 = full size, 50 = half size)",
        options={'SKIP_SAVE'}
    )
    
    override_samples: bpy.props.BoolProperty(
        name="Override Samples", 
        default=False,
        description="Use a custom sample count for this job",
        update=update_override_samples,
        options={'SKIP_SAVE'}
    )
    samples: bpy.props.IntProperty(
        name="Samples", 
        default=128, 
        min=1,
        soft_max=4096,
        description="Render samples (higher = better quality but slower)",
        options={'SKIP_SAVE'}
    )
    
    # ==================== CYCLES-ONLY OVERRIDES ====================
    
    # Denoising Override
    override_denoising: bpy.props.BoolProperty(
        name="Override Denoising",
        default=False,
        description="Enable/disable denoising (Cycles only)",
        update=update_override_denoising,
        options={'SKIP_SAVE'}
    )
    use_denoising: bpy.props.BoolProperty(
        name="Denoising",
        default=True,
        description="Denoise the rendered image (may blur fine details)",
        options={'SKIP_SAVE'}
    )
    
    # Device Override
    override_device: bpy.props.BoolProperty(
        name="Override Device",
        default=False,
        description="Choose CPU or GPU rendering (Cycles only)",
        update=update_override_device,
        options={'SKIP_SAVE'}
    )
    device: bpy.props.EnumProperty(
        name="Device",
        items=[
            ('CPU', "CPU", "Render on CPU"),
            ('GPU', "GPU", "Render on GPU"),
        ],
        default='GPU',
        description="Device to use for rendering",
        options={'SKIP_SAVE'}
    )
    
    # Time Limit Override
    override_time_limit: bpy.props.BoolProperty(
        name="Override Time Limit",
        default=False,
        description="Set maximum render time per frame (Cycles only)",
        update=update_override_time_limit,
        options={'SKIP_SAVE'}
    )
    time_limit: bpy.props.FloatProperty(
        name="Time Limit",
        default=0.0,
        min=0.0,
        soft_max=3600.0,
        description="Time limit in seconds (0 = unlimited)",
        options={'SKIP_SAVE'}
    )
    
    # Persistent Data Override
    override_persistent_data: bpy.props.BoolProperty(
        name="Override Persistent Data",
        default=False,
        description="Keep scene data in memory between frames (Cycles only)",
        update=update_override_persistent_data,
        options={'SKIP_SAVE'}
    )
    use_persistent_data: bpy.props.BoolProperty(
        name="Persistent Data",
        default=False,
        description="Keep scene data in memory (faster, but may cause issues with changing topology)",
        options={'SKIP_SAVE'}
    )
    
    # UI State Properties
    ui_show_output: bpy.props.BoolProperty(
        name="Output Settings",
        default=True,
        description="Show output settings",
        options={'SKIP_SAVE'}
    )
    ui_show_dimensions: bpy.props.BoolProperty(
        name="Range & Resolution",
        default=True,
        description="Show range and resolution settings",
        options={'SKIP_SAVE'}
    )
    ui_show_format: bpy.props.BoolProperty(
        name="Format",
        default=True,
        description="Show format settings",
        options={'SKIP_SAVE'}
    )
    ui_show_render: bpy.props.BoolProperty(
        name="Render",
        default=True,
        description="Show render settings",
        options={'SKIP_SAVE'}
    )

    # Job status tracking
    render_status: bpy.props.EnumProperty(
        name="Render Status",
        items=[
            ('PENDING', "Pending", "Job has not started yet", 'RADIOBUT_OFF', 0),
            ('RENDERING', "Rendering", "Job is currently rendering", 'RESTRICT_RENDER_OFF', 1),
            ('COMPLETED', "Completed", "Job finished successfully", 'CHECKMARK', 2),
            ('FAILED', "Failed", "Job failed with an error", 'ERROR', 3),
            ('CANCELLED', "Cancelled", "Job was cancelled", 'PANEL_CLOSE', 4),
        ],
        default='PENDING',
        description="Current status of this render job",
        options={'SKIP_SAVE'}
    )

    completed_frames: bpy.props.IntProperty(
        name="Completed Frames",
        default=0,
        min=0,
        description="Number of frames completed for this job",
        options={'SKIP_SAVE'}
    )

    total_frames: bpy.props.IntProperty(
        name="Total Frames",
        default=0,
        min=0,
        description="Total frames in this job",
        options={'SKIP_SAVE'}
    )

    error_message: bpy.props.StringProperty(
        name="Error Message",
        default="",
        description="Error message if job failed",
        options={'SKIP_SAVE'}
    )

    start_time: bpy.props.FloatProperty(
        name="Start Time",
        default=0.0,
        description="Timestamp when job started rendering",
        options={'SKIP_SAVE'}
    )

    end_time: bpy.props.FloatProperty(
        name="End Time",
        default=0.0,
        description="Timestamp when job finished",
        options={'SKIP_SAVE'}
    )
    
    override_format: bpy.props.BoolProperty(
        name="Override Format", 
        default=False,
        description="Use a custom output format for this job",
        update=update_override_format,
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
    """Global settings and state for the RenderCue addon."""
    jobs: bpy.props.CollectionProperty(type=RenderCueJob, options={'SKIP_SAVE'})
    active_job_index: bpy.props.IntProperty(name="Active Job Index", default=0, options={'SKIP_SAVE'})
    
    # Dynamic key for preview collection to force UI updates
    preview_icon_key: bpy.props.StringProperty(
        name="Preview Icon Key",
        default="thumbnail",
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    output_location: bpy.props.EnumProperty(
        name="Output Location",
        items=[
            ('BLEND', "Same as Blend File", "Save renders in a subfolder next to the blend file"),
            ('CUSTOM', "Custom Directory", "Save renders to a specific custom directory"),
        ],
        default='BLEND',
        description="Where to save the rendered files",
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
    
    paused_duration: bpy.props.FloatProperty(
        name="Paused Duration",
        default=0.0,
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
    
    has_preview_image: bpy.props.BoolProperty(
        name="Has Preview",
        default=False,
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

    # Summary Banner Properties
    show_summary_banner: bpy.props.BoolProperty(
        name="Show Summary Banner",
        default=False,
        description="Show the render completion summary banner",
        options={'SKIP_SAVE'}
    )

    summary_session_id: bpy.props.StringProperty(
        name="Summary Session ID",
        default="",
        description="Unique ID for this render session",
        options={'SKIP_SAVE'}
    )

    summary_timestamp: bpy.props.FloatProperty(
        name="Summary Timestamp",
        default=0.0,
        description="When this summary was generated",
        options={'SKIP_SAVE'}
    )
    
    summary_auto_dismiss_seconds: bpy.props.IntProperty(
        name="Auto Dismiss After",
        default=0,
        min=0,
        max=3600,
        description="Automatically dismiss banner after this many seconds (0 = never)",
        options={'SKIP_SAVE'}
    )

    summary_total_jobs: bpy.props.IntProperty(name="Total Jobs", default=0, options={'SKIP_SAVE'})
    summary_successful_jobs: bpy.props.IntProperty(name="Successful Jobs", default=0, options={'SKIP_SAVE'})
    summary_failed_jobs: bpy.props.IntProperty(name="Failed Jobs", default=0, options={'SKIP_SAVE'})
    summary_total_frames: bpy.props.IntProperty(name="Total Frames Rendered", default=0, options={'SKIP_SAVE'})
    summary_render_time: bpy.props.StringProperty(name="Total Render Time", default="", options={'SKIP_SAVE'})
    summary_blend_file: bpy.props.StringProperty(name="Blend File", default="", options={'SKIP_SAVE'})

    # Queue Preview UI State
    show_queue_preview: bpy.props.BoolProperty(
        name="Show Queue Preview",
        default=True,
        description="Show mini queue status during rendering",
        options={'SKIP_SAVE'}
    )

    # UI State (Collapse/Expand)
    ui_show_output: bpy.props.BoolProperty(name="Show Output", default=True, options={'SKIP_SAVE'})
    ui_show_overrides_main: bpy.props.BoolProperty(name="Show Overrides", default=True, options={'SKIP_SAVE'})
    ui_show_dimensions: bpy.props.BoolProperty(name="Show Dimensions", default=False, options={'SKIP_SAVE'})
    ui_show_format: bpy.props.BoolProperty(name="Show Format", default=False, options={'SKIP_SAVE'})
    ui_show_render: bpy.props.BoolProperty(name="Show Render", default=False, options={'SKIP_SAVE'})
    
    ui_show_override_summary: bpy.props.BoolProperty(
        name="Show Override Summary",
        description="Display a summary of active overrides for the selected job",
        default=False,
        options={'SKIP_SAVE'}
    )

    show_preview_thumbnail: bpy.props.BoolProperty(
        name="Show Preview Thumbnail",
        default=True,
        description="Show last rendered frame thumbnail",
        options={'SKIP_SAVE'}
    )
        


def register():
    bpy.utils.register_class(RenderCueJob)
    bpy.utils.register_class(RenderCueSettings)
    
    # Store settings in WindowManager so they are global across scenes
    # We handle persistence manually via Text Block
    if not hasattr(bpy.types.WindowManager, "rendercue"):
        bpy.types.WindowManager.rendercue = bpy.props.PointerProperty(type=RenderCueSettings)

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

