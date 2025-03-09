"""
Tests for the file_insights.insights module.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import TestCase

from file_insights.parser import FileInfo
from file_insights.insights import InsightGenerator, Insights


class TestInsights(TestCase):
    """Test cases for the InsightGenerator and Insights classes."""
    
    def setUp(self):
        """Set up test data."""
        now = datetime.now()
        
        # Create some sample FileInfo objects
        self.test_files = [
            FileInfo(
                path=Path('/test/file1.txt'),
                size=100,
                extension='.txt',
                created_time=now - timedelta(days=10),
                modified_time=now - timedelta(days=10),
                content_preview="This is a text file"
            ),
            FileInfo(
                path=Path('/test/file2.py'),
                size=200,
                extension='.py',
                created_time=now - timedelta(days=5),
                modified_time=now - timedelta(days=5),
                content_preview="print('Hello')"
            ),
            FileInfo(
                path=Path('/test/subdir/file3.py'),
                size=300,
                extension='.py',
                created_time=now - timedelta(days=1),
                modified_time=now - timedelta(days=1),
                content_preview="def main(): pass"
            ),
            FileInfo(
                path=Path('/test/subdir/file4.jpg'),
                size=1000,
                extension='.jpg',
                created_time=now - timedelta(hours=12),
                modified_time=now - timedelta(hours=12),
                content_preview=None
            ),
        ]
    
    def test_general_statistics(self):
        """Test general statistics generation."""
        generator = InsightGenerator(self.test_files)
        insights = generator.generate_insights()
        
        stats = insights.data["general_stats"]
        
        self.assertEqual(stats["total_files"], 4)
        self.assertEqual(stats["total_size"], 1600)  # Sum of all file sizes
        self.assertEqual(stats["average_size"], 400)  # 1600 / 4
        
        # Verify newest and oldest files
        self.assertIn("file4.jpg", stats["newest_file"])
        self.assertIn("file1.txt", stats["oldest_file"])
        
        # Verify directory count
        self.assertEqual(stats["total_directories"], 2)  # /test and /test/subdir
    
    def test_file_type_statistics(self):
        """Test file type statistics generation."""
        generator = InsightGenerator(self.test_files)
        insights = generator.generate_insights()
        
        file_types = insights.data["file_types"]
        
        # Find statistics for each extension
        txt_stats = next((t for t in file_types if t["extension"] == ".txt"), None)
        py_stats = next((t for t in file_types if t["extension"] == ".py"), None)
        jpg_stats = next((t for t in file_types if t["extension"] == ".jpg"), None)
        
        # Verify counts
        self.assertEqual(txt_stats["count"], 1)
        self.assertEqual(py_stats["count"], 2)
        self.assertEqual(jpg_stats["count"], 1)
        
        # Verify sizes
        self.assertEqual(txt_stats["size"], 100)
        self.assertEqual(py_stats["size"], 500)  # 200 + 300
        self.assertEqual(jpg_stats["size"], 1000)
        
        # Verify percentages
        self.assertAlmostEqual(txt_stats["percentage"], 6.25)  # 100/1600 * 100
        self.assertAlmostEqual(py_stats["percentage"], 31.25)  # 500/1600 * 100
        self.assertAlmostEqual(jpg_stats["percentage"], 62.5)  # 1000/1600 * 100
    
    def test_age_distribution(self):
        """Test age distribution generation."""
        generator = InsightGenerator(self.test_files)
        insights = generator.generate_insights()
        
        age_dist = insights.data["age_distribution"]
        
        # One file less than 24 hours old
        self.assertEqual(age_dist["Last 24 hours"], 1)
        
        # One file between 1-7 days old
        self.assertEqual(age_dist["Last 7 days"], 1)
        
        # One file between 7-30 days old
        self.assertEqual(age_dist["Last 30 days"], 2)
    
    def test_save_insights(self):
        """Test saving insights to a file."""
        generator = InsightGenerator(self.test_files)
        insights = generator.generate_insights()
        
        # Create a temporary file to save insights
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Save insights
            insights.save(temp_path)
            
            # Read the saved file
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            # Verify data was saved correctly
            self.assertEqual(saved_data["general_stats"]["total_files"], 4)
            self.assertEqual(len(saved_data["file_types"]), 3)  # txt, py, jpg
            
        finally:
            # Clean up
            Path(temp_path).unlink() 