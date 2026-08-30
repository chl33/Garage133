# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-08-21

### Added
- **Hardware Board v3.0 & ESP32-S3 Support**: Added PlatformIO configuration (`usb_s3`), pin assignments for ESP32-S3, updated schematic/PCB designs, and refreshed solder stencil fixture 3D models.
- **Quad-Sonar Support**: Integrated dual ultrasonic sensors per side (4 total) with updated state classification logic, training pipeline, and retrained HMM models.
- **Home Assistant Probability Export**: Exported garage state probabilities (`probOpen`, `probCar`, `probEmpty`) via Home Assistant MQTT discovery.

### Changed
- **Svelte Build Tooling**: Pinned `svelteesp32` to v3.2.5 and updated CI workflows to Node 22 for reproducible builds.
- **Dependency & Workflow Upgrades**: Upgraded `og3` to v0.6.3, `og3x-oled` to v0.6.1, and updated GitHub Actions workflows to latest versions.

## [1.0.3] - 2026-03-24

### Added
- **Declarative Dependency Management**: Refactored core modules to use the new `og3` `require<T>()` pattern, simplifying internal module linking and improving boot-time memory efficiency.
- **Svelte-Native JSON API**: Transitioned all status and configuration JSON keys to `camelCase` (e.g., `ipAddr`, `wifiPassword`, `mqttConnected`) to align with JavaScript/TypeScript standards and simplify the Svelte store logic.

### Changed
- **Framework Upgrade**: Bumped to **og3 v0.6.0**.
- **Enhanced API Handlers**: Re-implemented web API endpoints using the unified `NetRequest` and `NetResponse` abstraction layer for better portability and robustness.
- **Automatic Svelte Builds**: Integrated `build_svelte.py` into the PlatformIO lifecycle to ensure the web interface is always in sync with the firmware during the build process.
*   **Coding and infrastructure cleanups**: Linting, CI, coding improvements.

## [1.0.0] - 2026-03-10

### Added
- **Svelte Web Interface**
  - Responsive Single Page Application (SPA) dashboard for real-time monitoring.
  - Individual door detail pages with HMM probability visualizations.
  - Integrated manual state correction/labeling to refine detection logic.
  - Robust networking with `AbortController` timeouts and sequential polling.
- **HMM State Estimation**
  - Implemented Hidden Markov Models (HMM) for robust classification of door and car states.
  - Web-based management for uploading and reloading HMM JSON models.
  - Python-based analysis toolkit for data downloading and model training.
- **Modernized Networking**
  - Integrated `PsychicHttp` for a modernized Request/Response web server model.
  - Switched to `PsychicMqttClient` for improved MQTT reliability on ESP32.

### Changed
- **Infrastructure & Framework**
  - Upgraded to **og3 v0.5.0** and its ecosystem libraries.
  - Expanded flash partitions to `min_spiffs.csv` (1.9MB App space) to support richer UI and reliable OTA.
  - Moved legacy UI to `/root` and registered Svelte SPA as the primary interface.
  - Optimized build system with `build-svelte.sh` for automated asset generation.
- **Dependency Management**
  - Transitioned to registry-based dependencies with deep transitive resolution.
