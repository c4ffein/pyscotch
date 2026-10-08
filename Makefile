# Makefile for building PT-Scotch and PyScotch

# Directories.
#
# DECISION (2026-07-31): builds never touch the git submodule. The submodule
# (SCOTCH_SUBMODULE) is a pristine, read-only reference — tests read its
# check/ data, the differential tier builds gpart from it, and docs/QUESTIONS
# line references point into it. All compilation happens in a disposable,
# quickfix-patched COPY (SCOTCH_DIR, under build/), prepared by
# `pyscotch scotch prepare` — the same Python patch machinery that
# `pyscotch scotch build` uses on release tarballs: one catalog, one applier.
# Wheels build from this copy too, so shipped artifacts come from exactly the
# tree CI tested. User machines use the GitLab release tarball instead
# (`pyscotch scotch build`); both sources are maintained deliberately.
SCOTCH_SUBMODULE = external/scotch
SCOTCH_DIR = build/scotch-src
SCOTCH_SRC = $(SCOTCH_DIR)/src
BUILDS_DIR = scotch-builds
PYTHON ?= python3
# gen_api.py (docs-api) needs Python >= 3.14 WITH pyscotch+numpy importable —
# on this project that is the uv-managed .venv, not a bare python3. Prefer it
# when present; override with DOCS_PYTHON=... for a different 3.14 interpreter.
DOCS_PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(PYTHON))

# Compiler settings
CC = gcc
MPICC = mpicc
LDFLAGS = -lm -lpthread -lz

# Platform detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    SHARED_EXT = so
    SHARED_FLAGS = -shared
endif
ifeq ($(UNAME_S),Darwin)
    SHARED_EXT = dylib
    SHARED_FLAGS = -dynamiclib
endif

# Targets
.PHONY: all build-all build-32 build-64 build-seq-only build-seq-32 build-seq-64 build-reference-tools clean clean-scotch install test test-full test-quadrant test-differential docs-api help

help:
	@echo "PyScotch Build System"
	@echo "====================="
	@echo ""
	@echo "Build targets:"
	@echo "  make build-all    - Build all 4 variants (scotch+ptscotch × 32+64-bit)"
	@echo "  make build-32     - Build both scotch and ptscotch with 32-bit integers"
	@echo "  make build-64     - Build both scotch and ptscotch with 64-bit integers"
	@echo "  make build-seq-only - Build sequential-only libscotch (32+64-bit, no MPI needed)"
	@echo ""
	@echo "Output structure:"
	@echo "  scotch-builds/lib32/  - Sequential & parallel libraries (32-bit)"
	@echo "  scotch-builds/lib64/  - Sequential & parallel libraries (64-bit)"
	@echo "  scotch-builds/inc32/  - Headers (32-bit: SCOTCH_Num = int)"
	@echo "  scotch-builds/inc64/  - Headers (64-bit: SCOTCH_Num = int64_t)"
	@echo ""
	@echo "Other targets:"
	@echo "  make install         - Install Python package"
	@echo "  make test            - Run tests (64-bit parallel, skips hypothesis)"
	@echo "  make test-full       - Run full test suite including hypothesis"
	@echo "  make test-quadrant   - Run all 4 variants (32/64 × seq/parallel) with hypothesis"
	@echo "  make build-reference-tools - Build Scotch's own CLI tools (gpart, gord, gmap; dgpart, dgord) as differential oracles"
	@echo "  make test-differential     - Byte-compare PyScotch against those tools (needs build-reference-tools)"
	@echo "  make docs-api              - Regenerate docs/site/api_data.json after a public-API change (mirrors CI)"
	@echo "  make clean           - Clean Python build artifacts"
	@echo "  make clean-scotch    - Clean all Scotch builds"
	@echo "  make check-submodule - Gets Scotch as a submodule"
	@echo ""

# Build all variants
all: build-all

build-all: build-32 build-64
	@echo ""
	@echo "✓ All Scotch variants built successfully!"
	@echo "  - scotch-builds/lib32/ (sequential + parallel, 32-bit)"
	@echo "  - scotch-builds/lib64/ (sequential + parallel, 64-bit)"

