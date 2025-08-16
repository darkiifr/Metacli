"""View command implementation."""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Any

from ..core.extractor import MetadataExtractor
from ..utils.formatter import OutputFormatter
from ..utils.logger import get_logger


def execute(args) -> int:
    """Execute the view command."""
    logger = get_logger()
    
    try:
        # Initialize extractor
        extractor = MetadataExtractor()
        formatter = OutputFormatter()
        
        # Process each file
        all_metadata = []
        
        for file_path_str in args.files:
            file_path = Path(file_path_str)
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                print(f"Error: File not found: {file_path}")
                continue
            
            if not file_path.is_file():
                logger.error(f"Path is not a file: {file_path}")
                print(f"Error: Path is not a file: {file_path}")
                continue
            
            logger.info(f"Extracting metadata from: {file_path}")
            metadata = extractor.extract_metadata(file_path)
            
            # Filter fields if specified
            if args.fields:
                filtered_metadata = {}
                for field in args.fields:
                    if field in metadata:
                        filtered_metadata[field] = metadata[field]
                    else:
                        # Check nested fields (e.g., 'exif.DateTime')
                        if '.' in field:
                            parts = field.split('.')
                            current = metadata
                            try:
                                for part in parts:
                                    current = current[part]
                                filtered_metadata[field] = current
                            except (KeyError, TypeError):
                                pass  # Field not found
                metadata = filtered_metadata
            
            all_metadata.append({
                'file': str(file_path),
                'metadata': metadata
            })
        
        if not all_metadata:
            logger.error("No valid files to process")
            return 1
        
        # Display results based on format
        if args.format == 'json':
            _display_json(all_metadata)
        elif args.format == 'yaml':
            _display_yaml(all_metadata)
        else:  # table format
            _display_table(all_metadata, formatter)
        
        logger.info(f"Displayed metadata for {len(all_metadata)} files")
        return 0
    
    except Exception as e:
        logger.error(f"View command failed: {e}")
        return 1


def _display_json(metadata_list: List[Dict[str, Any]]) -> None:
    """Display metadata in JSON format."""
    if len(metadata_list) == 1:
        # Single file - display just the metadata
        print(json.dumps(metadata_list[0]['metadata'], indent=2, ensure_ascii=False))
    else:
        # Multiple files - display all
        print(json.dumps(metadata_list, indent=2, ensure_ascii=False))


def _display_yaml(metadata_list: List[Dict[str, Any]]) -> None:
    """Display metadata in YAML format."""
    try:
        if len(metadata_list) == 1:
            # Single file - display just the metadata
            print(yaml.dump(metadata_list[0]['metadata'], default_flow_style=False, allow_unicode=True))
        else:
            # Multiple files - display all
            print(yaml.dump(metadata_list, default_flow_style=False, allow_unicode=True))
    except ImportError:
        print("Error: PyYAML not installed. Install with: pip install PyYAML")
        # Fallback to JSON
        print("\nFalling back to JSON format:")
        _display_json(metadata_list)


def _display_table(metadata_list: List[Dict[str, Any]], formatter: OutputFormatter) -> None:
    """Display metadata in table format."""
    for i, item in enumerate(metadata_list):
        if i > 0:
            print("\n" + "="*80 + "\n")
        
        file_path = item['file']
        metadata = item['metadata']
        
        print(f"File: {file_path}")
        print("-" * len(f"File: {file_path}"))
        
        if 'error' in metadata:
            print(f"Error: {metadata['error']}")
            continue
        
        # Display basic information first
        basic_fields = [
            ('Filename', 'filename'),
            ('Size', 'size_human'),
            ('Type', 'file_type'),
            ('Extension', 'extension'),
            ('MIME Type', 'mime_type'),
            ('Created', 'created'),
            ('Modified', 'modified')
        ]
        
        print("\nBasic Information:")
        for label, key in basic_fields:
            if key in metadata:
                value = metadata[key]
                if value is not None and value != '':
                    print(f"  {label:<12}: {value}")
        
        # Display type-specific metadata
        file_type = metadata.get('file_type', 'unknown')
        
        if file_type == 'image':
            _display_image_metadata(metadata)
        elif file_type == 'audio':
            _display_audio_metadata(metadata)
        elif file_type == 'video':
            _display_video_metadata(metadata)
        elif file_type == 'document':
            _display_document_metadata(metadata)
        
        # Display any remaining metadata
        _display_other_metadata(metadata, basic_fields)


