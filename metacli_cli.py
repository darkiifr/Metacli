#!/usr/bin/env python3
"""
MetaCLI Command Line Interface

A comprehensive command-line interface for the MetaCLI metadata extraction tool.
Provides full CLI functionality with advanced options and path management.
"""

import argparse
import sys
import os
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Add the metacli package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from metacli.core.extractor import MetadataExtractor
    from metacli.core.scanner import DirectoryScanner
    from metacli.utils.formatter import OutputFormatter
    from metacli.utils.logger import setup_logger, get_logger
except ImportError as e:
    print(f"Error importing MetaCLI modules: {e}")
    sys.exit(1)


class MetaCLI:
    """Main CLI application class for MetaCLI."""
    
    def __init__(self):
        self.extractor = MetadataExtractor()
        self.scanner = DirectoryScanner()
        self.formatter = OutputFormatter()
        self.logger = None  # Will be set up in setup_logging
        
    def setup_logging(self, verbose: bool = False, log_file: Optional[str] = None):
        """Setup logging configuration."""
        log_file = log_file or 'metacli.log'
        self.logger = setup_logger(verbose=verbose, log_file=log_file)
            
    def extract_single_file(self, file_path: str, output_format: str = 'json', 
                           output_file: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
        """Extract metadata from a single file."""
        try:
            if verbose:
                print(f"Extracting metadata from: {file_path}")
                
            metadata = self.extractor.extract_metadata(file_path)
            
            # Format output
            if output_format.lower() == 'json':
                formatted_output = json.dumps(metadata, indent=2, default=str)
            elif output_format.lower() == 'yaml':
                try:
                    formatted_output = yaml.dump(metadata, default_flow_style=False, default_style=None)
                except ImportError:
                    print("Warning: PyYAML not installed, falling back to JSON")
                    formatted_output = json.dumps(metadata, indent=2, default=str)
            elif output_format.lower() == 'table':
                formatted_output = self._format_as_table(metadata)
            else:
                formatted_output = json.dumps(metadata, indent=2, default=str)
                
            # Output to file or stdout
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)
                if verbose:
                    print(f"Output saved to: {output_file}")
            else:
                print(formatted_output)
                
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
            return {}
            
    def scan_directory(self, directory: str, recursive: bool = True, 
                      file_types: Optional[List[str]] = None, max_files: int = 1000,
                      output_format: str = 'json', output_file: Optional[str] = None,
                      verbose: bool = False, include_metadata: bool = False) -> List[Dict[str, Any]]:
        """Scan directory for files and optionally extract metadata."""
        try:
            if verbose:
                print(f"Scanning directory: {directory}")
                print(f"Recursive: {recursive}, Max files: {max_files}")
                if file_types:
                    print(f"File types filter: {', '.join(file_types)}")
                    
            # Get file list
            files = list(self.scanner.find_files(
                Path(directory),
                recursive=recursive,
                file_types=file_types
            ))
            
            # Apply max_files limit
            if max_files and len(files) > max_files:
                files = files[:max_files]
                if verbose:
                    print(f"Limited to first {max_files} files")
            
            if verbose:
                print(f"Found {len(files)} files")
                
            results = []
            
            # Initialize progress tracking
            start_time = datetime.now()
            total_files = len(files)
            processed_files = 0
            failed_files = 0
            
            for i, file_path in enumerate(files):
                # Calculate progress and time estimates
                progress_percent = ((i + 1) / total_files) * 100
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                if i > 0:  # Avoid division by zero
                    estimated_total_time = elapsed_time * total_files / (i + 1)
                    remaining_time = max(0, estimated_total_time - elapsed_time)
                else:
                    remaining_time = 0
                
                if verbose:
                    # Create progress bar
                    bar_length = 30
                    filled_length = int(bar_length * (i + 1) // total_files)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    
                    # Format time estimates
                    remaining_min = int(remaining_time // 60)
                    remaining_sec = int(remaining_time % 60)
                    
                    # Truncate filename for display
                    display_name = file_path.name[:20]
                    if len(file_path.name) > 20:
                        display_name = display_name + "..."
                    
                    print(f"\r[{bar}] {progress_percent:.1f}% ({i+1}/{total_files}) - {display_name:<23} - ETA: {remaining_min:02d}:{remaining_sec:02d}", end='', flush=True)
                    
                # Enhanced file information with better error handling
                try:
                    stat_info = file_path.stat() if file_path.exists() else None
                    
                    file_info = {
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': stat_info.st_size if stat_info else 0,
                        'size_human': self._format_size(stat_info.st_size) if stat_info else '0 B',
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat() if stat_info else None,
                        'extension': file_path.suffix.lower(),
                        'file_type': self._get_file_type(file_path.suffix.lower())
                    }
                    
                    # Extract metadata if requested
                    if include_metadata:
                        try:
                            metadata = self.extractor.extract_metadata(str(file_path))
                            file_info['metadata'] = metadata
                            
                            # Add quick access to key metadata fields
                            if isinstance(metadata, dict):
                                if 'basic' in metadata:
                                    basic = metadata['basic']
                                    file_info['mime_type'] = basic.get('mime_type')
                                    file_info['created'] = basic.get('created')
                                    file_info['accessed'] = basic.get('accessed')
                                    
                                    # Add type-specific quick info
                                    if 'image' in metadata:
                                        img = metadata['image']
                                        file_info['dimensions'] = f"{img.get('width', 0)}x{img.get('height', 0)}"
                                        file_info['megapixels'] = img.get('megapixels')
                                    elif 'audio' in metadata:
                                        audio = metadata['audio']
                                        file_info['duration'] = audio.get('duration_human')
                                        file_info['bitrate'] = audio.get('bitrate_kbps')
                                    elif 'video' in metadata:
                                        video = metadata['video']
                                        file_info['duration'] = video.get('duration_human')
                                        file_info['resolution'] = video.get('resolution')
                                        file_info['quality'] = video.get('quality_category')
                                    elif 'document' in metadata:
                                        doc = metadata['document']
                                        file_info['pages'] = doc.get('pages')
                                        file_info['words'] = doc.get('words')
                                        file_info['reading_time'] = doc.get('estimated_reading_time')
                                        
                        except Exception as e:
                            file_info['metadata_error'] = str(e)
                            if verbose:
                                print(f"\nWarning: Failed to extract metadata for {file_path.name}: {e}")
                                
                    processed_files += 1
                                
                except Exception as e:
                    failed_files += 1
                    file_info = {
                        'path': str(file_path),
                        'name': file_path.name,
                        'error': f'Failed to process file: {str(e)}'
                    }
                        
                results.append(file_info)
            
            # Clear progress line and show completion
            if verbose:
                total_time = (datetime.now() - start_time).total_seconds()
                print(f"\n✓ Directory scan completed in {total_time:.1f}s")
                print(f"Processed: {processed_files} files, Failed: {failed_files} files")
                
            # Generate summary
            summary = self._generate_scan_summary(results)
            
            # Format output
            output_data = {
                'scan_info': {
                    'directory': directory,
                    'timestamp': datetime.now().isoformat(),
                    'recursive': recursive,
                    'file_types_filter': file_types,
                    'max_files': max_files,
                    'include_metadata': include_metadata
                },
                'summary': summary,
                'files': results
            }
            
            if output_format.lower() == 'json':
                formatted_output = json.dumps(output_data, indent=2, default=str)
            elif output_format.lower() == 'yaml':
                try:
                    formatted_output = yaml.dump(output_data, default_flow_style=False, default_style=None)
                except ImportError:
                    print("Warning: PyYAML not installed, falling back to JSON")
                    formatted_output = json.dumps(output_data, indent=2, default=str)
            elif output_format.lower() == 'summary':
                formatted_output = self._format_scan_summary(summary, results)
            else:
                formatted_output = json.dumps(output_data, indent=2, default=str)
                
            # Output to file or stdout
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)
                if verbose:
                    print(f"Scan results saved to: {output_file}")
            else:
                print(formatted_output)
                
            return results
            
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")
            return []
            
    def batch_process(self, input_file: str, output_dir: str, 
                     output_format: str = 'json', verbose: bool = False) -> None:
        """Process multiple files from a list."""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                file_paths = [line.strip() for line in f if line.strip()]
                
            if verbose:
                print(f"Processing {len(file_paths)} files from {input_file}")
                
            os.makedirs(output_dir, exist_ok=True)
            
            # Initialize progress tracking
            start_time = datetime.now()
            total_files = len(file_paths)
            processed_files = 0
            failed_files = 0
            
            for i, file_path in enumerate(file_paths):
                # Calculate progress and time estimates
                progress_percent = ((i + 1) / total_files) * 100
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                if i > 0:  # Avoid division by zero
                    estimated_total_time = elapsed_time * total_files / (i + 1)
                    remaining_time = max(0, estimated_total_time - elapsed_time)
                else:
                    remaining_time = 0
                
                if verbose:
                    # Create progress bar
                    bar_length = 30
                    filled_length = int(bar_length * (i + 1) // total_files)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    
                    # Format time estimates
                    remaining_min = int(remaining_time // 60)
                    remaining_sec = int(remaining_time % 60)
                    
                    # Truncate filename for display
                    display_name = Path(file_path).name[:20]
                    if len(Path(file_path).name) > 20:
                        display_name = display_name + "..."
                    
                    print(f"\r[{bar}] {progress_percent:.1f}% ({i+1}/{total_files}) - {display_name:<23} - ETA: {remaining_min:02d}:{remaining_sec:02d}", end='', flush=True)
                    
                try:
                    metadata = self.extractor.extract_metadata(file_path)
                    
                    # Generate output filename
                    base_name = Path(file_path).stem
                    output_file = os.path.join(output_dir, f"{base_name}_metadata.{output_format}")
                    
                    # Save metadata
                    if output_format.lower() == 'json':
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, indent=2, default=str)
                    elif output_format.lower() == 'yaml':
                        try:
                            with open(output_file, 'w', encoding='utf-8') as f:
                                yaml.dump(metadata, f, default_flow_style=False, default_style=None)
                        except ImportError:
                            print("Warning: PyYAML not installed, saving as JSON")
                            output_file = output_file.replace('.yaml', '.json')
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, indent=2, default=str)
                                
                    processed_files += 1
                    
                except Exception as e:
                    failed_files += 1
                    if verbose:
                        print(f"\nError processing {file_path}: {e}")
            
            # Clear progress line and show completion
            if verbose:
                total_time = (datetime.now() - start_time).total_seconds()
                print(f"\n✓ Batch processing completed in {total_time:.1f}s")
                print(f"Results saved to: {output_dir}")
                print(f"Processed: {processed_files} files, Failed: {failed_files} files")
                
        except Exception as e:
            print(f"Error in batch processing: {e}")
            
    def batch_report(self, input_file: str, output_file: str, 
                    report_format: str = 'html', verbose: bool = False) -> None:
        """Generate comprehensive batch report from file list."""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                file_paths = [line.strip() for line in f if line.strip()]
                
            if verbose:
                print(f"Generating batch report for {len(file_paths)} files from {input_file}")
                
            # Process all files and collect metadata
            results = []
            errors = []
            
            # Initialize progress tracking
            start_time = datetime.now()
            total_files = len(file_paths)
            
            for i, file_path in enumerate(file_paths):
                # Calculate progress and time estimates
                progress_percent = ((i + 1) / total_files) * 100
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                if i > 0:  # Avoid division by zero
                    estimated_total_time = elapsed_time * total_files / (i + 1)
                    remaining_time = max(0, estimated_total_time - elapsed_time)
                else:
                    remaining_time = 0
                
                if verbose:
                    # Create progress bar
                    bar_length = 30
                    filled_length = int(bar_length * (i + 1) // total_files)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    
                    # Format time estimates
                    remaining_min = int(remaining_time // 60)
                    remaining_sec = int(remaining_time % 60)
                    
                    # Truncate filename for display
                    display_name = Path(file_path).name[:20]
                    if len(Path(file_path).name) > 20:
                        display_name = display_name + "..."
                    
                    print(f"\r[{bar}] {progress_percent:.1f}% ({i+1}/{total_files}) - {display_name:<23} - ETA: {remaining_min:02d}:{remaining_sec:02d}", end='', flush=True)
                    
                try:
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        errors.append({
                            'file': file_path,
                            'error': 'File not found',
                            'type': 'FileNotFoundError'
                        })
                        continue
                        
                    # Get basic file info
                    stat_info = file_path_obj.stat()
                    file_info = {
                        'path': str(file_path_obj),
                        'name': file_path_obj.name,
                        'size': stat_info.st_size,
                        'size_human': self._format_size(stat_info.st_size),
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        'extension': file_path_obj.suffix.lower(),
                        'file_type': self._get_file_type(file_path_obj.suffix.lower())
                    }
                    
                    # Extract metadata
                    try:
                        metadata = self.extractor.extract_metadata(str(file_path_obj))
                        file_info['metadata'] = metadata
                        file_info['has_metadata'] = True
                        
                        # Extract key metadata fields for quick access
                        if isinstance(metadata, dict):
                            if 'basic' in metadata:
                                basic = metadata['basic']
                                file_info['mime_type'] = basic.get('mime_type')
                                file_info['created'] = basic.get('created')
                                
                            # Add type-specific info
                            if 'image' in metadata:
                                img = metadata['image']
                                file_info['dimensions'] = f"{img.get('width', 0)}x{img.get('height', 0)}"
                                file_info['megapixels'] = img.get('megapixels')
                            elif 'audio' in metadata:
                                audio = metadata['audio']
                                file_info['duration'] = audio.get('duration_human')
                                file_info['bitrate'] = audio.get('bitrate_kbps')
                            elif 'video' in metadata:
                                video = metadata['video']
                                file_info['duration'] = video.get('duration_human')
                                file_info['resolution'] = video.get('resolution')
                            elif 'document' in metadata:
                                doc = metadata['document']
                                file_info['pages'] = doc.get('pages')
                                file_info['words'] = doc.get('words')
                                
                    except Exception as e:
                        file_info['metadata_error'] = str(e)
                        file_info['has_metadata'] = False
                        errors.append({
                            'file': file_path,
                            'error': str(e),
                            'type': 'MetadataExtractionError'
                        })
                        
                    results.append(file_info)
                    
                except Exception as e:
                    errors.append({
                        'file': file_path,
                        'error': str(e),
                        'type': 'ProcessingError'
                    })
            
            # Clear progress line and show completion
            if verbose:
                total_time = (datetime.now() - start_time).total_seconds()
                print(f"\n✓ Processing completed in {total_time:.1f}s")
                    
            # Generate comprehensive report
            report_data = self._generate_batch_report_data(results, errors, file_paths)
            
            # Format and save report
            if report_format.lower() == 'html':
                report_content = self._generate_html_report(report_data)
            elif report_format.lower() == 'json':
                report_content = json.dumps(report_data, indent=2, default=str)
            elif report_format.lower() == 'csv':
                report_content = self._generate_csv_report(report_data)
            else:
                report_content = json.dumps(report_data, indent=2, default=str)
                
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            if verbose:
                print(f"Batch report generated: {output_file}")
                print(f"Processed: {len(results)} files, Errors: {len(errors)}")
                
        except Exception as e:
            print(f"Error generating batch report: {e}")
            
    def compare_files(self, file1: str, file2: str, output_format: str = 'json',
                     output_file: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
        """Compare metadata between two files."""
        try:
            if verbose:
                print(f"Comparing files: {file1} vs {file2}")
                
            metadata1 = self.extractor.extract_metadata(file1)
            metadata2 = self.extractor.extract_metadata(file2)
            
            comparison = {
                'file1': {'path': file1, 'metadata': metadata1},
                'file2': {'path': file2, 'metadata': metadata2},
                'comparison': self._compare_metadata(metadata1, metadata2),
                'timestamp': datetime.now().isoformat()
            }
            
            # Format output
            if output_format.lower() == 'json':
                formatted_output = json.dumps(comparison, indent=2, default=str)
            elif output_format.lower() == 'yaml':
                try:
                    formatted_output = yaml.dump(comparison, default_flow_style=False, default_style=None)
                except ImportError:
                    print("Warning: PyYAML not installed, falling back to JSON")
                    formatted_output = json.dumps(comparison, indent=2, default=str)
            else:
                formatted_output = json.dumps(comparison, indent=2, default=str)
                
            # Output to file or stdout
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)
                if verbose:
                    print(f"Comparison saved to: {output_file}")
            else:
                print(formatted_output)
                
            return comparison
            
        except Exception as e:
            print(f"Error comparing files: {e}")
            return {}
            
    def _format_as_table(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as an enhanced table with better organization."""
        output = ""
        
        # Handle both old and new metadata structure
        if 'basic' in metadata:
            # New structure with categorized metadata
            basic_info = metadata.get('basic', {})
            
            # File Information Section
            output += "\nFILE INFORMATION:\n"
            output += "=" * 50 + "\n"
            
            # Essential file info
            essential_fields = [
                ('filename', 'Filename'),
                ('filepath', 'Full Path'),
                ('size_human', 'Size'),
                ('size_kb', 'Size (KB)'),
                ('size_mb', 'Size (MB)'),
                ('extension', 'Extension'),
                ('file_type', 'File Type'),
                ('mime_type', 'MIME Type')
            ]
            
            for field, label in essential_fields:
                if field in basic_info:
                    output += f"{label:20}: {basic_info[field]}\n"
            
            # Dates section
            output += "\nDATES & TIMES:\n"
            output += "-" * 30 + "\n"
            date_fields = [
                ('created', 'Created'),
                ('modified', 'Modified'),
                ('accessed', 'Last Accessed'),
                ('extraction_timestamp', 'Analyzed')
            ]
            
            for field, label in date_fields:
                if field in basic_info:
                    value = basic_info[field]
                    if 'T' in str(value):  # ISO format
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            value = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    output += f"{label:20}: {value}\n"
            
            # Permissions section
            if any(field in basic_info for field in ['permissions', 'is_readable', 'is_writable']):
                output += "\nPERMISSIONS:\n"
                output += "-" * 30 + "\n"
                perm_fields = [
                    ('permissions', 'Permissions'),
                    ('is_readable', 'Readable'),
                    ('is_writable', 'Writable'),
                    ('is_executable', 'Executable')
                ]
                
                for field, label in perm_fields:
                    if field in basic_info:
                        output += f"{label:20}: {basic_info[field]}\n"
            
            # Type-specific metadata sections
            for section_name, section_data in metadata.items():
                if section_name == 'basic':
                    continue
                    
                if isinstance(section_data, dict) and section_data:
                    output += f"\n{section_name.upper()} METADATA:\n"
                    output += "=" * 50 + "\n"
                    
                    for key, value in section_data.items():
                        if isinstance(value, dict):
                            output += f"{key.title()}:\n"
                            for sub_key, sub_value in value.items():
                                output += f"  {sub_key:18}: {sub_value}\n"
                        else:
                            formatted_key = key.replace('_', ' ').title()
                            output += f"{formatted_key:20}: {value}\n"
                    output += "\n"
            
            # Error information
            error_fields = [k for k in metadata.keys() if 'error' in k.lower()]
            if error_fields:
                output += "\nERRORS/WARNINGS:\n"
                output += "=" * 50 + "\n"
                for field in error_fields:
                    output += f"{field.replace('_', ' ').title()}: {metadata[field]}\n"
                output += "\n"
                
        else:
            # Legacy structure - simple display
            for category, data in metadata.items():
                output += f"\n{category.upper()}:\n"
                output += "-" * 30 + "\n"
                if isinstance(data, dict):
                    for key, value in data.items():
                        formatted_key = key.replace('_', ' ').title()
                        output += f"{formatted_key:20}: {value}\n"
                else:
                    output += f"{data}\n"
                output += "\n"
        
        return output
        
    def _generate_scan_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics from scan results."""
        total_files = len(results)
        total_size = sum(file_info.get('size', 0) for file_info in results)
        
        # Group by extension
        extensions = {}
        for file_info in results:
            ext = file_info.get('extension', '(no extension)')
            extensions[ext] = extensions.get(ext, 0) + 1
            
        # Group by file type
        file_types = {}
        for file_info in results:
            ext = file_info.get('extension', '')
            file_type = file_info.get('file_type', self._get_file_type(ext))
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        # Count files with metadata and errors
        files_with_metadata = sum(1 for file_info in results if 'metadata' in file_info)
        files_with_errors = sum(1 for file_info in results if 'metadata_error' in file_info or 'error' in file_info)
        
        # Calculate size statistics
        sizes = [file_info.get('size', 0) for file_info in results if file_info.get('size', 0) > 0]
        size_stats = {}
        if sizes:
            size_stats = {
                'largest_file': max(sizes),
                'largest_file_human': self._format_size(max(sizes)),
                'smallest_file': min(sizes),
                'smallest_file_human': self._format_size(min(sizes)),
                'average_size': sum(sizes) // len(sizes),
                'average_size_human': self._format_size(sum(sizes) // len(sizes))
            }
        
        # Type-specific statistics
        type_stats = {}
        for file_info in results:
            if 'metadata' in file_info and isinstance(file_info['metadata'], dict):
                metadata = file_info['metadata']
                
                # Image statistics
                if 'image' in metadata:
                    if 'images' not in type_stats:
                        type_stats['images'] = {'count': 0, 'total_megapixels': 0}
                    type_stats['images']['count'] += 1
                    mp = metadata['image'].get('megapixels', 0)
                    if mp:
                        type_stats['images']['total_megapixels'] += mp
                
                # Audio statistics
                elif 'audio' in metadata:
                    if 'audio' not in type_stats:
                        type_stats['audio'] = {'count': 0, 'total_duration': 0}
                    type_stats['audio']['count'] += 1
                    duration = metadata['audio'].get('duration', 0)
                    if duration:
                        type_stats['audio']['total_duration'] += duration
                
                # Video statistics
                elif 'video' in metadata:
                    if 'video' not in type_stats:
                        type_stats['video'] = {'count': 0, 'total_duration': 0}
                    type_stats['video']['count'] += 1
                    duration = metadata['video'].get('duration', 0)
                    if duration:
                        type_stats['video']['total_duration'] += duration
                
                # Document statistics
                elif 'document' in metadata:
                    if 'documents' not in type_stats:
                        type_stats['documents'] = {'count': 0, 'total_pages': 0, 'total_words': 0}
                    type_stats['documents']['count'] += 1
                    pages = metadata['document'].get('pages', 0)
                    words = metadata['document'].get('words', 0)
                    if pages:
                        type_stats['documents']['total_pages'] += pages
                    if words:
                        type_stats['documents']['total_words'] += words
            
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': self._format_size(total_size),
            'extensions': dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)),
            'file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
            'files_with_metadata': files_with_metadata,
            'files_with_errors': files_with_errors,
            'success_rate': f"{((files_with_metadata / total_files) * 100):.1f}%" if total_files > 0 else "0%",
            'size_statistics': size_stats,
            'type_statistics': type_stats
        }
        
    def _format_scan_summary(self, summary: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Format scan summary as readable text with enhanced statistics."""
        output = "SCAN SUMMARY\n"
        output += "=" * 50 + "\n\n"
        output += f"Total files: {summary['total_files']}\n"
        output += f"Total size: {summary['total_size_formatted']}\n"
        
        # Metadata processing statistics
        if 'files_with_metadata' in summary:
            output += f"Files with metadata: {summary['files_with_metadata']}\n"
            output += f"Files with errors: {summary['files_with_errors']}\n"
            output += f"Success rate: {summary['success_rate']}\n"
        output += "\n"
        
        # Size statistics
        if 'size_statistics' in summary and summary['size_statistics']:
            size_stats = summary['size_statistics']
            output += "SIZE STATISTICS:\n"
            output += "-" * 30 + "\n"
            output += f"Largest file: {size_stats['largest_file_human']}\n"
            output += f"Smallest file: {size_stats['smallest_file_human']}\n"
            output += f"Average size: {size_stats['average_size_human']}\n\n"
        
        if summary['file_types']:
            output += "FILE TYPES:\n"
            output += "-" * 30 + "\n"
            for file_type, count in summary['file_types'].items():
                percentage = (count / summary['total_files']) * 100
                output += f"  {file_type}: {count} files ({percentage:.1f}%)\n"
            output += "\n"
            
        if summary['extensions']:
            output += "TOP EXTENSIONS:\n"
            output += "-" * 30 + "\n"
            for ext, count in list(summary['extensions'].items())[:10]:  # Top 10
                percentage = (count / summary['total_files']) * 100
                output += f"  {ext}: {count} files ({percentage:.1f}%)\n"
            if len(summary['extensions']) > 10:
                output += f"  ... and {len(summary['extensions']) - 10} more\n"
            output += "\n"
        
        # Type-specific statistics
        if 'type_statistics' in summary and summary['type_statistics']:
            type_stats = summary['type_statistics']
            output += "TYPE-SPECIFIC STATISTICS:\n"
            output += "-" * 30 + "\n"
            
            if 'images' in type_stats:
                img_stats = type_stats['images']
                avg_mp = img_stats['total_megapixels'] / img_stats['count'] if img_stats['count'] > 0 else 0
                output += f"Images: {img_stats['count']} files, {img_stats['total_megapixels']:.1f} total MP, {avg_mp:.1f} avg MP\n"
            
            if 'audio' in type_stats:
                audio_stats = type_stats['audio']
                total_duration_min = audio_stats['total_duration'] / 60
                avg_duration_min = total_duration_min / audio_stats['count'] if audio_stats['count'] > 0 else 0
                output += f"Audio: {audio_stats['count']} files, {total_duration_min:.1f} total minutes, {avg_duration_min:.1f} avg minutes\n"
            
            if 'video' in type_stats:
                video_stats = type_stats['video']
                total_duration_min = video_stats['total_duration'] / 60
                avg_duration_min = total_duration_min / video_stats['count'] if video_stats['count'] > 0 else 0
                output += f"Video: {video_stats['count']} files, {total_duration_min:.1f} total minutes, {avg_duration_min:.1f} avg minutes\n"
            
            if 'documents' in type_stats:
                doc_stats = type_stats['documents']
                avg_pages = doc_stats['total_pages'] / doc_stats['count'] if doc_stats['count'] > 0 else 0
                avg_words = doc_stats['total_words'] / doc_stats['count'] if doc_stats['count'] > 0 else 0
                output += f"Documents: {doc_stats['count']} files, {doc_stats['total_pages']} total pages ({avg_pages:.1f} avg), {doc_stats['total_words']} total words ({avg_words:.0f} avg)\n"
            
            output += "\n"
            
        # Sample files
        if results:
            output += "SAMPLE FILES (first 5):\n"
            output += "-" * 30 + "\n"
            for file_info in results[:5]:
                name = Path(file_info['path']).name
                size = self._format_size(file_info.get('size', 0))
                file_type = file_info.get('file_type', 'Unknown')
                output += f"  {name} ({size}, {file_type})\n"
            if len(results) > 5:
                output += f"  ... and {len(results) - 5} more files\n"
                
        return output
        
    def _compare_metadata(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two metadata dictionaries."""
        common_keys = set(metadata1.keys()) & set(metadata2.keys())
        unique_to_1 = set(metadata1.keys()) - set(metadata2.keys())
        unique_to_2 = set(metadata2.keys()) - set(metadata1.keys())
        
        differences = {}
        for key in common_keys:
            if metadata1[key] != metadata2[key]:
                differences[key] = {
                    'file1': metadata1[key],
                    'file2': metadata2[key]
                }
                
        return {
            'common_keys': list(common_keys),
            'unique_to_file1': list(unique_to_1),
            'unique_to_file2': list(unique_to_2),
            'differences': differences,
            'identical_keys': [key for key in common_keys if metadata1[key] == metadata2[key]]
        }
        
    def _get_file_type(self, extension: str) -> str:
        """Get file type from extension."""
        type_map = {
            '.jpg': 'Image', '.jpeg': 'Image', '.png': 'Image', '.gif': 'Image', '.bmp': 'Image',
            '.tiff': 'Image', '.webp': 'Image', '.svg': 'Image',
            '.pdf': 'Document', '.doc': 'Document', '.docx': 'Document', '.txt': 'Document',
            '.rtf': 'Document', '.odt': 'Document', '.xlsx': 'Spreadsheet', '.xls': 'Spreadsheet',
            '.csv': 'Spreadsheet', '.pptx': 'Presentation', '.ppt': 'Presentation',
            '.mp3': 'Audio', '.wav': 'Audio', '.flac': 'Audio', '.aac': 'Audio', '.ogg': 'Audio',
            '.m4a': 'Audio', '.wma': 'Audio',
            '.mp4': 'Video', '.avi': 'Video', '.mkv': 'Video', '.mov': 'Video', '.wmv': 'Video',
            '.flv': 'Video', '.webm': 'Video',
            '.zip': 'Archive', '.rar': 'Archive', '.7z': 'Archive', '.tar': 'Archive',
            '.gz': 'Archive', '.bz2': 'Archive',
            '.py': 'Code', '.js': 'Code', '.html': 'Code', '.css': 'Code', '.cpp': 'Code',
            '.c': 'Code', '.java': 'Code', '.php': 'Code', '.rb': 'Code', '.go': 'Code'
        }
        return type_map.get(extension.lower(), 'Unknown')
        
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
        
    def _generate_batch_report_data(self, results: List[Dict[str, Any]], 
                                   errors: List[Dict[str, Any]], 
                                   original_files: List[str]) -> Dict[str, Any]:
        """Generate comprehensive batch report data."""
        total_files = len(original_files)
        processed_files = len(results)
        error_count = len(errors)
        
        # Calculate statistics
        total_size = sum(r.get('size', 0) for r in results)
        files_with_metadata = sum(1 for r in results if r.get('has_metadata', False))
        
        # Extension statistics
        extensions = {}
        file_types = {}
        mime_types = {}
        
        for result in results:
            ext = result.get('extension', '')
            file_type = result.get('file_type', 'Unknown')
            mime_type = result.get('mime_type', 'Unknown')
            
            extensions[ext] = extensions.get(ext, 0) + 1
            file_types[file_type] = file_types.get(file_type, 0) + 1
            mime_types[mime_type] = mime_types.get(mime_type, 0) + 1
            
        # Size statistics
        sizes = [r.get('size', 0) for r in results if r.get('size', 0) > 0]
        size_stats = {
            'total_size': total_size,
            'total_size_human': self._format_size(total_size),
            'average_size': sum(sizes) // len(sizes) if sizes else 0,
            'largest_file': max(sizes) if sizes else 0,
            'smallest_file': min(sizes) if sizes else 0
        }
        
        if size_stats['average_size'] > 0:
            size_stats['average_size_human'] = self._format_size(size_stats['average_size'])
        if size_stats['largest_file'] > 0:
            size_stats['largest_file_human'] = self._format_size(size_stats['largest_file'])
        if size_stats['smallest_file'] > 0:
            size_stats['smallest_file_human'] = self._format_size(size_stats['smallest_file'])
            
        # Error statistics
        error_types = {}
        for error in errors:
            error_type = error.get('type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
        # Media-specific statistics
        media_stats = {
            'images': {'count': 0, 'total_megapixels': 0, 'formats': {}},
            'audio': {'count': 0, 'total_duration': 0, 'formats': {}},
            'video': {'count': 0, 'total_duration': 0, 'formats': {}},
            'documents': {'count': 0, 'total_pages': 0, 'total_words': 0}
        }
        
        for result in results:
            if result.get('file_type') == 'Image':
                media_stats['images']['count'] += 1
                if 'megapixels' in result:
                    media_stats['images']['total_megapixels'] += result.get('megapixels', 0)
                ext = result.get('extension', '')
                media_stats['images']['formats'][ext] = media_stats['images']['formats'].get(ext, 0) + 1
                
            elif result.get('file_type') == 'Audio':
                media_stats['audio']['count'] += 1
                ext = result.get('extension', '')
                media_stats['audio']['formats'][ext] = media_stats['audio']['formats'].get(ext, 0) + 1
                
            elif result.get('file_type') == 'Video':
                media_stats['video']['count'] += 1
                ext = result.get('extension', '')
                media_stats['video']['formats'][ext] = media_stats['video']['formats'].get(ext, 0) + 1
                
            elif result.get('file_type') == 'Document':
                media_stats['documents']['count'] += 1
                if 'pages' in result:
                    media_stats['documents']['total_pages'] += result.get('pages', 0)
                if 'words' in result:
                    media_stats['documents']['total_words'] += result.get('words', 0)
        
        return {
            'report_info': {
                'generated_at': datetime.now().isoformat(),
                'total_files_requested': total_files,
                'files_processed': processed_files,
                'files_with_errors': error_count,
                'success_rate': f"{((processed_files / total_files) * 100):.1f}%" if total_files > 0 else "0%",
                'metadata_extraction_rate': f"{((files_with_metadata / processed_files) * 100):.1f}%" if processed_files > 0 else "0%"
            },
            'statistics': {
                'size_statistics': size_stats,
                'extension_distribution': dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)),
                'file_type_distribution': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
                'mime_type_distribution': dict(sorted(mime_types.items(), key=lambda x: x[1], reverse=True)),
                'media_statistics': media_stats
            },
            'errors': {
                'total_errors': error_count,
                'error_types': error_types,
                'error_details': errors
            },
            'files': results
        }
        
    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report from report data."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>MetaCLI Batch Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .stat-card { background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #007acc; }
        .error { color: #d32f2f; }
        .success { color: #388e3c; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .file-list { max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body>
"""
        
        # Header
        report_info = report_data['report_info']
        html += f"""
    <div class="header">
        <h1>MetaCLI Batch Report</h1>
        <p>Generated: {report_info['generated_at']}</p>
        <p>Files Processed: {report_info['files_processed']} / {report_info['total_files_requested']}</p>
        <p>Success Rate: <span class="success">{report_info['success_rate']}</span></p>
        <p>Metadata Extraction Rate: <span class="success">{report_info['metadata_extraction_rate']}</span></p>
    </div>
"""
        
        # Statistics
        stats = report_data['statistics']
        html += """
    <div class="section">
        <h2>Statistics</h2>
        <div class="stats-grid">
"""
        
        # Size statistics
        size_stats = stats['size_statistics']
        html += f"""
            <div class="stat-card">
                <h3>Size Statistics</h3>
                <p>Total Size: {size_stats['total_size_human']}</p>
                <p>Average Size: {size_stats.get('average_size_human', 'N/A')}</p>
                <p>Largest File: {size_stats.get('largest_file_human', 'N/A')}</p>
                <p>Smallest File: {size_stats.get('smallest_file_human', 'N/A')}</p>
            </div>
"""
        
        # File type distribution
        html += """
            <div class="stat-card">
                <h3>File Types</h3>
"""
        for file_type, count in list(stats['file_type_distribution'].items())[:5]:
            html += f"<p>{file_type}: {count} files</p>"
        html += "</div>"
        
        # Extension distribution
        html += """
            <div class="stat-card">
                <h3>Top Extensions</h3>
"""
        for ext, count in list(stats['extension_distribution'].items())[:5]:
            html += f"<p>{ext or '(no extension)'}: {count} files</p>"
        html += "</div>"
        
        html += "</div></div>"
        
        # Errors section
        if report_data['errors']['total_errors'] > 0:
            html += """
    <div class="section">
        <h2>Errors</h2>
        <div class="error">
"""
            html += f"<p>Total Errors: {report_data['errors']['total_errors']}</p>"
            
            for error_type, count in report_data['errors']['error_types'].items():
                html += f"<p>{error_type}: {count} errors</p>"
                
            html += "</div></div>"
        
        # Files table
        html += """
    <div class="section">
        <h2>Files</h2>
        <div class="file-list">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Type</th>
                        <th>Modified</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for file_info in report_data['files'][:100]:  # Limit to first 100 files
            name = Path(file_info['path']).name
            size = file_info.get('size_human', 'N/A')
            file_type = file_info.get('file_type', 'Unknown')
            modified = file_info.get('modified', 'N/A')
            if modified != 'N/A' and 'T' in modified:
                try:
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                    modified = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
                    
            status = "Success" if file_info.get('has_metadata', False) else "No Metadata"
            if 'error' in file_info or 'metadata_error' in file_info:
                status = "Error"
                
            status_class = "success" if status == "Success" else "error" if status == "Error" else ""
            
            html += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{size}</td>
                        <td>{file_type}</td>
                        <td>{modified}</td>
                        <td class="{status_class}">{status}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        
        return html
        
    def _generate_csv_report(self, report_data: Dict[str, Any]) -> str:
        """Generate CSV report from report data."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'File Path', 'File Name', 'Size (Bytes)', 'Size (Human)', 'File Type',
            'Extension', 'MIME Type', 'Modified', 'Has Metadata', 'Error'
        ])
        
        # Write file data
        for file_info in report_data['files']:
            writer.writerow([
                file_info.get('path', ''),
                Path(file_info.get('path', '')).name,
                file_info.get('size', 0),
                file_info.get('size_human', ''),
                file_info.get('file_type', ''),
                file_info.get('extension', ''),
                file_info.get('mime_type', ''),
                file_info.get('modified', ''),
                file_info.get('has_metadata', False),
                file_info.get('error', file_info.get('metadata_error', ''))
            ])
        
        return output.getvalue()


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="MetaCLI - Advanced Metadata Extraction Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  metacli extract file.jpg                    # Extract metadata from a single file
  metacli scan /path/to/dir --recursive       # Scan directory recursively
  metacli scan /path/to/dir --format yaml     # Output in YAML format
  metacli batch files.txt ./output/           # Batch process files from list
  metacli compare file1.jpg file2.jpg         # Compare metadata between files
  metacli extract file.pdf --output result.json  # Save output to file
        """
    )
    
    # Global options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--log-file', type=str,
                       help='Log file path')
    parser.add_argument('--version', action='version', version='MetaCLI 2.0')
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract metadata from a single file')
    extract_parser.add_argument('file', help='File path to extract metadata from')
    extract_parser.add_argument('--format', '-f', choices=['json', 'yaml', 'table'], 
                               default='json', help='Output format')
    extract_parser.add_argument('--output', '-o', type=str,
                               help='Output file path')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory for files')
    scan_parser.add_argument('directory', help='Directory path to scan')
    scan_parser.add_argument('--recursive', '-r', action='store_true', default=True,
                            help='Scan recursively (default: True)')
    scan_parser.add_argument('--no-recursive', action='store_false', dest='recursive',
                            help='Disable recursive scanning')
    scan_parser.add_argument('--file-types', '-t', nargs='+',
                            help='Filter by file types (e.g., images documents audio)')
    scan_parser.add_argument('--max-files', '-m', type=int, default=1000,
                            help='Maximum number of files to process')
    scan_parser.add_argument('--format', '-f', choices=['json', 'yaml', 'summary'], 
                            default='json', help='Output format')
    scan_parser.add_argument('--output', '-o', type=str,
                            help='Output file path')
    scan_parser.add_argument('--include-metadata', action='store_true',
                            help='Extract metadata for each file (slower)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple files from a list')
    batch_parser.add_argument('input_file', help='Text file containing list of file paths')
    batch_parser.add_argument('output_dir', help='Output directory for results')
    batch_parser.add_argument('--format', '-f', choices=['json', 'yaml'], 
                             default='json', help='Output format')
    
    # Batch report command
    batch_report_parser = subparsers.add_parser('batch-report', help='Generate comprehensive batch report')
    batch_report_parser.add_argument('input_file', help='Text file containing list of file paths')
    batch_report_parser.add_argument('--output', '-o', help='Output file path')
    batch_report_parser.add_argument('--format', '-f', choices=['html', 'json', 'csv'], 
                                    default='html', help='Report format (default: html)')
    batch_report_parser.add_argument('--workers', type=int, default=4,
                                    help='Number of worker threads (default: 4)')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare metadata between two files')
    compare_parser.add_argument('file1', help='First file path')
    compare_parser.add_argument('file2', help='Second file path')
    compare_parser.add_argument('--format', '-f', choices=['json', 'yaml'], 
                               default='json', help='Output format')
    compare_parser.add_argument('--output', '-o', type=str,
                               help='Output file path')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch graphical user interface')
    
    return parser


def main():
    """Main entry point for the CLI application."""
    parser = create_parser()
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return
        
    # Initialize CLI application
    cli = MetaCLI()
    cli.setup_logging(verbose=args.verbose, log_file=getattr(args, 'log_file', None))
    
    try:
        if args.command == 'extract':
            cli.extract_single_file(
                file_path=args.file,
                output_format=args.format,
                output_file=args.output,
                verbose=args.verbose
            )
            
        elif args.command == 'scan':
            cli.scan_directory(
                directory=args.directory,
                recursive=args.recursive,
                file_types=args.file_types,
                max_files=args.max_files,
                output_format=args.format,
                output_file=args.output,
                verbose=args.verbose,
                include_metadata=args.include_metadata
            )
            
        elif args.command == 'batch':
            cli.batch_process(
                input_file=args.input_file,
                output_dir=args.output_dir,
                output_format=args.format,
                verbose=args.verbose
            )
            
        elif args.command == 'batch-report':
            cli.batch_report(
                input_file=args.input_file,
                output_file=args.output,
                report_format=args.format,
                verbose=args.verbose
            )
            
        elif args.command == 'compare':
            cli.compare_files(
                file1=args.file1,
                file2=args.file2,
                output_format=args.format,
                output_file=args.output,
                verbose=args.verbose
            )
            
        elif args.command == 'gui':
            # Launch GUI
            try:
                from metacli_gui import main as gui_main
                gui_main()
            except ImportError:
                print("Error: GUI components not available. Please install tkinter.")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()