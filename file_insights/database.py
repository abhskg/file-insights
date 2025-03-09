"""
Database module for storing and retrieving FileInfo objects in PostgreSQL.
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError as e:
    PSYCOPG_AVAILABLE = False
    PSYCOPG_IMPORT_ERROR = str(e)

from file_insights.parser import FileInfo


class DatabaseManager:
    """Manages database connections and operations for FileInfo objects."""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            connection_string: PostgreSQL connection string. If None, will use the
                               DATABASE_URL environment variable.
        """
        if not PSYCOPG_AVAILABLE:
            raise ImportError(
                f"The psycopg package is not available. Error: {PSYCOPG_IMPORT_ERROR}\n"
                f"Please install PostgreSQL requirements or reinstall with:\n"
                f"poetry remove psycopg && poetry add 'psycopg[binary]'"
            )
            
        self.connection_string = connection_string or os.environ.get("DATABASE_URL")
        if not self.connection_string:
            raise ValueError(
                "Database connection string must be provided or set in DATABASE_URL environment variable."
                "\nExample connection string: postgresql://user:password@localhost:5432/dbname"
            )
        
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        
        Raises:
            Exception with detailed error message if connection fails
        """
        try:
            with psycopg.connect(self.connection_string, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            error_message = str(e)
            
            # Provide more helpful error messages for common issues
            if "connection refused" in error_message.lower():
                raise ConnectionError(
                    f"Could not connect to PostgreSQL server. Is it running? Error: {error_message}"
                )
            elif "password authentication failed" in error_message.lower():
                raise PermissionError(
                    f"Authentication failed. Check your username and password. Error: {error_message}"
                )
            elif "database" in error_message.lower() and "does not exist" in error_message.lower():
                raise ValueError(
                    f"Database does not exist. Please create it first. Error: {error_message}"
                )
            else:
                raise Exception(f"Database connection error: {error_message}")
        
    def initialize_database(self, rebuild: bool = False) -> None:
        """
        Initialize the database schema if it doesn't exist.
        Creates necessary tables for storing file information.
        
        Args:
            rebuild: If True, drop existing tables and recreate them
        """
        try:
            # Test connection first
            self.test_connection()
            
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Drop tables if rebuild is requested
                    if rebuild:
                        print("Rebuilding database schema...")
                        # Drop in reverse order to respect foreign key constraints
                        cur.execute("DROP TABLE IF EXISTS video_metadata")
                        cur.execute("DROP TABLE IF EXISTS files")
                    
                    # Create the files table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS files (
                            id SERIAL PRIMARY KEY,
                            path TEXT NOT NULL,
                            name TEXT NOT NULL,
                            size BIGINT NOT NULL,
                            extension TEXT,
                            created_time TIMESTAMP NOT NULL,
                            modified_time TIMESTAMP NOT NULL,
                            mime_type TEXT,
                            is_binary BOOLEAN NOT NULL,
                            is_video BOOLEAN NOT NULL,
                            duration FLOAT NOT NULL DEFAULT 0,
                            scan_timestamp TIMESTAMP NOT NULL
                        )
                    """)
                    
                    # Create the video_metadata table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS video_metadata (
                            file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
                            duration FLOAT,
                            resolution_width INTEGER,
                            resolution_height INTEGER,
                            fps FLOAT,
                            video_codec TEXT,
                            audio_codec TEXT
                        )
                    """)
                    
                    # Create an index on path for faster lookups
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
                    
                    # Create an index on is_video for faster filtering
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_files_is_video ON files(is_video)")
                    
                    conn.commit()
        except Exception as e:
            # Add more context to the error
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def _sanitize_text(self, text: Optional[str]) -> Optional[str]:
        """
        Sanitize text for PostgreSQL by removing null bytes and controlling length.
        
        Args:
            text: String to sanitize
            
        Returns:
            Sanitized string that's safe for PostgreSQL
        """
        if text is None:
            return None
            
        # Replace null bytes with spaces
        sanitized = text.replace('\x00', ' ') if isinstance(text, str) else str(text)
        
        # Limit length for large text fields to prevent issues
        if len(sanitized) > 10000:  # Reasonable limit for text fields
            sanitized = sanitized[:10000] + '... (truncated)'
            
        return sanitized
    
    def _prepare_for_db(self, value: Any) -> Any:
        """
        Prepare a value for storage in the database by sanitizing if needed.
        
        Args:
            value: Value to prepare
            
        Returns:
            Database-safe value
        """
        if isinstance(value, str):
            return self._sanitize_text(value)
        elif isinstance(value, Path):
            return self._sanitize_text(str(value))
        return value
    
    def store_file_infos(self, file_infos: List[FileInfo], scan_id: Optional[str] = None) -> int:
        """
        Store multiple FileInfo objects in the database.
        
        Args:
            file_infos: List of FileInfo objects to store
            scan_id: Optional identifier for this batch of files
            
        Returns:
            Number of files successfully stored
        """
        if not file_infos:
            return 0
            
        scan_timestamp = datetime.now()
        count = 0
        errors = []
        
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    for file_info in file_infos:
                        try:
                            # Prepare data for database
                            path_str = self._prepare_for_db(file_info.path)
                            name = self._prepare_for_db(file_info.name)
                            extension = self._prepare_for_db(file_info.extension)
                            mime_type = self._prepare_for_db(file_info.mime_type)
                            
                            # Get duration for all files (0 for non-videos)
                            duration = 0.0
                            if file_info.is_video and file_info.video_duration is not None:
                                try:
                                    duration = float(file_info.video_duration)
                                except (ValueError, TypeError):
                                    duration = 0.0
                        
                            # Insert into files table with duration
                            cur.execute("""
                                INSERT INTO files (
                                    path, name, size, extension, created_time, modified_time, 
                                    mime_type, is_binary, is_video, duration, scan_timestamp
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (
                                path_str,
                                name,
                                file_info.size,
                                extension,
                                file_info.created_time,
                                file_info.modified_time,
                                mime_type,
                                file_info.is_binary,
                                file_info.is_video,
                                duration,
                                scan_timestamp
                            ))
                            
                            file_id = cur.fetchone()[0]
                            count += 1
                            
                            # If this is a video with metadata, store in video_metadata table
                            if file_info.is_video and hasattr(file_info, 'video_duration') and file_info.video_duration is not None:
                                resolution_width = None
                                resolution_height = None
                                
                                if file_info.video_resolution:
                                    try:
                                        if isinstance(file_info.video_resolution, tuple) and len(file_info.video_resolution) >= 2:
                                            resolution_width, resolution_height = file_info.video_resolution[0], file_info.video_resolution[1]
                                        elif isinstance(file_info.video_resolution, str) and 'x' in file_info.video_resolution:
                                            width_str, height_str = file_info.video_resolution.split('x', 1)
                                            resolution_width, resolution_height = int(width_str), int(height_str)
                                    except (ValueError, TypeError, IndexError) as e:
                                        print(f"  - Error parsing resolution: {e}")
                                        pass
                                
                                video_codec = self._prepare_for_db(file_info.video_codec)
                                audio_codec = self._prepare_for_db(file_info.audio_codec)
                                
                                # Ensure values are properly cast
                                try:
                                    video_fps = float(file_info.video_fps) if file_info.video_fps is not None else None
                                except (ValueError, TypeError):
                                    print(f"  - Error converting FPS {file_info.video_fps} to float")
                                    video_fps = None
                                
                                try:
                                    cur.execute("""
                                        INSERT INTO video_metadata (
                                            file_id, duration, resolution_width, resolution_height,
                                            fps, video_codec, audio_codec
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        file_id,
                                        duration,
                                        resolution_width,
                                        resolution_height,
                                        video_fps,
                                        video_codec,
                                        audio_codec
                                    ))
                                except Exception as e:
                                    print(f"  ✗ Failed to insert video metadata: {e}")
                                    raise
                                    
                        except Exception as e:
                            # Log the error but continue processing other files
                            errors.append(f"Error storing file {file_info.path}: {str(e)}")
                    
                    conn.commit()
        except Exception as e:
            if errors:
                raise Exception(f"Failed to store files in database: {str(e)}. Individual errors: {'; '.join(errors[:5])}{' and more...' if len(errors) > 5 else ''}")
            else:
                raise Exception(f"Failed to store files in database: {str(e)}")
        
        if errors:
            print(f"Warning: {len(errors)} files could not be stored. Example error: {errors[0]}")
        
        return count
    
    def retrieve_file_infos(self, 
                           limit: int = 1000, 
                           video_only: bool = False, 
                           extension_filter: Optional[List[str]] = None) -> List[FileInfo]:
        """
        Retrieve FileInfo objects from the database.
        
        Args:
            limit: Maximum number of records to retrieve
            video_only: If True, only retrieve video files
            extension_filter: Only retrieve files with these extensions
            
        Returns:
            List of FileInfo objects
        """
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT f.*, 
                               v.duration as video_duration, 
                               v.resolution_width, 
                               v.resolution_height,
                               v.fps as video_fps,
                               v.video_codec,
                               v.audio_codec
                        FROM files f
                        LEFT JOIN video_metadata v ON f.id = v.file_id
                        WHERE 1=1
                    """
                    params = []
                    
                    if video_only:
                        query += " AND f.is_video = true"
                    
                    if extension_filter:
                        placeholders = ', '.join(['%s'] * len(extension_filter))
                        query += f" AND f.extension IN ({placeholders})"
                        params.extend(extension_filter)
                    
                    query += f" ORDER BY f.path LIMIT {limit}"
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    file_infos = []
                    for row in rows:
                        # Convert path string back to Path object
                        path = Path(row['path'])
                        
                        # Build video resolution tuple if available
                        video_resolution = None
                        if row.get('resolution_width') is not None and row.get('resolution_height') is not None:
                            video_resolution = (row['resolution_width'], row['resolution_height'])
                        
                        # Use the duration from video_metadata if available, otherwise from files table
                        duration = row.get('video_duration') if row.get('video_duration') is not None else row.get('duration', 0.0)
                        
                        file_info = FileInfo(
                            path=path,
                            size=row['size'],
                            extension=row['extension'],
                            created_time=row['created_time'],
                            modified_time=row['modified_time'],
                            content_preview=None,  # Don't retrieve content preview
                            mime_type=row['mime_type'],
                            video_duration=duration,
                            video_resolution=video_resolution,
                            video_fps=row.get('video_fps'),
                            video_codec=row.get('video_codec'),
                            audio_codec=row.get('audio_codec')
                        )
                        file_infos.append(file_info)
                    
                    return file_infos
        except Exception as e:
            raise Exception(f"Failed to retrieve files from database: {str(e)}")
    
    def count_files(self, video_only: bool = False) -> int:
        """
        Count the number of files in the database.
        
        Args:
            video_only: If True, only count video files
            
        Returns:
            Number of files
        """
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    query = "SELECT COUNT(*) FROM files"
                    if video_only:
                        query += " WHERE is_video = true"
                    
                    cur.execute(query)
                    return cur.fetchone()[0]
        except Exception as e:
            raise Exception(f"Failed to count files in database: {str(e)}")
    
    def delete_all_files(self) -> int:
        """
        Delete all files from the database.
        
        Returns:
            Number of files deleted
        """
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM files")
                    count = cur.fetchone()[0]
                    
                    # Due to cascade delete, we only need to delete from files table
                    cur.execute("DELETE FROM files")
                    conn.commit()
                    
                    return count
        except Exception as e:
            raise Exception(f"Failed to delete files from database: {str(e)}") 