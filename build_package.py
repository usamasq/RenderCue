import zipfile
import os
import re

def get_version():
    """Extract version from __init__.py"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "__init__.py"), 'r') as f:
            content = f.read()
            match = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', content)
            if match:
                return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    except Exception as e:
        print(f"Error reading version: {e}")
    return "1.0.0"

def create_package():
    version = get_version()
    zip_filename = f"RenderCue_v{version}.zip"
    source_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Packaging RenderCue v{version}...")
    
    # Files/Folders to exclude
    excludes = {
        '__pycache__', '.git', '.vscode', '.idea', 
        'build', 'dist', 'artifacts', 
        zip_filename, os.path.basename(__file__),
        'task.md', 'audit_report.md', 'implementation_plan.md', 
        'walkthrough.md', 'suggestions.md'
    }
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in excludes]
            
            for file in files:
                if file in excludes or file.endswith('.zip'):
                    continue
                    
                file_path = os.path.join(root, file)
                
                # Create archive path (RenderCue/relative/path/to/file)
                rel_path = os.path.relpath(file_path, source_dir)
                arcname = os.path.join("RenderCue", rel_path)
                
                print(f"Adding: {rel_path}")
                zipf.write(file_path, arcname)
                
    print(f"\nSuccess! Created {zip_filename}")
    print("Upload this file to your GitHub Release.")

if __name__ == "__main__":
    create_package()
