"""Helper functions for RenderCue UI feedback."""
import bpy
import os
from . import version_compat

# =============================================================================
# OVERRIDE GROUPING & METADATA
# =============================================================================

OVERRIDE_GROUPS = [
    ('Render', ['engine', 'samples', 'device', 'denoising', 'time_limit', 'persistent_data']),
    ('Dimensions', ['frame_range', 'frame_step', 'resolution']),
    ('Output', ['output', 'format', 'transparent', 'compositor']),
    ('Scene', ['camera', 'view_layer']),
]

GROUP_ICONS = {
    'Render': 'SHADING_RENDERED',
    'Dimensions': 'ARROW_LEFTRIGHT',
    'Output': 'FILE_FOLDER',
    'Scene': 'SCENE_DATA',
}

# Metadata for each override type
# key: {display_name, bool_prop, val_prop, apply_type}
OVERRIDE_METADATA = {
    'engine': {
        'display': 'Engine', 
        'bool': 'override_engine', 
        'val': 'render_engine', 
        'apply': 'universal'
    },
    'samples': {
        'display': 'Samples', 
        'bool': 'override_samples', 
        'val': 'samples', 
        'apply': 'universal'
    },
    'device': {
        'display': 'Device', 
        'bool': 'override_device', 
        'val': 'device', 
        'apply': 'universal'
    },
    'denoising': {
        'display': 'Denoising', 
        'bool': 'override_denoising', 
        'val': 'use_denoising', 
        'apply': 'universal'
    },
    'time_limit': {
        'display': 'Time Limit', 
        'bool': 'override_time_limit', 
        'val': 'time_limit', 
        'apply': 'universal'
    },
    'persistent_data': {
        'display': 'Persistent Data', 
        'bool': 'override_persistent_data', 
        'val': 'use_persistent_data', 
        'apply': 'universal'
    },
    'frame_range': {
        'display': 'Frame Range', 
        'bool': 'override_frame_range', 
        'val': 'frame_range', # Special handling in operator
        'apply': 'universal'
    },
    'frame_step': {
        'display': 'Frame Step', 
        'bool': 'override_frame_step', 
        'val': 'frame_step', 
        'apply': 'universal'
    },
    'resolution': {
        'display': 'Resolution', 
        'bool': 'override_resolution', 
        'val': 'resolution_scale', 
        'apply': 'universal'
    },
    'output': {
        'display': 'Output', 
        'bool': 'override_output', 
        'val': 'output_path', # Special handling
        'apply': 'warn'
    },
    'format': {
        'display': 'Format', 
        'bool': 'override_format', 
        'val': 'render_format', 
        'apply': 'universal'
    },
    'transparent': {
        'display': 'Transparent', 
        'bool': 'override_transparent', 
        'val': 'film_transparent', 
        'apply': 'universal'
    },
    'compositor': {
        'display': 'Compositor', 
        'bool': 'override_compositor', 
        'val': 'use_compositor', 
        'apply': 'universal'
    },
    'camera': {
        'display': 'Camera', 
        'bool': 'override_camera', 
        'val': 'camera', 
        'apply': 'smart_camera'
    },
    'view_layer': {
        'display': 'View Layer', 
        'bool': 'override_view_layer', 
        'val': 'view_layer', 
        'apply': 'smart_view_layer'
    },
}

def get_applicable_jobs_count(context, override_key, source_job):
    """Calculate how many jobs can accept this override.
    
    Returns:
        tuple: (applicable_count, total_count)
    """
    settings = context.window_manager.rendercue
    all_jobs = settings.jobs
    total = len(all_jobs)
    
    if total <= 1:
        return 0, total # No other jobs to apply to
        
    meta = OVERRIDE_METADATA.get(override_key)
    if not meta:
        return 0, total
        
    apply_type = meta['apply']
    
    if apply_type == 'universal' or apply_type == 'warn':
        return total, total
        
    applicable = 0
    
    if apply_type == 'smart_camera':
        if not source_job.camera:
            return 0, total
        target_name = source_job.camera.name
        for job in all_jobs:
            if job.scene and target_name in job.scene.objects:
                applicable += 1
                
    elif apply_type == 'smart_view_layer':
        target_vl = source_job.view_layer
        for job in all_jobs:
            if job.scene and target_vl in [vl.name for vl in job.scene.view_layers]:
                applicable += 1
                
    return applicable, total

