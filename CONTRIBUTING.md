# Contributing to Subtitle

Thank you for your interest in contributing to the Subtitle project! This guide will help you get started.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/innovatorved/subtitle.git
   cd subtitle
   ```

2. **Set up Whisper.cpp**
   ```bash
   ./setup_whisper.sh
   ```

3. **Create conda environment**
   ```bash
   conda env create -f environment.yml
   conda activate subtitle
   ```

4. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest black flake8 mypy
   ```

## Code Style

We follow these conventions:

- **Formatter**: [Black](https://github.com/psf/black) with default settings
- **Linter**: [Flake8](https://flake8.pycqa.org/) for style checking
- **Type hints**: Use type annotations for function signatures
- **Docstrings**: Google-style docstrings for public functions and classes

### Running Code Quality Checks

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

## Testing

All changes must include tests. We use [pytest](https://pytest.org/) for testing.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_batch_processor.py -v
```

### Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests
├── e2e/            # End-to-end tests
└── fixtures/       # Shared test fixtures
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** from `master`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with tests
4. **Run tests and linting** to ensure quality
5. **Commit** with a descriptive message (see below)
6. **Push** and open a Pull Request

### Commit Message Format

Use clear, descriptive commit messages:

```
<type>: <short description>

[optional body with more details]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

**Examples:**
```
feat: add ASS subtitle format support
fix: handle missing ffmpeg gracefully
docs: add troubleshooting guide
test: add tests for batch processor
```

## Reporting Issues

When reporting bugs, please include:

1. Python version and OS
2. Steps to reproduce
3. Expected vs actual behavior
4. Error messages or logs

## Questions?

Feel free to open an issue for questions or reach out at vedgupta@protonmail.com.

---

Thank you for contributing! 🎉
