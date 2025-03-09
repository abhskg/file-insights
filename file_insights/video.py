"""
Module for video file processing and metadata extraction.
"""

from collections import Counter
from typing import Dict, List, Optional, Tuple

from rich.panel import Panel
from rich.table import Table

from file_insights.parser import FileInfo
from file_insights.constants import COMMON_VIDEO_EXTENSIONS


def extract_video_metadata(file_info: FileInfo) -> FileInfo:
    """
    Extract video metadata and update the file_info object.
    
    Args:
        file_info: FileInfo object to update with video metadata
        
    Returns:
        The updated FileInfo object
    """
    print(f"Extracting video metadata for: {file_info.path}")
    
    try:
        from moviepy.editor import VideoFileClip
        
        file_path = str(file_info.path)
        print(f"Opening video file: {file_path}")
        
        with VideoFileClip(file_path) as clip:
            print(f"Video loaded. Duration: {clip.duration}, Size: {clip.size}")
            
            file_info.video_duration = float(clip.duration) if clip.duration is not None else None
            
            if hasattr(clip, 'size') and clip.size and len(clip.size) == 2:
                width, height = clip.size
                file_info.video_resolution = (int(width), int(height))
                
            file_info.video_fps = float(clip.fps) if clip.fps is not None else None
            
            # Try to get codec information if available
            if hasattr(clip, 'codec_name'):
                file_info.video_codec = clip.codec_name
            
            # Get audio codec if audio is present
            if clip.audio is not None:
                if hasattr(clip.audio, 'codec_name'):
                    file_info.audio_codec = clip.audio.codec_name
                print(f"Audio track found in {file_path}")
            else:
                print(f"No audio track in {file_path}")
                
        print(f"Successfully extracted metadata from {file_path}: Resolution: {file_info.video_resolution}, FPS: {file_info.video_fps}")
                
    except Exception as e:
        print(f"Error extracting video metadata for {file_info.path}: {e}")
        # Don't return None - just keep the original file_info without metadata
        
    # Ensure we have valid metadata types for the database
    if file_info.video_duration is not None and not isinstance(file_info.video_duration, (int, float)):
        try:
            file_info.video_duration = float(file_info.video_duration)
        except (ValueError, TypeError):
            file_info.video_duration = None
            
    if file_info.video_fps is not None and not isinstance(file_info.video_fps, (int, float)):
        try:
            file_info.video_fps = float(file_info.video_fps)
        except (ValueError, TypeError):
            file_info.video_fps = None
        
    return file_info


def generate_video_statistics(video_files: List[FileInfo]) -> Dict:
    """
    Generate statistics about video files.
    
    Args:
        video_files: List of FileInfo objects that are videos
        
    Returns:
        Dictionary with video statistics
    """
    if not video_files:
        return {
            "total_videos": 0,
            "videos_with_metadata": 0,
            "total_duration": 0,
            "average_duration": 0,
            "resolution_counts": {},
            "codec_counts": {},
        }
    
    total_videos = len(video_files)
    
    # Get video files with metadata
    videos_with_metadata = [v for v in video_files if v.has_video_metadata]
    
    # Video duration stats
    total_duration = 0
    average_duration = 0
    
    # Resolution stats
    resolution_counts = Counter()
    
    # Codec stats
    codec_counts = Counter()
    
    if videos_with_metadata:
        # Calculate duration stats
        durations = [v.video_duration for v in videos_with_metadata if v.video_duration is not None]
        if durations:
            total_duration = sum(durations)
            average_duration = total_duration / len(durations)
        
        # Count resolutions
        for v in videos_with_metadata:
            if v.video_resolution:
                try:
                    if isinstance(v.video_resolution, tuple) and len(v.video_resolution) >= 2:
                        width, height = v.video_resolution[0], v.video_resolution[1]
                        resolution_counts[f"{width}x{height}"] += 1
                    elif isinstance(v.video_resolution, str):
                        resolution_counts[v.video_resolution] += 1
                except (TypeError, IndexError, ValueError):
                    # Skip if the resolution format is unexpected
                    pass
        
        # Count codecs
        for v in videos_with_metadata:
            if v.video_codec:
                codec_counts[v.video_codec] += 1
    
    return {
        "total_videos": total_videos,
        "videos_with_metadata": len(videos_with_metadata),
        "total_duration": total_duration,
        "average_duration": average_duration,
        "resolution_counts": dict(resolution_counts.most_common()),
        "codec_counts": dict(codec_counts.most_common()),
    }


def display_video_insights(console, video_stats: Dict) -> None:
    """
    Display video insights in a formatted way.
    
    Args:
        console: Rich console instance for output
        video_stats: Dictionary with video statistics
    """
    if not video_stats or video_stats.get("total_videos", 0) == 0:
        return
        
    console.print(Panel.fit("🎬 [bold]Video Files[/bold]", style="cyan"))
    
    # Basic video statistics table
    video_table = Table(title="Video Statistics")
    video_table.add_column("Statistic", style="cyan")
    video_table.add_column("Value", style="green")
    
    video_table.add_row("Total Videos", str(video_stats.get("total_videos", 0)))
    video_table.add_row("Videos with Metadata", str(video_stats.get("videos_with_metadata", 0)))
    
    total_duration = video_stats.get("total_duration", 0)
    if total_duration > 0:
        video_table.add_row("Total Video Duration", f"{total_duration:.2f} seconds")
        if total_duration > 3600:
            hours = total_duration / 3600
            video_table.add_row("", f"{hours:.2f} hours")
            
        avg_duration = video_stats.get("average_duration", 0)
        if avg_duration > 0:
            video_table.add_row("Average Duration", f"{avg_duration:.2f} seconds")
    
    console.print(video_table)
    
    # Resolution distribution table
    resolution_counts = video_stats.get("resolution_counts", {})
    if resolution_counts:
        res_table = Table(title="Resolution Distribution")
        res_table.add_column("Resolution", style="cyan")
        res_table.add_column("Count", style="green")
        res_table.add_column("Percentage", style="yellow")
        
        total = sum(resolution_counts.values())
        
        for res, count in resolution_counts.items():
            if res and count:
                percentage = (count / total) * 100 if total > 0 else 0
                res_table.add_row(str(res), str(count), f"{percentage:.1f}%")
            
        console.print(res_table)
        
    # Codec distribution table
    codec_counts = video_stats.get("codec_counts", {})
    if codec_counts:
        codec_table = Table(title="Video Codec Distribution")
        codec_table.add_column("Codec", style="cyan")
        codec_table.add_column("Count", style="green")
        codec_table.add_column("Percentage", style="yellow")
        
        total = sum(codec_counts.values())
        
        for codec, count in codec_counts.items():
            if count:
                percentage = (count / total) * 100 if total > 0 else 0
                codec_table.add_row(codec if codec else "Unknown", str(count), f"{percentage:.1f}%")
            
        console.print(codec_table)
    
    # Tip about file tree
    if video_stats.get("videos_with_metadata", 0) > 0:
        console.print("[dim italic]Note: Video details are also included in the file tree view[/dim italic]") 