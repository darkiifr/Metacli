"""Metadata extraction functionality for various file types."""

import os
import mimetypes
import hashlib
import functools
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import weakref

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import mutagen
    from mutagen.id3 import ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False


class MetadataExtractor:
    """Extract metadata from various file types with performance optimizations."""
    
    # Class-level cache for metadata results
    _cache = weakref.WeakValueDictionary()
    _cache_lock = threading.RLock()
    
    # Pre-compiled supported types for faster lookup
    _SUPPORTED_TYPES = {
        'image': frozenset(['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']),
        'audio': frozenset(['.mp3', '.flac', '.ogg', '.m4a', '.wav', '.wma']),
        'video': frozenset(['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']),
        'document': frozenset(['.pdf', '.docx', '.doc', '.txt', '.rtf']),
        'archive': frozenset(['.zip', '.rar', '.7z', '.tar', '.gz'])
    }
    
    # Flattened extension set for O(1) lookup
    _ALL_EXTENSIONS = frozenset().union(*_SUPPORTED_TYPES.values())
    
    def __init__(self, enable_cache: bool = True, max_workers: int = 4):
        """Initialize the metadata extractor.
        
        Args:
            enable_cache: Whether to enable metadata caching
            max_workers: Maximum number of threads for parallel processing
        """
        self.enable_cache = enable_cache
        self.max_workers = max_workers
        self.supported_types = {k: list(v) for k, v in self._SUPPORTED_TYPES.items()}
    
    def get_file_type(self, file_path: Path) -> str:
        """Determine the file type category with optimized lookup."""
        suffix = file_path.suffix.lower()
        for file_type, extensions in self._SUPPORTED_TYPES.items():
            if suffix in extensions:
                return file_type
        return 'unknown'
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate a cache key based on file path and modification time."""
        try:
            stat = file_path.stat()
            content = f"{file_path.absolute()}:{stat.st_mtime}:{stat.st_size}"
            return hashlib.md5(content.encode()).hexdigest()
        except (OSError, IOError):
            return str(file_path.absolute())
    
    def _get_cached_metadata(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached metadata if available."""
        if not self.enable_cache:
            return None
        
        with self._cache_lock:
            return self._cache.get(cache_key)
    
    def _cache_metadata(self, cache_key: str, metadata: Dict[str, Any]) -> None:
        """Cache metadata result."""
        if not self.enable_cache:
            return
        
        with self._cache_lock:
            # Create a copy to avoid reference issues
            self._cache[cache_key] = dict(metadata)
    
    def extract_basic_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file system metadata."""
        stat = file_path.stat()
        
        metadata = {
            'filename': file_path.name,
            'filepath': str(file_path.absolute()),
            'size': stat.st_size,
            'size_human': self._format_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'extension': file_path.suffix.lower(),
            'mime_type': mimetypes.guess_type(str(file_path))[0],
            'file_type': self.get_file_type(file_path)
        }
        
        return metadata
    
    def extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from image files with optimized processing."""
        metadata = {}
        
        if not PIL_AVAILABLE:
            metadata['error'] = 'PIL/Pillow not available for image metadata extraction'
            return metadata
        
        try:
            # Use context manager for proper resource cleanup
            with Image.open(file_path) as img:
                # Basic image properties
                metadata.update({
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                    'pixel_count': img.width * img.height
                })
                
                # Extract EXIF data more efficiently
                exif_dict = img.getexif()
                if exif_dict:
                    exif_data = {}
                    # Limit EXIF processing to avoid memory issues with large datasets
                    for tag_id, value in list(exif_dict.items())[:100]:  # Limit to first 100 tags
                        try:
                            tag = TAGS.get(tag_id, f'Tag_{tag_id}')
                            # Convert complex types to strings safely
                            if isinstance(value, (bytes, bytearray)):
                                exif_data[tag] = f'<binary_data_{len(value)}_bytes>'
                            else:
                                exif_data[tag] = str(value)[:500]  # Limit string length
                        except Exception:
                            continue  # Skip problematic tags
                    
                    if exif_data:
                        metadata['exif'] = exif_data
                
        except (IOError, OSError) as e:
            metadata['error'] = f'Failed to open image file: {str(e)}'
        except Exception as e:
            metadata['error'] = f'Failed to extract image metadata: {str(e)}'
        
        return metadata
    
    def extract_audio_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from audio files."""
        metadata = {}
        
        if not MUTAGEN_AVAILABLE:
            metadata['error'] = 'Mutagen not available for audio metadata extraction'
            return metadata
        
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is None:
                metadata['error'] = 'Unsupported audio format'
                return metadata
            
            # Basic audio info
            if hasattr(audio_file, 'info'):
                info = audio_file.info
                metadata.update({
                    'duration': getattr(info, 'length', 0),
                    'duration_human': self._format_duration(getattr(info, 'length', 0)),
                    'bitrate': getattr(info, 'bitrate', 0),
                    'sample_rate': getattr(info, 'sample_rate', 0),
                    'channels': getattr(info, 'channels', 0)
                })
            
            # Tags
            if audio_file.tags:
                tags = {}
                for key, value in audio_file.tags.items():
                    if isinstance(value, list):
                        tags[key] = [str(v) for v in value]
                    else:
                        tags[key] = str(value)
                metadata['tags'] = tags
                
                # Common tag mappings
                common_tags = {
                    'title': ['TIT2', 'TITLE', '\xa9nam'],
                    'artist': ['TPE1', 'ARTIST', '\xa9ART'],
                    'album': ['TALB', 'ALBUM', '\xa9alb'],
                    'date': ['TDRC', 'DATE', '\xa9day'],
                    'genre': ['TCON', 'GENRE', '\xa9gen']
                }
                
                for common_name, possible_keys in common_tags.items():
                    for key in possible_keys:
                        if key in tags:
                            metadata[common_name] = tags[key][0] if isinstance(tags[key], list) else tags[key]
                            break
        
        except Exception as e:
            metadata['error'] = f'Failed to extract audio metadata: {str(e)}'
        
        return metadata
    
    def extract_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from video files."""
        metadata = {}
        
        # For now, use mutagen for basic video metadata
        if not MUTAGEN_AVAILABLE:
            metadata['error'] = 'Mutagen not available for video metadata extraction'
            return metadata
        
        try:
            video_file = mutagen.File(file_path)
            if video_file is None:
                metadata['error'] = 'Unsupported video format'
                return metadata
            
            if hasattr(video_file, 'info'):
                info = video_file.info
                metadata.update({
                    'duration': getattr(info, 'length', 0),
                    'duration_human': self._format_duration(getattr(info, 'length', 0)),
                    'bitrate': getattr(info, 'bitrate', 0)
                })
            
            if video_file.tags:
                tags = {}
                for key, value in video_file.tags.items():
                    if isinstance(value, list):
                        tags[key] = [str(v) for v in value]
                    else:
                        tags[key] = str(value)
                metadata['tags'] = tags
        
        except Exception as e:
            metadata['error'] = f'Failed to extract video metadata: {str(e)}'
        
        return metadata
    
    def extract_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from document files."""
        metadata = {}
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            metadata.update(self._extract_pdf_metadata(file_path))
        elif extension == '.docx':
            metadata.update(self._extract_docx_metadata(file_path))
        elif extension == '.txt':
            metadata.update(self._extract_text_metadata(file_path))
        else:
            metadata['error'] = f'Unsupported document format: {extension}'
        
        return metadata
    
    def _extract_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF files."""
        metadata = {}
        
        if not PYPDF2_AVAILABLE:
            metadata['error'] = 'PyPDF2 not available for PDF metadata extraction'
            return metadata
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                metadata.update({
                    'pages': len(pdf_reader.pages),
                    'encrypted': pdf_reader.is_encrypted
                })
                
                if pdf_reader.metadata:
                    pdf_metadata = {}
                    for key, value in pdf_reader.metadata.items():
                        clean_key = key.replace('/', '').lower()
                        pdf_metadata[clean_key] = str(value)
                    metadata['pdf_metadata'] = pdf_metadata
        
        except Exception as e:
            metadata['error'] = f'Failed to extract PDF metadata: {str(e)}'
        
        return metadata
    
    def _extract_docx_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from DOCX files."""
        metadata = {}
        
        if not PYTHON_DOCX_AVAILABLE:
            metadata['error'] = 'python-docx not available for DOCX metadata extraction'
            return metadata
        
        try:
            doc = DocxDocument(file_path)
            
            # Count elements
            paragraphs = len(doc.paragraphs)
            tables = len(doc.tables)
            
            metadata.update({
                'paragraphs': paragraphs,
                'tables': tables
            })
            
            # Core properties
            if doc.core_properties:
                core_props = {}
                props = doc.core_properties
                
                for attr in ['author', 'category', 'comments', 'content_status',
                           'created', 'identifier', 'keywords', 'language',
                           'last_modified_by', 'last_printed', 'modified',
                           'revision', 'subject', 'title', 'version']:
                    value = getattr(props, attr, None)
                    if value is not None:
                        if isinstance(value, datetime):
                            core_props[attr] = value.isoformat()
                        else:
                            core_props[attr] = str(value)
                
                metadata['core_properties'] = core_props
        
        except Exception as e:
            metadata['error'] = f'Failed to extract DOCX metadata: {str(e)}'
        
        return metadata
    
    def _extract_text_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from text files."""
        metadata = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                
            metadata.update({
                'lines': len(content.splitlines()),
                'words': len(content.split()),
                'characters': len(content),
                'characters_no_spaces': len(content.replace(' ', ''))
            })
        
        except Exception as e:
            metadata['error'] = f'Failed to extract text metadata: {str(e)}'
        
        return metadata
    
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract all available metadata from a file with caching support."""
        # Convert string path to Path object if needed
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        if not file_path.exists():
            return {'error': f'File not found: {file_path}'}
        
        if not file_path.is_file():
            return {'error': f'Path is not a file: {file_path}'}
        
        # Check cache first
        cache_key = self._get_cache_key(file_path)
        cached_result = self._get_cached_metadata(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            # Start with basic metadata
            metadata = {'basic': self.extract_basic_metadata(file_path)}
            file_type = self.get_file_type(file_path)
            metadata['basic']['file_type'] = file_type
            
            # Extract type-specific metadata
            if file_type == 'image':
                metadata['image'] = self.extract_image_metadata(file_path)
            elif file_type == 'audio':
                metadata['audio'] = self.extract_audio_metadata(file_path)
            elif file_type == 'video':
                metadata['video'] = self.extract_video_metadata(file_path)
            elif file_type == 'document':
                metadata['document'] = self.extract_document_metadata(file_path)
            
            # Cache the result
            self._cache_metadata(cache_key, metadata)
            
            return metadata
            
        except Exception as e:
            error_result = {'error': f'Failed to extract metadata: {str(e)}'}
            return error_result
    
    def extract_metadata_batch(self, file_paths: List[Union[str, Path]], 
                              progress_callback: Optional[callable] = None) -> Dict[str, Dict[str, Any]]:
        """Extract metadata from multiple files in parallel.
        
        Args:
            file_paths: List of file paths to process
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary mapping file paths to their metadata
        """
        results = {}
        
        def process_file(file_path):
            path_obj = Path(file_path) if isinstance(file_path, str) else file_path
            return str(path_obj), self.extract_metadata(path_obj)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {executor.submit(process_file, fp): fp for fp in file_paths}
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_path):
                try:
                    file_path, metadata = future.result()
                    results[file_path] = metadata
                except Exception as e:
                    file_path = str(future_to_path[future])
                    results[file_path] = {'error': f'Processing failed: {str(e)}'}
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(file_paths))
        
        return results
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of all supported file extensions."""
        extensions = []
        for ext_list in self.supported_types.values():
            extensions.extend(ext_list)
        return sorted(extensions)
    
    def is_supported(self, file_path: Path) -> bool:
        """Check if file type is supported with O(1) lookup."""
        return file_path.suffix.lower() in self._ALL_EXTENSIONS
    
    def clear_cache(self) -> None:
        """Clear the metadata cache."""
        with self._cache_lock:
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                'cache_size': len(self._cache),
                'cache_enabled': self.enable_cache
            }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"