# MetaCLI v3.0 🚀

A powerful, modern desktop application for extracting and analyzing metadata from various file types. MetaCLI combines an intuitive graphical interface with a comprehensive command-line tool, featuring enhanced performance, beautiful UI, and automated dependency management.

## ✨ Features

### 🎯 Core Functionality
- **Multi-format Support**: Extract metadata from images, audio, video, documents, and archives
- **Dual Interface**: Both GUI and CLI for different use cases
- **Batch Processing**: Handle multiple files with parallel processing
- **Smart Caching**: Intelligent caching system for improved performance
- **Export Options**: Multiple output formats (JSON, CSV, XML, YAML)

### 🎨 Enhanced GUI (v3.0)
- **Modern Design**: Beautiful, responsive interface with dark/light themes
- **Tabbed Interface**: Organized workflow with File Scanner, Metadata Viewer, Batch Operations, and Settings
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Real-time Preview**: Live metadata display and analysis
- **Progress Tracking**: Visual progress indicators for long operations
- **Responsive Layout**: Adaptive design that works on different screen sizes

### ⚡ Performance Optimizations
- **Parallel Processing**: Multi-threaded file processing
- **Memory Optimization**: Efficient memory usage with weak references
- **Lazy Loading**: Load data only when needed
- **Caching System**: Smart caching to avoid redundant operations
- **Optimized Algorithms**: Faster file type detection and metadata extraction

### 🛠️ Developer Features
- **Automated Setup**: One-click dependency installation
- **Cross-platform**: Windows, macOS, and Linux support
- **Extensible Architecture**: Easy to add new file type support
- **Comprehensive Logging**: Detailed logging for debugging
- **Error Handling**: Robust error handling and recovery

## 🚀 Quick Start

### Automated Installation (Recommended)

1. **Clone the repository**:
```bash
git clone <repository-url>
cd metacli
```

2. **Run the automated setup**:
```bash
python setup_dependencies.py
```

3. **Activate the environment**:
```bash
# Windows
activate_metacli.bat

# macOS/Linux
./activate_metacli.sh
```

4. **Launch the application**:
```bash
# GUI Application
python metacli_gui.py

# Command Line
python -m metacli.cli --help
```

### Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install system tools (optional)
# Windows: Download FFmpeg and ExifTool manually
# macOS: brew install ffmpeg exiftool
# Linux: sudo apt-get install ffmpeg libimage-exiftool-perl
```

## Quick Start

### Basic Usage

```bash
# Scan a directory for files and extract metadata
metacli scan /path/to/directory

# View metadata for a specific file
metacli view /path/to/file.jpg

# Edit metadata for a file
metacli edit /path/to/file.jpg --set "title=My Photo" --set "author=John Doe"

# Export metadata to different formats
metacli export /path/to/directory --format csv --output metadata.csv
```

### Output Formats

```bash
# JSON output (default)
metacli view file.jpg --format json

# YAML output
metacli view file.jpg --format yaml

# Table output
metacli view file.jpg --format table

# Plain text output
metacli view file.jpg --format plain
```

## Commands

### scan

Scan directories for files and extract metadata.

```bash
metacli scan [OPTIONS] DIRECTORY

Options:
  -r, --recursive          Scan directories recursively
  -t, --types TEXT         File types to include (e.g., jpg,png,pdf)
  --min-size INTEGER       Minimum file size in bytes
  --max-size INTEGER       Maximum file size in bytes
  --include-hidden         Include hidden files
  --threads INTEGER        Number of threads for processing (default: 4)
  --save TEXT             Save results to file
  --stats                 Show scan statistics
```

**Examples:**

```bash
# Scan current directory recursively
metacli scan . --recursive

# Scan only image files
metacli scan /photos --types jpg,png,gif --recursive

# Scan with size filters
metacli scan /documents --min-size 1024 --max-size 10485760

# Save results to file
metacli scan /media --recursive --save scan_results.json

# Show detailed statistics
metacli scan /music --types mp3,flac --stats
```

### view

View metadata for specific files.

```bash
metacli view [OPTIONS] FILE [FILE ...]

Options:
  --format [json|yaml|table|plain]  Output format (default: json)
  --fields TEXT                     Specific fields to display
  --no-basic                       Exclude basic file information
```

**Examples:**

```bash
# View metadata for a single file
metacli view photo.jpg

# View specific fields only
metacli view photo.jpg --fields "title,author,date_taken"

# View multiple files in table format
metacli view *.jpg --format table

# View without basic file information
metacli view document.pdf --no-basic
```

### edit

Edit metadata for files.

```bash
metacli edit [OPTIONS] FILE

Options:
  --set TEXT     Set metadata field (format: key=value)
  --remove TEXT  Remove metadata field
  --backup       Create backup before editing
  --dry-run      Show what would be changed without making changes
```

**Examples:**

```bash
# Set metadata fields
metacli edit photo.jpg --set "title=Sunset" --set "author=Jane Doe"

# Remove metadata fields
metacli edit photo.jpg --remove "gps_latitude" --remove "gps_longitude"

# Create backup before editing
metacli edit document.pdf --set "author=John Smith" --backup

# Dry run to preview changes
metacli edit audio.mp3 --set "album=Greatest Hits" --dry-run
```

### export

Export metadata to various formats.

```bash
metacli export [OPTIONS] PATH

Options:
  --format [json|csv|xml|yaml]  Export format (default: json)
  --output TEXT                 Output file path
  --recursive                   Process directories recursively
  --types TEXT                  File types to include
  --fields TEXT                 Specific fields to export
