# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
