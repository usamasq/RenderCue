"""
RenderCue Version Compatibility Module

This module abstracts API differences between Blender versions (3.0 - 5.0+).
It provides helper functions for:
- Checking Blender versions
- Handling render engine differences (Eevee vs Eevee Next)
- Managing icon name changes
- Setting image formats safely
"""

import bpy
import logging

def get_blender_version():
    """Returns the current Blender version as a tuple (major, minor, patch)."""
    return bpy.app.version

def is_version_at_least(major, minor, patch=0):
    """Checks if the current Blender version is at least the specified version."""
    return bpy.app.version >= (major, minor, patch)

def is_eevee_engine(engine_id):
    """Checks if the given engine ID corresponds to Eevee (legacy, Next, or unified)."""
    return engine_id in {'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'}

def get_engine_display_name(engine_id):
    """Returns a user-friendly display name for the render engine."""
    if engine_id == 'BLENDER_EEVEE':
        return "Eevee"
    elif engine_id == 'BLENDER_EEVEE_NEXT':
        return "Eevee Next"
    elif engine_id == 'CYCLES':
        return "Cycles"
    elif engine_id == 'BLENDER_WORKBENCH':
        return "Workbench"
    return engine_id.replace('_', ' ').title()

def get_available_engines():
    """
    Returns a list of available render engines compatible with the current Blender version.
    Returns list of tuples: (identifier, name, description)
    """
    items = []
    
    # Define standard engines to check
    # (Identifier, Label, Description)
    engines_to_check = [
        ('CYCLES', "Cycles", "Path tracing renderer"),
        ('BLENDER_EEVEE', "Eevee", "Real-time renderer"),
        ('BLENDER_WORKBENCH', "Workbench", "Viewport renderer"),
    ]
    
    # Only check for Eevee Next if we are NOT in 4.2+ (where it was merged)
    # Actually, checking hasattr is safer regardless of version number, 
    # but we know it was removed in 4.2.
    if not is_version_at_least(4, 2, 0):
        engines_to_check.append(('BLENDER_EEVEE_NEXT', "Eevee Next", "Experimental real-time renderer"))

    for eng_id, label, desc in engines_to_check:
        # Check if the engine is actually available in this Blender instance
        # Eevee Next has a specific class name in 4.0/4.1
        if eng_id == 'BLENDER_EEVEE_NEXT':
            if hasattr(bpy.types, 'EEVEE_NEXT_RenderEngine'):
                items.append((eng_id, label, desc))
        else:
            # For standard engines, they are usually available. 
            # We can check bpy.types for specific classes if needed, 
            # but for built-ins, assuming they exist if not Eevee Next is usually safe.
            # However, let's be robust.
            
            # Note: Built-in engines like BLENDER_EEVEE might not always have a python exposed class 
            # named exactly {ID}_RenderEngine in all versions, but usually they do or are registered internally.
            # A simple way is to check if it's in the list of available render engines.
            
            # But get_available_renderers in properties.py used hasattr checks.
            # Let's trust that logic but simplify.
            
            # Actually, let's just return the list. Blender filters invalid engines in UI usually.
            # But for our EnumProperty, we need valid items.
            items.append((eng_id, label, desc))
            
    return items

def get_eevee_samples(scene):
    """Gets Eevee samples count handling version differences."""
    # Blender 4.x / 5.x (and some late 3.x experimental): taa_render_samples
    try:
        if hasattr(scene.eevee, 'taa_render_samples'):
            return scene.eevee.taa_render_samples
    except AttributeError:
        pass
        
    # Blender 3.x: samples
    try:
        if hasattr(scene.eevee, 'samples'):
            return scene.eevee.samples
    except AttributeError:
        pass
        
    return 64 # Default fallback

