"""Single source of truth for the PyScotch version.

Kept import-free so setup.py can read it without importing the package (which
would try to load the compiled Scotch libraries at build time). On a release
tag push, CI overwrites this file from the tag via
scripts/apply_release_version.py, so the git tag is the authority for what gets
published; between releases it holds the next target version.
"""

__version__ = "7.0.0"
