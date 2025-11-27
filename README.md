# RenderCue

**Sequence. Queue. Render.**

RenderCue is a Blender add-on designed to bridge the gap between Scene Management and Batch Rendering. Unlike standard command-line batch rendering, RenderCue provides a visual interface within Blender to queue multiple scenes, override their output settings per-job, and visualize the timing of these jobs using Blender's internal Video Sequence Editor (VSE).

## Features

- **Visual Queue**: Manage a list of scenes to render.
- **Per-Job Overrides**: Output Path, Frame Range, Resolution %, Format, Samples
- **VSE Sync**: Visualize your render queue in the Video Sequence Editor timeline.
- **Batch Render**: Render all queued jobs sequentially with a single click.
- **Apply to All**: Copy override settings from one job to all jobs.
- **Global Settings**: Organize outputs into separate folders or a single directory.

## Installation

1. Zip the **contents** of the RenderCue folder (not the folder itself).
2. Open Blender (4.2 or later).
3. Go to **Edit > Preferences > Get Extensions**.
4. Click the arrow icon (top right) and select **Install from Disk...**.
5. Select the `RenderCue.zip` file.

## Usage

### Accessing RenderCue

You can access the RenderCue panel in **two places**:

1. **Render Properties** tab (in the Properties panel)
2. **3D Viewport** sidebar (Press `N` > **RenderCue** tab)

### 1. Add Scenes to Queue

- Click **Add Scene** to add the current scene
- Click **Add All Scenes** to automatically add every scene in your .blend file

### 2. View Scene Information

The list displays key information for each scene:

- **Scene Name** with icon
- **Render Engine** icon (Cycles/Eevee)
- **Resolution** (actual final resolution like "1920x1080", with override icon if modified)
- **FPS** (frames per second, e.g., "24fps")
- **Samples** (shown as "S:64" for render quality)

### 3. Configure Per-Job Overrides

Select any job in the list to see its override options:

- **Output Path**: Custom directory for this scene
- **Frame Range**: Render specific frames (e.g., 1-120)
- **Resolution %**: Scale down for test renders (e.g., 50%)
- **Format**: Change file format (PNG, EXR, etc.)
- **Samples**: Override render samples

**Tip:** Click the **duplicate icon** (⧉) next to any override to apply it to ALL jobs in the queue.

### 4. Global Settings

- **Output Structure**:
  - _Separate Folders_: Each scene renders to its own subfolder
  - _Same Folder_: All renders go to one directory
- **Global Output Path**: Base directory for all renders

### 5. Sync to VSE (Video Sequence Editor)

Click **Sync to VSE** to visualize your render sequence:

- All queued scenes appear as strips in Channel 1
- Play the timeline to preview the final sequence
- Great for checking timing before rendering

### 6. Batch Render

Click **Render Cue** (the large button at the bottom of the panel) to start rendering all jobs sequentially. Progress will be shown in Blender's interface.

## Requirements

- Blender 4.2+

## License

GPL v3
