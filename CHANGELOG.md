# Changelog

All notable changes to this project will be documented in this file.

## [1.1.2] - 2025-12-05

### Added

- **UI Redesign**: Simplified 3-section layout (List, Overrides, Render) for better clarity.
- **Scene Summary Card**: New panel below the list showing engine, resolution, samples, and active overrides.
- **Context Menus**: Right-click job list for Move, Switch Scene, and Remove options.
- **Move to Top/Bottom**: New operators to quickly organize the queue.
- **Inline Validation**: Invalid jobs (e.g., missing cameras) are visually flagged with specific error messages.

### Changed

- **Queue List**: Removed redundant columns; now shows simplified Status • Name • [Switch] • Frames.
- **Validation**: Replaced "All scenes with camera" generic message with per-job validation warnings.
- **Global Output**: Collapsed by default to reduce clutter.

## [1.1.0] - 2025-12-04

### Added

- **Version Agnosticism**: RenderCue now supports Blender versions 3.0 through 5.0+.
- **Dynamic Engine Detection**: Automatically detects available render engines (Cycles, Eevee, Workbench, Eevee Next).
- **Version Compatibility Module**: New internal module to handle API differences between Blender versions transparently.

### Changed

- **Minimum Blender Version**: Lowered from 4.2.0 to 3.0.0.
- **Eevee Samples Handling**: Now intelligently switches between `samples` (Blender 3.x) and `taa_render_samples` (Blender 4.x/5.x).
- **Engine Overrides**: Removed hardcoded engine lists in favor of dynamic detection.
- **UI Updates**: Engine names and settings now adapt to the running Blender version.

### Fixed

- **Blender 5.0 Compatibility**: Resolved potential API conflicts with property access and Eevee settings in Blender 5.0.
- **Eevee Next Support**: Properly handles the merge of Eevee Next back into Eevee in Blender 4.2+.

## [1.0.2] - 2024-11-28

### Fixed

- Fixed `NameError` during installation.
- Fixed thumbnail refresh issues.

## [1.0.0] - 2024-11-27

- Initial Release
