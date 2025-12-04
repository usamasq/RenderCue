# RenderCue v1.1.0 Release Notes

## 🚀 Major Update: Version Agnosticism (Blender 3.0 - 5.0+)

This release marks a significant milestone for RenderCue, bringing true **version agnosticism**. You can now use RenderCue seamlessly across a wide range of Blender versions, from the stable 3.0 LTS to the cutting-edge Blender 5.0.

### ✨ What's New

- **Wide Compatibility**: Official support for Blender **3.0, 3.3 LTS, 3.6 LTS, 4.0, 4.1, 4.2 LTS, and 5.0+**.
- **Smart Engine Detection**: The addon now dynamically detects which render engines are available. It correctly handles "Eevee Next" in 4.1 and the unified Eevee in 4.2+.
- **Adaptive Settings**: Render settings like Eevee samples automatically use the correct API for your specific Blender version (no more python errors when switching versions!).

### 🛠️ Technical Improvements

- **New Compatibility Layer**: A robust `version_compat.py` module now handles all cross-version logic.
- **Future Proofing**: The codebase is prepared for future API changes in Blender 5.x.
- **Clean Metadata**: Updated manifest to allow installation on any Blender version >= 3.0.0.

### 📦 Installation

1. Download `rendercue-v1.1.0.zip`.
2. In Blender, go to **Edit > Preferences > Add-ons**.
3. Click **Install...** and select the zip file.
4. Enable **Render: RenderCue**.

### 🔄 Upgrading

If you are upgrading from v1.0.x:

1. Disable and remove the old version.
2. Restart Blender (recommended to clear cached modules).
3. Install v1.1.0.
