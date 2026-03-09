import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

logger = get_logger("app.common.file_storage")


class FileStorageService:
    """
    Service for managing file storage on the server.
    Handles saving, retrieving, and deleting files from the filesystem.
    """
    
    def __init__(
        self, 
        base_path: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize file storage service.
        
        Args:
            base_path: Base directory for file storage (defaults to FILE_STORAGE_PATH env var or ./uploads)
            base_url: Base URL for constructing file URLs (defaults to BASE_URL env var)
        """
        self.base_path = Path(base_path or os.getenv("FILE_STORAGE_PATH", "./uploads"))
        self.base_url = base_url or os.getenv("BASE_URL", "http://localhost:8000")
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"FileStorageService initialized with base_path: {self.base_path}")
    
    def _generate_storage_path(
        self, 
        filename: str, 
        category: str = "reports",
        subcategory: Optional[str] = None
    ) -> Path:
        """
        Generate a structured storage path for a file.
        
        Structure: uploads/{category}/{subcategory}/{year}/{month}/{filename}
        
        Args:
            filename: Original filename
            category: Top-level category (e.g., "reports")
            subcategory: Optional subcategory (e.g., "customer_visit")
            
        Returns:
            Full path for the file
        """
        now = datetime.now()
        
        # Build path components
        path_parts = [category]
        if subcategory:
            path_parts.append(subcategory)
        path_parts.extend([str(now.year), f"{now.month:02d}"])
        
        # Create directory structure
        dir_path = self.base_path / Path(*path_parts)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return dir_path / filename
    
    def save_file(
        self,
        source_path: str,
        category: str = "reports",
        subcategory: Optional[str] = None,
        filename: Optional[str] = None,
        delete_source: bool = False
    ) -> dict:
        """
        Save a file to storage.
        
        Args:
            source_path: Path to the source file
            category: Storage category (e.g., "reports")
            subcategory: Optional subcategory (e.g., "customer_visit")
            filename: Optional custom filename (defaults to source filename)
            delete_source: Whether to delete the source file after copying
            
        Returns:
            Dict with file info: {filename, file_path, file_url, file_size}
        """
        source = Path(source_path)
        
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Use provided filename or original
        final_filename = filename or source.name
        
        # Generate storage path
        dest_path = self._generate_storage_path(final_filename, category, subcategory)
        
        # Handle filename collision by adding timestamp
        if dest_path.exists():
            timestamp = datetime.now().strftime("%H%M%S")
            stem = dest_path.stem
            suffix = dest_path.suffix
            dest_path = dest_path.parent / f"{stem}_{timestamp}{suffix}"
        
        # Copy or move file
        if delete_source:
            shutil.move(str(source), str(dest_path))
            logger.debug(f"Moved file to: {dest_path}")
        else:
            shutil.copy2(str(source), str(dest_path))
            logger.debug(f"Copied file to: {dest_path}")
        
        # Get file info
        file_size = dest_path.stat().st_size
        relative_path = dest_path.relative_to(self.base_path)
        # Store relative URL path (frontend will prepend base URL)
        file_url = f"/files/{relative_path.as_posix()}"
        
        logger.info(f"Saved file: {final_filename} ({file_size} bytes)")
        
        return {
            "filename": final_filename,
            "file_path": str(relative_path.as_posix()),
            "file_url": file_url,
            "file_size": file_size,
            "absolute_path": str(dest_path)
        }
    
    def get_file_path(self, relative_path: str) -> Path:
        """
        Get the absolute path for a stored file.
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            Absolute Path object
        """
        return self.base_path / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in storage."""
        return (self.base_path / relative_path).exists()
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self.base_path / relative_path
        
        if not file_path.exists():
            logger.warning(f"File not found for deletion: {relative_path}")
            return False
        
        file_path.unlink()
        logger.info(f"Deleted file: {relative_path}")
        return True
    
    def get_file_url(self, relative_path: str) -> str:
        """
        Construct the download URL for a file.
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            Relative URL path for the file (frontend prepends base URL)
        """
        return f"/files/{relative_path}"
    
    def list_files(
        self, 
        category: str = "reports",
        subcategory: Optional[str] = None,
        pattern: str = "*"
    ) -> list:
        """
        List files in a category.
        
        Args:
            category: Storage category
            subcategory: Optional subcategory
            pattern: Glob pattern for filtering (default: all files)
            
        Returns:
            List of relative file paths
        """
        path_parts = [category]
        if subcategory:
            path_parts.append(subcategory)
        
        search_path = self.base_path / Path(*path_parts)
        
        if not search_path.exists():
            return []
        
        files = []
        for file_path in search_path.rglob(pattern):
            if file_path.is_file():
                files.append(str(file_path.relative_to(self.base_path).as_posix()))
        
        return sorted(files)
