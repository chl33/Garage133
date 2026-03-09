# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.5] - 2026-03-08

### Added
- **HMM State Estimation**: Implemented Hidden Markov Models (HMM) for robust garage door state classification (open, closed-with-car, closed-empty) using sonar distance data.
- **Model Training & Analysis**: Added Python-based tools in the `analysis/` directory for downloading Home Assistant data, training HMM models, and evaluating their performance.
- **Web-Based Model Management**: Added web endpoints and a dashboard UI for uploading and reloading HMM JSON models dynamically without firmware re-flashes.

### Changed
- **Modernized Framework**: Upgraded to **og3 v0.5.0** and its extension libraries (**og3x-oled**, **og3x-shtc3**).
- **PsychicHttp Integration**: Updated to use the modernized Request/Response networking model provided by PsychicHttp 2.1.1 on ESP32.
- **Improved Dependency Management**: Switched to formal registry-based dependencies and ensured all transitive dependencies are correctly resolved using `lib_ldf_mode = deep+`.
- **Environment-Based Config**: Refactored the build system to use environment-scoped configuration in `local.ini`.
