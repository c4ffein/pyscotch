# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Type hints marker file (py.typed) for PEP 561 compliance
- Comprehensive input validation in Graph class methods
- Named constant for opaque C structure size
- Project URLs and keywords in setup.py
- Enhanced package docstring with usage examples
- More descriptive error messages with context
- Validation for partition count and array dimensions

### Changed
- Replaced bare exception handlers with specific exception types
- Improved error messages to include operation context and parameters
- Made magic numbers (256) into named constants (_OPAQUE_STRUCTURE_SIZE)
- Enhanced docstrings with parameter validation details

### Fixed
- Missing ctypes.util import in libscotch.py
- Bare except clauses now catch specific exceptions (OSError, AttributeError, TypeError)
- Error messages now provide more diagnostic context

## [0.1.0] - 2024-XX-XX

### Added
- Initial release
- Graph partitioning support
- Mesh partitioning support
- Sparse matrix ordering support
- Command-line interface
- Python API with type hints
- PT-Scotch library integration
- Makefile-based build system

[Unreleased]: https://github.com/c4ffein/pyscotch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/c4ffein/pyscotch/releases/tag/v0.1.0