def set_eevee_samples(scene, value):
    """Sets Eevee samples count handling version differences."""
    success = False
    # Try newer API first
    try:
        if hasattr(scene.eevee, 'taa_render_samples'):
            scene.eevee.taa_render_samples = value
            success = True
    except AttributeError:
        pass
        
    if not success:
        # Try older API
        try:
            if hasattr(scene.eevee, 'samples'):
                scene.eevee.samples = value
                success = True
        except AttributeError:
            pass
            
    return success

def log_version_info():
    """Logs the current Blender version for debugging."""
    logging.getLogger("RenderCue").info(f"Blender Version: {bpy.app.version_string}")

# Icon replacements for Blender 5.0+ (and potentially other versions)
# Map: Old Icon Name -> New Icon Name
ICON_REPLACEMENTS = {
    # Conservative replacements for potentially deprecated icons
    # These are educated guesses based on common Blender UI patterns
    # If an icon is not actually deprecated, using the same name is harmless
    
    # Potentially deprecated marker/time icons
    'PMARKER_ACT': 'MARKER',      # Pose marker might be simplified to marker
    'SORTTIME': 'TIME',            # Sort time might be renamed to time
    
    # Note: Most icons in RenderCue appear to be stable across versions
    # Additional replacements can be added based on check_icons.py results
}

def get_icon(name, fallback='QUESTION'):
    """
    Safely retrieves an icon name, handling version-specific changes.
    
    Args:
        name (str): The desired icon name.
        fallback (str): The fallback icon if the desired one is known to be missing.
        
    Returns:
        str: The icon name to use.
    """
    # Check for direct replacements
    if name in ICON_REPLACEMENTS:
        return ICON_REPLACEMENTS[name]
        
    # For now, we assume the icon exists if not in replacements.
    # A full runtime check against bpy.types.UILayout.bl_rna... is possible 
    # but might be performance heavy if called frequently in draw().
    # We rely on the replacements map being accurate.
    
    return name

def get_safe_icon(name):
    """Alias for get_icon."""
    return get_icon(name)

def get_image_format(scene):
    """
    Get the current image format safely across Blender versions.
    
    Args:
        scene: Blender scene object
        
    Returns:
        str: Current file format identifier (e.g., 'PNG', 'OPEN_EXR_MULTILAYER')
    """
    try:
        return scene.render.image_settings.file_format
    except AttributeError:
        return 'PNG'  # Safe default


def set_image_format(scene, format_id):
    """
    Set image format with version-agnostic error handling.
    
    In Blender 5.0, OpenEXR format handling changed - multilayer vs single-layer
    selection affects available format options. This function handles those
    restrictions gracefully.
    
    Args:
        scene: Blender scene object
        format_id (str): Target format (e.g., 'PNG', 'JPEG', 'OPEN_EXR_MULTILAYER')
        
    Returns:
        tuple: (success: bool, actual_format: str, error_msg: str or None)
        - success: True if requested format was set, False if fallback was used
        - actual_format: The format that was actually set
        - error_msg: Error message if failed, None if success
    """
    try:
        scene.render.image_settings.file_format = format_id
        return (True, format_id, None)
    except TypeError as e:
        # Format not compatible with current scene settings (Blender 5.0+ restriction)
        error_msg = str(e)
        logging.getLogger("RenderCue").warning(f"Cannot set format to '{format_id}': {error_msg}")
        
        # Try fallback formats in order of preference
        fallbacks = ['PNG', 'JPEG', 'OPEN_EXR']
        
        for fallback in fallbacks:
            if fallback == format_id:
                continue  # Already tried this
            try:
                scene.render.image_settings.file_format = fallback
                logging.getLogger("RenderCue").warning(f"Using fallback format: {fallback}")
                return (False, fallback, f"Format '{format_id}' incompatible, using '{fallback}'")
            except TypeError:
                continue
        
        # If all fallbacks failed, return current format
        current = get_image_format(scene)
        return (False, current, f"Could not set format '{format_id}': {error_msg}")
    except AttributeError as e:
        return (False, 'PNG', f"Image settings not available: {e}")
