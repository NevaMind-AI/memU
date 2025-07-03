# Changelog

All notable changes to PersonaLab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete PostgreSQL integration for production-ready deployments
- Enhanced memory pipeline with LLM-powered psychological insights
- Vector embeddings support for semantic conversation search
- Multi-LLM provider support (OpenAI, Anthropic, Google Gemini, etc.)
- Comprehensive conversation management with session tracking
- Enhanced error handling and logging throughout the system

### Changed
- Production database backend using PostgreSQL
- Improved memory update pipeline with better event extraction
- Enhanced Persona API with personality configuration
- Better separation of memory types (Profile, Events, Mind)

### Fixed
- Fixed ConversationManager method naming (`record_conversation` vs `add_conversation`)
- Resolved database connection issues with PostgreSQL
- Fixed memory loading errors and improved error messages

### Documentation
- Added comprehensive PostgreSQL setup guide
- Enhanced README with updated examples
- Created database migration documentation
- Added troubleshooting guides

## [Previous Versions]

### [0.1.0] - Initial Release
- Basic memory management functionality
- Simple conversation recording
- Basic LLM integration 