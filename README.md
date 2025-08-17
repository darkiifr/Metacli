# MetaCLI - Advanced File Metadata Analysis Tool

MetaCLI is a powerful desktop application for analyzing file metadata, managing directory scans, and providing comprehensive file information with an intuitive graphical interface.

## ✨ Features

### Core Functionality
- **File Metadata Extraction**: Extract detailed metadata from various file types including images, documents, audio, video, and executables
- **Directory Scanning**: Recursive and non-recursive directory scanning with customizable filters
- **Advanced Filtering**: Filter by file types, size limits, hidden files, and more
- **Export Capabilities**: Export results to JSON, CSV, XML, and HTML formats
- **Search & Filter**: Real-time search and filtering of scan results

### GUI Features
- **Modern Interface**: Clean, responsive GUI built with tkinter
- **Performance Optimized**: Batch processing and threaded operations for smooth performance
- **Progress Tracking**: Real-time progress updates during scanning operations
- **Customizable Views**: Multiple view modes and sorting options
- **Theme Support**: Light and dark theme options

### Update System
- **Automatic Updates**: Built-in update system with hash verification
- **Executable Hashing**: Secure hash-based update verification
- **GitHub Integration**: Automatic checking for new releases
- **Selective Updates**: Update only necessary components

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows, macOS, or Linux

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/darkiifr/Metacli.git
   cd metacli
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI Application
Launch the graphical interface:
```bash
python metacli_gui.py
```

### Command Line Interface
Use the CLI for batch operations:
```bash
python -m metacli.cli --help
```

### Utility Tools

#### Hash Calculator
Calculate hashes for files or installations:
```bash
python -m metacli.utils.hasher --file path/to/file
python -m metacli.utils.hasher --installation
```

#### Update Manager
Check for and install updates:
```bash
python -m metacli.utils.updater --check
python -m metacli.utils.updater --update
python -m metacli.utils.updater --info
```

## Project Structure

```
metacli/
├── metacli/
│   ├── core/
│   │   ├── extractor.py      # Metadata extraction engine
│   │   ├── scanner.py        # Directory scanning functionality
│   │   └── formatter.py      # Output formatting
│   ├── utils/
│   │   ├── hasher.py         # Executable hashing utilities
│   │   └── updater.py        # Update system
│   └── cli.py                # Command line interface
├── metacli_gui.py            # Main GUI application
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Configuration

The application supports various configuration options:

- **File Type Filters**: Customize which file types to include in scans
- **Size Limits**: Set minimum and maximum file size limits
- **Output Formats**: Choose from JSON, CSV, XML, or HTML export formats
- **Performance Settings**: Adjust thread counts and batch sizes

## Supported File Types

- **Images**: JPEG, PNG, GIF, BMP, TIFF, WebP
- **Documents**: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- **Audio**: MP3, WAV, FLAC, AAC, OGG
- **Video**: MP4, AVI, MKV, MOV, WMV
- **Archives**: ZIP, RAR, 7Z, TAR, GZ
- **Executables**: EXE, DLL, MSI
- **And many more...**

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Building Executables
```bash
pyinstaller --onefile --windowed metacli_gui.py
```

### Contributing
1. Fork the repository at https://github.com/darkiifr/Metacli
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the project's coding standards
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Submit a pull request

**Note:** All contributions must comply with the project license terms.

## Security

- All updates are verified using SHA-256 hashes
- No sensitive data is transmitted or stored
- Local file access only (no network file operations)

## Performance

- Optimized for large directory scans
- Threaded operations prevent UI freezing
- Batch processing for memory efficiency
- Configurable performance settings

## Troubleshooting

### Common Issues

1. **Scan not working**: Ensure you have read permissions for the target directory
2. **GUI freezing**: Check if antivirus is interfering with file operations
3. **Update failures**: Verify internet connection and GitHub access

### Debug Mode
Run with debug logging:
```bash
python metacli_gui.py --debug
```

## License

This project is licensed under a custom license that restricts commercial use and distribution. See the LICENSE file for complete terms and conditions.

**Key License Points:**
- ✅ Personal and educational use allowed
- ✅ Non-commercial development and testing
- ✅ Contributing back to the original project
- ❌ Commercial use prohibited
- ❌ Distribution of modified versions prohibited
- ❌ Selling or monetizing prohibited

For commercial licensing inquiries, please contact us through the project repository.

## Changelog

### Version 1.0.0
- Initial release with core metadata extraction
- GUI interface with modern design
- Export functionality
- Update system with hash verification
- Performance optimizations

## Support

For support, please:
1. Check the troubleshooting section
2. Search existing GitHub issues at https://github.com/darkiifr/Metacli/issues
3. Create a new issue with detailed information
4. Visit the project repository: https://github.com/darkiifr/Metacli

## Acknowledgments

- Built with Python and tkinter
- Uses various metadata extraction libraries
- Inspired by the need for comprehensive file analysis tools