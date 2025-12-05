# RenderCue Architecture

This document provides a high-level overview of the RenderCue codebase to help new contributors understand how the addon is structured.

## 📂 Module Overview

The addon is organized into the following modules within the `rendercue/` package:

| Module              | Responsibility                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------- |
| `__init__.py`       | Entry point. Handles registration/unregistration of all other modules.                                                               |
| `core.py`           | **The Brain**. Contains the `BackgroundWorker` class (runs renders), `StateManager` (saves/loads queue), and logging infrastructure. |
| `properties.py`     | **Data Models**. Defines Blender `PropertyGroup` classes (`RenderCueJob`, `RenderCueSettings`) that store all addon data.            |
| `operators.py`      | **Actions**. Defines `bpy.types.Operator` classes for user interactions (Add Scene, Render, etc.).                                   |
| `ui.py`             | **Interface**. Defines `bpy.types.Panel` classes and the drawing logic for the UI.                                                   |
| `ui_helpers.py`     | **UI Utilities**. Reusable functions for drawing common UI elements (icons, headers).                                                |
| `render.py`         | **Execution**. Manages the modal operator that monitors the background process and updates the UI.                                   |
| `notifications.py`  | **Feedback**. Handles desktop notifications (toast messages) and webhooks.                                                           |
| `version_compat.py` | **Compatibility**. Abstraction layer for handling API differences between Blender 4.2 and 5.0+.                                      | \antml:parameter> |

<parameter name="StartLine">19
| `constants.py` | **Configuration**. Centralized file for constants, filenames, and default values. |
| `preferences.py` | **Settings**. Defines the addon preferences panel. |

## 🧩 Key Concepts

### 1. The Render Queue

The queue is a `CollectionProperty` of `RenderCueJob` items, stored in the current scene's `RenderCueSettings`. This means the queue is saved with the .blend file.

### 2. Background Rendering

RenderCue does **not** block the Blender UI while rendering.

1. When you click "Render", `core.BackgroundWorker` is initialized.
2. It launches a **new, headless Blender instance** as a subprocess.
3. This subprocess loads the same .blend file and executes the render job.
4. The main Blender instance monitors progress by reading a `status.json` file written by the subprocess.

### 3. State Persistence

To ensure the background process knows what to render, the current queue state is serialized to a JSON file (`rendercue_manifest.json`) before the subprocess starts. The subprocess reads this manifest to execute jobs.

### 4. Version Compatibility

We support Blender 4.2 through 5.0+.

- **Do not** use version-specific API calls directly in logic code.
- **Do** use `version_compat.py` helpers (e.g., `get_available_engines()`, `get_icon()`).

## 🛠️ Extension Points

- **Adding a new Override**:

  1. Add the property to `RenderCueJob` in `properties.py`.
  2. Add the UI control in `ui.py` (inside `draw_main_ui`).
  3. Handle the override logic in `core.py` (inside `BackgroundWorker.process_job`).

- **Adding a new Notification Channel**:
  1. Modify `notifications.py` to add the new method.
  2. Add configuration options in `preferences.py`.
