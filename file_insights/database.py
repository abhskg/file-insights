"""
Database module for storing and retrieving FileInfo objects in PostgreSQL.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import psycopg
from psycopg.rows import dict_row

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
        self.connection_string = connection_string or os.environ.get("DATABASE_URL")
        if not self.connection_string:
            raise ValueError(
                "Database connection string must be provided or set in DATABASE_URL environment variable"
            )
        
    def initialize_database(self) -> None:
        """
        Initialize the database schema if it doesn't exist.
        Creates necessary tables for storing file information.
        """
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
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
                        content_preview TEXT,
                        mime_type TEXT,
                        is_binary BOOLEAN NOT NULL,
                        is_video BOOLEAN NOT NULL,
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
        
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                for file_info in file_infos:
                    # Insert into files table
                    cur.execute("""
                        INSERT INTO files (
                            path, name, size, extension, created_time, modified_time, 
                            content_preview, mime_type, is_binary, is_video, scan_timestamp
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        str(file_info.path),
                        file_info.name,
                        file_info.size,
                        file_info.extension,
                        file_info.created_time,
                        file_info.modified_time,
                        file_info.content_preview,
                        file_info.mime_type,
                        file_info.is_binary,
                        file_info.is_video,
                        scan_timestamp
                    ))
                    
                    file_id = cur.fetchone()[0]
                    count += 1
                    
                    # If this is a video with metadata, store in video_metadata table
                    if file_info.is_video and file_info.has_video_metadata:
                        resolution_width = None
                        resolution_height = None
                        
                        if file_info.video_resolution:
                            try:
                                if isinstance(file_info.video_resolution, tuple) and len(file_info.video_resolution) >= 2:
                                    resolution_width, resolution_height = file_info.video_resolution[0], file_info.video_resolution[1]
                                elif isinstance(file_info.video_resolution, str) and 'x' in file_info.video_resolution:
                                    width_str, height_str = file_info.video_resolution.split('x', 1)
                                    resolution_width, resolution_height = int(width_str), int(height_str)
                            except (ValueError, TypeError, IndexError):
                                pass
                        
                        cur.execute("""
                            INSERT INTO video_metadata (
                                file_id, duration, resolution_width, resolution_height,
                                fps, video_codec, audio_codec
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            file_id,
                            file_info.video_duration,
                            resolution_width,
                            resolution_height,
                            file_info.video_fps,
                            file_info.video_codec,
                            file_info.audio_codec
                        ))
                
                conn.commit()
        
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
                    
                    file_info = FileInfo(
                        path=path,
                        size=row['size'],
                        extension=row['extension'],
                        created_time=row['created_time'],
                        modified_time=row['modified_time'],
                        content_preview=row['content_preview'],
                        mime_type=row['mime_type'],
                        video_duration=row.get('video_duration'),
                        video_resolution=video_resolution,
                        video_fps=row.get('video_fps'),
                        video_codec=row.get('video_codec'),
                        audio_codec=row.get('audio_codec')
                    )
                    file_infos.append(file_info)
                
                return file_infos
    
    def count_files(self, video_only: bool = False) -> int:
        """
        Count the number of files in the database.
        
        Args:
            video_only: If True, only count video files
            
        Returns:
            Number of files
        """
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                query = "SELECT COUNT(*) FROM files"
                if video_only:
                    query += " WHERE is_video = true"
                
                cur.execute(query)
                return cur.fetchone()[0]
    
    def delete_all_files(self) -> int:
        """
        Delete all files from the database.
        
        Returns:
            Number of files deleted
        """
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM files")
                count = cur.fetchone()[0]
                
                # Due to cascade delete, we only need to delete from files table
                cur.execute("DELETE FROM files")
                conn.commit()
                
                return count 