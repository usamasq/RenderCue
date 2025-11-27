# RenderCue

**Sequence. Queue. Render.**

RenderCue is a powerful Blender add-on that bridges the gap between Scene Management and Batch Rendering. It provides a streamlined visual interface to queue multiple scenes, override their output settings per-job, sync with the Video Sequence Editor (VSE), and execute renders in the background while keeping your UI responsive.

## Features

- **Global Queue**: Access and manage your render queue from any scene in your project.
- **Visual Queue**: Manage a list of scenes to render with drag-and-drop reordering.
- **Per-Job Overrides**: Customize Output Path, Frame Range, Resolution %, Format, and Samples for each job without changing the original scene settings.
- **Background Rendering**: Render your queue in a separate process, keeping Blender responsive and providing live progress updates.
- **Status Bar Integration**: Monitor render progress directly in Blender's status bar.
- **Desktop Notifications**: Get native system notifications when renders complete or fail.
- **VSE Sync**: Automatically visualize your render queue to the Video Sequence Editor timeline.
- **Presets**: Save and load your queue configurations for different workflows.
- **Batch Actions**: Apply overrides to all jobs with a single click.
- **Smart Output**: Organize outputs into separate folders or a single directory automatically.

## Installation

1. Download the latest release zip file.
2. Open Blender (4.2 or later).
3. Go to **Edit > Preferences > Get Extensions**.
4. Click the arrow icon (top right) and select **Install from Disk...**.
5. Select the `RenderCue.zip` file.

## Usage

### Accessing RenderCue

You can access the RenderCue panel in:

- **Render Properties** tab (Properties Panel)
- **3D Viewport** sidebar (Press `N` > **RenderCue** tab)
- **Video Sequencer** sidebar (Press `N` > **RenderCue** tab)

### 1. Building Your Queue

- Click **Add Scene** to add the current scene.
- Click **Add All Scenes** to automatically populate the queue with every scene in your .blend file.
- Use the **Up/Down** arrows to reorder jobs.

### 2. Customizing Jobs (Overrides)

Select any job in the list to access its override settings. These changes apply _only_ to the RenderCue job, leaving your actual scene settings untouched.

- **Output**: Set a custom output folder.
- **Frame Range**: Render a specific range (e.g., 1-100).
- **Resolution**: Scale resolution (e.g., 50% for test renders).
- **Format**: Change output format (e.g., PNG, OpenEXR Multilayer, FFMPEG).
- **Samples**: Override render samples for Cycles or Eevee.

**Pro Tip:** Click the **Duplicate Icon** (⧉) next to any override to apply that setting to ALL jobs in the queue.

### 3. VSE Integration

Visualize your render flow before you start:

- Click **Sync to VSE** to generate strips in the Video Sequence Editor for all queued jobs.

### 4. Rendering

RenderCue performs all renders in the **background**, keeping your Blender UI responsive.

1.  **Start Render**: Click the **Render Cue** button in the panel.
2.  **Progress**: The panel will update with the current job, frame progress, and an estimated time remaining (ETR).
3.  **Preview**: A preview of the last rendered frame is displayed in the panel.
4.  **Controls**:
    - **Pause**: Temporarily pause the render process (finishes current frame first).
    - **Resume**: Continue rendering from where it left off.
    - **Stop**: Cancel the render process immediately.

> [!NOTE]
> Closing Blender while a render is in progress will terminate the background render process.

### 5. Notifications

RenderCue can notify you when a batch render completes or fails:

- **Desktop Notifications**: Enable in **Preferences > Add-ons > RenderCue** to receive system toasts.
- **Sound**: Enable "Play Sound on Finish" for an audible alert.
- **Webhook**: Configure a URL to receive a POST request upon completion (useful for Discord/Slack bots).

## Support

If you find this tool useful, consider supporting its development:
[**Support on Patreon**](https://www.patreon.com/c/usamasq)

## License

GPL v3
