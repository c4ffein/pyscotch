"""
Setup script for PyScotch.
"""

from setuptools import setup, find_packages
from setuptools.dist import Distribution
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# NOTE: version is declared dynamic in pyproject.toml, sourced from
# pyscotch/_version.py — do not set it here (setuptools forbids setting a field
# both statically in setup() and dynamically in [project]).

# When scripts/build_wheel_libs.sh has staged the Scotch shared libraries into
# pyscotch/_libs/, we ship them as package data and must produce a
# platform-specific wheel. Otherwise (sdist / dev install), the package is
# pure Python and users build Scotch from source (see README).
_libs_dir = Path(__file__).parent / "pyscotch" / "_libs"
HAS_BUNDLED_LIBS = _libs_dir.is_dir() and any(_libs_dir.rglob("*.so"))

try:
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # older setuptools keeps it in the wheel package
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel


class BinaryDistribution(Distribution):
    """Force a platform-specific wheel when native libraries are bundled."""

    def has_ext_modules(self):
        return HAS_BUNDLED_LIBS


class PlatformBdistWheel(_bdist_wheel):
    """Tag bundled-libs wheels as py3-none-<platform>.

    PyScotch is ctypes-only (no CPython C-API usage), so a single wheel per
    platform works for every Python 3 version.
    """

    def finalize_options(self):
        super().finalize_options()
        if HAS_BUNDLED_LIBS:
            self.root_is_pure = False

    def get_tag(self):
        python, abi, plat = super().get_tag()
        if HAS_BUNDLED_LIBS:
            return "py3", "none", plat
        return python, abi, plat


setup(
    name="pyscotch",
    author="c4ffein",
    description="Python wrapper for PT-Scotch graph partitioning library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/c4ffein/pyscotch",
    project_urls={
        "Bug Reports": "https://github.com/c4ffein/pyscotch/issues",
        "Source": "https://github.com/c4ffein/pyscotch",
    },
    keywords=[
        "graph-partitioning",
        "mesh-partitioning",
        "sparse-matrix",
        "scientific-computing",
        "pt-scotch",
        "scotch",
        "parallel-computing",
    ],
    packages=find_packages(include=["pyscotch", "pyscotch.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
        "docs": [
            "sphinx",
            "sphinx-rtd-theme",
        ],
    },
    entry_points={
        "console_scripts": [
            "pyscotch=pyscotch.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        # _libs/lib{32,64}/*.so are staged by scripts/build_wheel_libs.sh for
        # binary wheels; the globs are harmless no-ops when the dir is absent.
        "pyscotch": [
            "py.typed",
            "native/*.c",
            "_patches/*.patch",  # bundled Scotch build fixes (pyscotch scotch build)
            "_libs/lib32/*.so",
            "_libs/lib64/*.so",
        ],
    },
    distclass=BinaryDistribution,
    cmdclass={"bdist_wheel": PlatformBdistWheel},
    zip_safe=False,
)
