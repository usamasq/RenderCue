- Go to **Edit > Preferences > Get Extensions**
- Find "RenderCue" in your installed extensions
- Click the **X** or **Remove** button
- Restart Blender (important!)

2. **Create Fresh Zip:**

   - Go to `C:\Users\usama\Downloads\Ropositories\RenderCue\`
   - Select **all files inside** (don't select the folder itself):
     - `__init__.py`
     - `properties.py`
     - `ui.py`
     - `operators.py`
     - `vse.py`
     - `render.py`
     - `blender_manifest.toml`
     - `LICENSE`
     - `README.md`
     - `.gitignore`
   - Right-click > **Send to > Compressed (zipped) folder**
   - Name it `RenderCue.zip`

3. **Reinstall:**

   - In Blender: **Edit > Preferences > Get Extensions**
   - Click the arrow (top right) > **Install from Disk...**
   - Select `RenderCue.zip`
   - Wait for confirmation

4. **Verify Installation:**

   - Go to **Render Properties** tab (camera icon on the right sidebar)
   - Scroll down - you should see the **"RenderCue"** panel
   - OR press `N` in the 3D Viewport, click the **"RenderCue"** tab

5. **Check for the Buttons:**
   At the bottom of the panel, you should see two large buttons:
   - **"Sync to VSE"** (with sequencer icon)
   - **"Render Cue"** (with render icon)

## Common Issues:

### Panel is empty or addon won't load

- **Check the System Console**: In Blender, go to **Window > Toggle System Console**
- Look for Python errors (usually red text)
- Common error: "blender_manifest.toml" issues - make sure the license field is `["GPL-3.0-or-later"]`

### Buttons still not visible

- Make sure you have at least **one scene added to the queue**
- The buttons are always visible, but check if the panel is collapsed

### "Apply to All" buttons not working

- These only work when you have multiple jobs in the queue
- Select a job, set an override, then click the ⧉ icon

---

**If you still have issues, check the System Console for errors and let me know what you see!**
