import json
import subprocess
import sys
import bpy

def send_webhook(url, message, title="RenderCue Notification", color=0x00ff00):
    """
    Send a Discord/Slack compatible webhook using a subprocess to avoid blocking Blender.
    """
    if not url:
        return

    # Check for Online Access preference
    if not bpy.context.preferences.system.use_online_access:
        print("RenderCue: Online Access disabled in preferences. Skipping webhook.")
        return

    # Prepare payload
    payload = {
        "username": "RenderCue Bot",
        "embeds": [{
            "title": title,
            "description": message,
            "color": color
        }]
    }
    
    # Slack compatibility
    if "hooks.slack.com" in url:
        payload = {"text": f"*{title}*\n{message}"}

    # Create a small Python script to run in subprocess
    # We use sys.executable to ensure we use the same Python interpreter
    script = f"""
import urllib.request
import json
import sys

url = "{url}"
payload = {json.dumps(payload)}

try:
    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'RenderCue/1.0')
    data = json.dumps(payload).encode('utf-8')
    with urllib.request.urlopen(req, data=data) as response:
        pass
except Exception as e:
    pass
"""
    
    try:
        # Run asynchronously
        subprocess.Popen([sys.executable, "-c", script])
    except Exception as e:
        print(f"RenderCue: Failed to trigger webhook subprocess: {e}")

def show_toast(title, message):
    """
    Show a native Windows toast notification using PowerShell via subprocess.
    Only works on Windows.
    """
    if sys.platform != 'win32':
        return
        
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $textNodes = $template.GetElementsByTagName("text")
    $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
    $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("RenderCue")
    $notifier.Show($toast)
    """
    
    try:
        # Run asynchronously
        subprocess.Popen(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"RenderCue: Failed to show toast: {e}")

