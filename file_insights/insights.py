"""
Module for generating and displaying insights about collections of files.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import rich
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from file_insights.parser import FileInfo
from file_insights.video import display_video_insights


class Insights:
    """Container for file insights data and display methods."""

    def __init__(self, data: Dict):
        self.data = data
        self.console = Console()

    def display(self):
        """Display the insights in a formatted way."""
        # General statistics
        self.console.print(Panel.fit("📊 [bold]File Insights[/bold]", style="blue"))

        stats = self.data["general_stats"]
        stats_table = Table(title="General Statistics")
        stats_table.add_column("Statistic", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Total Files", str(stats["total_files"]))
        stats_table.add_row("Total Size", format_size(stats["total_size"]))
        stats_table.add_row("Average File Size", format_size(stats["average_size"]))
        stats_table.add_row("Oldest File", stats["oldest_file"])
        stats_table.add_row("Newest File", stats["newest_file"])
        stats_table.add_row("Total Directories", str(stats["total_directories"]))

        self.console.print(stats_table)

        # File types
        type_table = Table(title="File Types")
        type_table.add_column("Extension", style="cyan")
        type_table.add_column("Count", style="green")
        type_table.add_column("Total Size", style="green")
        type_table.add_column("Percentage", style="green")

        for ext_data in self.data["file_types"]:
            type_table.add_row(
                ext_data["extension"] or "(no extension)",
                str(ext_data["count"]),
                format_size(ext_data["size"]),
                f"{ext_data['percentage']:.1f}%",
            )

        self.console.print(type_table)

        # File age distribution
        self.console.print(
            Panel.fit("📅 [bold]File Age Distribution[/bold]", style="yellow")
        )
        for period, count in self.data["age_distribution"].items():
            self.console.print(f"[cyan]{period}:[/cyan] {count} files")

        # Display file tree if not too large
        if len(self.data["file_tree"]) <= 100:  # Limit to avoid overwhelming output
            file_tree = self._build_tree(self.data["file_tree"])
            self.console.print("\n[bold]File Tree:[/bold]")
            self.console.print(file_tree)

        # Add video statistics if available
        if "video_stats" in self.data and self.data["video_stats"]["total_videos"] > 0:
            display_video_insights(self.console, self.data["video_stats"])

    def _build_tree(self, tree_data: Dict) -> Tree:
        """Build a rich Tree from the tree data."""
        root_tree = Tree("📁 [bold]Root[/bold]")

        def add_node(parent_tree, node_data, path=""):
            for name, data in sorted(node_data.items()):
                if isinstance(data, dict):  # Directory
                    subpath = f"{path}/{name}" if path else name
                    subdir = parent_tree.add(f"📁 [blue]{name}[/blue]")
                    add_node(subdir, data, subpath)
                else:  # File
                    filesize = data[0]
                    extension = data[1]
                    icon = "📄"
                    parent_tree.add(
                        f"{icon} [green]{name}[/green] ({format_size(filesize)})"
                    )

        add_node(root_tree, tree_data)
        return root_tree

    def save(self, output_path: str):
        """Save insights to a JSON file."""
        # Convert data to a serializable format
        data_copy = json.loads(json.dumps(self.data, default=str))

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data_copy, f, indent=2)


class InsightGenerator:
    """Generate insights from a collection of files."""

    def __init__(self, files: List[FileInfo]):
        self.files = files

    def generate_insights(self) -> Insights:
        """Generate insights from the files."""
        data = {
            "general_stats": self._general_statistics(),
            "file_types": self._file_type_statistics(),
            "age_distribution": self._age_distribution(),
            "file_tree": self._build_file_tree(),
        }
        
        # Add video statistics if video files are present
        video_files = [f for f in self.files if f.is_video]
        if video_files:
            from file_insights.video import generate_video_statistics
            data["video_stats"] = generate_video_statistics(video_files)
            
        return Insights(data)

    def _general_statistics(self) -> Dict:
        """Generate general statistics about the files."""
        total_files = len(self.files)
        if total_files == 0:
            return {
                "total_files": 0,
                "total_size": 0,
                "average_size": 0,
                "oldest_file": "N/A",
                "newest_file": "N/A",
                "total_directories": 0,
            }

        total_size = sum(f.size for f in self.files)
        average_size = total_size / total_files if total_files > 0 else 0

        # Find oldest and newest files
        oldest_file = min(self.files, key=lambda f: f.created_time)
        newest_file = max(self.files, key=lambda f: f.created_time)

        # Count unique directories
        directories = {f.path.parent for f in self.files}
        total_directories = len(directories)

        return {
            "total_files": total_files,
            "total_size": total_size,
            "average_size": average_size,
            "oldest_file": f"{oldest_file.name} ({oldest_file.created_time.strftime('%Y-%m-%d')})",
            "newest_file": f"{newest_file.name} ({newest_file.created_time.strftime('%Y-%m-%d')})",
            "total_directories": total_directories,
        }

    def _file_type_statistics(self) -> List[Dict]:
        """Generate statistics about file types."""
        if not self.files:
            return []

        # Group files by extension
        extension_groups = defaultdict(list)
        for file_info in self.files:
            extension_groups[file_info.extension].append(file_info)

        # Calculate stats for each extension
        total_size = sum(f.size for f in self.files)
        results = []

        for ext, files in sorted(extension_groups.items(), key=lambda x: len(x[1]), reverse=True):
            ext_size = sum(f.size for f in files)
            percentage = (ext_size / total_size) * 100 if total_size > 0 else 0

            results.append(
                {
                    "extension": ext,
                    "count": len(files),
                    "size": ext_size,
                    "percentage": percentage,
                }
            )

        return results

    def _age_distribution(self) -> Dict:
        """Group files by age."""
        if not self.files:
            return {}

        now = datetime.now()
        age_distribution = {
            "Last 24 hours": 0,
            "Last week": 0,
            "Last month": 0,
            "Last year": 0,
            "Older": 0,
        }

        for file_info in self.files:
            age = (now - file_info.created_time).total_seconds()

            if age < 86400:  # 24 hours
                age_distribution["Last 24 hours"] += 1
            elif age < 604800:  # 1 week
                age_distribution["Last week"] += 1
            elif age < 2592000:  # 30 days
                age_distribution["Last month"] += 1
            elif age < 31536000:  # 365 days
                age_distribution["Last year"] += 1
            else:
                age_distribution["Older"] += 1

        # Remove empty categories
        return {k: v for k, v in age_distribution.items() if v > 0}

    def _build_file_tree(self) -> Dict:
        """Build a tree representation of files."""
        tree = {}

        for file_info in self.files:
            parts = file_info.path.parts
            
            # Skip the first part if it's a drive letter or root
            start_idx = 0
            if parts and (parts[0].endswith(":\\") or parts[0] == "/"):
                start_idx = 1
                
            current = tree
            # Navigate to the correct spot in the tree
            for part in parts[start_idx:-1]:  # All but the last part (filename)
                if part not in current:
                    current[part] = {}
                current = current[part]
                
            # Add the file with its size
            current[file_info.path.name] = (
                file_info.size,
                file_info.extension,
            )

        return tree


def format_size(size_bytes: int) -> str:
    """Format bytes as a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
