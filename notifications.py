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
