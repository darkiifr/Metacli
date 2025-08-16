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
                directory,
                recursive=recursive,
                file_types=file_types,
                max_files=max_files
            ))
            
            if verbose:
                print(f"Found {len(files)} files")
                
            results = []
            
            for i, file_path in enumerate(files):
                if verbose and i % 10 == 0:
                    print(f"Processing file {i+1}/{len(files)}: {file_path.name}")
                    
                file_info = {
                    'path': str(file_path),
                    'name': file_path.name,
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else None,
                    'extension': file_path.suffix.lower()
                }
                
                # Extract metadata if requested
                if include_metadata:
                    try:
                        metadata = self.extractor.extract_metadata(str(file_path))
                        file_info['metadata'] = metadata
                    except Exception as e:
                        file_info['metadata_error'] = str(e)
                        
                results.append(file_info)
                
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
            
            for i, file_path in enumerate(file_paths):
                if verbose:
                    print(f"Processing {i+1}/{len(file_paths)}: {file_path}")
                    
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
                                
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    
            if verbose:
                print(f"Batch processing completed. Results saved to: {output_dir}")
                
        except Exception as e:
            print(f"Error in batch processing: {e}")
            
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
        """Format metadata as a simple table."""
        output = ""
        for category, data in metadata.items():
            output += f"\n{category.upper()}:\n"
            output += "-" * 30 + "\n"
            if isinstance(data, dict):
                for key, value in data.items():
                    output += f"{key:20}: {value}\n"
            else:
                output += f"{data}\n"
            output += "\n"
        return output
        
    def _generate_scan_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from scan results."""
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
            file_type = self._get_file_type(ext)
            file_types[file_type] = file_types.get(file_type, 0) + 1
            
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': self._format_size(total_size),
            'extensions': dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)),
            'file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True))
        }
        
    def _format_scan_summary(self, summary: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Format scan summary as readable text."""
        output = "SCAN SUMMARY\n"
        output += "=" * 50 + "\n\n"
        output += f"Total files: {summary['total_files']}\n"
        output += f"Total size: {summary['total_size_formatted']}\n\n"
        
        if summary['file_types']:
            output += "File types:\n"
            for file_type, count in summary['file_types'].items():
                output += f"  {file_type}: {count} files\n"
            output += "\n"
            
        if summary['extensions']:
            output += "Extensions:\n"
            for ext, count in list(summary['extensions'].items())[:10]:  # Top 10
                output += f"  {ext}: {count} files\n"
            if len(summary['extensions']) > 10:
                output += f"  ... and {len(summary['extensions']) - 10} more\n"
            output += "\n"
            
        # Sample files
        if results:
            output += "Sample files (first 5):\n"
            for file_info in results[:5]:
                name = Path(file_info['path']).name
                size = self._format_size(file_info.get('size', 0))
                output += f"  {name} ({size})\n"
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