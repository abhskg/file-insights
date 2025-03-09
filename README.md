# File Insights

A Python tool that recursively parses directories and generates insights about files.

## Features

- Recursively scan directories for files
- Analyze file content, size, type, and other attributes
- Generate detailed insights and statistics about file collections
- Extract and analyze video metadata (duration, resolution, codec, etc.)
- Store and retrieve file information in PostgreSQL database
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

### Basic Usage

```bash
# Basic usage (scan current directory)
poetry run file-insights scan ./

# Scan a specific directory with output file
poetry run file-insights scan /path/to/directory --output insights.json

# Extract video metadata while scanning
poetry run file-insights scan /path/to/directory --video-metadata

# Get help with available options
poetry run file-insights --help
```

### Database Integration

File Insights can store file metadata in a PostgreSQL database for persistent storage and retrieval:

```bash
# Scan directory and save to database
poetry run file-insights scan /path/to/directory --db-save

# Specify a custom database connection string
poetry run file-insights scan /path/to/directory --db-save --db-connection "postgresql://user:password@localhost:5432/fileinsights"

# Generate insights from files stored in the database
poetry run file-insights db-insights

# Get insights for only video files in the database
poetry run file-insights db-insights --video-only

# Filter by file extension
poetry run file-insights db-insights --extension .mp4 --extension .avi

# Clear all data from the database
poetry run file-insights db-clear
```

#### Database Configuration

You can provide a database connection string in two ways:

1. Set the `DATABASE_URL` environment variable:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost:5432/fileinsights"
   ```

2. Use the `--db-connection` command-line option:
   ```bash
   poetry run file-insights scan --db-save --db-connection "postgresql://user:password@localhost:5432/fileinsights"
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
poetry run file-insights scan /path/to/directory --video-metadata
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