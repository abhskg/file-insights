# File Insights

A Python tool that recursively parses files in a directory and generates insights about them.

## Features

- Recursively scan directories for files
- Analyze file content, size, type, and other attributes
- Generate detailed insights and statistics about file collections
- Extract and analyze video metadata (duration, resolution, codec, etc.)
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
poetry run file-insights /path/to/directory --output insights.json

# Extract video metadata while scanning
poetry run file-insights /path/to/directory --video-metadata

# Get help with available options
poetry run file-insights --help
```

### Video Metadata

The tool can extract detailed information about video files, including:

- Duration
- Resolution
- Frame rate (FPS)
- Video codec
- Audio codec

To enable video metadata extraction, use the `--video-metadata` flag:

```bash
poetry run file-insights /path/to/directory --video-metadata
```

This feature requires the `moviepy` library, which is automatically installed as a dependency.

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