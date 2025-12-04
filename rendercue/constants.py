"""
Constants for RenderCue addon.
Centralizes filenames, status keys, manifest keys, and default values.
"""

# Filenames
MANIFEST_FILENAME = "rendercue_manifest.json"
STATUS_FILENAME = "rendercue_status.json"
PAUSE_SIGNAL_FILENAME = "rendercue_pause.signal"
PREVIEW_FILENAME_PREFIX = ".rendercue_preview_"
DEBUG_LOG_FILENAME = "worker_debug.log"

# Status Keys
STATUS_JOB_INDEX = "job_index"
STATUS_TOTAL_JOBS = "total_jobs"
STATUS_MESSAGE = "message"
STATUS_ETR = "etr"
STATUS_FINISHED = "finished"
STATUS_ERROR = "error"
STATUS_TIMESTAMP = "timestamp"
STATUS_FINISHED_FRAMES = "finished_frames"
STATUS_TOTAL_FRAMES = "total_frames"
STATUS_LAST_FRAME = "last_frame"
STATUS_PAUSED_DURATION = "paused_duration"
STATUS_JOB_STATUSES = "job_statuses"
STATUS_JOB_PROGRESS = "job_progress"
STATUS_JOB_TIMINGS = "job_timings"

# Defaults
DEFAULT_ETR = "--:--"
DEFAULT_PROGRESS_MESSAGE = "Rendering..."

# Manifest Keys
MANIFEST_JOBS = "jobs"
MANIFEST_GLOBAL_OUTPUT = "global_output_path"
MANIFEST_OUTPUT_LOCATION = "output_location"
MANIFEST_RENUMBER_OUTPUT = "renumber_output"

# Job Keys
JOB_SCENE_NAME = "scene_name"
JOB_FRAME_START = "frame_start"
JOB_FRAME_END = "frame_end"
JOB_OVERRIDE_FRAME_RANGE = "override_frame_range"
JOB_OVERRIDE_OUTPUT = "override_output"
JOB_OUTPUT_PATH = "output_path"
JOB_OVERRIDE_ENGINE = "override_engine"
JOB_RENDER_ENGINE = "render_engine"
JOB_OVERRIDE_VIEW_LAYER = "override_view_layer"
JOB_VIEW_LAYER = "view_layer"
JOB_OVERRIDE_RESOLUTION = "override_resolution"
JOB_RESOLUTION_SCALE = "resolution_scale"
JOB_OVERRIDE_FORMAT = "override_format"
JOB_RENDER_FORMAT = "render_format"
JOB_OVERRIDE_SAMPLES = "override_samples"
JOB_SAMPLES = "samples"

# New Overrides
JOB_OVERRIDE_CAMERA = "override_camera"
JOB_CAMERA = "camera"
JOB_OVERRIDE_FRAME_STEP = "override_frame_step"
JOB_FRAME_STEP = "frame_step"
JOB_OVERRIDE_TRANSPARENT = "override_transparent"
JOB_FILM_TRANSPARENT = "film_transparent"
JOB_OVERRIDE_COMPOSITOR = "override_compositor"
JOB_USE_COMPOSITOR = "use_compositor"
JOB_OVERRIDE_DENOISING = "override_denoising"
JOB_USE_DENOISING = "use_denoising"
JOB_OVERRIDE_DEVICE = "override_device"
JOB_DEVICE = "device"
JOB_OVERRIDE_TIME_LIMIT = "override_time_limit"
JOB_TIME_LIMIT = "time_limit"
JOB_OVERRIDE_PERSISTENT_DATA = "override_persistent_data"
JOB_USE_PERSISTENT_DATA = "use_persistent_data"

# UI Constants
UI_RESOLUTION_PERCENTAGE_BASE = 100
UI_BANNER_SCALE = 1.1
UI_SPACER_SCALE = 2.0
UI_QUEUE_PREVIEW_BEFORE = 5
UI_QUEUE_PREVIEW_AFTER = 4
UI_MAX_JOB_NAME_LENGTH = 18
UI_PREVIEW_COLLECTION_KEY = "main"

# Icon Mappings
UI_STATUS_ICONS = {
    'PENDING': 'SORTTIME',
    'RENDERING': 'RENDER_ANIMATION',
    'COMPLETED': 'CHECKMARK',
    'FAILED': 'ERROR',
    'CANCELLED': 'CANCEL',
}
