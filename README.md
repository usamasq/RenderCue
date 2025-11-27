# RenderCue

**Sequence. Queue. Render.**

RenderCue is a powerful Blender add-on that bridges the gap between Scene Management and Batch Rendering. It provides a streamlined visual interface to queue multiple scenes, override their output settings per-job, and execute renders in the background while keeping your UI responsive.

## 🚀 Features

- **Global Render Queue**: Add scenes from anywhere in your .blend file to a centralized queue.
- **Batch Rendering**: Render all queued scenes in one go with a single click.
- **Background Rendering**: Renders are performed in the background, keeping Blender responsive.
- **Pause/Resume**: Pause renders at any time and resume them later.
- **Overrides**:
  - **Output Path**: Set a global output folder or override per job.
  - **Frame Range**: Render specific frame ranges for each job.
  - **Resolution**: Quickly scale resolution (e.g., 50% for drafts).
  - **Render Engine**: Switch between Cycles and Eevee per job.
  - **View Layer**: Select specific view layers to render.
- **Presets**: Save and load queue configurations, or use quick "Draft"/"Production" presets.
- **Desktop Notifications**: Get notified when your batch render completes or fails.
- **Status Bar Integration**: Monitor render progress directly from the status bar.

## 📦 Installation

1. Download the latest release zip file.
2. Open Blender.
3. Go to **Edit > Preferences > Add-ons**.
4. Click **Install...** and select the zip file.
5. Enable the addon by checking the box next to **Render: RenderCue**.

## 🎮 Usage

### 1. Building the Queue

- Open the **RenderCue** panel in the **Render Properties** tab or the **3D Viewport N-Panel**.
- Click **Add Scene** to add the current scene, or **Add All Scenes** to populate the queue with all scenes in the file.
- Reorder jobs using the up/down arrows.

### 2. Configuring Jobs

- Use the **Batch Settings** box to set a global output path.
- Expand the **Overrides** section for any job to set specific settings:
  - **Output**: Custom output path for this job.
  - **Frame Range**: Override the scene's frame range.
  - **Resolution %**: Scale the render resolution.
  - **Format**: Change the file format (PNG, JPEG, etc.).
  - **Samples**: Override render samples.
  - **Engine**: Switch render engine (Cycles/Eevee).
  - **View Layer**: Select a specific view layer.
- **Tip**: Click the duplicate icon (⧉) next to an override to apply that setting to **ALL** jobs in the queue.

### 3. Presets

- Use the **Presets** menu to:
  - Apply **Quick Settings** like "Draft" (50% res, low samples) or "Production".
  - **Save** your current queue configuration to a JSON file.
  - **Load** a previously saved queue.

### 4. Rendering

- Click **Render Cue** to start the batch process.
- Monitor progress in the panel or the status bar.
- Use **Pause**, **Resume**, or **Stop** buttons to control the process.
- You can continue working in Blender while rendering (rendering happens in the background).

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
