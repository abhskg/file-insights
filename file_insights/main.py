#!/usr/bin/env python3
"""
Main entry point for the file-insights tool.
"""

import sys
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from file_insights.parser import FileParser
from file_insights.insights import InsightGenerator

# Import DatabaseManager, but handle potential import errors
try:
    import psycopg
    from file_insights.database import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    DATABASE_IMPORT_ERROR = str(e)

console = Console()


@click.group()
def cli():
    """File Insights - Analyze and get insights about files in directories."""
    pass


@cli.command()
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
@click.option(
    "--video-metadata/--no-video-metadata",
    default=False,
    help="Extract metadata for video files",
)
@click.option(
    "--db-save",
    is_flag=True,
    help="Save results to database",
)
@click.option(
    "--db-connection",
    help="Database connection string. If not provided, uses DATABASE_URL environment variable.",
)
@click.option(
    "--rebuild-db",
    is_flag=True,
    help="Rebuild the database schema (drops all existing data)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Print verbose debug information",
)
@click.option(
    "--debug-video",
    is_flag=True,
    help="Extra debugging for video metadata extraction",
)
def scan(
    directory: str,
    output: Optional[str] = None,
    recursive: bool = True,
    exclude: tuple = (),
    video_metadata: bool = False,
    db_save: bool = False,
    db_connection: Optional[str] = None,
    rebuild_db: bool = False,
    verbose: bool = False,
    debug_video: bool = False,
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
        
        # Configure video metadata extraction if requested
        if video_metadata:
            console.print("[bold]Video metadata extraction enabled[/bold]")
            if debug_video:
                console.print("[yellow]Video debugging mode enabled - will print detailed info[/yellow]")
            parser.set_extract_video_metadata(True)
            
        files = parser.parse_directory(Path(directory))

        console.print(f"[green]Found {len(files)} files[/green]")
        
        # Print debug info about video files if verbose
        if (verbose or debug_video) and video_metadata:
            video_files = [f for f in files if f.is_video]
            console.print(f"[yellow]Found {len(video_files)} video files[/yellow]")
            
            videos_with_metadata = [v for v in video_files if v.has_video_metadata]
            console.print(f"[yellow]Successfully extracted metadata for {len(videos_with_metadata)} videos[/yellow]")
            
            if videos_with_metadata:
                console.print("[dim]Example metadata from videos:")
                for video in videos_with_metadata[:3]:  # Show just a few examples
                    console.print(f"[dim]- {video.name}: Duration={video.video_duration}, Resolution={video.video_resolution}, FPS={video.video_fps}[/dim]")
            else:
                console.print("[bold red]No videos had metadata extracted! Check file formats and permissions.[/bold red]")

        # Save to database if requested
        if db_save:
            if not DATABASE_AVAILABLE:
                console.print(f"[bold red]Database functionality not available:[/bold red] {DATABASE_IMPORT_ERROR}")
                console.print("[yellow]Install PostgreSQL and psycopg with binary extras:[/yellow]")
                console.print("[yellow]poetry remove psycopg && poetry add 'psycopg[binary]'[/yellow]")
                console.print("[yellow]Continuing with insights generation...[/yellow]")
            else:
                try:
                    console.print("[bold]Saving to database...[/bold]")
                    db_manager = DatabaseManager(connection_string=db_connection)
                    
                    # Test DB connection first
                    db_manager.test_connection()
                    console.print("[green]Database connection successful[/green]")
                    
                    if rebuild_db:
                        console.print("[bold yellow]Rebuilding database schema (all existing data will be lost)[/bold yellow]")
                        console.print("[yellow]This is necessary if the database structure has changed (like adding duration field)[/yellow]")
                    
                    db_manager.initialize_database(rebuild=rebuild_db)
                    console.print("[green]Database schema initialized[/green]")
                    
                    if verbose:
                        console.print(f"[yellow]Saving {len(files)} files to database...[/yellow]")
                        if video_metadata:
                            video_count = sum(1 for f in files if f.is_video)
                            videos_with_duration = sum(1 for f in files if f.is_video and hasattr(f, 'video_duration') and f.video_duration is not None)
                            console.print(f"[yellow]Including {video_count} video files ({videos_with_duration} with duration information)[/yellow]")
                    
                    saved_count = db_manager.store_file_infos(files)
                    console.print(f"[green]Saved {saved_count} files to database[/green]")
                    
                    # Verify video storage if verbose
                    if verbose and video_metadata:
                        video_count = db_manager.count_files(video_only=True)
                        
                        # Check if the count matches
                        videos_in_files = sum(1 for f in files if f.is_video)
                        if video_count != videos_in_files:
                            console.print(f"[bold yellow]Warning: Found {videos_in_files} videos but saved {video_count} to database[/bold yellow]")
                        else:
                            console.print(f"[green]Successfully saved all {video_count} video files in database[/green]")
                            
                        # Now query the database to check for video metadata
                        with psycopg.connect(db_connection or os.environ.get("DATABASE_URL")) as conn:
                            with conn.cursor() as cur:
                                cur.execute("SELECT COUNT(*) FROM video_metadata")
                                video_metadata_count = cur.fetchone()[0]
                                
                                if video_metadata_count == 0:
                                    console.print("[bold red]No entries in video_metadata table![/bold red]")
                                    console.print("[yellow]This may indicate a problem with metadata extraction or storage[/yellow]")
                                else:
                                    console.print(f"[green]Found {video_metadata_count} entries in video_metadata table[/green]")
                                    
                                    # Check for files with duration
                                    cur.execute("SELECT COUNT(*) FROM files WHERE duration > 0")
                                    duration_count = cur.fetchone()[0]
                                    console.print(f"[green]Found {duration_count} files with duration > 0 in files table[/green]")
                        
                except Exception as e:
                    console.print(f"[bold red]Database error:[/bold red] {str(e)}")
                    console.print("[yellow]Continuing with insights generation...[/yellow]")

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
        if verbose:
            import traceback
            console.print("[bold red]Detailed error:[/bold red]")
            console.print(traceback.format_exc())
        return 1


@cli.command()
@click.option(
    "--limit",
    type=int,
    default=1000,
    help="Maximum number of files to retrieve",
)
@click.option(
    "--video-only",
    is_flag=True,
    help="Only retrieve video files",
)
@click.option(
    "--extension",
    "-e",
    multiple=True,
    help="Filter by file extension (can be used multiple times)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Output file to save insights",
)
@click.option(
    "--db-connection",
    help="Database connection string. If not provided, uses DATABASE_URL environment variable.",
)
def db_insights(
    limit: int = 1000,
    video_only: bool = False,
    extension: tuple = (),
    output: Optional[str] = None,
    db_connection: Optional[str] = None,
):
    """
    Generate insights from files stored in the database.
    """
    console.print(Panel.fit("File Insights Tool - Database Mode", style="bold blue"))

    if not DATABASE_AVAILABLE:
        console.print(f"[bold red]Database functionality not available:[/bold red] {DATABASE_IMPORT_ERROR}")
        console.print("[yellow]Install PostgreSQL and psycopg with binary extras:[/yellow]")
        console.print("[yellow]poetry remove psycopg && poetry add 'psycopg[binary]'[/yellow]")
        return 1

    try:
        # Connect to database
        console.print("[bold]Connecting to database...[/bold]")
        db_manager = DatabaseManager(connection_string=db_connection)
        
        # Initialize database if needed
        db_manager.initialize_database()
        
        # Count files before retrieval
        total_count = db_manager.count_files(video_only=video_only)
        console.print(f"[green]Database contains {total_count} {'video ' if video_only else ''}files[/green]")
        
        if total_count == 0:
            console.print("[yellow]No files found in database. Run 'scan --db-save' to add files.[/yellow]")
            return 0
            
        # Retrieve files
        extension_list = list(extension) if extension else None
        console.print(f"[bold]Retrieving up to {limit} files from database...[/bold]")
        files = db_manager.retrieve_file_infos(
            limit=limit,
            video_only=video_only,
            extension_filter=extension_list
        )

        console.print(f"[green]Retrieved {len(files)} files[/green]")

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


@cli.command()
@click.option(
    "--db-connection",
    help="Database connection string. If not provided, uses DATABASE_URL environment variable.",
)
@click.confirmation_option(
    prompt="Are you sure you want to delete all files from the database?"
)
def db_clear(db_connection: Optional[str] = None):
    """
    Clear all files from the database.
    """
    console.print(Panel.fit("File Insights Tool - Database Clear", style="bold red"))

    if not DATABASE_AVAILABLE:
        console.print(f"[bold red]Database functionality not available:[/bold red] {DATABASE_IMPORT_ERROR}")
        console.print("[yellow]Install PostgreSQL and psycopg with binary extras:[/yellow]")
        console.print("[yellow]poetry remove psycopg && poetry add 'psycopg[binary]'[/yellow]")
        return 1

    try:
        # Connect to database
        console.print("[bold]Connecting to database...[/bold]")
        db_manager = DatabaseManager(connection_string=db_connection)
        
        # Delete all files
        deleted_count = db_manager.delete_all_files()
        console.print(f"[green]Deleted {deleted_count} files from database[/green]")

        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


def main():
    """Entry point for the CLI."""
    return cli()


if __name__ == "__main__":
    sys.exit(main())
