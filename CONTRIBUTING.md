# Contributing to RenderCue

Thank you for your interest in contributing to RenderCue! We welcome contributions from the community to help make this addon better.

## 🚀 Getting Started

### 1. Fork & Clone

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/usamasq/RenderCue.git
   cd RenderCue
   ```

### 2. Development Installation

For rapid development, we recommend using a symlink so changes are reflected immediately in Blender without reinstalling.

**Windows (PowerShell):**

```powershell
New-Item -ItemType SymbolicLink -Path "C:\Users\YOUR_USER\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\rendercue" -Target "C:\path\to\RenderCue\rendercue"
```

_(Adjust the Blender version path as needed)_

**macOS/Linux:**

```bash
ln -s /path/to/RenderCue/rendercue ~/.config/blender/4.2/scripts/addons/rendercue
```

## 📂 Code Structure Overview

- **`core.py`**: The heart of the addon. Handles the background worker process, state management, and logging.
- **`operators.py`**: Defines all Blender operators (buttons and actions).
- **`ui.py`**: Manages the UI panels and drawing logic.
- **`properties.py`**: Defines `PropertyGroups` for jobs and settings.
- **`render.py`**: Manages the render execution flow and status monitoring.
- **`version_compat.py`**: Handles API differences between Blender 3.0 - 5.0+.
- **`notifications.py`**: Handles desktop toasts and webhooks.

## 📏 Coding Standards

- **Style**: Follow **PEP 8** guidelines.
- **Naming**: Use `snake_case` for functions/variables and `CamelCase` for classes.
- **Blender API**:
  - Use `version_compat.py` for any API that differs between Blender versions.
  - Do not import `bpy` at the top level of modules that are imported by the background worker (unless guarded).
- **Docstrings**: Add docstrings to all new classes and complex functions.

## 🧪 Testing

Before submitting a PR, please test your changes:

1. **UI Check**: Does the panel look correct? Are tooltips working?
2. **Render Check**: Run a small batch render (e.g., 2 scenes, 1 frame each).
3. **Version Check**: If possible, test on at least two Blender versions (e.g., 3.6 LTS and 4.2).

## 📤 Submitting Changes

1. Create a new branch: `git checkout -b feature/my-new-feature`
2. Commit your changes with clear messages.
3. Push to your fork and submit a **Pull Request**.
4. Describe your changes and include screenshots if relevant.

## 🐛 Reporting Issues

Please open an issue on GitHub with:

- Blender version
- OS version
- Steps to reproduce
- Error logs (Window > Toggle System Console)

## License

By contributing, you agree that your contributions will be licensed under the project's [GPL-3.0 License](LICENSE).
