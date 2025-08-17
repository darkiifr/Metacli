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
import time
from collections import OrderedDict

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


class MetadataCache:
    """Thread-safe LRU cache for metadata results."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key in self._cache:
                # Check if entry is still valid
                if time.time() - self._timestamps[key] < self.ttl:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    return self._cache[key].copy()  # Return a copy to avoid reference issues
                else:
                    # Entry expired, remove it
                    del self._cache[key]
                    del self._timestamps[key]
            return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            # Remove oldest entries if cache is full
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            # Store a copy to avoid reference issues
            self._cache[key] = value.copy()
            self._timestamps[key] = time.time()
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class MetadataExtractor:
    """Extract metadata from various file types with performance optimizations."""
    
    # Class-level cache for metadata results
    _cache = MetadataCache(max_size=1000, ttl=3600)
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
        
        return self._cache.get(cache_key)
    
    def _cache_metadata(self, cache_key: str, metadata: Dict[str, Any]) -> None:
        """Cache metadata result."""
        if not self.enable_cache:
            return
        
        self._cache.set(cache_key, metadata)
    
    def extract_basic_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file system metadata with enhanced error handling."""
        try:
            stat = file_path.stat()
            
            metadata = {
                'filename': file_path.name,
                'filepath': str(file_path.absolute()),
                'size': stat.st_size,
                'size_human': self._format_size(stat.st_size),
                'size_kb': round(stat.st_size / 1024, 2),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'extension': file_path.suffix.lower(),
                'mime_type': mimetypes.guess_type(str(file_path))[0],
                'file_type': self.get_file_type(file_path),
                'is_hidden': file_path.name.startswith('.'),
                'parent_directory': str(file_path.parent),
                'stem': file_path.stem
            }
            
            # Add file permissions (cross-platform)
            try:
                metadata['permissions'] = oct(stat.st_mode)[-3:]
                metadata['is_readable'] = os.access(file_path, os.R_OK)
                metadata['is_writable'] = os.access(file_path, os.W_OK)
                metadata['is_executable'] = os.access(file_path, os.X_OK)
            except (OSError, AttributeError):
                pass
            
            return metadata
            
        except (OSError, IOError) as e:
            return {
                'filename': file_path.name if file_path else 'unknown',
                'filepath': str(file_path) if file_path else 'unknown',
                'error': f'Failed to extract basic metadata: {str(e)}'
            }
    
    def extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from image files with enhanced information and better error handling."""
        metadata = {}
        
        if not PIL_AVAILABLE:
            metadata['error'] = 'PIL/Pillow not available for image metadata extraction'
            return metadata
        
        try:
            # Use context manager for proper resource cleanup
            with Image.open(file_path) as img:
                # Basic image properties with enhanced information
                metadata.update({
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                    'pixel_count': img.width * img.height,
                    'aspect_ratio': round(img.width / img.height, 2) if img.height > 0 else 0,
                    'megapixels': round((img.width * img.height) / 1000000, 2),
                    'color_depth': len(img.getbands()) if hasattr(img, 'getbands') else None
                })
                
                # Add image info
                if hasattr(img, 'info') and img.info:
                    info_data = {}
                    for key, value in img.info.items():
                        if isinstance(value, (str, int, float, bool)):
                            info_data[key] = value
                        elif isinstance(value, (bytes, bytearray)):
                            info_data[key] = f'<binary_data_{len(value)}_bytes>'
                    if info_data:
                        metadata['image_info'] = info_data
                
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
        """Extract metadata from audio files with enhanced information and better error handling."""
        metadata = {}
        
        if not MUTAGEN_AVAILABLE:
            metadata['error'] = 'Mutagen not available for audio metadata extraction'
            return metadata
        
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is None:
                metadata['error'] = 'Unsupported audio format'
                return metadata
            
            # Basic audio info with enhanced details
            if hasattr(audio_file, 'info'):
                info = audio_file.info
                duration = getattr(info, 'length', 0)
                bitrate = getattr(info, 'bitrate', 0)
                sample_rate = getattr(info, 'sample_rate', 0)
                channels = getattr(info, 'channels', 0)
                
                metadata.update({
                    'duration': duration,
                    'duration_human': self._format_duration(duration),
                    'duration_minutes': round(duration / 60, 2) if duration > 0 else 0,
                    'bitrate': bitrate,
                    'bitrate_kbps': f'{bitrate} kbps' if bitrate > 0 else 'Unknown',
                    'sample_rate': sample_rate,
                    'sample_rate_khz': f'{sample_rate / 1000:.1f} kHz' if sample_rate > 0 else 'Unknown',
                    'channels': channels,
                    'channel_mode': 'Stereo' if channels == 2 else 'Mono' if channels == 1 else f'{channels} channels',
                    'quality': 'High' if bitrate >= 320 else 'Medium' if bitrate >= 128 else 'Low' if bitrate > 0 else 'Unknown'
                })
                
                # Calculate estimated file size for different qualities
                if duration > 0:
                    metadata['estimated_sizes'] = {
                        '128_kbps': f'{round((128 * duration) / 8 / 1024, 2)} MB',
                        '192_kbps': f'{round((192 * duration) / 8 / 1024, 2)} MB',
                        '320_kbps': f'{round((320 * duration) / 8 / 1024, 2)} MB'
                    }
            
            # Enhanced tag extraction
            if audio_file.tags:
                tags = {}
                for key, value in audio_file.tags.items():
                    try:
                        if isinstance(value, list):
                            tags[key] = [str(v) for v in value if v]
                        else:
                            tags[key] = str(value)
                    except (TypeError, AttributeError):
                        continue
                
                if tags:
                    metadata['tags'] = tags
                
                # Enhanced common tag mappings with more formats
                common_tags = {
                    'title': ['TIT2', 'TITLE', '\xa9nam', 'Title'],
                    'artist': ['TPE1', 'ARTIST', '\xa9ART', 'Artist'],
                    'album': ['TALB', 'ALBUM', '\xa9alb', 'Album'],
                    'date': ['TDRC', 'DATE', '\xa9day', 'Date'],
                    'genre': ['TCON', 'GENRE', '\xa9gen', 'Genre'],
                    'track': ['TRCK', 'TRACKNUMBER', '\xa9trk', 'Track'],
                    'album_artist': ['TPE2', 'ALBUMARTIST', 'aART'],
                    'composer': ['TCOM', 'COMPOSER', '\xa9wrt'],
                    'disc': ['TPOS', 'DISCNUMBER', 'disk']
                }
                
                for common_name, possible_keys in common_tags.items():
                    for key in possible_keys:
                        if key in tags and tags[key]:
                            value = tags[key][0] if isinstance(tags[key], list) else tags[key]
                            if value and str(value).strip():
                                metadata[common_name] = str(value).strip()
                                break
        
        except Exception as e:
            metadata['error'] = f'Failed to extract audio metadata: {str(e)}'
        
        return metadata
    
    def extract_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from video files with enhanced information and better error handling."""
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
                duration = getattr(info, 'length', 0)
                bitrate = getattr(info, 'bitrate', 0)
                
                metadata.update({
                    'duration': duration,
                    'duration_human': self._format_duration(duration),
                    'duration_minutes': round(duration / 60, 2) if duration > 0 else 0,
                    'duration_hours': round(duration / 3600, 2) if duration > 0 else 0,
                    'bitrate': bitrate,
                    'bitrate_kbps': f'{bitrate} kbps' if bitrate > 0 else 'Unknown',
                    'file_size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
                    'file_size_gb': round(file_path.stat().st_size / (1024 * 1024 * 1024), 3)
                })
                
                # Add video-specific properties if available
                if hasattr(info, 'width') and hasattr(info, 'height'):
                    width = getattr(info, 'width', 0)
                    height = getattr(info, 'height', 0)
                    metadata.update({
                        'width': width,
                        'height': height,
                        'resolution': f'{width}x{height}' if width and height else 'Unknown',
                        'aspect_ratio': round(width / height, 2) if height > 0 else 0,
                        'total_pixels': width * height if width and height else 0
                    })
                    
                    # Determine video quality category
                    if width >= 3840:  # 4K
                        metadata['quality_category'] = '4K Ultra HD'
                    elif width >= 1920:  # 1080p
                        metadata['quality_category'] = 'Full HD (1080p)'
                    elif width >= 1280:  # 720p
                        metadata['quality_category'] = 'HD (720p)'
                    elif width >= 854:  # 480p
                        metadata['quality_category'] = 'SD (480p)'
                    else:
                        metadata['quality_category'] = 'Low Resolution'
                
                # Add frame rate if available
                if hasattr(info, 'fps'):
                    fps = getattr(info, 'fps', 0)
                    metadata['fps'] = fps
                    metadata['frame_rate'] = f'{fps} fps' if fps > 0 else 'Unknown'
                
                # Calculate estimated data rate
                if duration > 0 and bitrate > 0:
                    metadata['data_rate_mbps'] = round(bitrate / 1000, 2)
            
            if video_file.tags:
                tags = {}
                # Common video tag mappings
                tag_mappings = {
                    'TIT2': 'title', 'TITLE': 'title', '\xa9nam': 'title',
                    'TPE1': 'artist', 'ARTIST': 'artist', '\xa9ART': 'artist',
                    'TALB': 'album', 'ALBUM': 'album', '\xa9alb': 'album',
                    'TDRC': 'year', 'DATE': 'year', '\xa9day': 'year',
                    'TCON': 'genre', 'GENRE': 'genre', '\xa9gen': 'genre',
                    'TDES': 'description', 'DESCRIPTION': 'description',
                    'TCOM': 'composer', 'COMPOSER': 'composer'
                }
                
                for key, value in video_file.tags.items():
                    try:
                        mapped_key = tag_mappings.get(key, key.lower())
                        if isinstance(value, list) and value:
                            clean_value = str(value[0]).strip()
                        else:
                            clean_value = str(value).strip()
                        
                        if clean_value:
                            tags[mapped_key] = clean_value
                    except (TypeError, AttributeError):
                        continue
                
                if tags:
                    metadata['tags'] = tags
        
        except Exception as e:
            metadata['error'] = f'Failed to extract video metadata: {str(e)}'
        
        return metadata
    
    def extract_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract document-specific metadata with enhanced information."""
        metadata = {}
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.pdf':
                metadata.update(self._extract_pdf_metadata(file_path))
                # Add enhanced PDF analysis
                if 'pages' in metadata:
                    page_count = metadata['pages']
                    estimated_words = page_count * 250
                    reading_time_minutes = round(estimated_words / 200, 1)
                    metadata['estimated_reading_time'] = f'{reading_time_minutes} minutes'
                    metadata['estimated_words'] = estimated_words
                    metadata['document_type'] = 'PDF Document'
            elif extension == '.docx':
                metadata.update(self._extract_docx_metadata(file_path))
                # Add enhanced DOCX analysis
                if 'paragraphs' in metadata:
                    metadata['document_type'] = 'Word Document'
            elif extension == '.txt':
                metadata.update(self._extract_text_metadata(file_path))
                # Add enhanced text analysis
                if 'words' in metadata:
                    word_count = metadata['words']
                    metadata['estimated_reading_time'] = f'{round(word_count / 200, 1)} minutes'
                    metadata['document_type'] = 'Text Document'
            else:
                metadata['document_type'] = 'Unknown Document Type'
                metadata['note'] = f'Limited metadata extraction for {extension} files'
        
        except Exception as e:
            metadata['error'] = f'Failed to extract document metadata: {str(e)}'
        
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
        """Extract comprehensive metadata from a file with enhanced error handling."""
        # Convert string path to Path object if needed
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        # Basic validation
        if not file_path.exists():
            return {
                'error': f'File not found: {file_path}',
                'filepath': str(file_path),
                'status': 'file_not_found'
            }
        
        if not file_path.is_file():
            return {
                'error': f'Path is not a file: {file_path}',
                'filepath': str(file_path),
                'status': 'not_a_file'
            }
        
        # Check cache first
        cache_key = self._get_cache_key(file_path)
        try:
            cached_result = self._get_cached_metadata(cache_key)
            if cached_result is not None:
                cached_result['from_cache'] = True
                return cached_result
        except Exception as cache_error:
            # Continue without cache if there's an issue
            pass
        
        try:
            # Start with basic metadata
            metadata = {'basic': self.extract_basic_metadata(file_path)}
            
            # If basic metadata extraction failed, return early
            if 'error' in metadata['basic']:
                return metadata['basic']
            
            file_type = self.get_file_type(file_path)
            metadata['basic']['file_type'] = file_type
            
            # Add extraction timestamp
            metadata['basic']['extraction_timestamp'] = datetime.now().isoformat()
            metadata['basic']['extractor_version'] = '3.0.0'
            
            # Extract type-specific metadata with individual error handling
            try:
                if file_type == 'image':
                    image_meta = self.extract_image_metadata(file_path)
                    if image_meta and 'error' not in image_meta:
                        metadata['image'] = image_meta
                    elif 'error' in image_meta:
                        metadata['image_extraction_error'] = image_meta['error']
                        
                elif file_type == 'audio':
                    audio_meta = self.extract_audio_metadata(file_path)
                    if audio_meta and 'error' not in audio_meta:
                        metadata['audio'] = audio_meta
                    elif 'error' in audio_meta:
                        metadata['audio_extraction_error'] = audio_meta['error']
                        
                elif file_type == 'video':
                    video_meta = self.extract_video_metadata(file_path)
                    if video_meta and 'error' not in video_meta:
                        metadata['video'] = video_meta
                    elif 'error' in video_meta:
                        metadata['video_extraction_error'] = video_meta['error']
                        
                elif file_type == 'document':
                    doc_meta = self.extract_document_metadata(file_path)
                    if doc_meta and 'error' not in doc_meta:
                        metadata['document'] = doc_meta
                    elif 'error' in doc_meta:
                        metadata['document_extraction_error'] = doc_meta['error']
                        
            except Exception as type_error:
                metadata[f'{file_type}_extraction_error'] = f'Failed to extract {file_type} metadata: {str(type_error)}'
            
            # Add success status
            metadata['basic']['status'] = 'success'
            metadata['basic']['from_cache'] = False
            
            # Cache the result (with error handling)
            try:
                self._cache_metadata(cache_key, metadata)
            except Exception as cache_error:
                # Don't fail the entire operation if caching fails
                metadata['basic']['cache_warning'] = f'Failed to cache result: {str(cache_error)}'
            
            return metadata
            
        except Exception as e:
            error_result = {
                'error': f'Failed to extract metadata: {str(e)}',
                'filepath': str(file_path),
                'status': 'extraction_failed',
                'extraction_timestamp': datetime.now().isoformat(),
                'extractor_version': '3.0.0'
            }
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
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': self._cache.size(),
            'cache_enabled': self.enable_cache,
            'cache_max_size': self._cache.max_size,
            'cache_ttl': self._cache.ttl
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