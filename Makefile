# Makefile for building PT-Scotch and PyScotch

# Directories
SCOTCH_DIR = external/scotch
SCOTCH_SRC = $(SCOTCH_DIR)/src
SCOTCH_BUILD = $(SCOTCH_DIR)/build
LIB_DIR = lib
INCLUDE_DIR = include

# Compiler settings
CC = gcc
MPICC = mpicc
CFLAGS = -O3 -fPIC -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -DSCOTCH_PTHREAD
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
.PHONY: all build-scotch build-ptscotch clean clean-scotch install test help

help:
	@echo "PyScotch Build System"
	@echo "====================="
	@echo ""
	@echo "Available targets:"
	@echo "  make build-scotch    - Build the Scotch library"
	@echo "  make build-ptscotch  - Build the PT-Scotch library (parallel)"
	@echo "  make all            - Build both Scotch and PT-Scotch"
	@echo "  make install        - Install Python package"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make clean-scotch   - Clean Scotch build"
	@echo "  make test           - Run tests"
	@echo ""

all: build-scotch build-ptscotch

# Create necessary directories
$(LIB_DIR):
	mkdir -p $(LIB_DIR)

$(INCLUDE_DIR):
	mkdir -p $(INCLUDE_DIR)

# Check if scotch submodule exists
check-submodule:
	@if [ ! -d "$(SCOTCH_DIR)" ] || [ ! -f "$(SCOTCH_DIR)/README.md" ]; then \
		echo "Error: Scotch submodule not found!"; \
		echo "Please run: git submodule add https://gitlab.inria.fr/scotch/scotch.git external/scotch"; \
		echo "Then run: git submodule update --init --recursive"; \
		exit 1; \
	fi

# Build Scotch (sequential version)
build-scotch: check-submodule $(LIB_DIR) $(INCLUDE_DIR)
	@echo "Building Scotch library..."
	@if [ -f "$(SCOTCH_SRC)/Makefile" ]; then \
		cd $(SCOTCH_SRC) && \
		$(MAKE) scotch || true; \
	else \
		echo "Warning: Scotch Makefile not found. Creating stub library."; \
		echo "Please ensure the scotch submodule is properly initialized."; \
	fi
	@echo "Copying libraries and headers..."
	@if [ -d "$(SCOTCH_DIR)/lib" ]; then \
		cp -f $(SCOTCH_DIR)/lib/libscotch*.a $(LIB_DIR)/ 2>/dev/null || true; \
		cp -f $(SCOTCH_DIR)/lib/libscotch*.$(SHARED_EXT) $(LIB_DIR)/ 2>/dev/null || true; \
	fi
	@if [ -d "$(SCOTCH_DIR)/include" ]; then \
		cp -f $(SCOTCH_DIR)/include/*.h $(INCLUDE_DIR)/ 2>/dev/null || true; \
	fi
	@echo "Scotch build complete!"

# Build PT-Scotch (parallel version)
build-ptscotch: check-submodule $(LIB_DIR) $(INCLUDE_DIR)
	@echo "Building PT-Scotch library..."
	@if [ -f "$(SCOTCH_SRC)/Makefile" ]; then \
		cd $(SCOTCH_SRC) && \
		$(MAKE) ptscotch || true; \
	else \
		echo "Warning: Scotch Makefile not found. Creating stub library."; \
		echo "Please ensure the scotch submodule is properly initialized."; \
	fi
	@echo "Copying libraries and headers..."
	@if [ -d "$(SCOTCH_DIR)/lib" ]; then \
		cp -f $(SCOTCH_DIR)/lib/libptscotch*.a $(LIB_DIR)/ 2>/dev/null || true; \
		cp -f $(SCOTCH_DIR)/lib/libptscotch*.$(SHARED_EXT) $(LIB_DIR)/ 2>/dev/null || true; \
	fi
	@if [ -d "$(SCOTCH_DIR)/include" ]; then \
		cp -f $(SCOTCH_DIR)/include/*.h $(INCLUDE_DIR)/ 2>/dev/null || true; \
	fi
	@echo "PT-Scotch build complete!"

# Install Python package
install: build-scotch
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

# Clean Scotch build
clean-scotch:
	@if [ -f "$(SCOTCH_SRC)/Makefile" ]; then \
		cd $(SCOTCH_SRC) && $(MAKE) clean; \
	fi
	rm -rf $(LIB_DIR) $(INCLUDE_DIR)

# Full clean
distclean: clean clean-scotch
	rm -rf $(SCOTCH_DIR)