def _display_image_metadata(metadata: Dict[str, Any]) -> None:
    """Display image-specific metadata."""
    image_fields = [
        ('Dimensions', lambda m: f"{m.get('width', '?')} x {m.get('height', '?')}"),
        ('Mode', 'mode'),
        ('Format', 'format'),
        ('Has Transparency', 'has_transparency')
    ]
    
    print("\nImage Information:")
    for label, key in image_fields:
        if callable(key):
            value = key(metadata)
        else:
            value = metadata.get(key)
        
        if value is not None and value != '':
            print(f"  {label:<15}: {value}")
    
    # Display EXIF data
    if 'exif' in metadata and metadata['exif']:
        print("\nEXIF Data:")
        exif_data = metadata['exif']
        
        # Show important EXIF fields first
        important_exif = [
            'DateTime', 'DateTimeOriginal', 'Make', 'Model', 'Software',
            'ExposureTime', 'FNumber', 'ISO', 'FocalLength', 'Flash'
        ]
        
        for field in important_exif:
            if field in exif_data:
                print(f"  {field:<20}: {exif_data[field]}")
        
        # Show other EXIF fields
        other_fields = {k: v for k, v in exif_data.items() if k not in important_exif}
        if other_fields:
            print("\n  Other EXIF fields:")
            for key, value in sorted(other_fields.items()):
                if len(str(value)) < 100:  # Skip very long values
                    print(f"    {key}: {value}")


def _display_audio_metadata(metadata: Dict[str, Any]) -> None:
    """Display audio-specific metadata."""
    audio_fields = [
        ('Duration', 'duration_human'),
        ('Bitrate', lambda m: f"{m.get('bitrate', '?')} kbps" if m.get('bitrate') else None),
        ('Sample Rate', lambda m: f"{m.get('sample_rate', '?')} Hz" if m.get('sample_rate') else None),
        ('Channels', 'channels'),
        ('Title', 'title'),
        ('Artist', 'artist'),
        ('Album', 'album'),
        ('Date', 'date'),
        ('Genre', 'genre')
    ]
    
    print("\nAudio Information:")
    for label, key in audio_fields:
        if callable(key):
            value = key(metadata)
        else:
            value = metadata.get(key)
        
        if value is not None and value != '':
            print(f"  {label:<12}: {value}")
    
    # Display all tags if available
    if 'tags' in metadata and metadata['tags']:
        print("\nAll Tags:")
        for key, value in sorted(metadata['tags'].items()):
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            print(f"  {key}: {value}")


def _display_video_metadata(metadata: Dict[str, Any]) -> None:
    """Display video-specific metadata."""
    video_fields = [
        ('Duration', 'duration_human'),
        ('Bitrate', lambda m: f"{m.get('bitrate', '?')} kbps" if m.get('bitrate') else None)
    ]
    
    print("\nVideo Information:")
    for label, key in video_fields:
        if callable(key):
            value = key(metadata)
        else:
            value = metadata.get(key)
        
        if value is not None and value != '':
            print(f"  {label:<12}: {value}")
    
    # Display tags if available
    if 'tags' in metadata and metadata['tags']:
        print("\nVideo Tags:")
        for key, value in sorted(metadata['tags'].items()):
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            print(f"  {key}: {value}")


def _display_document_metadata(metadata: Dict[str, Any]) -> None:
    """Display document-specific metadata."""
    # PDF metadata
    if 'pages' in metadata:
        print("\nDocument Information:")
        print(f"  Pages       : {metadata['pages']}")
        if 'encrypted' in metadata:
            print(f"  Encrypted   : {metadata['encrypted']}")
        
        if 'pdf_metadata' in metadata:
            print("\nPDF Metadata:")
            for key, value in sorted(metadata['pdf_metadata'].items()):
                print(f"  {key.title():<12}: {value}")
    
    # DOCX metadata
    if 'paragraphs' in metadata:
        print("\nDocument Information:")
        print(f"  Paragraphs  : {metadata['paragraphs']}")
        if 'tables' in metadata:
            print(f"  Tables      : {metadata['tables']}")
        
        if 'core_properties' in metadata:
            print("\nDocument Properties:")
            for key, value in sorted(metadata['core_properties'].items()):
                if value:
                    print(f"  {key.replace('_', ' ').title():<15}: {value}")
    
    # Text file metadata
    if 'lines' in metadata:
        print("\nText Information:")
        print(f"  Lines       : {metadata['lines']}")
        print(f"  Words       : {metadata['words']}")
        print(f"  Characters  : {metadata['characters']}")


def _display_other_metadata(metadata: Dict[str, Any], basic_fields: List) -> None:
    """Display any remaining metadata not shown in other sections."""
    # Get list of keys already displayed
    displayed_keys = set()
    for _, key in basic_fields:
        displayed_keys.add(key)
    
    # Add type-specific keys
    type_specific_keys = {
        'width', 'height', 'mode', 'format', 'has_transparency', 'exif',
        'duration', 'duration_human', 'bitrate', 'sample_rate', 'channels',
        'title', 'artist', 'album', 'date', 'genre', 'tags',
        'pages', 'encrypted', 'pdf_metadata', 'paragraphs', 'tables',
        'core_properties', 'lines', 'words', 'characters', 'characters_no_spaces'
    }
    displayed_keys.update(type_specific_keys)
    
    # Find remaining keys
    remaining = {k: v for k, v in metadata.items() 
                if k not in displayed_keys and not k.startswith('_')}
    
    if remaining:
        print("\nOther Metadata:")
        for key, value in sorted(remaining.items()):
            if isinstance(value, (dict, list)):
                print(f"  {key}: {type(value).__name__} with {len(value)} items")
            else:
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"  {key}: {value_str}")