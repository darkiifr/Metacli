#!/usr/bin/env python3
"""Simple test script to verify MetaCLI installation and basic functionality."""

import os
import sys
import tempfile
from pathlib import Path

# Add the metacli package to the path for testing
sys.path.insert(0, str(Path(__file__).parent))

try:
    from metacli.core.extractor import MetadataExtractor
    from metacli.core.scanner import DirectoryScanner
    from metacli.utils.logger import setup_logger
    from metacli.utils.formatter import OutputFormatter
    print("✓ All core modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def test_metadata_extractor():
    """Test the metadata extractor with a simple text file."""
    print("\nTesting MetadataExtractor...")
    
    # Create a temporary text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file for MetaCLI.\n")
        temp_file = f.name
    
    try:
        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(temp_file)
        
        if metadata and 'basic' in metadata:
            print("✓ MetadataExtractor working correctly")
            print(f"  - File: {metadata['basic']['filename']}")
            print(f"  - Size: {metadata['basic']['size']} bytes")
            print(f"  - Type: {metadata['basic']['file_type']}")
        else:
            print("✗ MetadataExtractor returned unexpected result")
            return False
    
    except Exception as e:
        print(f"✗ MetadataExtractor error: {e}")
        return False
    
    finally:
        # Clean up
        try:
            os.unlink(temp_file)
        except:
            pass
    
    return True

def test_directory_scanner():
    """Test the directory scanner."""
    print("\nTesting DirectoryScanner...")
    
    try:
        scanner = DirectoryScanner()
        
        # Test with current directory
        current_dir = Path.cwd()
        files = scanner.find_files_list(current_dir, recursive=False)
        
        if files:
            print(f"✓ DirectoryScanner found {len(files)} files")
            print(f"  - Example: {files[0] if files else 'None'}")
        else:
            print("✓ DirectoryScanner working (no files found in current directory)")
        
        return True
    
    except Exception as e:
        print(f"✗ DirectoryScanner error: {e}")
        return False

def test_logger():
    """Test the logger setup."""
    print("\nTesting Logger...")
    
    try:
        logger = setup_logger(verbose=False)
        logger.info("Test log message")
        print("✓ Logger setup successful")
        return True
    
    except Exception as e:
        print(f"✗ Logger error: {e}")
        return False

def test_formatter():
    """Test the output formatter."""
    print("\nTesting OutputFormatter...")
    
    try:
        formatter = OutputFormatter('json')
        test_data = {'test': 'data', 'number': 42}
        
        json_output = formatter.format_data(test_data)
        if 'test' in json_output and 'data' in json_output:
            print("✓ JSON formatting working")
        else:
            print("✗ JSON formatting failed")
            return False
        
        # Test table format if tabulate is available
        try:
            table_formatter = OutputFormatter('table')
            table_output = table_formatter.format_data(test_data)
            if 'test' in table_output:
                print("✓ Table formatting working")
            else:
                print("! Table formatting available but output unexpected")
        except:
            print("! Table formatting not available (tabulate not installed)")
        
        return True
    
    except Exception as e:
        print(f"✗ OutputFormatter error: {e}")
        return False

def test_cli_entry_point():
    """Test the CLI entry point."""
    print("\nTesting CLI entry point...")
    
    try:
        from metacli.main import main
        print("✓ CLI entry point imported successfully")
        return True
    
    except Exception as e:
        print(f"✗ CLI entry point error: {e}")
        return False

def main():
    """Run all tests."""
    print("MetaCLI Installation Test")
    print("=" * 25)
    
    tests = [
        test_metadata_extractor,
        test_directory_scanner,
        test_logger,
        test_formatter,
        test_cli_entry_point,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 25)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! MetaCLI is ready to use.")
        print("\nTry running:")
        print("  python -m metacli --help")
        print("  python -m metacli scan . --help")
        return 0
    else:
        print(f"\n❌ {total - passed} tests failed. Please check the installation.")
        return 1

if __name__ == '__main__':
    sys.exit(main())