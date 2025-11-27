import bpy
import requests
import threading

class RENDERCUE_OT_check_updates(bpy.types.Operator):
    bl_idname = "rendercue.check_updates"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for the latest release"
    
    def execute(self, context):
        self.report({'INFO'}, "Checking for updates...")
        
        try:
            repo_url = "https://api.github.com/repos/usamasq/RenderCue/releases/latest"
            response = requests.get(repo_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_version_str = data["tag_name"].lstrip('v')
                latest_version = tuple(map(int, latest_version_str.split('.')))
                
                # Get current version safely
                addon_name = __package__ if __package__ else "RenderCue"
                preferences = context.preferences.addons.get(addon_name)
                
                if preferences:
                    current_version = preferences.bl_info.get('version', (0, 0, 0))
                else:
                    current_version = (0, 0, 0)
                
                if latest_version > current_version:
                    self.report({'INFO'}, f"Update available: v{latest_version_str}")
                    bpy.ops.wm.url_open(url="https://github.com/usamasq/RenderCue/releases/latest")
                else:
                    self.report({'INFO'}, "RenderCue is up to date.")
            else:
                self.report({'WARNING'}, f"Check failed (Status {response.status_code})")
                
        except Exception as e:
            self.report({'ERROR'}, f"Update check failed: {str(e)}")

        return {'FINISHED'}

def register():
    bpy.utils.register_class(RENDERCUE_OT_check_updates)

def unregister():
    bpy.utils.unregister_class(RENDERCUE_OT_check_updates)