def get_override_summary(context, job):
    """Get summary of active overrides for a job, grouped by category.
    
    Returns:
        dict: {
            'count': int,
            'groups': list[dict] # List of groups with overrides
        }
    """
    if not job:
        return {'count': 0, 'groups': []}
    
    active_count = 0
    groups_data = []
    
    for group_name, override_keys in OVERRIDE_GROUPS:
        group_overrides = []
        
        for key in override_keys:
            meta = OVERRIDE_METADATA.get(key)
            if not meta:
                continue
                
            # Check if override is active
            is_active = getattr(job, meta['bool'])
            if not is_active:
                continue
                
            # Get value string
            value_str = ""
            if key == 'engine':
                # Use version_compat for friendly engine names
                val = getattr(job, meta['val'])
                value_str = version_compat.get_engine_display_name(val)
            elif key == 'format':
                # Use RNA enum definition for friendly format names
                val = getattr(job, meta['val'])
                try:
                    # Access the EnumProperty definition to get the display name
                    value_str = job.bl_rna.properties[meta['val']].enum_items[val].name
                except (KeyError, AttributeError):
                    value_str = str(val)
            elif key == 'frame_range':
                value_str = f"{job.frame_start}-{job.frame_end}"
            elif key == 'frame_step':
                # Smart Frame Step: Show output count
                frame_range = job.frame_end - job.frame_start
                # Avoid division by zero if step is invalid (though min is 1)
                step = max(1, job.frame_step)
                output_count = (frame_range // step) + 1
                value_str = f"{job.frame_step} ({output_count} frames)"
            elif key == 'resolution':
                value_str = f"{job.resolution_scale}%"
            elif key == 'camera':
                value_str = job.camera.name if job.camera else "None"
            elif key == 'transparent':
                value_str = 'Yes' if job.film_transparent else 'No'
            elif key == 'compositor':
                value_str = 'Yes' if job.use_compositor else 'No'
            elif key == 'denoising':
                value_str = 'Yes' if job.use_denoising else 'No'
            elif key == 'persistent_data':
                value_str = 'Yes' if job.use_persistent_data else 'No'
            elif key == 'time_limit':
                value_str = f"{job.time_limit}s"
            elif key == 'output':
                value_str = 'Custom'
            else:
                # Default: get value from property
                val = getattr(job, meta['val'])
                value_str = str(val)
            
            # Calculate Apply to All stats
            applicable, total = get_applicable_jobs_count(context, key, job)
            
            group_overrides.append({
                'key': key,
                'display_name': meta['display'],
                'value': value_str,
                'bool_prop': meta['bool'],
                'val_prop': meta['val'],
                'apply_stats': (applicable, total),
                'can_apply': applicable > 0
            })
            active_count += 1
            
        if group_overrides:
            groups_data.append({
                'name': group_name,
                'icon': GROUP_ICONS.get(group_name, 'NONE'),
                'overrides': group_overrides
            })
    
    return {'count': active_count, 'groups': groups_data}

def get_scene_statistics(context):
    """Calculate scene availability and queue health statistics.
    
    Returns:
        dict: {
            'total': int,              # Total scenes in file
            'with_cameras': int,       # Scenes that have a camera
            'available': int,          # Scenes that can be added to queue
            'in_queue': int,           # Scenes already in queue
            'invalid_jobs': int,       # Jobs missing camera
            'invalid_job_names': list  # Names of invalid jobs
        }
    """
    settings = context.window_manager.rendercue
    existing_scenes = {job.scene for job in settings.jobs if job.scene}
    
    total = len(bpy.data.scenes)
    with_cameras = sum(1 for s in bpy.data.scenes if s.camera)
    available = sum(
        1 for s in bpy.data.scenes 
        if s not in existing_scenes and s.camera
    )
    in_queue = len(existing_scenes)
    
    # Check for invalid jobs in queue (no camera)
    invalid_job_names = []
    for job in settings.jobs:
        if job.scene:
            # Job is valid if: scene has camera OR job has camera override
            has_camera = job.scene.camera is not None
            has_override = job.override_camera and job.camera is not None
            if not has_camera and not has_override:
                invalid_job_names.append(job.scene.name)
    
    return {
        'total': total,
        'with_cameras': with_cameras,
        'available': available,
        'in_queue': in_queue,
        'invalid_jobs': len(invalid_job_names),
        'invalid_job_names': invalid_job_names
    }

def get_queue_validation_summary(context):
    """Run lightweight validation for UI display.
    
    This is a SUBSET of full validation for performance.
    Use validate_queue operator for complete checks.
    
    Returns:
        dict: {
            'errors': list[str],      # Critical issues
            'warnings': list[str],    # Non-blocking issues
            'is_valid': bool         # True if no errors
        }
    """
    settings = context.window_manager.rendercue
    errors = []
    warnings = []
    
    # Quick queue check
    if not settings.jobs:
        errors.append("Queue is empty")
        return {'errors': errors, 'warnings': warnings, 'is_valid': False}

    # Check File Status
    if not bpy.data.filepath:
        errors.append("File not saved (save to render)")
    elif bpy.data.is_dirty:
        warnings.append("Unsaved changes (save before rendering)")
    
    # Check each job (lightweight checks only)
    for i, job in enumerate(settings.jobs):
        job_num = i + 1
        
        # Critical: missing scene/camera
        if not job.scene:
            errors.append(f"Job {job_num}: No scene")
        elif not job.scene.camera and not job.override_camera:
            errors.append(f"Job {job_num}: No camera")
        
        # Warning: override issues
        if job.override_camera and job.camera and job.scene:
            if job.camera.name not in job.scene.objects:
                warnings.append(f"Job {job_num}: Camera not in scene")
        
        if job.override_view_layer and job.view_layer and job.scene:
            if job.view_layer not in [vl.name for vl in job.scene.view_layers]:
                warnings.append(f"Job {job_num}: Invalid view layer")
    
    is_valid = len(errors) == 0
    return {'errors': errors, 'warnings': warnings, 'is_valid': is_valid}

def get_mixed_engine_warning(settings):
    """Check if queue has mixed render engines.
    
    Returns:
        str or None: Warning message if mixed engines detected
    """
    if not settings.jobs:
        return None
    
    engines = set()
    for job in settings.jobs:
        if job.scene:
            engine = job.render_engine if job.override_engine else job.scene.render.engine
            engines.add(engine)
    
    if len(engines) > 1:
        return f"Queue uses {len(engines)} different engines"
    
    return None

def validate_queue_for_render(context):
    """Run comprehensive validation checks and return warnings and errors.
    
    Returns:
        tuple: (warnings: list[str], errors: list[str])
    """
    settings = context.window_manager.rendercue
    errors = []
    warnings = []
    
    # Check File Status
    if not bpy.data.filepath:
        errors.append("Blender file has not been saved. Please save first.")
    elif bpy.data.is_dirty:
        warnings.append("File has unsaved changes. It will be saved automatically.")

    # Check Output Path
    if not settings.global_output_path:
        errors.append("Global Output Path is empty")
    else:
        path = bpy.path.abspath(settings.global_output_path)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError:
                errors.append(f"Cannot create output directory: {path}")
    
    # Check Jobs
    if not settings.jobs:
        errors.append("Queue is empty")
        
    for i, job in enumerate(settings.jobs):
        job_num = i + 1
        
        if not job.scene:
            errors.append(f"Job {job_num}: No scene assigned")
        elif not job.scene.camera:
            errors.append(f"Job {job_num} ({job.scene.name}): No active camera")
        
        # Validate Overrides
        if job.override_camera:
            if not job.camera:
                errors.append(f"Job {job_num}: Camera override enabled but no camera selected")
            elif job.camera.name not in bpy.data.objects:
                 errors.append(f"Job {job_num}: Overridden camera '{job.camera.name}' not found")
        
        if job.override_frame_step:
            if job.frame_step < 1:
                errors.append(f"Job {job_num}: Frame step must be at least 1")
            elif job.frame_step > (job.frame_end - job.frame_start + 1):
                 errors.append(f"Job {job_num}: Frame step ({job.frame_step}) is larger than frame range")

        if job.override_device and job.device == 'GPU':
            try:
                preferences = context.preferences.addons['cycles'].preferences
                has_devices = False
                for device_type in preferences.get_device_types(context):
                    preferences.get_devices_for_type(device_type[0])
                    if preferences.devices:
                         has_devices = True
                         break
                if not has_devices:
                     errors.append(f"Job {job_num}: GPU override selected but no GPU devices found")
            except:
                pass 

        # Validate Camera Linkage
        if job.override_camera and job.camera and job.scene:
            if job.camera.name not in job.scene.objects:
                errors.append(f"Job {job_num}: Camera '{job.camera.name}' is not linked to scene '{job.scene.name}'")

        # Validate View Layer
        if job.override_view_layer and job.view_layer and job.scene:
            if job.view_layer not in [vl.name for vl in job.scene.view_layers]:
                errors.append(f"Job {job_num}: View layer '{job.view_layer}' not found in scene '{job.scene.name}'")

        # Warn about extreme resolutions
        if job.override_resolution:
            res_x = job.scene.render.resolution_x if job.scene else 1920
            res_y = job.scene.render.resolution_y if job.scene else 1080
            final_x = int(res_x * job.resolution_scale / 100)
            final_y = int(res_y * job.resolution_scale / 100)
            
            if final_x > 8192 or final_y > 8192:
                warnings.append(f"Job {job_num}: Resolution {final_x}x{final_y} exceeds 8K")
            
    return warnings, errors

def get_job_confirmation_details(job):
    """Get comprehensive summary of a job for confirmation dialog."""
    if not job.scene:
        return {'scene_name': "Invalid Job", 'is_valid': False}
        
    # Helper for formatting
    def fmt(base, override, is_active):
        return f"{base} -> {override}" if is_active else str(base)

    # Camera
    scene_cam = job.scene.camera.name if job.scene.camera else "None"
    job_cam = job.camera.name if job.camera else "None"
    camera_display = fmt(scene_cam, job_cam, job.override_camera)
        
    # Resolution
    res_x = job.scene.render.resolution_x
    res_y = job.scene.render.resolution_y
    base_scale = job.scene.render.resolution_percentage
    
    base_x = int(res_x * base_scale / 100)
    base_y = int(res_y * base_scale / 100)
    base_res = f"{base_x}x{base_y} ({base_scale}%)"
    
    final_scale = job.resolution_scale if job.override_resolution else base_scale
    final_x = int(res_x * final_scale / 100)
    final_y = int(res_y * final_scale / 100)
    final_res = f"{final_x}x{final_y} ({final_scale}%)"
    
    res_display = fmt(base_res, final_res, job.override_resolution)
    
    # Engine
    base_engine = version_compat.get_engine_display_name(job.scene.render.engine)
    job_engine = version_compat.get_engine_display_name(job.render_engine)
    engine_display = fmt(base_engine, job_engine, job.override_engine)
    
    # Frame Range
    base_start = job.scene.frame_start
    base_end = job.scene.frame_end
    base_range = f"{base_start}-{base_end}"
    
    job_range = f"{job.frame_start}-{job.frame_end}"
    range_display = fmt(base_range, job_range, job.override_frame_range)
    
    # Frame Count (Calculated)
    # Use scene defaults when override is disabled
    if job.override_frame_range:
        start = job.frame_start
        end = job.frame_end
    else:
        start = job.scene.frame_start
        end = job.scene.frame_end
    
    step = job.frame_step if job.override_frame_step else job.scene.frame_step
    count = max(0, (end - start) // max(1, step) + 1)
    frames_display = f"{count} frames"
    if step > 1:
        frames_display += f" (step {step})"

    # Collect all active overrides for display
    overrides = []
    if job.override_output: overrides.append("Output")
    if job.override_camera: overrides.append("Camera")
    if job.override_resolution: overrides.append("Resolution")
    if job.override_frame_range: overrides.append("Range")
    if job.override_engine: overrides.append("Engine")
    if job.override_samples: overrides.append("Samples")
    if job.override_device: overrides.append("Device")
    if job.override_view_layer: overrides.append("View Layer")
    
    return {
        'scene_name': job.scene.name,
        'camera_display': camera_display,
        'resolution_display': res_display,
        'engine_display': engine_display,
        'range_display': range_display,
        'frames_display': frames_display,
        'overrides_count': len(overrides),
        'override_names': overrides,
        'has_overrides': len(overrides) > 0,
        'is_valid': True
    }

def get_queue_summary(context):
    """Get queue summary statistics."""
    settings = context.window_manager.rendercue
    
    total_jobs = len(settings.jobs)
    total_frames = 0
    
    for job in settings.jobs:
        if job.scene:
            # Use scene defaults when override is disabled
            if job.override_frame_range:
                start = job.frame_start
                end = job.frame_end
            else:
                start = job.scene.frame_start
                end = job.scene.frame_end
            
            step = job.frame_step if job.override_frame_step else job.scene.frame_step
            count = max(0, (end - start) // max(1, step) + 1)
            total_frames += count
            
    is_saved = bool(bpy.data.filepath)
    is_dirty = bpy.data.is_dirty
    
    return {
        'total_jobs': total_jobs,
        'total_frames': total_frames,
        'is_saved': is_saved,
        'is_dirty': is_dirty,
        'filename': os.path.basename(bpy.data.filepath) if is_saved else "Untitled.blend"
    }
