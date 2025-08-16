"""Scan command implementation."""

import json
import sys
from pathlib import Path
from typing import Optional

from ..core.scanner import DirectoryScanner
from ..core.extractor import MetadataExtractor
from ..utils.formatter import OutputFormatter
from ..utils.logger import get_logger


def execute(args) -> int:
    """Execute the scan command."""
    logger = get_logger()
    
    try:
        # Validate input path
        scan_path = Path(args.path)
        if not scan_path.exists():
            logger.error(f"Path does not exist: {scan_path}")
            return 1
        
        # Initialize scanner
        extractor = MetadataExtractor()
        scanner = DirectoryScanner(extractor)
        
        # Set up progress callback
        def progress_callback(current: int, total: int):
            if sys.stdout.isatty():  # Only show progress in interactive terminals
                percent = (current / total) * 100
                print(f"\rProgress: {current}/{total} ({percent:.1f}%)", end="", flush=True)
        
        scanner.set_progress_callback(progress_callback)
        
        logger.info(f"Starting scan of: {scan_path}")
        
        # Perform the scan
        results = scanner.scan_directory(
            path=scan_path,
            recursive=args.recursive,
            file_types=args.file_types,
            include_hidden=False,
            extract_metadata=True,
            max_workers=4
        )
        
        # Clear progress line
        if sys.stdout.isatty():
            print("\r" + " " * 50 + "\r", end="")
        
        if not results:
            logger.info("No files found matching the criteria")
            return 0
        
        # Generate statistics
        stats = scanner.get_file_statistics(results)
        
        # Display results
        formatter = OutputFormatter()
        
        print(f"\nScan completed successfully!")
        print(f"Found {stats['total_files']} files")
        print(f"Successfully processed: {stats['successful_scans']}")
        if stats['failed_scans'] > 0:
            print(f"Failed to process: {stats['failed_scans']}")
        print(f"Total size: {stats['total_size_human']}")
        
        # Show file type breakdown
        if stats['file_types']:
            print("\nFile types found:")
            for file_type, count in sorted(stats['file_types'].items()):
                print(f"  {file_type}: {count} files")
        
        # Show extension breakdown
        if stats['extensions']:
            print("\nExtensions found:")
            for ext, count in sorted(stats['extensions'].items()):
                ext_display = ext if ext != 'none' else '(no extension)'
                print(f"  {ext_display}: {count} files")
        
        # Show largest and smallest files
        if stats['largest_file']:
            print(f"\nLargest file: {stats['largest_file']['path']} ({stats['largest_file']['size_human']})")
        if stats['smallest_file']:
            print(f"Smallest file: {stats['smallest_file']['path']} ({stats['smallest_file']['size_human']})")
        
        # Save results if output file specified
        if args.output:
            output_path = Path(args.output)
            
            # Prepare data for export
            export_data = {
                'scan_info': {
                    'path': str(scan_path),
                    'recursive': args.recursive,
                    'file_types': args.file_types,
                    'timestamp': formatter.get_timestamp()
                },
                'statistics': stats,
                'files': []
            }
            
            for result in results:
                file_data = {
                    'path': str(result.file_path),
                    'metadata': result.metadata
                }
                if result.error:
                    file_data['error'] = result.error
                export_data['files'].append(file_data)
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Results saved to: {output_path}")
                print(f"\nResults saved to: {output_path}")
            
            except Exception as e:
                logger.error(f"Failed to save results: {e}")
                print(f"Warning: Failed to save results to {output_path}: {e}")
        
        # Show sample files if not saving to file
        if not args.output and results:
            print("\nSample files (first 5):")
            for i, result in enumerate(results[:5]):
                if result.error:
                    print(f"  {result.file_path} - ERROR: {result.error}")
                else:
                    metadata = result.metadata
                    file_type = metadata.get('file_type', 'unknown')
                    size = metadata.get('size_human', 'unknown')
                    print(f"  {result.file_path} ({file_type}, {size})")
            
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more files")
                print(f"\nUse --output to save complete results to a file")
        
        logger.info(f"Scan completed: {stats['successful_scans']} files processed")
        return 0
    
    except KeyboardInterrupt:
        logger.info("Scan cancelled by user")
        return 130
    
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return 1