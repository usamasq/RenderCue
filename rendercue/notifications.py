"""
RenderCue Notifications Module

This module handles user notifications via:
- Blender Info Area (Console)
- Native OS Toasts (Windows only)
- Webhooks (Discord/Slack)
"""

import json
import logging
import subprocess
import sys
import bpy

def send_webhook(url, message, title="RenderCue Notification", color=0x00ff00):
    """Send a Discord/Slack compatible webhook using a subprocess.

    This function runs asynchronously to avoid blocking the Blender UI.

    Args:
        url (str): The webhook URL.
        message (str): The message content.
        title (str, optional): The title of the embed. Defaults to "RenderCue Notification".
        color (int, optional): The color of the embed. Defaults to 0x00ff00 (Green).
    """
    if not url:
        return

    # Check for Online Access preference
    try:
        if not bpy.context.preferences.system.use_online_access:
            logging.getLogger("RenderCue").info("Online Access disabled in preferences. Skipping webhook.")
            return
    except AttributeError:
        # Older Blender versions may not have this attribute
        pass

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

url = {json.dumps(url)}
payload = {json.dumps(payload)}

try:
    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'RenderCue/1.0')
    data = json.dumps(payload).encode('utf-8')
    with urllib.request.urlopen(req, data=data, timeout=10) as response:
        pass
except Exception:
    pass
"""
    
    try:
        # Run asynchronously with Blender's Python environment
        # Use bpy.app.python_args to ensure compatibility with Blender's Python setup
        subprocess.Popen([sys.executable, *bpy.app.python_args, "-c", script])
    except (OSError, ValueError) as e:
        logging.getLogger("RenderCue").error(f"Failed to trigger webhook subprocess: {e}")

def show_notification(title, message):
    """Show a notification using the best available method for the platform.
    
    Falls back to Blender's info area if native notifications are unavailable.
    
    Args:
        title (str): The notification title.
        message (str): The notification message.
    """
    # Always show in Blender's info area (cross-platform fallback)
    _show_blender_notification(title, message)
    
    # Additionally, try to show native OS notification
    if sys.platform == 'win32':
        _show_windows_toast(title, message)
    # TODO: Add macOS and Linux support (see GitHub issue)

def _show_blender_notification(title, message):
    """Show notification in Blender's info area.
    
    Args:
        title (str): The notification title.
        message (str): The notification message.
    """
    try:
        # Format message for info area
        full_message = f"{title}: {message}"
        # Show in Blender's info panel
        # bpy.ops.wm.console_toggle()  # Removed disruptive toggle
        # bpy.ops.wm.console_toggle()  # Removed disruptive toggle
        # bpy.ops.wm.console_toggle()  # Removed disruptive toggle
        logging.getLogger("RenderCue").info(f"{full_message}")
    except (AttributeError, RuntimeError):
        # Fallback to simple print
        logging.getLogger("RenderCue").info(f"{title}: {message}")

def _show_windows_toast(title, message):
    """Show a native Windows toast notification using PowerShell.

    This function runs asynchronously and only works on Windows.
    PowerShell is included by default in Windows 10/11.

    Args:
        title (str): The title of the notification.
        message (str): The message content.
    """
    # Sanitize input to prevent PowerShell injection
    title = str(title).replace('"', '""').replace("'", "''")
    message = str(message).replace('"', '""').replace("'", "''")
    
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
        # Run asynchronously with no window
        subprocess.Popen(
            ["powershell", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
    except (OSError, ValueError, FileNotFoundError) as e:
        logging.getLogger("RenderCue").warning(f"Failed to show Windows toast notification: {e}")

# Backward compatibility alias
show_toast = show_notification
