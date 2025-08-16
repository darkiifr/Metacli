#!/usr/bin/env python3
"""Main entry point for MetaCLI application."""

import argparse
import sys
from pathlib import Path

from metacli.commands import scan, view, edit, export
from metacli.utils.logger import setup_logger, get_logger
from metacli.utils.formatter import get_color_formatter, set_output_format


def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog='metacli',
        description='Extract, process, and manage metadata from various file types',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path (default: metacli.log)'
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='COMMAND'
    )
    
    # Scan command
    scan_parser = subparsers.add_parser(
        'scan',
        help='Scan directories for files and extract metadata'
    )
    scan_parser.add_argument(
        'path',
        type=str,
        help='Directory or file path to scan'
    )
    scan_parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Scan directories recursively'
    )
    scan_parser.add_argument(
        '--file-types',
        nargs='+',
        help='Filter by file types (e.g., jpg png pdf mp3)'
    )
    scan_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file to save scan results'
    )
    
    # View command
    view_parser = subparsers.add_parser(
        'view',
        help='View metadata of specific files'
    )
    view_parser.add_argument(
        'files',
        nargs='+',
        help='File paths to view metadata'
    )
    view_parser.add_argument(
        '--format',
        choices=['table', 'json', 'yaml'],
        default='table',
        help='Output format (default: table)'
    )
    view_parser.add_argument(
        '--fields',
        nargs='+',
        help='Specific metadata fields to display'
    )
    
    # Edit command
    edit_parser = subparsers.add_parser(
        'edit',
        help='Edit metadata of files'
    )
    edit_parser.add_argument(
        'file',
        type=str,
        help='File path to edit metadata'
    )
    edit_parser.add_argument(
        '--set',
        nargs=2,
        metavar=('FIELD', 'VALUE'),
        action='append',
        help='Set metadata field value (can be used multiple times)'
    )
    edit_parser.add_argument(
        '--remove',
        nargs='+',
        help='Remove metadata fields'
    )
    edit_parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before editing'
    )
    
    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export metadata to various formats'
    )
    export_parser.add_argument(
        'input',
        type=str,
        help='Input file or directory'
    )
    export_parser.add_argument(
        'output',
        type=str,
        help='Output file path'
    )
    export_parser.add_argument(
        '--format',
        choices=['json', 'csv', 'xml', 'yaml'],
        default='json',
        help='Export format (default: json)'
    )
    export_parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Process directories recursively'
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_file = args.log_file or 'metacli.log'
    logger = setup_logger(verbose=args.verbose, log_file=log_file)
    
    # Set up output formatting
    if hasattr(args, 'format'):
        set_output_format(args.format)
    
    # Configure color formatter
    color_formatter = get_color_formatter()
    if hasattr(args, 'no_color') and args.no_color:
        color_formatter.enabled = False
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Execute the appropriate command
        if args.command == 'scan':
            return scan.execute(args)
        elif args.command == 'view':
            return view.execute(args)
        elif args.command == 'edit':
            return edit.execute(args)
        elif args.command == 'export':
            return export.execute(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print(color_formatter.warning("\nOperation cancelled by user"))
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(color_formatter.error(f"Error: {e}"))
        if args.verbose:
            logger.exception("Full traceback:")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())