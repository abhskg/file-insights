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
    try:
        from moviepy.editor import VideoFileClip
        
        with VideoFileClip(str(file_info.path)) as clip:
            file_info.video_duration = clip.duration
            file_info.video_resolution = (clip.w, clip.h)
            file_info.video_fps = clip.fps
            
            # Try to get codec information if available
            if hasattr(clip, 'codec_name'):
                file_info.video_codec = clip.codec_name
            
            # Get audio codec if audio is present
            if clip.audio is not None and hasattr(clip.audio, 'codec_name'):
                file_info.audio_codec = clip.audio.codec_name
                
    except Exception as e:
        print(f"Error extracting video metadata for {file_info.path}: {e}")
        
    return file_info


def generate_video_statistics(video_files: List[FileInfo]) -> Dict:
    """
    Generate statistics about video files.
    
    Args:
        video_files: List of FileInfo objects that are videos
        
    Returns:
        Dictionary with video statistics
    """
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
                width, height = v.video_resolution
                resolution_counts[f"{width}x{height}"] += 1
        
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
    if not video_stats or video_stats["total_videos"] == 0:
        return
        
    console.print(Panel.fit("🎬 [bold]Video Files[/bold]", style="cyan"))
    
    video_table = Table(title="Video Statistics")
    video_table.add_column("Statistic", style="cyan")
    video_table.add_column("Value", style="green")
    
    video_table.add_row("Total Videos", str(video_stats["total_videos"]))
    video_table.add_row("Total Video Duration", f"{video_stats['total_duration']:.2f} seconds")
    if video_stats["total_duration"] > 3600:
        hours = video_stats["total_duration"] / 3600
        video_table.add_row("", f"{hours:.2f} hours")
        
    video_table.add_row("Average Duration", f"{video_stats['average_duration']:.2f} seconds")
    
    console.print(video_table)
    
    if video_stats["resolution_counts"]:
        res_table = Table(title="Resolution Distribution")
        res_table.add_column("Resolution", style="cyan")
        res_table.add_column("Count", style="green")
        
        for res, count in video_stats["resolution_counts"].items():
            res_table.add_row(res, str(count))
            
        console.print(res_table)
        
    if video_stats["codec_counts"]:
        codec_table = Table(title="Video Codec Distribution")
        codec_table.add_column("Codec", style="cyan")
        codec_table.add_column("Count", style="green")
        
        for codec, count in video_stats["codec_counts"].items():
            codec_table.add_row(codec if codec else "Unknown", str(count))
            
        console.print(codec_table) 