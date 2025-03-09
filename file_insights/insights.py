"""
Module for generating and displaying insights about collections of files.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import rich
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from file_insights.parser import FileInfo


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

    def _build_tree(self, tree_data: Dict) -> Tree:
        """Build a rich Tree from the tree data."""
        root = Tree("📁 Root")

        def add_node(parent_tree, node_data, path=""):
            for name, value in sorted(node_data.items()):
                current_path = f"{path}/{name}" if path else name
                if isinstance(value, dict):  # Directory
                    branch = parent_tree.add(f"📁 {name}")
                    add_node(branch, value, current_path)
                else:  # File
                    size = format_size(value)
                    parent_tree.add(f"📄 {name} ({size})")

        add_node(root, tree_data)
        return root

    def save(self, output_path: str):
        """Save insights to a JSON file."""
        with open(output_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)


class InsightGenerator:
    """Generates insights from a collection of files."""

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

        return Insights(data)

    def _general_statistics(self) -> Dict:
        """Generate general statistics about the files."""
        if not self.files:
            return {
                "total_files": 0,
                "total_size": 0,
                "average_size": 0,
                "oldest_file": "N/A",
                "newest_file": "N/A",
                "total_directories": 0,
            }

        # Calculate basic stats
        total_size = sum(f.size for f in self.files)
        average_size = total_size / len(self.files) if self.files else 0

        # Find oldest and newest files
        oldest = min(self.files, key=lambda f: f.created_time)
        newest = max(self.files, key=lambda f: f.created_time)

        # Count unique directories
        directories = {f.path.parent for f in self.files}

        return {
            "total_files": len(self.files),
            "total_size": total_size,
            "average_size": average_size,
            "oldest_file": f"{oldest.name} ({oldest.created_time.strftime('%Y-%m-%d')})",
            "newest_file": f"{newest.name} ({newest.created_time.strftime('%Y-%m-%d')})",
            "total_directories": len(directories),
        }

    def _file_type_statistics(self) -> List[Dict]:
        """Generate statistics about file types."""
        # Group files by extension
        files_by_ext = defaultdict(list)
        for file in self.files:
            files_by_ext[file.extension].append(file)

        # Calculate statistics for each extension
        total_size = sum(f.size for f in self.files)
        result = []

        for ext, files in sorted(
            files_by_ext.items(), key=lambda x: sum(f.size for f in x[1]), reverse=True
        ):
            ext_size = sum(f.size for f in files)
            result.append(
                {
                    "extension": ext,
                    "count": len(files),
                    "size": ext_size,
                    "percentage": (ext_size / total_size * 100)
                    if total_size > 0
                    else 0,
                }
            )

        return result

    def _age_distribution(self) -> Dict:
        """Generate statistics about file age distribution."""
        now = datetime.now()
        age_counts = {
            "Last 24 hours": 0,
            "Last 7 days": 0,
            "Last 30 days": 0,
            "Last 90 days": 0,
            "Last year": 0,
            "Older": 0,
        }

        for file in self.files:
            age = (now - file.modified_time).days

            if age < 1:
                age_counts["Last 24 hours"] += 1
            elif age < 7:
                age_counts["Last 7 days"] += 1
            elif age < 30:
                age_counts["Last 30 days"] += 1
            elif age < 90:
                age_counts["Last 90 days"] += 1
            elif age < 365:
                age_counts["Last year"] += 1
            else:
                age_counts["Older"] += 1

        return age_counts

    def _build_file_tree(self) -> Dict:
        """Build a tree representation of the files."""
        result = {}

        for file in self.files:
            # Get the parts of the path relative to the common base
            parts = file.path.parts

            # Navigate the tree and create necessary nodes
            current = result
            for i, part in enumerate(parts[:-1]):  # Process directories
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add the file with its size
            current[parts[-1]] = file.size

        return result


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0 or unit == "TB":
            break
        size_bytes /= 1024.0

    return f"{size_bytes:.2f} {unit}"
