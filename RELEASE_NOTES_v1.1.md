# RenderCue v1.1 Release Notes

## 🎉 Major New Features

### 1. ✅ Bidirectional VSE Integration

**"Sync from VSE"** button now available!

- **Sync to VSE** → Send queue to Video Sequencer (existing)
- **Sync from VSE** → Import strip order FROM Video Sequencer (NEW!)

**How it works**:

1. Arrange scene strips in VSE Channel 1
2. Click "Sync from VSE"
3. RenderCue queue updates to match strip order
4. Frame range overrides detected automatically

**Use Case**: Visually arrange your render sequence in VSE, then import to RenderCue!

---

### 2. ✅ VSE Panel Access

RenderCue panel now available in **Video Sequence Editor**!

**Panel Locations** (all 3 show the same queue):

- ✓ Render Properties (original)
- ✓ 3D Viewport N-Panel
- ✓ **Video Sequencer N-Panel** (NEW!)

**Benefit**: Work directly in VSE while managing your render queue

---

### 3. ✅ Addon Preferences Page

Complete settings page with instructions and tips!

**Access**: Edit > Preferences > Add-ons > Search "RenderCue" > Expand

**Features**:

- **Quick Start Guide**: Step-by-step instructions
- **Preferences**:
  - Show/hide instructions toggle
  - Auto-sync VSE option (future enhancement)
- **Tips Section**: Helpful workflow hints
- **Links**: Documentation and issue reporting

---

### 4. ✅ Better Defaults

**Output Structure** default changed to **"Separate Folders"**

**Before**: All renders in same folder (confusing)
**After**: Each scene gets its own subfolder (organized)

```
render_cue_output/
├── Scene.001/
│   └── Scene_001_0001.png
└── Scene.002/
    └── Scene_002_0001.png
```

---

### 5. ✅ Persistent Storage

Queue **saves with your .blend file**!

- No more rebuilding queue every session
- Settings persist across Blender restarts
- Each .blend file has its own queue
- Perfect for project workflows

---

## Updated Features

### UI Improvements

- **Clearer labels**: "Samples: 64" instead of "S:64"
- **Renderer names**: Shows "Cycles", "Eevee", or "Eevee Next"
- **Better button layout**: VSE sync buttons grouped together
- **Large render button**: Main "Render Cue" button more prominent

### Progress Tracking

- Progress bar in status bar
- Console output with frame-by-frame updates
- Job count tracking (e.g., "Rendering 2/5")
- Proper Eevee render handling

### File Saving

- Auto-creates output directories
- Proper filename patterns for image sequences
- Video format support (MP4)
- Handles relative and absolute paths

---

## Version History

### v1.1.0 (This Release)

- ✅ Bidirectional VSE sync
- ✅ VSE panel access
- ✅ Addon preferences page
- ✅ Persistent storage (saves with .blend)
- ✅ SEPARATE folders default
- ✅ Blender 5.0 full compatibility
- ✅ Better progress tracking
- ✅ File saving fixes

### v1.0.0 (Initial)

- Basic render queue
- Per-job overrides
- Sync to VSE
- Batch rendering

---

## Quick Start (v1.1)

### Basic Workflow:

1. **Add scenes** → Click "Add Scene" or "Add All Scenes"
2. **Configure** → Set overrides (resolution, samples, etc.)
3. **Visualize** → Click "Sync to VSE" to preview
4. **Render** → Click "Render Cue"

### Advanced Workflow:

1. **Arrange in VSE** → Drag scene strips in Channel 1
2. **Import order** → Click "Sync from VSE"
3. **Fine-tune** → Adjust overrides in RenderCue panel
4. **Re-sync if needed** → "Sync to VSE" to see changes
5. **Render** → Click "Render Cue"

---

## Compatibility

- ✅ Blender 4.2+
- ✅ Blender 5.0 (fully tested)
- ✅ Windows, macOS, Linux

---

## File Structure

New files in v1.1:

- `preferences.py` - Addon settings page
- `vse_sync.py` - Sync FROM VSE operator
- `.PERSISTENCE_FEATURE.md` - Technical docs
- `.BLENDER5_COMPAT.md` - Compatibility notes

---

## Breaking Changes

**None!** v1.1 is fully backward compatible with v1.0.

Existing .blend files with v1.0 queues will work seamlessly in v1.1.

---

## Known Limitations

1. Sync from VSE only detects frame range overrides
2. Other overrides (resolution, samples) must be set manually
3. Only reads from VSE Channel 1

Future versions may add full metadata preservation!
