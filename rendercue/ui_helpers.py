"""Helper functions for RenderCue UI feedback."""
import bpy

def get_scene_statistics(context):
    """Calculate scene availability statistics.
    
    Returns:
        dict: {
            'total': int,           # Total scenes in file
            'with_cameras': int,    # Scenes that have a camera
            'available': int,       # Scenes that can be added to queue
            'in_queue': int        # Scenes already in queue
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
    
    return {
        'total': total,
        'with_cameras': with_cameras,
        'available': available,
        'in_queue': in_queue
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

def get_override_summary(job):
    """Get summary of active overrides for a job.
    
    Returns:
        dict: {
            'count': int,
            'overrides': list[tuple[str, str]]  # (name, value) pairs
        }
    """
    if not job:
        return {'count': 0, 'overrides': []}
    
    active = []
    
    # Collect all active overrides
    if job.override_frame_range:
        active.append(('Frame Range', f"{job.frame_start}-{job.frame_end}"))
    if job.override_frame_step:
        active.append(('Frame Step', str(job.frame_step)))
    if job.override_camera and job.camera:
        active.append(('Camera', job.camera.name))
    if job.override_resolution:
        active.append(('Resolution', f"{job.resolution_scale}%"))
    if job.override_samples:
        active.append(('Samples', str(job.samples)))
    if job.override_engine:
        active.append(('Engine', job.render_engine))
    if job.override_view_layer:
        active.append(('View Layer', job.view_layer))
    if job.override_format:
        active.append(('Format', job.render_format))
    if job.override_output:
        active.append(('Output', 'Custom'))
    if job.override_transparent:
        active.append(('Transparent', 'Yes' if job.film_transparent else 'No'))
    if job.override_compositor:
        active.append(('Compositor', 'Yes' if job.use_compositor else 'No'))
    if job.override_denoising:
        active.append(('Denoising', 'Yes' if job.use_denoising else 'No'))
    if job.override_device:
        active.append(('Device', job.device))
    if job.override_time_limit and job.time_limit > 0:
        active.append(('Time Limit', f"{job.time_limit}s"))
    if job.override_persistent_data:
        active.append(('Persistent Data', 'Yes' if job.use_persistent_data else 'No'))
    
    
    return {'count': len(active), 'overrides': active}

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
        engine_list = ', '.join(sorted(engines))
        return f"Queue uses {len(engines)} engines: {engine_list}"
    
    return None
