#!/usr/bin/env python3
"""
Main entry point for the file-insights tool.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from file_insights.parser import FileParser
from file_insights.insights import InsightGenerator

console = Console()


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Output file to save insights",
)
@click.option(
    "--recursive/--no-recursive", default=True, help="Scan directories recursively"
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Patterns to exclude (supports glob patterns)",
)
def main(
    directory: str,
    output: Optional[str] = None,
    recursive: bool = True,
    exclude: tuple = (),
):
    """
    Parse files in DIRECTORY and generate insights.

    If no DIRECTORY is specified, the current directory will be used.
    """
    console.print(Panel.fit("File Insights Tool", style="bold blue"))

    try:
        # Parse the directory
        console.print(f"[bold]Scanning directory:[/bold] {directory}")
        parser = FileParser(recursive=recursive, exclude_patterns=exclude)
        files = parser.parse_directory(Path(directory))

        console.print(f"[green]Found {len(files)} files[/green]")

        # Generate insights
        console.print("[bold]Generating insights...[/bold]")
        generator = InsightGenerator(files)
        insights = generator.generate_insights()

        # Display insights
        insights.display()

        # Save insights if requested
        if output:
            insights.save(output)
            console.print(f"[green]Insights saved to {output}[/green]")

        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
