"""
File parser module responsible for traversing directories and collecting file information.
"""

import fnmatch
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from tqdm import tqdm

from file_insights.constants import COMMON_BINARY_EXTENSIONS, COMMON_VIDEO_EXTENSIONS


@dataclass
class FileInfo:
    """Container for file information."""

    path: Path
    size: int
    extension: str
    created_time: datetime
    modified_time: datetime
    content_preview: Optional[str] = None
    mime_type: Optional[str] = None
    # Video specific attributes
    video_duration: Optional[float] = None
    video_resolution: Optional[Tuple[int, int]] = None
    video_fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None

    @property
    def is_binary(self) -> bool:
        """Check if the file appears to be binary."""
        if self.mime_type:
            return not self.mime_type.startswith(("text/", "application/json"))
        return False

    @property
    def name(self) -> str:
        """Get the file name."""
        return self.path.name
    
    @property
    def is_video(self) -> bool:
        """Check if the file appears to be a video."""
        return self.extension in COMMON_VIDEO_EXTENSIONS
    
    @property
    def has_video_metadata(self) -> bool:
        """Check if video metadata has been extracted."""
        return self.is_video and self.video_duration is not None
    

class FileParser:
    """Parser that traverses directories and extracts file information."""

    def __init__(self, recursive: bool = True, exclude_patterns: Tuple[str, ...] = ()):
        self.recursive = recursive
        self.exclude_patterns = exclude_patterns
        self._common_binary_extensions = COMMON_BINARY_EXTENSIONS
        self._common_video_extensions = COMMON_VIDEO_EXTENSIONS
        self._extract_video_metadata = False  # Default to not extracting video metadata

    def set_extract_video_metadata(self, value: bool) -> None:
        """
        Enable or disable extraction of video metadata.
        
        Args:
            value: Whether to extract video metadata
        """
        self._extract_video_metadata = value

    def parse_directory(self, directory_path: Path) -> List[FileInfo]:
        """
        Parse a directory and return information about all files found.

        Args:
            directory_path: Path to the directory to parse

        Returns:
            List of FileInfo objects
        """
        if not directory_path.is_dir():
            raise ValueError(f"{directory_path} is not a directory")

        result = []

        # Get the list of paths to process
        if self.recursive:
            paths_to_process = self._walk_directory(directory_path)
        else:
            paths_to_process = [p for p in directory_path.iterdir() if p.is_file()]

        # Process each file
        for file_path in tqdm(paths_to_process, desc="Scanning files"):
            if self._should_exclude(file_path):
                continue

            file_info = self._get_file_info(file_path)
            result.append(file_info)

        return result

    def _walk_directory(self, directory_path: Path) -> List[Path]:
        """Recursively walk a directory and return all file paths."""
        result = []
        for root, dirs, files in os.walk(directory_path):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(Path(root) / d)]

            # Add files
            for file in files:
                file_path = Path(root) / file
                if not self._should_exclude(file_path):
                    result.append(file_path)

        return result

    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded based on patterns."""
        path_str = str(path)
        return any(
            fnmatch.fnmatch(path_str, pattern) for pattern in self.exclude_patterns
        )

    def _get_file_info(self, file_path: Path) -> FileInfo:
        """Extract information about a file."""
        stat = file_path.stat()

        # Get file times
        created_time = datetime.fromtimestamp(stat.st_ctime)
        modified_time = datetime.fromtimestamp(stat.st_mtime)

        # Get file extension (normalized to lowercase)
        extension = file_path.suffix.lower()

        # Get a preview of the file content if it's not a common binary format
        content_preview = None
        if extension not in self._common_binary_extensions:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content_preview = f.read(1000)  # First 1000 characters
            except Exception:
                pass

        # Try to determine MIME type
        mime_type = None
        try:
            import mimetypes

            mime_type, _ = mimetypes.guess_type(str(file_path))
        except Exception:
            pass

        file_info = FileInfo(
            path=file_path,
            size=stat.st_size,
            extension=extension,
            created_time=created_time,
            modified_time=modified_time,
            content_preview=content_preview,
            mime_type=mime_type,
        )
        
        # Extract video metadata if enabled and file is a video
        if self._extract_video_metadata and extension in self._common_video_extensions:
            self._extract_video_info(file_info)
            
        return file_info
    
    def _extract_video_info(self, file_info: FileInfo) -> None:
        """
        Extract video metadata and update the file_info object.
        
        Args:
            file_info: FileInfo object to update with video metadata
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
