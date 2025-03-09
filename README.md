# File Insights

A Python tool that recursively parses files in a directory and generates insights about them.

## Features

- Recursively scan directories for files
- Analyze file content, size, type, and other attributes
- Generate detailed insights and statistics about file collections
- Easy-to-use command line interface

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/file-insights.git
cd file-insights

# Install with Poetry
poetry install
```

## Usage

```bash
# Basic usage (scan current directory)
poetry run file-insights ./

# Scan a specific directory with output file
poetry run file-insights ./file-insights /path/to/directory --output insights.json

# Get help with available options
poetry run file-insights ./file-insights --help
```

## Development

```bash
# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Format code
poetry run black .
poetry run isort .
```

## License

MIT 