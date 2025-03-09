"""
Utility functions for the file-insights tool.
"""

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Dict, List, Optional, Set


def get_file_hash(file_path: Path, algorithm: str = 'md5', buffer_size: int = 65536) -> str:
    """
    Calculate the hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
        buffer_size: Buffer size for reading the file
        
    Returns:
        Hash digest as a hexadecimal string
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    try:
        with open(file_path, 'rb') as f:
            buffer = f.read(buffer_size)
            while buffer:
                hash_obj.update(buffer)
                buffer = f.read(buffer_size)
                
        return hash_obj.hexdigest()
    except Exception as e:
        return f"Error: {str(e)}"


def detect_duplicates(files: List[Path]) -> Dict[str, List[Path]]:
    """
    Detect duplicate files based on their content hash.
    
    Args:
        files: List of file paths to check
        
    Returns:
        Dictionary mapping hash to list of duplicate files
    """
    hash_to_files = {}
    
    for file_path in files:
        file_hash = get_file_hash(file_path)
        if file_hash in hash_to_files:
            hash_to_files[file_hash].append(file_path)
        else:
            hash_to_files[file_hash] = [file_path]
    
    # Return only entries with duplicates (more than one file)
    return {h: files for h, files in hash_to_files.items() if len(files) > 1}


def get_mime_type(file_path: Path) -> Optional[str]:
    """
    Determine the MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type as a string or None if it couldn't be determined
    """
    # Initialize mimetypes database
    if not mimetypes.inited:
        mimetypes.init()
    
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type


def is_text_file(file_path: Path) -> bool:
    """
    Check if a file is likely a text file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is likely a text file, False otherwise
    """
    # Check by mime type first
    mime_type = get_mime_type(file_path)
    if mime_type:
        return mime_type.startswith(('text/', 'application/json', 'application/xml'))
    
    # Fallback: try to open as text and look for binary data
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' not in chunk  # If no null bytes, probably text
    except Exception:
        return False


def find_empty_directories(root_path: Path) -> List[Path]:
    """
    Find empty directories in a given path.
    
    Args:
        root_path: Root directory to search in
        
    Returns:
        List of paths to empty directories
    """
    empty_dirs = []
    
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        if not dirnames and not filenames:
            empty_dirs.append(Path(dirpath))
    
    return empty_dirs 