# MetaCLI Installer Documentation

This document provides comprehensive information about the MetaCLI installer system, including installation, repair, modification, and uninstallation capabilities.

## Overview

The MetaCLI installer is a sophisticated Windows application that provides a complete installation experience with GUI support for multiple operation modes:

- **Install**: Fresh installation of MetaCLI
- **Repair**: Fix corrupted or incomplete installations
- **Modify**: Change installation components and settings
- **Uninstall**: Complete removal of MetaCLI from the system

## Installation Modes

### 1. Install Mode (Default)

**Purpose**: Performs a fresh installation of MetaCLI on the system.

**Usage**:
```bash
python metacli_installer.py
# or
python metacli_installer.py --help
```

**Features**:
- System requirements validation
- Dependency checking and installation
- Component selection (GUI and/or CLI)
- Installation path customization
- System integration options:
  - Add to system PATH
  - Create desktop shortcuts
  - Create Start Menu shortcuts
  - Register in Add/Remove Programs
- Administrator privilege handling
- Antivirus exclusion setup

### 2. Repair Mode

**Purpose**: Repairs existing MetaCLI installations by restoring missing or corrupted files and system integrations.

**Usage**:
```bash
python metacli_installer.py --repair
# or
repair_metacli.bat
```

**Features**:
- Detects existing installation automatically
- Validates and restores application files
- Re-creates missing system integrations
- Preserves user settings and data
- Fixes registry entries
- Restores shortcuts and PATH entries

**When to Use**:
- Application files are missing or corrupted
- Shortcuts are broken or missing
- PATH entries are incorrect
- Registry entries are damaged
- Installation appears incomplete

### 3. Modify Mode

**Purpose**: Allows modification of existing installation components and system integrations.

**Usage**:
```bash
python metacli_installer.py --modify
# or
modify_metacli.bat
```

**Features**:
- Shows current installation status
- Allows adding/removing system integrations:
  - Desktop shortcuts
  - Start Menu shortcuts
  - System PATH entries
- Preserves existing installation files
- Updates registry entries as needed

**Use Cases**:
- Add or remove desktop shortcuts
- Add or remove Start Menu shortcuts
- Add or remove PATH integration
- Change system integration preferences

### 4. Uninstall Mode

**Purpose**: Completely removes MetaCLI from the system.

**Usage**:
```bash
python metacli_installer.py --uninstall
# or
uninstall_metacli.bat
```

**Features**:
- Detects all installed components
- Removes application files
- Cleans up system integrations:
  - Removes shortcuts
  - Removes PATH entries
  - Removes registry entries
- Option to preserve user data
- Complete cleanup verification

**Removal Process**:
1. Detection of installed components
2. User confirmation with component list
3. Removal of shortcuts and PATH entries
4. Registry cleanup
5. File removal (optional user data preservation)
6. Verification of complete removal

## System Requirements

- **Operating System**: Windows 10 or later
- **Python**: 3.8 or later
- **Administrator Privileges**: Required for install, repair, and uninstall modes
- **Dependencies**: 
  - tkinter (GUI framework)
  - pywin32 (Windows integration)
  - requests (dependency downloads)

## File Structure

```
metacli/
├── metacli_installer.py          # Main installer application
├── repair_metacli.bat            # Repair mode launcher
├── modify_metacli.bat            # Modify mode launcher
├── uninstall_metacli.bat         # Uninstall mode launcher
├── installer/
│   ├── dependency_manager.py     # Dependency handling
│   ├── system_integration.py     # Windows system integration
│   ├── INSTALLER_README.md       # This documentation
│   └── INSTALLER_COMPLETE.md     # Complete technical documentation
└── README.md                     # Main project documentation
```

## Administrator Privileges

The installer automatically handles administrator privilege requests:

- **Install Mode**: Always requires admin privileges
- **Repair Mode**: Always requires admin privileges
- **Modify Mode**: No admin privileges required (only modifies user-level integrations)
- **Uninstall Mode**: Always requires admin privileges

When admin privileges are needed, the installer will:
1. Detect current privilege level
2. Display a UAC prompt if needed
3. Restart with elevated permissions
4. Continue with the requested operation

## Installation Detection

The installer uses multiple methods to detect existing installations:

1. **Registry Check**: Looks for MetaCLI entries in Windows Registry
2. **File System Check**: Verifies installation directory and files
3. **Component Analysis**: Identifies which components are installed:
   - GUI application
   - CLI application
   - Desktop shortcuts
   - Start Menu shortcuts
   - PATH entries

## Error Handling and Logging

The installer provides comprehensive error handling:

- **Installation Logs**: Detailed logs for troubleshooting
- **Progress Tracking**: Real-time progress updates
- **Error Recovery**: Automatic cleanup on installation failure
- **User Feedback**: Clear error messages and resolution steps

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Solution: Run installer as administrator
   - Use right-click → "Run as administrator"

2. **Installation Not Detected**
   - Check if MetaCLI was installed manually
   - Verify registry entries exist
   - Use repair mode to restore detection

3. **Dependency Installation Failures**
   - Ensure internet connection is available
   - Check Windows Defender/antivirus settings
   - Run installer with antivirus temporarily disabled

4. **Shortcut Creation Failures**
   - Verify pywin32 is installed correctly
   - Check desktop and Start Menu permissions
   - Use modify mode to recreate shortcuts

### Log Files

Installation logs are stored in:
- `%TEMP%/metacli_installer.log`
- Installation directory (if created)

## Advanced Usage

### Command Line Arguments

```bash
# Show help
python metacli_installer.py --help

# Install mode (default)
python metacli_installer.py

# Repair existing installation
python metacli_installer.py --repair

# Modify installation components
python metacli_installer.py --modify

# Uninstall MetaCLI
python metacli_installer.py --uninstall
```

### Batch File Launchers

For convenience, use the provided batch files:
- `repair_metacli.bat` - Launch repair mode
- `modify_metacli.bat` - Launch modify mode
- `uninstall_metacli.bat` - Launch uninstall mode

## Security Considerations

- Administrator privileges are only requested when necessary
- All file operations are validated before execution
- Registry modifications are limited to MetaCLI-specific entries
- User data preservation options in uninstall mode
- Secure handling of temporary files and downloads

## Support

For additional support:
1. Check the installation logs for detailed error information
2. Review the troubleshooting section above
3. Use repair mode for corrupted installations
4. Refer to the main README.md for general MetaCLI documentation