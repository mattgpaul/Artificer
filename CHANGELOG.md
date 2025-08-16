# Changelog

All notable changes to the Artificer microservices monorepo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial Bazel monorepo setup with MODULE.bazel
- Telemetry collector service with versioned schema support
- Industry-standard versioning and rollback safety patterns
- Exact dependency pinning for reproducible builds

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## Template for Future Releases

## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability fixes

---

## Version Guidelines

### Schema Versions (Telemetry Messages)
- **v1**: Initial CPU telemetry format
- **v2**: (Planned) Add memory and disk metrics
- **v3**: (Planned) Network and process-level telemetry

### Service Versions
Follow semantic versioning:
- **MAJOR**: Breaking changes, incompatible API changes
- **MINOR**: New functionality, backward compatible
- **PATCH**: Bug fixes, backward compatible

### When to Update This File
- Every service version change
- Every schema version change  
- Every dependency security update
- Before each release/deployment
