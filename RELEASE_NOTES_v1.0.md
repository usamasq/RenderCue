# RenderCue v1.0 Release Notes

## 🎉 Major Features

### 1. ✅ Global Queue Architecture

**Access your queue from anywhere!**

- **Global Access**: The render queue is now accessible from **any scene** in your project. No need to switch scenes to check your job list.
- **Persistent Storage**: The queue is saved within your `.blend` file using a robust custom data block. It persists across sessions and reloads.

### 2. ✅ Background Rendering Only

**Streamlined for performance!**

- **Non-Blocking**: All renders are now performed in the background, keeping Blender responsive.
- **Live Progress**: Track job progress, frame counts, and ETR directly in the panel.
- **Live Preview**: See a thumbnail of the last rendered frame in real-time.
- **Controls**: Pause, Resume, and Stop renders at any time.

### 3. ✅ Desktop Notifications

**Get notified when your render is done!**

- **System Toasts**: Receive a native Windows notification when a batch render completes or fails.
- **Sound Alerts**: Optional sound notification on completion.
- **Webhooks**: Send completion status to a URL (e.g., Discord/Slack).

### 4. ✅ Status Bar Integration

**Monitor progress without the panel!**

- **Live Updates**: Render progress (Job X/Y, Frame %, ETR) is displayed directly in Blender's bottom status bar.
- **Always Visible**: Keep track of renders while working in other editors (Shading, Modeling, etc.).

---

## Core Features

### UI Improvements

- **Clean UI**: Removed "Animatable" indicators (yellow/green dots) from queue properties for a cleaner look.
- **Scene Switching**: Added a "Switch to Scene" button (View 3D icon) next to each job to instantly jump to that scene.
- **Clearer labels**: "Samples: 64" instead of "S:64".
- **Renderer names**: Shows "Cycles", "Eevee", or "Eevee Next".

### Better Defaults

- **Output Structure** default changed to **"Separate Folders"**.
- **Before**: All renders in same folder (confusing).
- **After**: Each scene gets its own subfolder (organized).

---

## Version History

### v1.0.0 (Initial Release)

- ✅ Global Queue (WindowManager based)
- ✅ Background Rendering (Pause/Resume/Stop)
- ✅ Desktop Notifications & Webhooks
- ✅ Status Bar Integration
- ✅ Addon preferences page
- ✅ Persistent storage (saves with .blend)
- ✅ SEPARATE folders default
- ✅ Blender 5.0 full compatibility
- ✅ Basic render queue
- ✅ Per-job overrides
- ✅ Batch rendering

---

## Quick Start

### Basic Workflow:

1. **Add scenes** → Click "Add Scene" or "Add All Scenes"
2. **Configure** → Set overrides (resolution, samples, etc.)
3. **Render** → Click "Render Cue" (Background)

---

## Compatibility

- ✅ Blender 4.2+
- ✅ Blender 5.0 (fully tested)
- ✅ Windows

---

## File Structure

- `preferences.py` - Addon settings page
- `notifications.py` - Notification utilities
- `core.py` - Persistence logic
- `render.py` - Background render logic
- `worker.py` - Background process script

---

## Known Limitations

1. **Appending**: Because the queue is global and stored in a custom text block, you cannot "Append" a render queue from another .blend file like a Scene.
