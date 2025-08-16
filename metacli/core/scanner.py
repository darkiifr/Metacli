"""Directory scanning functionality for file discovery."""

import os
from pathlib import Path
from typing import List, Set, Optional, Generator, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass

from .extractor import MetadataExtractor


@dataclass
class ScanResult:
    """Result of a file scan operation."""
    file_path: Path
    metadata: Dict[str, Any]
    error: Optional[str] = None


class DirectoryScanner:
    """Scanner for discovering and processing files in directories."""
    
    def __init__(self, extractor: Optional[MetadataExtractor] = None):
        """Initialize the directory scanner."""
        self.extractor = extractor or MetadataExtractor()
        self._stop_event = threading.Event()
        self._progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set a callback function for progress updates."""
        self._progress_callback = callback
    
    def stop_scan(self):
        """Stop the current scan operation."""
        self._stop_event.set()
    
    def find_files(self, 
                   path: Path, 
                   recursive: bool = True,
                   file_types: Optional[List[str]] = None,
                   include_hidden: bool = False,
                   max_size: Optional[int] = None,
                   min_size: Optional[int] = None) -> Generator[Path, None, None]:
        """Find files in the given path with optional filtering.
        
        Args:
            path: Directory or file path to scan
            recursive: Whether to scan subdirectories
            file_types: List of file extensions to include (e.g., ['.jpg', '.png'])
            include_hidden: Whether to include hidden files
            max_size: Maximum file size in bytes
            min_size: Minimum file size in bytes
            
        Yields:
            Path objects for matching files
        """
        yield from self._find_files_generator(path, recursive, file_types, include_hidden, max_size, min_size)
    
    def find_files_list(self, 
                       path: Path, 
                       recursive: bool = True,
                       file_types: Optional[List[str]] = None,
                       include_hidden: bool = False,
                       max_size: Optional[int] = None,
                       min_size: Optional[int] = None) -> List[Path]:
        """Find files and return as a list (convenience method for testing)."""
        return list(self.find_files(path, recursive, file_types, include_hidden, max_size, min_size))
    
    def _find_files_generator(self, 
                             path: Path, 
                             recursive: bool = True,
                             file_types: Optional[List[str]] = None,
                             include_hidden: bool = False,
                             max_size: Optional[int] = None,
                             min_size: Optional[int] = None) -> Generator[Path, None, None]:
        """Find files in the given path with optional filtering.
        
        Args:
            path: Directory or file path to scan
            recursive: Whether to scan subdirectories
            file_types: List of file extensions to include (e.g., ['.jpg', '.png'])
            include_hidden: Whether to include hidden files
            max_size: Maximum file size in bytes
            min_size: Minimum file size in bytes
            
        Yields:
            Path objects for matching files
        """
        if self._stop_event.is_set():
            return
        
        # If path is a file, yield it directly if it matches criteria
        if path.is_file():
            if self._should_include_file(path, file_types, include_hidden, max_size, min_size):
                yield path
            return
        
        # If path is a directory, scan it
        if not path.is_dir():
            return
        
        try:
            if recursive:
                # Use rglob for recursive scanning
                pattern = '**/*' if include_hidden else '**/[!.]*'
                for file_path in path.rglob('*'):
                    if self._stop_event.is_set():
                        break
                    
                    if file_path.is_file() and self._should_include_file(
                        file_path, file_types, include_hidden, max_size, min_size
                    ):
                        yield file_path
            else:
                # Scan only the current directory
                for item in path.iterdir():
                    if self._stop_event.is_set():
                        break
                    
                    if item.is_file() and self._should_include_file(
                        item, file_types, include_hidden, max_size, min_size
                    ):
                        yield item
        
        except PermissionError:
            # Skip directories we don't have permission to read
            pass
        except Exception:
            # Skip other errors and continue scanning
            pass
    
    def _should_include_file(self, 
                           file_path: Path,
                           file_types: Optional[List[str]] = None,
                           include_hidden: bool = False,
                           max_size: Optional[int] = None,
                           min_size: Optional[int] = None) -> bool:
        """Check if a file should be included based on filtering criteria."""
        # Check if file is hidden
        if not include_hidden and file_path.name.startswith('.'):
            return False
        
        # Check file extension
        if file_types:
            # Normalize extensions (ensure they start with '.')
            normalized_types = []
            for ext in file_types:
                if not ext.startswith('.'):
                    ext = '.' + ext
                normalized_types.append(ext.lower())
            
            if file_path.suffix.lower() not in normalized_types:
                return False
        
        # Check file size
        try:
            file_size = file_path.stat().st_size
            
            if min_size is not None and file_size < min_size:
                return False
            
            if max_size is not None and file_size > max_size:
                return False
        
        except (OSError, PermissionError):
            # If we can't get file stats, skip the file
            return False
        
        return True
    
    def scan_files(self, 
                   files: List[Path],
                   extract_metadata: bool = True,
                   max_workers: int = 4) -> List[ScanResult]:
        """Scan a list of files and optionally extract metadata.
        
        Args:
            files: List of file paths to scan
            extract_metadata: Whether to extract metadata from files
            max_workers: Number of worker threads for parallel processing
            
        Returns:
            List of ScanResult objects
        """
        results = []
        total_files = len(files)
        
        if not extract_metadata:
            # Just return basic file info without metadata extraction
            for i, file_path in enumerate(files):
                if self._stop_event.is_set():
                    break
                
                try:
                    basic_info = {
                        'filename': file_path.name,
                        'filepath': str(file_path.absolute()),
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix.lower()
                    }
                    results.append(ScanResult(file_path, basic_info))
                except Exception as e:
                    results.append(ScanResult(file_path, {}, str(e)))
                
                if self._progress_callback:
                    self._progress_callback(i + 1, total_files)
            
            return results
        
        # Extract metadata using thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._extract_file_metadata, file_path): file_path
                for file_path in files
            }
            
            completed = 0
            for future in as_completed(future_to_file):
                if self._stop_event.is_set():
                    # Cancel remaining futures
                    for f in future_to_file:
                        f.cancel()
                    break
                
                file_path = future_to_file[future]
                try:
                    metadata = future.result()
                    results.append(ScanResult(file_path, metadata))
                except Exception as e:
                    results.append(ScanResult(file_path, {}, str(e)))
                
                completed += 1
                if self._progress_callback:
                    self._progress_callback(completed, total_files)
        
        return results
    
    def _extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from a single file."""
        return self.extractor.extract_metadata(file_path)
    
    def scan_directory(self, 
                      path: Path,
                      recursive: bool = True,
                      file_types: Optional[List[str]] = None,
                      include_hidden: bool = False,
                      extract_metadata: bool = True,
                      max_workers: int = 4,
                      max_size: Optional[int] = None,
                      min_size: Optional[int] = None) -> List[ScanResult]:
        """Scan a directory and extract metadata from matching files.
        
        Args:
            path: Directory path to scan
            recursive: Whether to scan subdirectories
            file_types: List of file extensions to include
            include_hidden: Whether to include hidden files
            extract_metadata: Whether to extract metadata from files
            max_workers: Number of worker threads for parallel processing
            max_size: Maximum file size in bytes
            min_size: Minimum file size in bytes
            
        Returns:
            List of ScanResult objects
        """
        self._stop_event.clear()
        
        # Find all matching files
        files = list(self.find_files(
            path, recursive, file_types, include_hidden, max_size, min_size
        ))
        
        if not files:
            return []
        
        # Scan the files
        return self.scan_files(files, extract_metadata, max_workers)
    
    def get_file_statistics(self, results: List[ScanResult]) -> Dict[str, Any]:
        """Generate statistics from scan results."""
        stats = {
            'total_files': len(results),
            'successful_scans': 0,
            'failed_scans': 0,
            'total_size': 0,
            'file_types': {},
            'extensions': {},
            'largest_file': None,
            'smallest_file': None
        }
        
        largest_size = 0
        smallest_size = float('inf')
        
        for result in results:
            if result.error:
                stats['failed_scans'] += 1
                continue
            
            stats['successful_scans'] += 1
            
            # File size
            file_size = result.metadata.get('size', 0)
            stats['total_size'] += file_size
            
            # Track largest and smallest files
            if file_size > largest_size:
                largest_size = file_size
                stats['largest_file'] = {
                    'path': str(result.file_path),
                    'size': file_size,
                    'size_human': result.metadata.get('size_human', '')
                }
            
            if file_size < smallest_size:
                smallest_size = file_size
                stats['smallest_file'] = {
                    'path': str(result.file_path),
                    'size': file_size,
                    'size_human': result.metadata.get('size_human', '')
                }
            
            # File type and extension counts
            file_type = result.metadata.get('file_type', 'unknown')
            extension = result.metadata.get('extension', 'none')
            
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
            stats['extensions'][extension] = stats['extensions'].get(extension, 0) + 1
        
        # Format total size
        stats['total_size_human'] = MetadataExtractor._format_size(stats['total_size'])
        
        return stats
    
    def filter_results(self, 
                      results: List[ScanResult],
                      file_type: Optional[str] = None,
                      extension: Optional[str] = None,
                      min_size: Optional[int] = None,
                      max_size: Optional[int] = None,
                      has_metadata: Optional[bool] = None) -> List[ScanResult]:
        """Filter scan results based on various criteria."""
        filtered = []
        
        for result in results:
            if result.error and has_metadata is True:
                continue
            
            metadata = result.metadata
            
            # Filter by file type
            if file_type and metadata.get('file_type') != file_type:
                continue
            
            # Filter by extension
            if extension:
                if not extension.startswith('.'):
                    extension = '.' + extension
                if metadata.get('extension', '').lower() != extension.lower():
                    continue
            
            # Filter by size
            file_size = metadata.get('size', 0)
            if min_size is not None and file_size < min_size:
                continue
            if max_size is not None and file_size > max_size:
                continue
            
            # Filter by metadata presence
            if has_metadata is not None:
                has_meta = len(metadata) > 8  # More than basic file info
                if has_metadata != has_meta:
                    continue
            
            filtered.append(result)
        
        return filtered