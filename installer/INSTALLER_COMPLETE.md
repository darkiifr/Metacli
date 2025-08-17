# MetaCLI Installer - Complete Technical Documentation

This document provides comprehensive technical documentation for the MetaCLI installer system, covering architecture, implementation details, and all supported operation modes.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Installation Modes](#installation-modes)
4. [System Integration](#system-integration)
5. [Installation Detection](#installation-detection)
6. [User Interface](#user-interface)
7. [Error Handling](#error-handling)
8. [Security Model](#security-model)
9. [API Reference](#api-reference)
10. [Development Guidelines](#development-guidelines)

## Architecture Overview

The MetaCLI installer follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    MetaCLI Installer                        │
├─────────────────────────────────────────────────────────────┤
│  GUI Layer (Tkinter)                                       │
│  ├── Welcome Page    ├── Options Page                      │
│  ├── Progress Page   └── Complete Page                     │
├─────────────────────────────────────────────────────────────┤
│  Core Installer Logic                                      │
│  ├── Mode Dispatcher  ├── Installation Detection          │
│  ├── Progress Tracking └── Error Handling                 │
├─────────────────────────────────────────────────────────────┤
│  System Integration Layer                                  │
│  ├── Registry Management  ├── Shortcut Creation           │
│  ├── PATH Management      └── File Operations             │
├─────────────────────────────────────────────────────────────┤
│  Dependency Management                                     │
│  ├── Dependency Detection  ├── Download Management        │
│  └── Installation Verification                            │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MetaCLIInstaller Class

**File**: `metacli_installer.py`

**Purpose**: Main installer class that orchestrates the entire installation process.

**Key Attributes**:
```python
class MetaCLIInstaller:
    def __init__(self, mode='install'):
        self.mode = mode  # install, repair, modify, uninstall
        self.existing_installation = None
        self.installed_components = {}
        self.dependency_manager = DependencyManager()
        self.system_integration = SystemIntegration()
```

**Core Methods**:
- `detect_existing_installation()`: Identifies existing MetaCLI installations
- `run_installation()`: Mode dispatcher for different operation types
- `_run_install()`: Fresh installation logic
- `_run_repair()`: Repair existing installation
- `_run_modify()`: Modify installation components
- `_run_uninstall()`: Complete uninstallation

### 2. SystemIntegration Class

**File**: `installer/system_integration.py`

**Purpose**: Handles all Windows system integration tasks.

**Key Features**:
- Registry management (read/write/delete)
- Shortcut creation and removal
- System PATH manipulation
- Installation detection and validation

**New Methods for Multi-Mode Support**:
```python
# Uninstall methods
def remove_desktop_shortcuts(self, install_dir: Path) -> bool
def remove_start_menu_shortcuts(self, install_dir: Path) -> bool
def remove_all_shortcuts(self, install_dir: Path) -> bool

# Detection methods
def get_installation_info(self) -> Optional[Dict[str, str]]
def is_metacli_installed(self) -> bool
def get_installed_components(self, install_dir: Path) -> Dict[str, bool]

# Complete operations
def complete_uninstall(self, install_dir: Path, keep_user_data: bool = False) -> bool
```

### 3. DependencyManager Class

**File**: `installer/dependency_manager.py`

**Purpose**: Manages Python dependencies and system requirements.

**Features**:
- Dependency detection and validation
- Automatic dependency installation
- Version compatibility checking
- Fallback mechanisms for offline scenarios

## Installation Modes

### Mode Architecture

The installer uses a mode-based architecture where each mode has specific behavior:

```python
def run_installation(self):
    """Main installation dispatcher based on mode"""
    mode_handlers = {
        'install': self._run_install,
        'repair': self._run_repair,
        'modify': self._run_modify,
        'uninstall': self._run_uninstall
    }
    
    handler = mode_handlers.get(self.mode)
    if handler:
        handler()
    else:
        raise ValueError(f"Unknown installation mode: {self.mode}")
```

### 1. Install Mode

**Process Flow**:
1. System requirements validation
2. Dependency checking and installation
3. Installation directory creation
4. Antivirus exclusion setup
5. Application file copying
6. System integration (PATH, shortcuts)
7. Registry registration
8. Completion verification

**Implementation**:
```python
def _run_install(self):
    """Perform fresh installation"""
    steps = [
        ("Checking dependencies", self.check_and_install_dependencies),
        ("Creating installation directory", self.create_install_directory),
        ("Adding antivirus exclusion", self.add_antivirus_exclusion),
        ("Copying application files", self.copy_application_files),
        ("Adding to system PATH", self.add_to_system_path),
        ("Creating shortcuts", self.create_shortcuts),
        ("Registering application", self.register_application)
    ]
    
    for i, (description, step_func) in enumerate(steps):
        self.update_progress((i + 1) * 100 // len(steps), description)
        step_func()
```

### 2. Repair Mode

**Process Flow**:
1. Existing installation detection
2. Component validation
3. Missing file restoration
4. System integration repair
5. Registry entry validation
6. Verification of repair completion

**Key Features**:
- Preserves user settings and data
- Only repairs missing or corrupted components
- Validates existing installation integrity
- Restores system integrations based on original installation

### 3. Modify Mode

**Process Flow**:
1. Current installation analysis
2. Component status evaluation
3. User selection processing
4. Selective component modification
5. Registry update
6. Verification of changes

**Modification Capabilities**:
- Add/remove desktop shortcuts
- Add/remove Start Menu shortcuts
- Add/remove system PATH entries
- Update registry entries

### 4. Uninstall Mode

**Process Flow**:
1. Installation detection and analysis
2. Component inventory
3. User confirmation with component list
4. System integration removal
5. File removal (with user data options)
6. Registry cleanup
7. Verification of complete removal

**Safety Features**:
- User data preservation option
- Component-by-component removal
- Rollback capability for failed uninstalls
- Verification of complete cleanup

## System Integration

### Registry Management

**Registry Structure**:
```
HKEY_LOCAL_MACHINE\SOFTWARE\MetaCLI
├── InstallPath          (REG_SZ)
├── Version             (REG_SZ)
├── InstallDate         (REG_SZ)
├── Components
│   ├── GUI             (REG_DWORD)
│   ├── CLI             (REG_DWORD)
│   ├── DesktopShortcuts (REG_DWORD)
│   ├── StartMenuShortcuts (REG_DWORD)
│   └── PathEntry       (REG_DWORD)
└── Uninstall
    ├── DisplayName     (REG_SZ)
    ├── UninstallString (REG_SZ)
    ├── DisplayVersion  (REG_SZ)
    └── Publisher       (REG_SZ)
```

**Registry Operations**:
```python
def write_registry_value(self, key_path: str, value_name: str, value: Any, value_type: int) -> bool
def read_registry_value(self, key_path: str, value_name: str) -> Optional[Any]
def delete_registry_key(self, key_path: str) -> bool
def registry_key_exists(self, key_path: str) -> bool
```

### Shortcut Management

**Desktop Shortcuts**:
- Location: `%USERPROFILE%\Desktop`
- Types: MetaCLI GUI.lnk, MetaCLI CLI.lnk
- Properties: Target path, working directory, description, icon

**Start Menu Shortcuts**:
- Location: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\MetaCLI`
- Folder structure with organized shortcuts
- Automatic folder creation and cleanup

**Implementation**:
```python
def create_desktop_shortcuts(self, install_dir: Path, components: Dict[str, bool]) -> bool
def create_start_menu_shortcuts(self, install_dir: Path, components: Dict[str, bool]) -> bool
def remove_desktop_shortcuts(self, install_dir: Path) -> bool
def remove_start_menu_shortcuts(self, install_dir: Path) -> bool
```

### PATH Management

**System PATH Integration**:
- Adds installation directory to system PATH
- Handles both user and system-level PATH
- Automatic cleanup on uninstall
- Duplicate entry prevention

**Implementation**:
```python
def add_to_path(self, install_dir: Path) -> bool
def remove_from_path(self, install_dir: Path) -> bool
def is_in_path(self, install_dir: Path) -> bool
```

## Installation Detection

### Detection Methods

The installer uses multiple detection methods for robustness:

1. **Registry-Based Detection**:
   ```python
   def get_installation_info(self) -> Optional[Dict[str, str]]:
       try:
           with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.REGISTRY_KEY) as key:
               install_path = winreg.QueryValueEx(key, "InstallPath")[0]
               version = winreg.QueryValueEx(key, "Version")[0]
               return {"path": install_path, "version": version}
       except FileNotFoundError:
           return None
   ```

2. **File System Validation**:
   ```python
   def validate_installation(self, install_dir: Path) -> bool:
       required_files = ["MetaCLI-GUI.exe", "metacli.exe"]
       return all((install_dir / file).exists() for file in required_files)
   ```

3. **Component Analysis**:
   ```python
   def get_installed_components(self, install_dir: Path) -> Dict[str, bool]:
       return {
           "gui": (install_dir / "MetaCLI-GUI.exe").exists(),
           "cli": (install_dir / "metacli.exe").exists(),
           "desktop_shortcuts": self._check_desktop_shortcuts(install_dir),
           "start_menu_shortcuts": self._check_start_menu_shortcuts(install_dir),
           "path_entry": self.is_in_path(install_dir)
       }
   ```

## User Interface

### Dynamic UI Architecture

The UI adapts based on the current mode:

```python
def setup_welcome_page(self):
    # Dynamic title and description based on mode
    titles = {
        'install': 'Welcome to MetaCLI Installation',
        'repair': 'MetaCLI Repair Tool',
        'modify': 'MetaCLI Modification Tool',
        'uninstall': 'MetaCLI Uninstall Tool'
    }
    
    # Show existing installation info for non-install modes
    if self.mode != 'install' and self.existing_installation:
        self._show_installation_info()
```

### Page-Specific Adaptations

**Options Page**:
- Install mode: Full component selection
- Repair mode: Read-only display with repair options
- Modify mode: Current status with modification options
- Uninstall mode: Confirmation with component list

**Progress Page**:
- Mode-specific progress messages
- Dynamic step descriptions
- Real-time status updates

**Complete Page**:
- Mode-specific success messages
- Conditional launch options
- Next steps guidance

## Error Handling

### Error Categories

1. **System Errors**:
   - Permission denied
   - File system errors
   - Registry access errors

2. **Installation Errors**:
   - Dependency failures
   - File corruption
   - Incomplete installations

3. **User Errors**:
   - Invalid paths
   - Insufficient disk space
   - Conflicting installations

### Error Recovery

```python
def cleanup_partial_installation(self):
    """Clean up after failed installation"""
    try:
        install_dir = Path(self.install_path.get())
        if install_dir.exists():
            # Remove partial files
            shutil.rmtree(install_dir, ignore_errors=True)
            
        # Clean up registry entries
        self.system_integration.delete_registry_key(self.system_integration.REGISTRY_KEY)
        
        # Remove any created shortcuts
        self.system_integration.remove_all_shortcuts(install_dir)
        
        self.log_message("Cleaned up partial installation")
    except Exception as e:
        self.log_message(f"Warning: Could not fully clean up partial installation: {e}")
```

## Security Model

### Privilege Management

**Administrator Privileges**:
- Required for: Install, Repair, Uninstall
- Not required for: Modify (user-level changes only)
- Automatic UAC prompting
- Privilege validation before operations

**Security Measures**:
- Input validation for all user inputs
- Path traversal prevention
- Registry access validation
- Secure temporary file handling

### File System Security

```python
def _requires_admin_privileges(self, install_dir: Path) -> bool:
    """Check if admin privileges are required for installation"""
    # Check if installing to system directories
    system_dirs = [
        Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')),
        Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')),
        Path(os.environ.get('SYSTEMROOT', 'C:\\Windows'))
    ]
    
    return any(self._is_subdirectory(install_dir, sys_dir) for sys_dir in system_dirs)
```

## API Reference

### MetaCLIInstaller Class

#### Constructor
```python
def __init__(self, mode='install')
```
**Parameters**:
- `mode` (str): Installation mode ('install', 'repair', 'modify', 'uninstall')

#### Core Methods

```python
def detect_existing_installation(self) -> None
```
Detects existing MetaCLI installations and populates installation info.

```python
def run_installation(self) -> None
```
Main installation dispatcher that calls appropriate mode handler.

```python
def update_progress(self, percentage: int, status: str) -> None
```
Updates installation progress and status message.

```python
def log_message(self, message: str) -> None
```
Logs installation messages to both file and UI.

### SystemIntegration Class

#### Registry Methods
```python
def write_registry_value(self, key_path: str, value_name: str, value: Any, value_type: int) -> bool
def read_registry_value(self, key_path: str, value_name: str) -> Optional[Any]
def delete_registry_key(self, key_path: str) -> bool
```

#### Shortcut Methods
```python
def create_desktop_shortcuts(self, install_dir: Path, components: Dict[str, bool]) -> bool
def create_start_menu_shortcuts(self, install_dir: Path, components: Dict[str, bool]) -> bool
def remove_all_shortcuts(self, install_dir: Path) -> bool
```

#### PATH Methods
```python
def add_to_path(self, install_dir: Path) -> bool
def remove_from_path(self, install_dir: Path) -> bool
def is_in_path(self, install_dir: Path) -> bool
```

#### Detection Methods
```python
def get_installation_info(self) -> Optional[Dict[str, str]]
def is_metacli_installed(self) -> bool
def get_installed_components(self, install_dir: Path) -> Dict[str, bool]
```

## Development Guidelines

### Code Organization

1. **Separation of Concerns**:
   - UI logic in main installer class
   - System operations in SystemIntegration
   - Dependency management in DependencyManager

2. **Error Handling**:
   - Always use try-catch blocks for system operations
   - Provide meaningful error messages
   - Implement cleanup for failed operations

3. **Logging**:
   - Log all significant operations
   - Include timestamps and operation details
   - Separate user-facing messages from debug logs

### Testing Considerations

1. **Mode Testing**:
   - Test each mode independently
   - Verify mode transitions
   - Test edge cases for each mode

2. **System Integration Testing**:
   - Test on different Windows versions
   - Verify registry operations
   - Test shortcut creation/removal
   - Validate PATH modifications

3. **Error Scenario Testing**:
   - Test permission denied scenarios
   - Test partial installation cleanup
   - Test corrupted installation repair

### Extension Points

1. **Adding New Modes**:
   ```python
   def _run_new_mode(self):
       """Implement new installation mode"""
       # Add mode-specific logic here
       pass
   
   # Update mode dispatcher
   mode_handlers = {
       'install': self._run_install,
       'repair': self._run_repair,
       'modify': self._run_modify,
       'uninstall': self._run_uninstall,
       'new_mode': self._run_new_mode  # Add new mode
   }
   ```

2. **Adding New Components**:
   - Update component detection logic
   - Add component-specific installation/removal methods
   - Update UI to reflect new components
   - Update registry structure if needed

3. **Adding New System Integrations**:
   - Extend SystemIntegration class
   - Add detection methods for new integrations
   - Update installation and removal workflows
   - Add UI options for new integrations

## Conclusion

The MetaCLI installer provides a comprehensive, multi-mode installation system with robust error handling, security considerations, and extensibility. The modular architecture allows for easy maintenance and future enhancements while providing a professional user experience across all operation modes.