# Build 32-bit variants (sequential + parallel) with suffix
build-32: check-submodule
	@echo "=========================================="
	@echo "Building 32-bit Scotch with suffix '_32'"
	@echo "=========================================="
	@mkdir -p $(BUILDS_DIR)/lib32 $(BUILDS_DIR)/inc32
	@cd $(SCOTCH_SRC) && $(MAKE) realclean
	@echo ""
	@echo "[1/3] Building sequential scotch (32-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) scotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DSCOTCH_NAME_SUFFIX=_32 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "[2/3] Building parallel ptscotch (32-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) ptscotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DSCOTCH_NAME_SUFFIX=_32 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "[3/3] Building PyScotch file compatibility layer (32-bit)..."
	@$(CC) $(SHARED_FLAGS) -fPIC -O2 -o $(BUILDS_DIR)/lib32/libpyscotch_compat.$(SHARED_EXT) \
		pyscotch/native/file_compat.c
	@echo ""
	@echo "Copying 32-bit libraries and headers..."
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.$(SHARED_EXT) $(BUILDS_DIR)/lib32/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.a $(BUILDS_DIR)/lib32/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/include/*.h $(BUILDS_DIR)/inc32/ 2>/dev/null || true
	@echo "✓ 32-bit build complete: scotch-builds/{lib32,inc32}/"

# Build 64-bit variants (sequential + parallel) with suffix
build-64: check-submodule
	@echo "=========================================="
	@echo "Building 64-bit Scotch with suffix '_64'"
	@echo "=========================================="
	@mkdir -p $(BUILDS_DIR)/lib64 $(BUILDS_DIR)/inc64
	@cd $(SCOTCH_SRC) && $(MAKE) realclean
	@echo ""
	@echo "[1/3] Building sequential scotch (64-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) scotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DINTSIZE64 -DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "[2/3] Building parallel ptscotch (64-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) ptscotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DINTSIZE64 -DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "[3/3] Building PyScotch file compatibility layer (64-bit)..."
	@$(CC) $(SHARED_FLAGS) -fPIC -O2 -o $(BUILDS_DIR)/lib64/libpyscotch_compat.$(SHARED_EXT) \
		pyscotch/native/file_compat.c
	@echo ""
	@echo "Copying 64-bit libraries and headers..."
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.$(SHARED_EXT) $(BUILDS_DIR)/lib64/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.a $(BUILDS_DIR)/lib64/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/include/*.h $(BUILDS_DIR)/inc64/ 2>/dev/null || true
	@echo "✓ 64-bit build complete: scotch-builds/{lib64,inc64}/"

# Sequential-only builds (no MPI toolchain required).
# Used for binary wheels: builds only libscotch/libscotcherr (suffixed) plus the
# PyScotch compat layer. Unlike build-32/build-64, failures are NOT swallowed.
build-seq-only: build-seq-32 build-seq-64
	@echo ""
	@echo "✓ Sequential-only Scotch variants built successfully!"

build-seq-32: check-submodule
	@echo "=========================================="
	@echo "Building sequential-only 32-bit Scotch ('_32' suffix)"
	@echo "=========================================="
	@mkdir -p $(BUILDS_DIR)/lib32 $(BUILDS_DIR)/inc32
	@cd $(SCOTCH_SRC) && $(MAKE) realclean
	@cd $(SCOTCH_SRC) && \
		$(MAKE) libscotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DSCOTCH_NAME_SUFFIX=_32 -DSCOTCH_RENAME_ALL"
	@$(CC) $(SHARED_FLAGS) -fPIC -O2 -o $(BUILDS_DIR)/lib32/libpyscotch_compat.$(SHARED_EXT) \
		pyscotch/native/file_compat.c
	@cp -f $(SCOTCH_DIR)/lib/libscotch.$(SHARED_EXT) $(SCOTCH_DIR)/lib/libscotcherr*.$(SHARED_EXT) $(BUILDS_DIR)/lib32/
	@cp -f $(SCOTCH_DIR)/include/*.h $(BUILDS_DIR)/inc32/
	@echo "✓ Sequential 32-bit build complete: scotch-builds/{lib32,inc32}/"

build-seq-64: check-submodule
	@echo "=========================================="
	@echo "Building sequential-only 64-bit Scotch ('_64' suffix)"
	@echo "=========================================="
	@mkdir -p $(BUILDS_DIR)/lib64 $(BUILDS_DIR)/inc64
	@cd $(SCOTCH_SRC) && $(MAKE) realclean
	@cd $(SCOTCH_SRC) && \
		$(MAKE) libscotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DINTSIZE64 -DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL"
	@$(CC) $(SHARED_FLAGS) -fPIC -O2 -o $(BUILDS_DIR)/lib64/libpyscotch_compat.$(SHARED_EXT) \
		pyscotch/native/file_compat.c
	@cp -f $(SCOTCH_DIR)/lib/libscotch.$(SHARED_EXT) $(SCOTCH_DIR)/lib/libscotcherr*.$(SHARED_EXT) $(BUILDS_DIR)/lib64/
	@cp -f $(SCOTCH_DIR)/include/*.h $(BUILDS_DIR)/inc64/
	@echo "✓ Sequential 64-bit build complete: scotch-builds/{lib64,inc64}/"

# Upstream's reference CLI tools (gpart, gord, gmap; dgpart, dgord) for the differential tier
# (tests/pyscotch_base/test_differential.py), built from the same
# prepared source copy as the libraries but with the stock (unsuffixed)
# Makefile.inc flags — the tools must drive libscotch exactly as released.
# The binaries dynamically link the unsuffixed libscotch.so, so it is copied
# next to them; run them with LD_LIBRARY_PATH pointing there.
build-reference-tools: check-submodule
	@echo "Building upstream reference tools (gpart, gord, gmap; dgpart, dgord if MPI)..."
	@cd $(SCOTCH_SRC) && $(MAKE) realclean
	@cd $(SCOTCH_SRC) && $(MAKE) scotch
	@mkdir -p $(BUILDS_DIR)/bin
	@cp -f $(SCOTCH_DIR)/bin/gpart $(SCOTCH_DIR)/bin/gord $(SCOTCH_DIR)/bin/gmap $(BUILDS_DIR)/bin/
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.$(SHARED_EXT) $(BUILDS_DIR)/bin/
	@echo "Building parallel reference tools (dgpart, dgord)..."
	@cd $(SCOTCH_SRC) && $(MAKE) ptscotch || echo "⚠ ptscotch build failed (no MPI?) — parallel differential tier will skip"
	@cp -f $(SCOTCH_DIR)/bin/dgpart $(SCOTCH_DIR)/bin/dgord $(BUILDS_DIR)/bin/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/lib/lib*ptscotch*.$(SHARED_EXT) $(BUILDS_DIR)/bin/ 2>/dev/null || true
	@echo "✓ Reference tools ready: $(BUILDS_DIR)/bin/ (gpart, gord, gmap; dgpart, dgord if MPI)"

# Regenerate the committed docs API catalog (docs/site/api_data.json). Run this
# whenever you add/remove/rename a public method, change a signature, or edit a
# method's one-line summary — otherwise the "Verify docs API data" CI job fails.
# This MUST match that job's environment or it produces a stale-in-CI file: the
# catalog embeds the loaded Scotch version and the set of available (parallel)
# symbols, so it needs a fresh 64-bit build (not a stray ~/.local one — hence
# the pinned PYSCOTCH_LIB_DIR) built WITH parallel, and Python >= 3.14 (older
# stringifies annotations differently; gen_api.py errors out if so).
docs-api: build-64
	PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1 \
	PYSCOTCH_LIB_DIR=$(CURDIR)/$(BUILDS_DIR)/lib64 \
	LD_LIBRARY_PATH=$(CURDIR)/$(BUILDS_DIR)/lib64:$$LD_LIBRARY_PATH \
	$(DOCS_PYTHON) docs/site/gen_api.py --dump
	@echo "✓ Regenerated docs/site/api_data.json — commit it alongside the API change."

# Differential tier: byte-compare PyScotch's outputs against gpart/gord/gmap
# (and dgpart/dgord under mpirun) driving the same library (requires
# build-reference-tools; the parallel tier also needs the suffixed lib32 from build-all).
# 32-bit on purpose: it matches the stock Makefile.inc int size the reference
# binaries were built with. PYSCOTCH_LIB_DIR is pinned to the fresh lib32 so a
# stray wheel-layout pyscotch/_libs/lib32 (older Scotch) cannot shadow it and
# make the tier compare two different Scotch versions. The deterministic knobs must be set before the
# pytest session starts — the tests skip (never silently pass) when a binary,
# the parallel lib dir, or mpirun is missing.
test-differential:
	PYSCOTCH_INT_SIZE=32 PYSCOTCH_PARALLEL=0 \
	PYSCOTCH_LIB_DIR=$(CURDIR)/$(BUILDS_DIR)/lib32 \
	SCOTCH_PTHREAD_NUMBER=1 SCOTCH_DETERMINISTIC=1 \
	PYSCOTCH_GPART=$(CURDIR)/$(BUILDS_DIR)/bin/gpart \
	PYSCOTCH_GORD=$(CURDIR)/$(BUILDS_DIR)/bin/gord \
	PYSCOTCH_GMAP=$(CURDIR)/$(BUILDS_DIR)/bin/gmap \
	PYSCOTCH_DGPART=$(CURDIR)/$(BUILDS_DIR)/bin/dgpart \
	PYSCOTCH_DGORD=$(CURDIR)/$(BUILDS_DIR)/bin/dgord \
	PYSCOTCH_PAR_LIB_DIR=$(CURDIR)/$(BUILDS_DIR)/lib32 \
	PYSCOTCH_PAR_INT_SIZE=32 \
	PYSCOTCH_MPI_OVERSUBSCRIBE=1 \
	LD_LIBRARY_PATH=$(CURDIR)/$(BUILDS_DIR)/bin:$$LD_LIBRARY_PATH \
	pytest tests/pyscotch_base/test_differential.py \
	       tests/scotch_ports_mpi/test_differential_parallel.py -v

# Ensure the submodule exists, then prepare the disposable patched copy that
# builds compile in (see the Directories comment above). Version detection,
# patch selection and idempotency all live in pyscotch/scotch_build.py —
# one implementation shared with `pyscotch scotch build`.
check-submodule:
	@if [ ! -d "$(SCOTCH_SUBMODULE)" ] || [ ! -f "$(SCOTCH_SUBMODULE)/README.md" ]; then \
		echo "Scotch submodule not initialized. Initializing..."; \
		git submodule update --init --recursive; \
		echo "✓ Submodule initialized"; \
	fi
	@$(PYTHON) -m pyscotch.cli scotch prepare --source $(SCOTCH_SUBMODULE) --dest $(SCOTCH_DIR)
	@if [ ! -f "$(SCOTCH_SRC)/Makefile.inc" ]; then \
		echo "Creating default Makefile.inc..."; \
		cp patches/Makefile.inc.default $(SCOTCH_SRC)/Makefile.inc; \
		echo "✓ Makefile.inc created"; \
	fi
	@echo "✓ Patched source copy ready"

# Install Python package
install:
	pip install -e .

# Run tests (64-bit parallel by default, skip slow hypothesis tests)
test:
	PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1 pytest tests/ -v --ignore=tests/hypothesis/

# Run full test suite including hypothesis property tests
test-full:
	PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1 pytest tests/ -v

# Run all 4 variants (32/64-bit × sequential/parallel) with hypothesis
test-quadrant:
	@echo "========================================"
	@echo "[1/4] Testing 32-bit sequential"
	@echo "========================================"
	PYSCOTCH_INT_SIZE=32 PYSCOTCH_PARALLEL=0 pytest tests/ -v
	@echo ""
	@echo "========================================"
	@echo "[2/4] Testing 32-bit parallel"
	@echo "========================================"
	PYSCOTCH_INT_SIZE=32 PYSCOTCH_PARALLEL=1 pytest tests/ -v
	@echo ""
	@echo "========================================"
	@echo "[3/4] Testing 64-bit sequential"
	@echo "========================================"
	PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=0 pytest tests/ -v
	@echo ""
	@echo "========================================"
	@echo "[4/4] Testing 64-bit parallel"
	@echo "========================================"
	PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1 pytest tests/ -v
	@echo ""
	@echo "✓ All 4 variants tested successfully!"

# Clean Python build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Clean Scotch builds (removes the disposable source copy too; the pristine
# submodule is never touched)
clean-scotch:
	rm -rf $(SCOTCH_DIR)
	rm -rf $(BUILDS_DIR)
	rm -rf lib lib32 lib64 include include32 include64

# Full clean
distclean: clean clean-scotch
	rm -rf $(SCOTCH_DIR)
