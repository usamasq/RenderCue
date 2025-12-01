"""
RenderCue Background Worker Entry Point

This script is executed by Blender in background mode (-b -P worker.py)
to process the render queue independently of the main UI thread.

Note: When run with -P flag, Python doesn't treat this as a package module,
so we must use absolute imports with sys.path manipulation.
"""

import sys
import os

# Add parent directory to sys.path to enable absolute imports
# This is necessary because -P flag runs the script as __main__
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Use dynamic import based on actual package name (supports folder renaming)
import importlib
package_name = os.path.basename(script_dir)
core_module = importlib.import_module(f"{package_name}.core")
BackgroundWorker = core_module.BackgroundWorker

def main():
    """Parse arguments and execute the background worker."""
    argv = sys.argv
    if "--" not in argv:
        print("RenderCue Worker: No arguments passed")
        return
    
    args = argv[argv.index("--") + 1:]
    
    try:
        manifest_path = args[args.index("--manifest") + 1]
        status_path = args[args.index("--status") + 1]
    except (ValueError, IndexError):
        print("RenderCue Worker: Missing required arguments (--manifest, --status)")
        return
        
    worker = BackgroundWorker(manifest_path, status_path)
    worker.run()

if __name__ == "__main__":
    main()