```

**Examples:**

```bash
# Export to CSV
metacli export /photos --format csv --output metadata.csv

# Export specific file types
metacli export /media --types jpg,png,mp4 --format json

# Export specific fields only
metacli export /documents --fields "filename,size,modified_date" --format xml

# Export with recursive scanning
metacli export /archive --recursive --format yaml --output archive_metadata.yaml
```

## Supported File Types

### Images
- **JPEG/JPG**: EXIF data, camera settings, GPS coordinates
- **PNG**: Basic metadata, text chunks
- **TIFF**: EXIF data, image properties
- **GIF**: Basic properties, animation info
- **BMP**: Basic image properties
- **WEBP**: Basic properties and EXIF (when available)

### Audio
- **MP3**: ID3 tags (v1 and v2), bitrate, duration
- **FLAC**: Vorbis comments, audio properties
- **OGG**: Vorbis comments, codec information
- **M4A/AAC**: iTunes-style metadata
- **WAV**: Basic audio properties

### Video
- **MP4**: Metadata, codec information, duration
- **AVI**: Basic properties, codec details
- **MKV**: Matroska metadata, track information
- **MOV**: QuickTime metadata
- **WMV**: Windows Media metadata

### Documents
- **PDF**: Document properties, author, creation date
- **DOCX**: Document properties, author, statistics
- **TXT**: Basic file properties, encoding detection

## Configuration

### Global Options

```bash
# Enable verbose logging
metacli --verbose scan /path

# Disable colored output
metacli --no-color view file.jpg

# Custom log file
metacli --log-file custom.log scan /path

# Set output format globally
metacli --format yaml view file.jpg
```

### Environment Variables

```bash
# Set default output format
export METACLI_FORMAT=yaml

# Set default log level
export METACLI_LOG_LEVEL=DEBUG

# Disable colors
export METACLI_NO_COLOR=1
```

## Advanced Usage

### Filtering and Processing

```bash
# Complex file type filtering
metacli scan /media --types "jpg,png,gif,mp4,avi,mp3" --recursive

# Size-based filtering
metacli scan /documents --min-size 1048576 --max-size 104857600  # 1MB to 100MB

# Combine with system tools
metacli scan /photos --format json | jq '.[] | select(.width > 1920)'
```

### Batch Operations

```bash
# Process multiple directories
for dir in /photos/*; do
    metacli export "$dir" --format csv --output "${dir##*/}_metadata.csv"
done

# Batch metadata editing
find /photos -name "*.jpg" -exec metacli edit {} --set "copyright=© 2024 My Company" \;
```

### Integration with Other Tools

```bash
# Find files missing specific metadata
metacli scan /photos --format json | jq '.[] | select(.author == null) | .filepath'

# Generate reports
metacli export /media --format csv | csvstat --count

# Backup metadata before bulk operations
metacli export /important_files --format json --output backup_metadata.json
```

## Error Handling

MetaCLI provides comprehensive error handling and logging:

- **File Access Errors**: Gracefully handles permission issues and missing files
- **Format Errors**: Reports unsupported file formats with suggestions
- **Dependency Errors**: Clear messages when optional dependencies are missing
- **Validation Errors**: Validates input parameters and provides helpful error messages

### Common Issues

1. **Missing Dependencies**:
   ```bash
   # Install optional dependencies for full functionality
   pip install "metacli[full]"
   ```

2. **Permission Errors**:
   ```bash
   # Run with appropriate permissions or check file ownership
   sudo metacli scan /system/files
   ```

3. **Large Directory Processing**:
   ```bash
   # Use threading for better performance
   metacli scan /large_directory --threads 8 --verbose
   ```

## Development

### Setting Up Development Environment

```bash
# Clone and setup
git clone https://github.com/metacli/metacli.git
cd metacli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev,full]"

# Run tests
pytest

# Code formatting
black metacli/
flake8 metacli/
```

### Project Structure

```
metacli/
├── metacli/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── extractor.py     # Metadata extraction
│   │   └── scanner.py       # Directory scanning
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── scan.py          # Scan command
│   │   ├── view.py          # View command
│   │   ├── edit.py          # Edit command
│   │   └── export.py        # Export command
│   └── utils/
│       ├── __init__.py
│       ├── logger.py        # Logging utilities
│       └── formatter.py     # Output formatting
├── tests/
├── requirements.txt
├── setup.py
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Format code (`black metacli/`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### Version 1.0.0
- Initial release
- Support for images, audio, video, and document metadata
- CLI interface with scan, view, edit, and export commands
- Multiple output formats (JSON, YAML, table, plain text)
- Export to JSON, CSV, XML, and YAML
- Comprehensive logging and error handling
- Cross-platform support

## Support

- **Documentation**: [https://metacli.readthedocs.io/](https://metacli.readthedocs.io/)
- **Issues**: [https://github.com/metacli/metacli/issues](https://github.com/metacli/metacli/issues)
- **Discussions**: [https://github.com/metacli/metacli/discussions](https://github.com/metacli/metacli/discussions)

## Acknowledgments

- [Pillow](https://pillow.readthedocs.io/) for image processing
- [Mutagen](https://mutagen.readthedocs.io/) for audio metadata
- [PyPDF2](https://pypdf2.readthedocs.io/) for PDF processing
- [python-docx](https://python-docx.readthedocs.io/) for DOCX processing
- [Click](https://click.palletsprojects.com/) for CLI framework inspiration
- [Tabulate](https://github.com/astanin/python-tabulate) for table formatting