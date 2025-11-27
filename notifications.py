import requests
import json
import threading

def send_webhook(url, message, title="RenderCue Notification", color=0x00ff00):
    """
    Send a Discord/Slack compatible webhook.
    Runs in a separate thread to avoid blocking the UI.
    """
    if not url:
        return

    def _send():
        payload = {
            "username": "RenderCue Bot",
            "embeds": [{
                "title": title,
                "description": message,
                "color": color
            }]
        }
        
        # Slack compatibility (simple text)
        if "hooks.slack.com" in url:
            payload = {"text": f"*{title}*\n{message}"}

        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Failed to send webhook: {e}")

    thread = threading.Thread(target=_send)
    thread.start()

def show_toast(title, message):
    """
    Show a native Windows toast notification using PowerShell.
    """
    import subprocess
    
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
    
    def _run():
        try:
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Failed to show toast: {e}")

    threading.Thread(target=_run).start()
