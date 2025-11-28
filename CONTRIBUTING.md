# Contributing to RenderCue

Thank you for your interest in contributing to RenderCue! We welcome contributions from the community to help make this addon better.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/usamasq/RenderCue.git
    ```
3.  **Install the addon** in Blender:
    - Zip the `RenderCue` folder (excluding `.git` and `__pycache__`).
    - Install via `Edit > Preferences > Add-ons > Install...`.
    - Alternatively, symlink the folder to your Blender addons directory for easier development.

## Development Workflow

- **Code Style**: Please follow PEP 8 guidelines for Python code.
- **Blender API**: We target Blender 4.2 LTS. Please ensure compatibility.
- **Testing**: Test your changes thoroughly.
  - Verify UI elements in the Properties panel and VSE.
  - Run test renders (both single frame and animation).
  - Check background rendering functionality.

## Submitting Changes

1.  Create a new branch for your feature or fix:
    ```bash
    git checkout -b feature/my-new-feature
    ```
2.  Commit your changes with clear, descriptive messages.
3.  Push to your fork and submit a **Pull Request** to the `main` branch.
4.  Provide a detailed description of your changes and any relevant screenshots.

## Reporting Bugs

If you find a bug, please open an issue on GitHub with:

- Blender version.
- OS version.
- Steps to reproduce.
- Error logs (if any).

## License

By contributing, you agree that your contributions will be licensed under the project's [GPL-3.0 License](LICENSE).
