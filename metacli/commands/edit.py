"""Edit command implementation."""

import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.extractor import MetadataExtractor
from ..utils.logger import get_logger

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import mutagen
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


class MetadataEditor:
    """Edit metadata in various file types."""
    
    def __init__(self):
        """Initialize the metadata editor."""
        self.extractor = MetadataExtractor()
    
    def edit_file_metadata(self, 
                          file_path: Path, 
                          set_fields: Optional[Dict[str, str]] = None,
                          remove_fields: Optional[list] = None,
                          create_backup: bool = False) -> bool:
        """Edit metadata in a file.
        
        Args:
            file_path: Path to the file to edit
            set_fields: Dictionary of field names and values to set
            remove_fields: List of field names to remove
            create_backup: Whether to create a backup before editing
            
        Returns:
            True if successful, False otherwise
        """
        if not file_path.exists() or not file_path.is_file():
            return False
        
        # Create backup if requested
        if create_backup:
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            shutil.copy2(file_path, backup_path)
        
        file_type = self.extractor.get_file_type(file_path)
        
        try:
            if file_type == 'image':
                return self._edit_image_metadata(file_path, set_fields, remove_fields)
            elif file_type == 'audio':
                return self._edit_audio_metadata(file_path, set_fields, remove_fields)
            elif file_type == 'video':
                return self._edit_video_metadata(file_path, set_fields, remove_fields)
            elif file_type == 'document':
                return self._edit_document_metadata(file_path, set_fields, remove_fields)
            else:
                return False
        
        except Exception:
            # If editing fails and we created a backup, restore it
            if create_backup:
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                if backup_path.exists():
                    shutil.copy2(backup_path, file_path)
            return False
    
    def _edit_image_metadata(self, 
                           file_path: Path, 
                           set_fields: Optional[Dict[str, str]] = None,
                           remove_fields: Optional[list] = None) -> bool:
        """Edit image metadata using PIL/Pillow."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            # For now, we'll focus on basic EXIF editing
            # Note: PIL/Pillow has limited EXIF editing capabilities
            # For comprehensive EXIF editing, consider using exifread/piexif
            
            with Image.open(file_path) as img:
                # Get existing EXIF data
                exif_dict = img.getexif()
                
                if set_fields:
                    # Map common field names to EXIF tags
                    field_mapping = {
                        'artist': 315,  # Artist
                        'copyright': 33432,  # Copyright
                        'software': 305,  # Software
                        'datetime': 306,  # DateTime
                        'description': 270,  # ImageDescription
                    }
                    
                    for field, value in set_fields.items():
                        if field.lower() in field_mapping:
                            tag_id = field_mapping[field.lower()]
                            exif_dict[tag_id] = value
                
                if remove_fields:
                    field_mapping = {
                        'artist': 315,
                        'copyright': 33432,
                        'software': 305,
                        'datetime': 306,
                        'description': 270,
                    }
                    
                    for field in remove_fields:
                        if field.lower() in field_mapping:
                            tag_id = field_mapping[field.lower()]
                            if tag_id in exif_dict:
                                del exif_dict[tag_id]
                
                # Save the image with updated EXIF
                img.save(file_path, exif=exif_dict)
            
            return True
        
        except Exception:
            return False
    
    def _edit_audio_metadata(self, 
                           file_path: Path, 
                           set_fields: Optional[Dict[str, str]] = None,
                           remove_fields: Optional[list] = None) -> bool:
        """Edit audio metadata using Mutagen."""
        if not MUTAGEN_AVAILABLE:
            return False
        
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is None:
                return False
            
            # Ensure tags exist
            if audio_file.tags is None:
                audio_file.add_tags()
            
            if set_fields:
                # Map common field names to ID3 tags
                field_mapping = {
                    'title': 'TIT2',
                    'artist': 'TPE1', 
                    'album': 'TALB',
                    'date': 'TDRC',
                    'year': 'TDRC',
                    'genre': 'TCON',
                    'albumartist': 'TPE2',
                    'composer': 'TCOM',
                    'track': 'TRCK'
                }
                
                for field, value in set_fields.items():
                    field_lower = field.lower()
                    
                    if field_lower in field_mapping:
                        tag_name = field_mapping[field_lower]
                        
                        # Handle different tag types
                        if tag_name == 'TIT2':
                            audio_file.tags[tag_name] = TIT2(encoding=3, text=value)
                        elif tag_name == 'TPE1':
                            audio_file.tags[tag_name] = TPE1(encoding=3, text=value)
                        elif tag_name == 'TALB':
                            audio_file.tags[tag_name] = TALB(encoding=3, text=value)
                        elif tag_name == 'TDRC':
                            audio_file.tags[tag_name] = TDRC(encoding=3, text=value)
                        elif tag_name == 'TCON':
                            audio_file.tags[tag_name] = TCON(encoding=3, text=value)
                        else:
                            # Generic text frame
                            audio_file.tags[tag_name] = value
                    else:
                        # Direct tag assignment
                        audio_file.tags[field] = value
            
            if remove_fields:
                field_mapping = {
                    'title': 'TIT2',
                    'artist': 'TPE1',
                    'album': 'TALB',
                    'date': 'TDRC',
                    'year': 'TDRC',
                    'genre': 'TCON',
                    'albumartist': 'TPE2',
                    'composer': 'TCOM',
                    'track': 'TRCK'
                }
                
                for field in remove_fields:
                    field_lower = field.lower()
                    
                    if field_lower in field_mapping:
                        tag_name = field_mapping[field_lower]
                        if tag_name in audio_file.tags:
                            del audio_file.tags[tag_name]
                    else:
                        # Direct tag removal
                        if field in audio_file.tags:
                            del audio_file.tags[field]
            
            # Save changes
            audio_file.save()
            return True
        
        except Exception:
            return False
    
    def _edit_video_metadata(self, 
                           file_path: Path, 
                           set_fields: Optional[Dict[str, str]] = None,
                           remove_fields: Optional[list] = None) -> bool:
        """Edit video metadata using Mutagen."""
        # Similar to audio metadata editing
        return self._edit_audio_metadata(file_path, set_fields, remove_fields)
    
    def _edit_document_metadata(self, 
                              file_path: Path, 
                              set_fields: Optional[Dict[str, str]] = None,
                              remove_fields: Optional[list] = None) -> bool:
        """Edit document metadata."""
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self._edit_pdf_metadata(file_path, set_fields, remove_fields)
        elif extension == '.docx':
            return self._edit_docx_metadata(file_path, set_fields, remove_fields)
        
        return False
    
    def _edit_pdf_metadata(self, 
                         file_path: Path, 
                         set_fields: Optional[Dict[str, str]] = None,
                         remove_fields: Optional[list] = None) -> bool:
        """Edit PDF metadata."""
        if not PYPDF2_AVAILABLE:
            return False
        
        try:
            # Note: PyPDF2 has limited metadata editing capabilities
            # For comprehensive PDF metadata editing, consider using PyPDF4 or pdftk
            
            with open(file_path, 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                pdf_writer = PyPDF2.PdfWriter()
                
                # Copy all pages
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                # Get existing metadata
                metadata = pdf_reader.metadata or {}
                
                if set_fields:
                    field_mapping = {
                        'title': '/Title',
                        'author': '/Author',
                        'subject': '/Subject',
                        'creator': '/Creator',
                        'producer': '/Producer',
                        'keywords': '/Keywords'
                    }
                    
                    for field, value in set_fields.items():
                        if field.lower() in field_mapping:
                            key = field_mapping[field.lower()]
                            metadata[key] = value
                
                if remove_fields:
                    field_mapping = {
                        'title': '/Title',
                        'author': '/Author',
                        'subject': '/Subject',
                        'creator': '/Creator',
                        'producer': '/Producer',
                        'keywords': '/Keywords'
                    }
                    
                    for field in remove_fields:
                        if field.lower() in field_mapping:
                            key = field_mapping[field.lower()]
                            if key in metadata:
                                del metadata[key]
                
                # Set metadata
                pdf_writer.add_metadata(metadata)
                
                # Write to temporary file first
                temp_path = file_path.with_suffix('.tmp')
                with open(temp_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                # Replace original file
                temp_path.replace(file_path)
            
            return True
        
        except Exception:
            return False
    
    def _edit_docx_metadata(self, 
                          file_path: Path, 
                          set_fields: Optional[Dict[str, str]] = None,
                          remove_fields: Optional[list] = None) -> bool:
        """Edit DOCX metadata."""
        try:
            from docx import Document as DocxDocument
            
            doc = DocxDocument(file_path)
            
            if set_fields:
                field_mapping = {
                    'title': 'title',
                    'author': 'author',
                    'subject': 'subject',
                    'keywords': 'keywords',
                    'comments': 'comments',
                    'category': 'category',
                    'language': 'language'
                }
                
                for field, value in set_fields.items():
                    if field.lower() in field_mapping:
                        attr_name = field_mapping[field.lower()]
                        if hasattr(doc.core_properties, attr_name):
                            setattr(doc.core_properties, attr_name, value)
            
            if remove_fields:
                field_mapping = {
                    'title': 'title',
                    'author': 'author',
                    'subject': 'subject',
                    'keywords': 'keywords',
                    'comments': 'comments',
                    'category': 'category',
                    'language': 'language'
                }
                
                for field in remove_fields:
                    if field.lower() in field_mapping:
                        attr_name = field_mapping[field.lower()]
                        if hasattr(doc.core_properties, attr_name):
                            setattr(doc.core_properties, attr_name, None)
            
            # Save the document
            doc.save(file_path)
            return True
        
        except ImportError:
            return False
        except Exception:
            return False


def execute(args) -> int:
    """Execute the edit command."""
    logger = get_logger()
    
    try:
        file_path = Path(args.file)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            print(f"Error: File not found: {file_path}")
            return 1
        
        if not file_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            print(f"Error: Path is not a file: {file_path}")
            return 1
        
        # Prepare fields to set and remove
        set_fields = {}
        if args.set:
            for field, value in args.set:
                set_fields[field] = value
        
        remove_fields = args.remove or []
        
        if not set_fields and not remove_fields:
            logger.error("No fields specified to set or remove")
            print("Error: No fields specified to set or remove")
            print("Use --set FIELD VALUE to set fields or --remove FIELD to remove fields")
            return 1
        
        # Initialize editor
        editor = MetadataEditor()
        
        # Check if file type is supported for editing
        extractor = MetadataExtractor()
        file_type = extractor.get_file_type(file_path)
        
        if file_type == 'unknown':
            logger.error(f"Unsupported file type: {file_path.suffix}")
            print(f"Error: Unsupported file type: {file_path.suffix}")
            return 1
        
        logger.info(f"Editing metadata for: {file_path}")
        
        # Show what will be changed
        if set_fields:
            print("Fields to set:")
            for field, value in set_fields.items():
                print(f"  {field}: {value}")
        
        if remove_fields:
            print("Fields to remove:")
            for field in remove_fields:
                print(f"  {field}")
        
        # Perform the edit
        success = editor.edit_file_metadata(
            file_path=file_path,
            set_fields=set_fields,
            remove_fields=remove_fields,
            create_backup=args.backup
        )
        
        if success:
            print(f"\nSuccessfully updated metadata for: {file_path}")
            if args.backup:
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                print(f"Backup created: {backup_path}")
            
            logger.info(f"Metadata updated successfully: {file_path}")
            return 0
        else:
            error_msg = f"Failed to update metadata for: {file_path}"
            
            # Provide specific error messages based on file type
            if file_type == 'image' and not PIL_AVAILABLE:
                error_msg += " (PIL/Pillow not installed)"
            elif file_type in ['audio', 'video'] and not MUTAGEN_AVAILABLE:
                error_msg += " (Mutagen not installed)"
            elif file_type == 'document' and file_path.suffix.lower() == '.pdf' and not PYPDF2_AVAILABLE:
                error_msg += " (PyPDF2 not installed)"
            
            logger.error(error_msg)
            print(f"Error: {error_msg}")
            return 1
    
    except Exception as e:
        logger.error(f"Edit command failed: {e}")
        print(f"Error: Edit command failed: {e}")
        return 1