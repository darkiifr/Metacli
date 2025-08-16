"""Export command implementation."""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.scanner import DirectoryScanner, ScanResult
from ..core.extractor import MetadataExtractor
from ..utils.formatter import OutputFormatter
from ..utils.logger import get_logger

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class MetadataExporter:
    """Export metadata to various formats."""
    
    def __init__(self):
        """Initialize the metadata exporter."""
        self.extractor = MetadataExtractor()
        self.scanner = DirectoryScanner(self.extractor)
    
    def export_to_json(self, results: List[ScanResult], output_path: Path, 
                      include_stats: bool = True) -> bool:
        """Export metadata to JSON format."""
        try:
            export_data = {
                'export_info': {
                    'format': 'json',
                    'timestamp': datetime.now().isoformat(),
                    'total_files': len(results)
                },
                'files': []
            }
            
            # Add statistics if requested
            if include_stats:
                stats = self.scanner.get_file_statistics(results)
                export_data['statistics'] = stats
            
            # Add file data
            for result in results:
                file_data = {
                    'path': str(result.file_path),
                    'metadata': result.metadata
                }
                if result.error:
                    file_data['error'] = result.error
                export_data['files'].append(file_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception:
            return False
    
    def export_to_csv(self, results: List[ScanResult], output_path: Path) -> bool:
        """Export metadata to CSV format."""
        try:
            # Collect all unique metadata fields
            all_fields = set(['filepath'])
            for result in results:
                if not result.error:
                    all_fields.update(self._flatten_dict(result.metadata).keys())
            
            # Sort fields for consistent output
            fieldnames = ['filepath'] + sorted([f for f in all_fields if f != 'filepath'])
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    row = {'filepath': str(result.file_path)}
                    
                    if result.error:
                        row['error'] = result.error
                    else:
                        # Flatten nested metadata
                        flattened = self._flatten_dict(result.metadata)
                        row.update(flattened)
                    
                    # Convert all values to strings and handle None values
                    for key, value in row.items():
                        if value is None:
                            row[key] = ''
                        elif isinstance(value, (list, dict)):
                            row[key] = str(value)
                        else:
                            row[key] = str(value)
                    
                    writer.writerow(row)
            
            return True
        
        except Exception:
            return False
    
    def export_to_xml(self, results: List[ScanResult], output_path: Path,
                     include_stats: bool = True) -> bool:
        """Export metadata to XML format."""
        try:
            root = ET.Element('metadata_export')
            
            # Add export info
            export_info = ET.SubElement(root, 'export_info')
            ET.SubElement(export_info, 'format').text = 'xml'
            ET.SubElement(export_info, 'timestamp').text = datetime.now().isoformat()
            ET.SubElement(export_info, 'total_files').text = str(len(results))
            
            # Add statistics if requested
            if include_stats:
                stats = self.scanner.get_file_statistics(results)
                stats_elem = ET.SubElement(root, 'statistics')
                self._dict_to_xml(stats, stats_elem)
            
            # Add files
            files_elem = ET.SubElement(root, 'files')
            
            for result in results:
                file_elem = ET.SubElement(files_elem, 'file')
                file_elem.set('path', str(result.file_path))
                
                if result.error:
                    ET.SubElement(file_elem, 'error').text = result.error
                else:
                    metadata_elem = ET.SubElement(file_elem, 'metadata')
                    self._dict_to_xml(result.metadata, metadata_elem)
            
            # Write to file
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)  # Pretty print
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            return True
        
        except Exception:
            return False
    
    def export_to_yaml(self, results: List[ScanResult], output_path: Path,
                      include_stats: bool = True) -> bool:
        """Export metadata to YAML format."""
        if not YAML_AVAILABLE:
            return False
        
        try:
            export_data = {
                'export_info': {
                    'format': 'yaml',
                    'timestamp': datetime.now().isoformat(),
                    'total_files': len(results)
                },
                'files': []
            }
            
            # Add statistics if requested
            if include_stats:
                stats = self.scanner.get_file_statistics(results)
                export_data['statistics'] = stats
            
            # Add file data
            for result in results:
                file_data = {
                    'path': str(result.file_path),
                    'metadata': result.metadata
                }
                if result.error:
                    file_data['error'] = result.error
                export_data['files'].append(file_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            
            return True
        
        except Exception:
            return False
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten a nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to comma-separated strings
                items.append((new_key, ', '.join(str(item) for item in v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element) -> None:
        """Convert dictionary to XML elements."""
        for key, value in data.items():
            # Clean key name for XML
            clean_key = str(key).replace(' ', '_').replace('.', '_')
            
            if isinstance(value, dict):
                elem = ET.SubElement(parent, clean_key)
                self._dict_to_xml(value, elem)
            elif isinstance(value, list):
                elem = ET.SubElement(parent, clean_key)
                for i, item in enumerate(value):
                    item_elem = ET.SubElement(elem, 'item')
                    item_elem.set('index', str(i))
                    item_elem.text = str(item)
            else:
                elem = ET.SubElement(parent, clean_key)
                elem.text = str(value) if value is not None else ''


def execute(args) -> int:
    """Execute the export command."""
    logger = get_logger()
    
    try:
        input_path = Path(args.input)
        output_path = Path(args.output)
        
        if not input_path.exists():
            logger.error(f"Input path does not exist: {input_path}")
            print(f"Error: Input path does not exist: {input_path}")
            return 1
        
        # Check output format
        if args.format == 'yaml' and not YAML_AVAILABLE:
            logger.error("PyYAML not installed. Install with: pip install PyYAML")
            print("Error: PyYAML not installed. Install with: pip install PyYAML")
            return 1
        
        # Initialize exporter
        exporter = MetadataExporter()
        
        # Collect files to process
        results = []
        
        if input_path.is_file():
            # Single file
            logger.info(f"Processing single file: {input_path}")
            metadata = exporter.extractor.extract_metadata(input_path)
            from ..core.scanner import ScanResult
            results.append(ScanResult(input_path, metadata))
        
        elif input_path.is_dir():
            # Directory
            logger.info(f"Scanning directory: {input_path}")
            
            # Set up progress callback
            def progress_callback(current: int, total: int):
                if total > 0:
                    percent = (current / total) * 100
                    print(f"\rProcessing: {current}/{total} ({percent:.1f}%)", end="", flush=True)
            
            exporter.scanner.set_progress_callback(progress_callback)
            
            results = exporter.scanner.scan_directory(
                path=input_path,
                recursive=args.recursive,
                extract_metadata=True
            )
            
            # Clear progress line
            print("\r" + " " * 50 + "\r", end="")
        
        else:
            logger.error(f"Invalid input path: {input_path}")
            print(f"Error: Invalid input path: {input_path}")
            return 1
        
        if not results:
            logger.info("No files found to export")
            print("No files found to export")
            return 0
        
        logger.info(f"Exporting {len(results)} files to {args.format.upper()} format")
        print(f"Exporting {len(results)} files to {args.format.upper()} format...")
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export based on format
        success = False
        
        if args.format == 'json':
            success = exporter.export_to_json(results, output_path)
        elif args.format == 'csv':
            success = exporter.export_to_csv(results, output_path)
        elif args.format == 'xml':
            success = exporter.export_to_xml(results, output_path)
        elif args.format == 'yaml':
            success = exporter.export_to_yaml(results, output_path)
        else:
            logger.error(f"Unsupported export format: {args.format}")
            print(f"Error: Unsupported export format: {args.format}")
            return 1
        
        if success:
            # Show export statistics
            stats = exporter.scanner.get_file_statistics(results)
            
            print(f"\nExport completed successfully!")
            print(f"Output file: {output_path}")
            print(f"Files exported: {stats['successful_scans']}")
            if stats['failed_scans'] > 0:
                print(f"Files with errors: {stats['failed_scans']}")
            print(f"Total size: {stats['total_size_human']}")
            
            # Show file type breakdown
            if stats['file_types']:
                print("\nFile types exported:")
                for file_type, count in sorted(stats['file_types'].items()):
                    print(f"  {file_type}: {count} files")
            
            logger.info(f"Export completed: {output_path}")
            return 0
        
        else:
            logger.error(f"Failed to export to {args.format} format")
            print(f"Error: Failed to export to {args.format} format")
            return 1
    
    except KeyboardInterrupt:
        logger.info("Export cancelled by user")
        print("\nExport cancelled by user")
        return 130
    
    except Exception as e:
        logger.error(f"Export command failed: {e}")
        print(f"Error: Export command failed: {e}")
        return 1