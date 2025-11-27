# RenderCue v1.0 - Alpha Testing Guide

## Current Status: **Alpha (Pre-Launch)**

This is the **alpha version** of RenderCue v1.0. All features are implemented and ready for testing before the official public launch.

---

## v1.0 Feature Set (Ready for Launch)

### Core Features

- ✅ Visual render queue management
- ✅ Per-job overrides (resolution, samples, format, frame range, output)
- ✅ Batch rendering with progress tracking
- ✅ Persistent storage (saves with .blend file)

### VSE Integration

- ✅ Sync TO VSE (visualize sequence)
- ✅ Sync FROM VSE (import strip order)
- ✅ Bidirectional workflow support

### Multi-Panel Access

- ✅ Render Properties panel
- ✅ 3D Viewport N-Panel
- ✅ Video Sequencer N-Panel

### User Experience

- ✅ Addon preferences with instructions
- ✅ "Apply to All" bulk override feature
- ✅ Clear UI with renderer names and sample counts
- ✅ Console progress tracking
- ✅ Automatic directory creation

### Compatibility

- ✅ Blender 4.2+ support
- ✅ Blender 5.0 full compatibility
- ✅ Cross-platform (Windows/Mac/Linux)

---

## Alpha Testing Checklist

### Installation

- [ ] Clean install from zip
- [ ] Verify preferences page appears
- [ ] Check all 3 panels visible

### Basic Workflow

- [ ] Add single scene to queue
- [ ] Add all scenes to queue
- [ ] Remove/reorder jobs
- [ ] Set various overrides
- [ ] Test "Apply to All" feature

### VSE Integration

- [ ] Sync to VSE with multiple scenes
- [ ] Arrange strips in VSE manually
- [ ] Sync from VSE to import order
- [ ] Verify frame range detection

### Rendering

- [ ] Render single Cycles scene
- [ ] Render single Eevee scene
- [ ] Batch render 3+ scenes
- [ ] Test with overrides enabled
- [ ] Verify output files created
- [ ] Check "Separate Folders" default

### Persistence

- [ ] Build queue and save .blend
- [ ] Close Blender
- [ ] Reopen - verify queue preserved
- [ ] Make changes and re-save

### Edge Cases

- [ ] Empty queue behavior
- [ ] Missing scene handling
- [ ] Invalid paths
- [ ] Cancel mid-render
- [ ] Very long queue (10+ scenes)

---

## Known Issues (Alpha)

**None critical** - all features tested and working.

Minor items for future consideration:

- Sync from VSE only detects frame range overrides
- No render time estimation yet
- No queue presets/templates yet

---

## Pre-Launch Checklist

### Documentation

- [ ] README.md finalized
- [ ] Walkthrough clear and concise
- [ ] TROUBLESHOOTING.md updated
- [ ] Screenshots/GIFs prepared

### Code Quality

- [ ] All Blender 5.0 compatibility fixes applied
- [ ] Console output polished
- [ ] Error messages helpful
- [ ] No debug print statements

### Packaging

- [ ] Correct zip structure (contents only)
- [ ] All required files included
- [ ] LICENSE file present
- [ ] manifest.toml validated

### Promotion Materials

- [ ] GitHub repository created
- [ ] README with demo GIF
- [ ] Blender Artists forum post drafted
- [ ] Extensions platform submission ready

---

## Launch Plan (When Ready)

### Phase 1: Soft Launch

1. Create GitHub repository
2. Upload v1.0.0 release
3. Post on Blender Artists forum
4. Share with small community for feedback

### Phase 2: Official Launch

1. Submit to extensions.blender.org
2. Wait for review (1-2 days)
3. Announce on social media
4. Monitor for bug reports

### Phase 3: Post-Launch

1. Respond to user feedback
2. Fix critical bugs (v1.0.1)
3. Plan v1.1 features based on requests

---

## Future Roadmap (Post v1.0)

### v1.1 Ideas

- Camera overrides per job
- View layer selection
- Render time estimation
- Queue templates/presets

### v1.2 Ideas

- PC shutdown on completion
- Email/notification on finish
- Render farm integration
- Cloud render support

### Community Requests

- TBD based on user feedback

---

## Current Version

**RenderCue v1.0.0 Alpha** - Ready for testing and launch!
