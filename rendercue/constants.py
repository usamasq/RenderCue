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

# Defaults
DEFAULT_ETR = "--:--"
DEFAULT_PROGRESS_MESSAGE = "Rendering..."

# Manifest Keys
MANIFEST_JOBS = "jobs"
MANIFEST_GLOBAL_OUTPUT = "global_output_path"
MANIFEST_OUTPUT_LOCATION = "output_location"

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
