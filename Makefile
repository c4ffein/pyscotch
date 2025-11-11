# Makefile for building PT-Scotch and PyScotch

# Directories
SCOTCH_DIR = external/scotch
SCOTCH_SRC = $(SCOTCH_DIR)/src
BUILDS_DIR = scotch-builds

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
.PHONY: all build-all build-32 build-64 clean clean-scotch install test help

help:
	@echo "PyScotch Build System"
	@echo "====================="
	@echo ""
	@echo "Build targets:"
	@echo "  make build-all    - Build all 4 variants (scotch+ptscotch × 32+64-bit)"
	@echo "  make build-32     - Build both scotch and ptscotch with 32-bit integers"
	@echo "  make build-64     - Build both scotch and ptscotch with 64-bit integers"
	@echo ""
	@echo "Output structure:"
	@echo "  scotch-builds/lib32/  - Sequential & parallel libraries (32-bit)"
	@echo "  scotch-builds/lib64/  - Sequential & parallel libraries (64-bit)"
	@echo "  scotch-builds/inc32/  - Headers (32-bit: SCOTCH_Num = int)"
	@echo "  scotch-builds/inc64/  - Headers (64-bit: SCOTCH_Num = int64_t)"
	@echo ""
	@echo "Patches:"
	@echo "  Temporary patches in patches/ are auto-applied during build"
	@echo "  See patches/README.md for details"
	@echo ""
	@echo "Other targets:"
	@echo "  make install         - Install Python package"
	@echo "  make test            - Run tests"
	@echo "  make clean           - Clean Python build artifacts"
	@echo "  make clean-scotch    - Clean all Scotch builds"
	@echo "  make check-submodule - Gets Scotch as a submodule (and auto-applies the temporary fix)"
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
	@echo "[1/2] Building sequential scotch (32-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) scotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DSCOTCH_NAME_SUFFIX=_32 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "[2/2] Building parallel ptscotch (32-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) ptscotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DSCOTCH_NAME_SUFFIX=_32 -DSCOTCH_RENAME_ALL" || true
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
	@echo "[1/2] Building sequential scotch (64-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) scotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DINTSIZE64 -DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "[2/2] Building parallel ptscotch (64-bit + suffix)..."
	@cd $(SCOTCH_SRC) && \
		$(MAKE) ptscotch CFLAGS="$$(grep '^CFLAGS' Makefile.inc | cut -d= -f2-) -DINTSIZE64 -DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL" || true
	@echo ""
	@echo "Copying 64-bit libraries and headers..."
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.$(SHARED_EXT) $(BUILDS_DIR)/lib64/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/lib/lib*scotch*.a $(BUILDS_DIR)/lib64/ 2>/dev/null || true
	@cp -f $(SCOTCH_DIR)/include/*.h $(BUILDS_DIR)/inc64/ 2>/dev/null || true
	@echo "✓ 64-bit build complete: scotch-builds/{lib64,inc64}/"

# Check if scotch submodule exists and apply patches
check-submodule:
	@if [ ! -d "$(SCOTCH_DIR)" ] || [ ! -f "$(SCOTCH_DIR)/README.md" ]; then \
		echo "Error: Scotch submodule not found!"; \
		echo "Please run: git submodule update --init --recursive"; \
		exit 1; \
	fi
	@echo "Checking for required patches..."
	@if ! grep -q "SCOTCH_NUM_MPI.*SCOTCH_NAME_PUBLIC" $(SCOTCH_DIR)/src/libscotch/module.h; then \
		echo "Applying scotch-suffix-fixes.patch..."; \
		cd $(SCOTCH_DIR) && git apply ../../patches/scotch-suffix-fixes.patch && \
		echo "✓ Patch applied successfully"; \
	else \
		echo "✓ Patches already applied"; \
	fi

# Install Python package
install:
	pip install -e .

# Run tests
test:
	pytest tests/ -v

# Clean Python build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Clean Scotch builds
clean-scotch:
	@if [ -f "$(SCOTCH_SRC)/Makefile" ]; then \
		cd $(SCOTCH_SRC) && $(MAKE) realclean; \
	fi
	rm -rf $(BUILDS_DIR)
	rm -rf lib lib32 lib64 include include32 include64

# Full clean
distclean: clean clean-scotch
	rm -rf $(SCOTCH_DIR)
