# MetaCLI Windows Installer

A professional Windows installer application with a Python-style GUI that bundles the MetaCLI GUI and CLI applications with automatic dependency management.

## Features

- **Python-style GUI**: Clean, professional interface similar to the standard Python installer
- **Component Selection**: Choose to install GUI application, CLI application, or both
- **Automatic Dependency Management**: Automatically downloads and installs required Python packages
- **System Integration**: 
  - Add CLI to system PATH
  - Create desktop shortcuts
  - Create Start Menu shortcuts
  - Register in Add/Remove Programs
- **Customizable Installation**: Choose installation directory and components
- **Progress Tracking**: Real-time progress bar and detailed logging
- **Error Handling**: Comprehensive error handling with fallback options

## Building the Installer

### Prerequisites

1. **Python 3.8+** with pip
2. **Required packages**:
   ```bash
   pip install -r installer_requirements.txt
   ```

### Build Process

1. **Prepare the environment**:
   ```bash
   # Install build dependencies
   pip install pyinstaller pywin32
   ```

2. **Build the installer**:
   ```bash
   python build_installer.py
   ```

3. **Output**: The installer will be created as `installer_dist/MetaCLI_Installer.exe`

## Project Structure

```
metacli/
├── metacli_installer.py          # Main installer application
├── build_installer.py            # Build script for creating executable
├── installer_requirements.txt    # Dependencies for the installer
├── installer/                    # Installer modules
│   ├── __init__.py
│   ├── dependency_manager.py     # Python package management
│   └── system_integration.py     # Windows system integration
├── dist/                         # Application executables
│   └── metacli.exe
├── MetaCLI_Portable/            # Portable version
│   └── MetaCLI-GUI.exe
└── requirements.txt             # Application dependencies
```

## Using the Installer

### For End Users

1. **Run the installer**: Double-click `MetaCLI_Installer.exe`
2. **Welcome page**: Click "Next" to begin
3. **Options page**: 
   - Choose installation directory
   - Select components (GUI/CLI)
   - Choose integration options (PATH, shortcuts, etc.)
4. **Installation**: Monitor progress and review logs
5. **Complete**: Launch the application or finish

### Installation Options

- **Installation Directory**: Default is `C:\Program Files\MetaCLI`
- **Components**:
  - MetaCLI GUI Application
  - MetaCLI Command Line Interface
- **System Integration**:
  - Add CLI to system PATH
  - Create desktop shortcuts
  - Create Start Menu shortcuts
  - Register in Add/Remove Programs

## Dependencies

### Installer Dependencies
- `pywin32>=306` - Windows system integration
- `pyinstaller>=5.0` - For building executable (build-time only)

### Application Dependencies (Auto-installed)
- `click>=8.0.0` - Command line interface
- `Pillow>=9.0.0` - Image processing
- `mutagen>=1.45.0` - Audio metadata
- `PyPDF2>=3.0.0` - PDF processing
- `python-docx>=0.8.11` - Word document processing
- `pyyaml>=6.0` - YAML parsing
- `tabulate>=0.9.0` - Table formatting
- `openpyxl>=3.0.0` - Excel file processing
- `chardet>=5.0.0` - Character encoding detection

## Technical Details

### Architecture

- **Main Application**: `metacli_installer.py` - Tkinter-based GUI
- **Dependency Manager**: Handles Python package installation and verification
- **System Integration**: Manages Windows registry, shortcuts, and PATH modifications
- **Modular Design**: Separate modules for different functionality with fallback options

### Error Handling

- **Graceful Degradation**: If advanced features fail, installer falls back to basic functionality
- **Comprehensive Logging**: All operations are logged to `metacli_installer.log`
- **User Feedback**: Clear error messages and progress updates

### Security

- **No Hardcoded Secrets**: No sensitive information in the installer
- **Safe Registry Operations**: Careful handling of Windows registry modifications
- **Permission Handling**: Graceful handling of insufficient permissions

## Troubleshooting

### Common Issues

1. **"Could not modify system PATH"**
   - Run installer as Administrator
   - Manually add installation directory to PATH

2. **"Could not create shortcuts"**
   - Ensure pywin32 is installed
   - Check file permissions

3. **"Dependency installation failed"**
   - Check internet connection
   - Ensure pip is available and updated
   - Run installer as Administrator

### Log Files

- **Installation Log**: `metacli_installer.log` in the installer directory
- **Application Logs**: Check the installed application directory

## Development

### Modifying the Installer

1. **Edit the source files** in the project directory
2. **Test changes** by running `python metacli_installer.py`
3. **Rebuild** using `python build_installer.py`

### Adding Features

- **New Dependencies**: Add to `dependencies` list in `metacli_installer.py`
- **UI Changes**: Modify the respective page setup methods
- **System Integration**: Extend `system_integration.py`

## License

This installer is part of the MetaCLI project. See the main project license for details.