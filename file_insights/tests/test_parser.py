"""
Tests for the file_insights.parser module.
"""

import os
import tempfile
from pathlib import Path
from unittest import TestCase

from file_insights.parser import FileParser, FileInfo


class TestFileParser(TestCase):
    """Test cases for the FileParser class."""

    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create a simple file structure for testing
        self.test_files = {
            "file1.txt": "This is file 1",
            "file2.py": 'print("Hello, World!")',
            "subdir/file3.md": "# Markdown File",
            "subdir/nested/file4.json": '{"key": "value"}',
        }

        for file_path, content in self.test_files.items():
            full_path = self.temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    def test_parse_directory_recursive(self):
        """Test parsing a directory recursively."""
        parser = FileParser(recursive=True)
        results = parser.parse_directory(self.temp_path)

        # Should find all 4 files
        self.assertEqual(len(results), 4)

        # Check that all expected files are found
        paths = {str(result.path.relative_to(self.temp_path)) for result in results}
        expected_paths = set(self.test_files.keys())
        self.assertEqual(paths, expected_paths)

    def test_parse_directory_non_recursive(self):
        """Test parsing a directory non-recursively."""
        parser = FileParser(recursive=False)
        results = parser.parse_directory(self.temp_path)

        # Should only find 2 files in the root directory
        self.assertEqual(len(results), 2)

        # Check that only top-level files are found
        paths = {str(result.path.relative_to(self.temp_path)) for result in results}
        expected_paths = {"file1.txt", "file2.py"}
        self.assertEqual(paths, expected_paths)

    def test_exclude_patterns(self):
        """Test excluding files with patterns."""
        parser = FileParser(recursive=True, exclude_patterns=("*.py", "**/nested/*"))
        results = parser.parse_directory(self.temp_path)

        # Should find 2 files (excluding the .py file and the nested directory)
        self.assertEqual(len(results), 2)

        # Check that the correct files are found
        paths = {str(result.path.relative_to(self.temp_path)) for result in results}
        expected_paths = {"file1.txt", "subdir/file3.md"}
        self.assertEqual(paths, expected_paths)

    def test_file_info_attributes(self):
        """Test that FileInfo objects have the correct attributes."""
        parser = FileParser()
        results = parser.parse_directory(self.temp_path)

        # Find the Python file
        py_file = next(
            result
            for result in results
            if str(result.path.relative_to(self.temp_path)) == "file2.py"
        )

        # Check attributes
        self.assertEqual(py_file.extension, ".py")
        self.assertEqual(py_file.size, len('print("Hello, World!")'))
        self.assertEqual(py_file.name, "file2.py")
        self.assertEqual(py_file.content_preview, 'print("Hello, World!")')
