# Contributing to PyScotch

Thank you for your interest in contributing to PyScotch!

## Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd pyscotch
```

2. Add the Scotch submodule:
```bash
git submodule add https://gitlab.inria.fr/scotch/scotch.git external/scotch
git submodule update --init --recursive
```

3. Build the Scotch library:
```bash
make build-scotch
```

4. Install development dependencies:
```bash
pip install -e ".[dev]"
```

## Building the Library

The project uses a Makefile to build the Scotch library:

```bash
# Build sequential Scotch
make build-scotch

# Build parallel PT-Scotch
make build-ptscotch

# Build both
make all

# Clean build artifacts
make clean-scotch
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Maximum line length: 100 characters
- Use Black for formatting: `black pyscotch/`
- Run flake8 for linting: `flake8 pyscotch/`

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=pyscotch --cov-report=html

# Run specific test file
pytest tests/test_graph.py -v
```

Note: Tests require the Scotch library to be built first.

## Documentation

- Add docstrings to all public functions and classes
- Follow Google-style docstring format
- Update API.md when adding new features
- Add examples for significant new features

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation
7. Commit with clear messages
8. Push to your fork
9. Open a pull request

## Commit Message Guidelines

- Use present tense: "Add feature" not "Added feature"
- Use imperative mood: "Move cursor to..." not "Moves cursor to..."
- Reference issues and pull requests when relevant
- First line: brief summary (50 chars or less)
- Followed by blank line and detailed description if needed

## Adding New Features

When adding new PT-Scotch functionality:

1. Add low-level bindings in `libscotch.py`
2. Create or update high-level Python class
3. Add CLI command if appropriate (in `cli.py`)
4. Write tests
5. Update documentation
6. Add example if helpful

## Project Structure

```
pyscotch/
├── pyscotch/           # Main package
│   ├── __init__.py     # Package initialization
│   ├── libscotch.py    # Low-level C bindings
│   ├── graph.py        # Graph class
│   ├── mesh.py         # Mesh class
│   ├── strategy.py     # Strategy class
│   ├── arch.py         # Architecture class
│   ├── mapping.py      # Mapping class
│   ├── ordering.py     # Ordering class
│   └── cli.py          # Command-line interface
├── tests/              # Test files
├── examples/           # Example scripts
├── docs/               # Documentation
├── external/           # External dependencies
│   └── scotch/         # Scotch submodule
├── Makefile           # Build system
└── setup.py           # Package configuration
```

## Questions?

Feel free to open an issue for:
- Bug reports
- Feature requests
- Questions about usage or development
- Documentation improvements

Thank you for contributing!
