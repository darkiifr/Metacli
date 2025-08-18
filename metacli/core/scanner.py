"""Directory scanning functionality for file discovery."""

import os
import logging
from pathlib import Path
from typing import List, Set, Optional, Generator, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass
from datetime import datetime

from .extractor import MetadataExtractor, ExtractionError, ErrorSeverity

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of scanning a single file."""
    file_path: Path
    metadata: Dict[str, Any]
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_severity: Optional[str] = None
    scan_timestamp: Optional[str] = None
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        if self.scan_timestamp is None:
            self.scan_timestamp = datetime.now().isoformat()
    
    @property
    def has_error(self) -> bool:
        """Check if this result contains an error."""
        return self.error is not None
    
    @property
    def is_recoverable_error(self) -> bool:
        """Check if the error is recoverable (low/medium severity)."""
        return self.error_severity in ['low', 'medium'] if self.error_severity else False


class DirectoryScanner:
    """Scanner for discovering and processing files in directories."""
    
    # Default directories to exclude from scanning
    DEFAULT_EXCLUDED_DIRS = {
        '.venv', 'venv', '.env', 'env',  # Virtual environments
        '__pycache__', '.pytest_cache',  # Python cache
        '.git', '.svn', '.hg',  # Version control
        'node_modules', '.npm',  # Node.js
        '.idea', '.vscode',  # IDEs
        'build', 'dist', '.build',  # Build directories
        '.tox', '.coverage',  # Testing
        'logs', 'log', 'tmp', 'temp'  # Temporary files
    }
    
    def __init__(self, extractor: Optional[MetadataExtractor] = None, excluded_dirs: Optional[Set[str]] = None):
        """Initialize the directory scanner."""
        self.extractor = extractor or MetadataExtractor()
        self.excluded_dirs = excluded_dirs or self.DEFAULT_EXCLUDED_DIRS.copy()
        self._stop_event = threading.Event()
        self._progress_callback = None
    
    def set_stop_event(self, stop_event: threading.Event):
        """Set the stop event for cancelling operations."""
        self._stop_event = stop_event
    
    def stop_scanning(self):
        """Signal to stop the current scanning operation."""
        self._stop_event.set()
    
    def reset_stop_event(self):
        """Reset the stop event for new operations."""
        self._stop_event.clear()
    
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
            # Optimize file discovery using OS-level filtering
            if file_types:
                # Use glob patterns for specific file types (OS-level filtering)
                normalized_types = []
                for ext in file_types:
                    if not ext.startswith('.'):
                        ext = '.' + ext
                    normalized_types.append(ext.lower())
                
                # Create glob patterns for each file type
                for ext in normalized_types:
                    pattern = f"**/*{ext}" if recursive else f"*{ext}"
                    try:
                        for file_path in path.glob(pattern):
                            if self._stop_event.is_set():
                                return
                            
                            if (file_path.is_file() and 
                                self._should_include_file_fast(file_path, include_hidden, max_size, min_size)):
                                yield file_path
                    except (OSError, PermissionError):
                        continue
            else:
                # General file discovery with optimized filtering
                if recursive:
                    for file_path in self._walk_directory_recursive(path, include_hidden):
                        if self._stop_event.is_set():
                            break
                        
                        if (file_path.is_file() and 
                            self._should_include_file_fast(file_path, include_hidden, max_size, min_size)):
                            yield file_path
                else:
                    # Scan only the current directory
                    try:
                        for item in path.iterdir():
                            if self._stop_event.is_set():
                                break
                            
                            if (item.is_file() and 
                                self._should_include_file_fast(item, include_hidden, max_size, min_size)):
                                yield item
                    except (OSError, PermissionError):
                        pass
        
        except PermissionError:
            # Skip directories we don't have permission to read
            pass
        except Exception:
            # Skip other errors and continue scanning
            pass
    
    def _walk_directory_recursive(self, path: Path, include_hidden: bool = False) -> Generator[Path, None, None]:
        """Recursively walk directory while respecting excluded directories."""
        try:
            for item in path.iterdir():
                if self._stop_event.is_set():
                    break
                    
                # Skip hidden items if not included
                if not include_hidden and item.name.startswith('.'):
                    continue
                    
                # Skip excluded directories
                if item.is_dir() and item.name in self.excluded_dirs:
                    continue
                    
                if item.is_file():
                    yield item
                elif item.is_dir():
                    # Recursively walk subdirectories
                    yield from self._walk_directory_recursive(item, include_hidden)
                    
        except (OSError, PermissionError):
            # Skip directories we don't have permission to read
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
    
    def _should_include_file_fast(self, 
                                file_path: Path,
                                include_hidden: bool = False,
                                max_size: Optional[int] = None,
                                min_size: Optional[int] = None) -> bool:
        """Fast file filtering without extension check (already done by glob)."""
        # Check if file is hidden
        if not include_hidden and file_path.name.startswith('.'):
            return False
        
        # Check file size only if needed
        if max_size is not None or min_size is not None:
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
                   max_workers: int = 4,
                   timeout_per_file: Optional[float] = 30.0) -> List[ScanResult]:
        """Scan a list of files and optionally extract metadata.
        
        Args:
            files: List of file paths to scan
            extract_metadata: Whether to extract metadata from files
            max_workers: Number of worker threads for parallel processing
            timeout_per_file: Maximum time to spend on each file (seconds)
            
        Returns:
            List of ScanResult objects
        """
        results = []
        total_files = len(files)
        start_time = datetime.now()
        
        logger.info(f"Starting scan of {total_files} files with metadata extraction: {extract_metadata}")
        
        if not extract_metadata:
            # Just return basic file info without metadata extraction
            for i, file_path in enumerate(files):
                if self._stop_event.is_set():
                    logger.info("Scan stopped by user request")
                    break
                
                file_start_time = datetime.now()
                try:
                    basic_info = {
                        'filename': file_path.name,
                        'filepath': str(file_path.absolute()),
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix.lower(),
                        'scan_type': 'basic_info_only'
                    }
                    processing_time = (datetime.now() - file_start_time).total_seconds()
                    results.append(ScanResult(
                        file_path=file_path, 
                        metadata=basic_info,
                        processing_time=processing_time
                    ))
                except Exception as e:
                    processing_time = (datetime.now() - file_start_time).total_seconds()
                    error_type = type(e).__name__
                    logger.warning(f"Failed to get basic info for {file_path}: {e}")
                    results.append(ScanResult(
                        file_path=file_path, 
                        metadata={}, 
                        error=str(e),
                        error_type=error_type,
                        error_severity='low',
                        processing_time=processing_time
                    ))
                
                if self._progress_callback:
                    self._progress_callback(i + 1, total_files)
            
            logger.info(f"Basic scan completed: {len(results)} files processed")
            return results
        
        # Use improved batch extraction with stop event support
        batch_start_time = datetime.now()
        try:
            file_paths = [str(f) for f in files]
            logger.info(f"Starting batch metadata extraction for {len(file_paths)} files")
            
            metadata_results = self.extractor.extract_metadata_batch(
                file_paths, 
                progress_callback=self._progress_callback,
                stop_event=self._stop_event
            )
            
            # Convert results to ScanResult objects with enhanced error handling
            for file_path in files:
                file_str = str(file_path)
                if file_str in metadata_results:
                    metadata = metadata_results[file_str]
                    
                    # Check for errors in metadata
                    if isinstance(metadata, dict) and metadata.get('error'):
                        error_info = metadata
                        results.append(ScanResult(
                            file_path=file_path,
                            metadata={},
                            error=error_info.get('error', 'Unknown error'),
                            error_type=error_info.get('error_type', 'UnknownError'),
                            error_severity=error_info.get('error_severity', 'medium'),
                            processing_time=error_info.get('processing_time')
                        ))
                    else:
                        # Successful extraction
                        processing_time = metadata.get('processing_time') if isinstance(metadata, dict) else None
                        results.append(ScanResult(
                            file_path=file_path,
                            metadata=metadata,
                            processing_time=processing_time
                        ))
                else:
                    # File not in results - likely skipped or failed
                    logger.warning(f"File {file_path} not found in batch results")
                    results.append(ScanResult(
                        file_path=file_path,
                        metadata={},
                        error='File not processed in batch',
                        error_type='BatchProcessingError',
                        error_severity='medium'
                    ))
                    
        except Exception as e:
            # Fallback to individual processing if batch fails
            logger.warning(f"Batch processing failed, falling back to individual processing: {e}")
            
            for i, file_path in enumerate(files):
                if self._stop_event.is_set():
                    logger.info("Individual processing stopped by user request")
                    break
                    
                file_start_time = datetime.now()
                try:
                    metadata = self._extract_file_metadata(file_path, timeout_per_file)
                    processing_time = (datetime.now() - file_start_time).total_seconds()
                    
                    if isinstance(metadata, dict) and metadata.get('error'):
                        error_info = metadata
                        results.append(ScanResult(
                            file_path=file_path,
                            metadata={},
                            error=error_info.get('error', 'Unknown error'),
                            error_type=error_info.get('error_type', 'UnknownError'),
                            error_severity=error_info.get('error_severity', 'medium'),
                            processing_time=processing_time
                        ))
                    else:
                        results.append(ScanResult(
                            file_path=file_path,
                            metadata=metadata,
                            processing_time=processing_time
                        ))
                        
                except Exception as ex:
                    processing_time = (datetime.now() - file_start_time).total_seconds()
                    error_type = type(ex).__name__
                    logger.error(f"Individual processing failed for {file_path}: {ex}")
                    
                    results.append(ScanResult(
                        file_path=file_path,
                        metadata={},
                        error=str(ex),
                        error_type=error_type,
                        error_severity='high' if isinstance(ex, ExtractionError) else 'medium',
                        processing_time=processing_time
                    ))
                
                if self._progress_callback:
                    self._progress_callback(i + 1, total_files)
        
        total_time = (datetime.now() - batch_start_time).total_seconds()
        successful_scans = len([r for r in results if not r.has_error])
        logger.info(f"Metadata scan completed: {successful_scans}/{len(results)} files successful in {total_time:.2f}s")
        
        return results
    
    def _extract_file_metadata(self, file_path: Path, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Extract metadata from a single file with timeout support.
        
        Args:
            file_path: Path to the file to extract metadata from
            timeout: Maximum time to spend on extraction (seconds)
            
        Returns:
            Dictionary containing metadata or error information
        """
        if self._stop_event.is_set():
            return {
                'error': 'Operation cancelled by user',
                'error_type': 'OperationCancelled',
                'error_severity': 'low'
            }
        
        try:
            # Use enhanced extraction with timeout and retry logic
            metadata = self.extractor.extract_metadata(
                file_path, 
                max_retries=2,  # Allow retries for individual processing
                timeout=timeout
            )
            return metadata
            
        except ExtractionError as e:
            logger.warning(f"Extraction error for {file_path}: {e}")
            return {
                'error': str(e),
                'error_type': type(e).__name__,
                'error_severity': 'medium'
            }
        except Exception as e:
            logger.error(f"Unexpected error extracting metadata from {file_path}: {e}")
            return {
                'error': f'Unexpected error: {str(e)}',
                'error_type': type(e).__name__,
                'error_severity': 'high'
            }
    
    def scan_directory(self, 
                      path: Path,
                      recursive: bool = True,
                      file_types: Optional[List[str]] = None,
                      include_hidden: bool = False,
                      extract_metadata: bool = True,
                      max_workers: int = 4,
                      max_size: Optional[int] = None,
                      min_size: Optional[int] = None,
                      timeout_per_file: Optional[float] = 30.0) -> List[ScanResult]:
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
            timeout_per_file: Maximum time to spend on each file (seconds)
            
        Returns:
            List of ScanResult objects
        """
        self._stop_event.clear()
        
        logger.info(f"Starting directory scan: {path} (recursive: {recursive})")
        
        # Find all matching files
        try:
            files = list(self.find_files(
                path, recursive, file_types, include_hidden, max_size, min_size
            ))
            
            if not files:
                logger.info(f"No files found in {path}")
                return []
            
            logger.info(f"Found {len(files)} files to scan")
            
            # Scan the files with enhanced error handling
            return self.scan_files(files, extract_metadata, max_workers, timeout_per_file)
            
        except Exception as e:
            logger.error(f"Directory scan failed for {path}: {e}")
            # Return empty results rather than crashing
            return []
    
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