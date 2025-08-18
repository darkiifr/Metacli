#!/usr/bin/env python3
"""
MetaCLI Windows Installer
A Python-style GUI installer for MetaCLI application
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import subprocess
import threading
import shutil
import winreg
from pathlib import Path
import json
import time
import logging
from typing import Dict, List, Optional
import tempfile
try:
    import msvcrt
except ImportError:
    msvcrt = None

# Import our custom modules
try:
    from installer.dependency_manager import DependencyManager
    from installer.system_integration import SystemIntegration
    INSTALLER_MODULES_AVAILABLE = True
except ImportError as e:
    # Fallback if modules are not available
    print(f"Warning: Installer modules not available: {e}")
    print("Installer will use fallback functionality.")
    DependencyManager = None
    SystemIntegration = None
    INSTALLER_MODULES_AVAILABLE = False


class MetaCLIInstaller:
    def __init__(self, mode='install'):
        """Initialize the installer with comprehensive error handling"""
        try:
            print(f"Initializing MetaCLI Installer in {mode} mode...")
            
            # Check for existing instance
            try:
                if not self.check_singleton():
                    error_msg = "Another instance of MetaCLI Setup is already running."
                    print(f"Error: {error_msg}")
                    try:
                        messagebox.showerror("MetaCLI Setup", error_msg)
                    except:
                        pass  # If messagebox fails, continue with print
                    sys.exit(1)
                print("Singleton check passed")
            except Exception as e:
                print(f"Warning: Singleton check failed: {e}")
                # Continue anyway as this is not critical
                
            # Initialize basic variables first
            try:
                self.installation_cancelled = False
                self.current_step = 0
                self.total_steps = 8
                self.installation_complete = False
                print("Basic variables initialized")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize basic variables: {e}")
            
            # Set installer mode (install, repair, modify, uninstall)
            try:
                self.mode = mode
                self.existing_installation = None
                self.installed_components = {}
                self.installation_health = None
                self.multiple_installations = []
                print(f"Mode set to: {mode}")
            except Exception as e:
                raise RuntimeError(f"Failed to set installer mode: {e}")
            
            # Initialize paths and directories
            try:
                self.installer_dir = Path(__file__).parent.absolute()
                self.dist_dir = self.installer_dir / 'dist'
                print(f"Installer directory: {self.installer_dir}")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize paths: {e}")
            
            # Setup logging early
            try:
                self.setup_logging()
                print("Logging setup completed")
            except Exception as e:
                print(f"Warning: Failed to setup logging: {e}")
                # Continue without logging if it fails
            
            # Detect existing installation
            try:
                self.detect_existing_installation()
                print("Installation detection completed")
            except Exception as e:
                print(f"Warning: Failed to detect existing installation: {e}")
                self.existing_installation = None
            
            # Create and configure main window
            try:
                self.root = tk.Tk()
                print("Tkinter window created")
            except Exception as e:
                raise RuntimeError(f"Failed to create Tkinter window: {e}")
        
            # Set window title based on mode
            try:
                mode_titles = {
                    'install': 'MetaCLI Setup',
                    'repair': 'MetaCLI Repair',
                    'modify': 'MetaCLI Modify',
                    'uninstall': 'MetaCLI Uninstall'
                }
                self.root.title(mode_titles.get(self.mode, 'MetaCLI Setup'))
                
                self.root.geometry("650x550")
                self.root.minsize(650, 550)
                self.root.resizable(False, False)
                self.root.configure(bg='#f0f0f0')
                print("Window configuration completed")
            except Exception as e:
                raise RuntimeError(f"Failed to configure window: {e}")
            
            # Center window on screen
            try:
                self.center_window()
                print("Window centered")
            except Exception as e:
                print(f"Warning: Failed to center window: {e}")
            
            # Installation configuration - use user directory by default to avoid permission issues
            try:
                default_install_path = str(Path.home() / 'AppData' / 'Local' / 'MetaCLI')
                self.install_path = tk.StringVar(value=default_install_path)
                self.add_to_path = tk.BooleanVar(value=True)
                self.install_gui = tk.BooleanVar(value=True)
                self.install_cli = tk.BooleanVar(value=True)
                self.create_shortcuts = tk.BooleanVar(value=True)
                self.create_start_menu = tk.BooleanVar(value=True)
                self.register_uninstaller = tk.BooleanVar(value=True)
                print("Installation configuration variables initialized")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize configuration variables: {e}")
            
            # Required dependencies
            try:
                self.dependencies = [
                    'click>=8.0.0',
                    'Pillow>=9.0.0',
                    'mutagen>=1.45.0',
                    'PyPDF2>=3.0.0',
                    'python-docx>=0.8.11',
                    'pyyaml>=6.0',
                    'tabulate>=0.9.0',
                    'openpyxl>=3.0.0',
                    'chardet>=5.0.0'
                ]
                print(f"Dependencies list initialized with {len(self.dependencies)} packages")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize dependencies list: {e}")
            
            # Defer expensive manager initialization
            self.dependency_manager = None
            self.system_integration = None
            
            # Setup UI immediately
            try:
                self.setup_ui()
                print("UI setup completed")
            except Exception as e:
                raise RuntimeError(f"Failed to setup UI: {e}")
            
            # Initialize managers after UI is ready
            try:
                self.root.after(100, self.initialize_managers)
                print("Manager initialization scheduled")
            except Exception as e:
                print(f"Warning: Failed to schedule manager initialization: {e}")
                
            print("MetaCLI Installer initialization completed successfully")
            
        except Exception as e:
            print(f"Critical error during installer initialization: {e}")
            # Try to cleanup if possible
            try:
                if hasattr(self, 'root') and self.root:
                    self.root.destroy()
            except:
                pass
            raise
        
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def initialize_managers(self):
        """Initialize dependency and system integration managers after UI is ready"""
        try:
            if INSTALLER_MODULES_AVAILABLE:
                self.dependency_manager = DependencyManager(logger_callback=self.log_message) if DependencyManager else None
                self.system_integration = SystemIntegration(logger_callback=self.log_message) if SystemIntegration else None
                self.log_message("Installer modules initialized successfully")
            else:
                self.dependency_manager = None
                self.system_integration = None
                self.log_message("Using fallback functionality - some features may be limited")
        except Exception as e:
            self.dependency_manager = None
            self.system_integration = None
            error_msg = f"Could not initialize installer modules: {e}"
            print(f"Warning: {error_msg}")
            self.log_message(f"Warning: {error_msg}")
            self.log_message("Falling back to basic functionality")
    
    def check_singleton(self):
        """Check if another instance of the installer is already running"""
        try:
            self.lock_file_path = os.path.join(tempfile.gettempdir(), 'metacli_installer.lock')
            
            # Try to create and lock the file
            if os.name == 'nt':  # Windows
                try:
                    # Try to open the file exclusively
                    self.lock_file = open(self.lock_file_path, 'w')
                    if msvcrt:
                        msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    return True
                except (IOError, OSError):
                    return False
            else:  # Unix-like systems
                try:
                    self.lock_file = open(self.lock_file_path, 'w')
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except (IOError, OSError):
                    return False
        except Exception:
            # If we can't create the lock, assume no other instance
            return True
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.installer_dir / 'metacli_installer.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def detect_existing_installation(self):
        """Detect existing MetaCLI installation using enhanced detection methods"""
        try:
            if INSTALLER_MODULES_AVAILABLE and SystemIntegration:
                # Initialize system integration to check for existing installation
                temp_system_integration = SystemIntegration(logger_callback=self.log_message)
                
                # Use enhanced detection mechanism
                self.existing_installation = temp_system_integration.get_installation_info()
                
                if self.existing_installation:
                    detection_method = self.existing_installation.get('DetectionMethod', 'Unknown')
                    install_location = self.existing_installation.get('InstallLocation')
                    
                    self.log_message(f"Existing installation detected via {detection_method}: {self.existing_installation}")
                    
                    if install_location:
                        install_path = Path(install_location)
                        
                        # Get installed components and health status
                        if install_path.exists():
                            self.installed_components = temp_system_integration.get_installed_components(install_path)
                            self.installation_health = self._assess_installation_health(install_path)
                            
                            # Update install path to existing location
                            self.install_path.set(str(install_path))
                else:
                    self.log_message("No existing installation detected")
            else:
                # Fallback detection using basic registry check
                self.log_message("Using fallback installation detection")
                self.existing_installation = self._fallback_detect_installation()
                
        except Exception as e:
            self.log_message(f"Error during installation detection: {e}")
            self.existing_installation = None
            
    def _fallback_detect_installation(self):
        """Fallback method to detect existing installation without system integration module"""
        try:
            import winreg
            registry_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MetaCLI'
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_key) as key:
                install_location = winreg.QueryValueEx(key, 'InstallLocation')[0]
                version = winreg.QueryValueEx(key, 'DisplayVersion')[0]
                
                return {
                    'InstallLocation': install_location,
                    'Version': version,
                    'DetectionMethod': 'Registry (Fallback)'
                }
        except (FileNotFoundError, OSError):
            # Try user registry
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_key) as key:
                    install_location = winreg.QueryValueEx(key, 'InstallLocation')[0]
                    version = winreg.QueryValueEx(key, 'DisplayVersion')[0]
                    
                    return {
                        'InstallLocation': install_location,
                        'Version': version,
                        'DetectionMethod': 'User Registry (Fallback)'
                    }
            except (FileNotFoundError, OSError):
                return None
        except Exception as e:
            self.log_message(f"Fallback detection error: {e}")
            return None
            
    def _assess_installation_health(self, install_path):
        """Assess the health of an existing installation"""
        try:
            required_files = ['MetaCLI-GUI.exe', 'metacli.exe']
            missing_files = []
            
            for file_name in required_files:
                if not (install_path / file_name).exists():
                    missing_files.append(file_name)
                    
            if missing_files:
                return {
                    'status': 'damaged',
                    'missing_files': missing_files,
                    'description': f'Missing files: {", ".join(missing_files)}'
                }
            else:
                return {
                    'status': 'healthy',
                    'missing_files': [],
                    'description': 'Installation appears to be complete'
                }
        except Exception as e:
            return {
                'status': 'unknown',
                'missing_files': [],
                'description': f'Could not assess installation health: {e}'
            }
        
    def setup_ui(self):
        """Setup the main user interface"""
        # Create main container frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Create notebook for different pages
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 15))
        
        # Welcome page
        self.welcome_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.welcome_frame, text="Welcome")
        self.setup_welcome_page()
        
        # Options page (defer setup until needed)
        self.options_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.options_frame, text="Installation Options")
        
        # Progress page (defer setup until needed)
        self.progress_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.progress_frame, text="Installing")
        
        # Completion page (defer setup until needed)
        self.complete_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.complete_frame, text="Complete")
        
        # Initially disable all tabs except welcome
        for i in range(1, 4):
            self.notebook.tab(i, state='disabled')
            
        # Bottom button frame with consistent layout
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill='x', pady=(5, 0))
        
        # Create button container for better spacing
        button_container = ttk.Frame(self.button_frame)
        button_container.pack(fill='x')
        
        # Left side - Back button
        self.back_button = ttk.Button(button_container, text="< Back", command=self.go_back, 
                                     state='disabled', width=12)
        self.back_button.pack(side='left')
        
        # Right side - Next and Cancel buttons
        right_frame = ttk.Frame(button_container)
        right_frame.pack(side='right')
        
        self.next_button = ttk.Button(right_frame, text="Next >", command=self.go_next, width=12)
        self.next_button.pack(side='right', padx=(5, 0))
        
        self.cancel_button = ttk.Button(right_frame, text="Cancel", command=self.cancel_installation, width=12)
        self.cancel_button.pack(side='right', padx=(0, 5))
        
        # Bind notebook tab change event to setup pages on demand
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
        
        # Track which pages have been setup
        self.pages_setup = {'welcome': True, 'options': False, 'progress': False, 'complete': False}
        
    def on_tab_changed(self, event):
        """Handle tab change events to setup pages on demand"""
        current_tab = self.notebook.index(self.notebook.select())
        
        # Setup pages lazily
        if current_tab == 1 and not self.pages_setup['options']:
            self.setup_options_page()
            self.pages_setup['options'] = True
        elif current_tab == 2 and not self.pages_setup['progress']:
            self.setup_progress_page()
            self.pages_setup['progress'] = True
        elif current_tab == 3 and not self.pages_setup['complete']:
            self.setup_complete_page()
            self.pages_setup['complete'] = True
            
        # Update button states
        self.update_buttons()
        
    def setup_welcome_page(self):
        """Setup the welcome page with enhanced detection info and icons"""
        # Check for existing installation and adjust mode if needed
        if self.mode == 'install' and self.existing_installation:
            self._show_existing_installation_options()
            return
        
        # If repair/modify/uninstall mode but no existing installation, switch to install mode
        if self.mode in ['repair', 'modify', 'uninstall'] and not self.existing_installation:
            self.mode = 'install'
            self.root.title("MetaCLI Setup")
            messagebox.showwarning(
                "No Installation Found",
                f"MetaCLI is not currently installed on this computer.\n\n"
                f"The installer will now switch to installation mode."
            )
            
        # Title based on mode with icons
        mode_titles = {
            'install': 'Welcome to MetaCLI Setup',
            'repair': 'MetaCLI Repair',
            'modify': 'MetaCLI Modify Installation',
            'uninstall': 'MetaCLI Uninstall'
        }
        
        # Create title frame with icon
        title_frame = ttk.Frame(self.welcome_frame)
        title_frame.pack(pady=(20, 10))
        
        # Add mode-specific icon (using Unicode symbols as fallback)
        mode_icons = {
            'install': '📦',
            'repair': '🔧', 
            'modify': '⚙️',
            'uninstall': '🗑️'
        }
        
        icon_label = ttk.Label(title_frame, text=mode_icons.get(self.mode, '📦'), 
                              font=('Segoe UI', 20))
        icon_label.pack(side='left', padx=(0, 10))
        
        title_label = ttk.Label(title_frame, text=mode_titles.get(self.mode, 'Welcome to MetaCLI Setup'), 
                               font=('Arial', 16, 'bold'))
        title_label.pack(side='left')
        
        # Description based on mode
        if self.mode == 'install':
            desc_text = (
                "This will install MetaCLI on your computer.\n\n"
                "MetaCLI is a command-line interface for metadata extraction and management.\n\n"
                "It includes both a GUI application and a command-line tool for processing\n"
                "various file types and extracting metadata information.\n\n"
                "Click Next to continue or Cancel to exit Setup."
            )
        elif self.mode == 'repair':
            desc_text = (
                "This will repair your MetaCLI installation.\n\n"
                "The repair process will:\n"
                "• Re-install missing or corrupted files\n"
                "• Restore missing shortcuts and registry entries\n"
                "• Verify and fix system PATH entries\n"
                "• Re-install missing dependencies\n\n"
                "Click Next to continue or Cancel to exit."
            )
        elif self.mode == 'modify':
            desc_text = (
                "This will modify your MetaCLI installation.\n\n"
                "You can:\n"
                "• Add or remove components (GUI/CLI)\n"
                "• Change shortcut preferences\n"
                "• Modify system PATH integration\n"
                "• Update installation location\n\n"
                "Click Next to continue or Cancel to exit."
            )
        elif self.mode == 'uninstall':
            desc_text = (
                "This will completely remove MetaCLI from your computer.\n\n"
                "The uninstall process will:\n"
                "• Remove all MetaCLI files and folders\n"
                "• Delete desktop and Start Menu shortcuts\n"
                "• Remove system PATH entries\n"
                "• Clean up registry entries\n\n"
                "Click Next to continue or Cancel to exit."
            )
        else:
            desc_text = "Unknown operation mode."
            
        desc_label = ttk.Label(self.welcome_frame, text=desc_text, justify='left')
        desc_label.pack(pady=10, padx=20)
        
        # Show existing installation info if available
        if self.existing_installation and self.mode != 'install':
            install_frame = ttk.LabelFrame(self.welcome_frame, text="Current Installation")
            install_frame.pack(fill='x', padx=20, pady=10)
            
            install_location = self.existing_installation.get('InstallLocation', 'Unknown')
            install_version = self.existing_installation.get('DisplayVersion', 'Unknown')
            detection_method = self.existing_installation.get('DetectionMethod', 'Unknown')
            
            ttk.Label(install_frame, text=f"Location: {install_location}").pack(anchor='w', padx=10, pady=2)
            ttk.Label(install_frame, text=f"Version: {install_version}").pack(anchor='w', padx=10, pady=2)
            ttk.Label(install_frame, text=f"Detected via: {detection_method}").pack(anchor='w', padx=10, pady=2)
            
            # Show installed components
            if self.installed_components:
                components_text = ", ".join([comp for comp, installed in self.installed_components.items() if installed])
                ttk.Label(install_frame, text=f"Components: {components_text}").pack(anchor='w', padx=10, pady=2)
                
            # Show installation health status
            if self.installation_health:
                health_color = 'green' if self.installation_health['is_healthy'] else 'red'
                health_text = 'Healthy' if self.installation_health['is_healthy'] else 'Issues Detected'
                health_label = ttk.Label(install_frame, text=f"Status: {health_text}")
                health_label.pack(anchor='w', padx=10, pady=2)
                
                # Show issues if any
                if not self.installation_health['is_healthy'] and self.installation_health.get('issues'):
                    issues_text = "; ".join(self.installation_health['issues'][:3])  # Show first 3 issues
                    ttk.Label(install_frame, text=f"Issues: {issues_text}", foreground='red').pack(anchor='w', padx=10, pady=2)
            
            # Show version status if available
            if hasattr(self, 'version_status') and self.version_status:
                version_frame = ttk.LabelFrame(self.welcome_frame, text="Version Information")
                version_frame.pack(fill='x', padx=20, pady=10)
                
                installed_ver = self.version_status['installed_version']
                current_ver = self.version_status['current_version']
                recommendation = self.version_status['recommendation']
                
                ttk.Label(version_frame, text=f"Installed: {installed_ver}").pack(anchor='w', padx=10, pady=2)
                ttk.Label(version_frame, text=f"Installer: {current_ver}").pack(anchor='w', padx=10, pady=2)
                
                # Color-code the recommendation
                if self.version_status['is_outdated']:
                    color = 'orange'
                elif self.version_status['is_newer']:
                    color = 'blue'
                else:
                    color = 'green'
                    
                ttk.Label(version_frame, text=recommendation, foreground=color).pack(anchor='w', padx=10, pady=2)
                    
        # Show multiple installations warning
        if hasattr(self, 'multiple_installations') and len(self.multiple_installations) > 1:
            warning_frame = ttk.LabelFrame(self.welcome_frame, text="⚠️ Multiple Installations Detected")
            warning_frame.pack(fill='x', padx=20, pady=10)
            
            ttk.Label(warning_frame, text=f"Found {len(self.multiple_installations)} MetaCLI installations:",
                     foreground='orange').pack(anchor='w', padx=10, pady=2)
            
            for i, install in enumerate(self.multiple_installations[:3]):  # Show first 3
                location = install.get('InstallLocation', 'Unknown')
                method = install.get('DetectionMethod', 'Unknown')
                ttk.Label(warning_frame, text=f"  {i+1}. {location} ({method})").pack(anchor='w', padx=10, pady=2)
            if self.installed_components:
                components_text = "Components: "
                components = []
                if self.installed_components.get('gui'): components.append('GUI')
                if self.installed_components.get('cli'): components.append('CLI')
                if self.installed_components.get('shortcuts_desktop'): components.append('Desktop Shortcuts')
                if self.installed_components.get('shortcuts_start_menu'): components.append('Start Menu')
                if self.installed_components.get('path_entry'): components.append('PATH Entry')
                
                components_text += ', '.join(components) if components else 'None detected'
                ttk.Label(install_frame, text=components_text).pack(anchor='w', padx=10, pady=2)
        
        # System requirements check (only for install and repair)
        if self.mode in ['install', 'repair']:
            req_frame = ttk.LabelFrame(self.welcome_frame, text="System Requirements")
            req_frame.pack(fill='x', padx=20, pady=10)
            
            python_version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            ttk.Label(req_frame, text=f"✓ {python_version} detected", foreground='green').pack(anchor='w', padx=10, pady=5)
            ttk.Label(req_frame, text=f"✓ Windows {os.name} compatible", foreground='green').pack(anchor='w', padx=10, pady=5)
    
    def _show_existing_installation_options(self):
        """Show options when MetaCLI is already installed"""
        # Clear the welcome frame
        for widget in self.welcome_frame.winfo_children():
            widget.destroy()
            
        # Title with warning icon
        title_frame = ttk.Frame(self.welcome_frame)
        title_frame.pack(pady=(20, 10))
        
        icon_label = ttk.Label(title_frame, text='⚠️', font=('Segoe UI', 20))
        icon_label.pack(side='left', padx=(0, 10))
        
        title_label = ttk.Label(title_frame, text='MetaCLI Already Installed', 
                               font=('Arial', 16, 'bold'))
        title_label.pack(side='left')
        
        # Description
        desc_text = (
            "MetaCLI is already installed on your computer.\n\n"
            "Please choose what you would like to do:"
        )
        desc_label = ttk.Label(self.welcome_frame, text=desc_text, justify='center')
        desc_label.pack(pady=10, padx=20)
        
        # Show existing installation info
        if self.existing_installation:
            install_frame = ttk.LabelFrame(self.welcome_frame, text="Current Installation")
            install_frame.pack(fill='x', padx=20, pady=10)
            
            install_location = self.existing_installation.get('InstallLocation', 'Unknown')
            install_version = self.existing_installation.get('DisplayVersion', 'Unknown')
            detection_method = self.existing_installation.get('DetectionMethod', 'Unknown')
            
            ttk.Label(install_frame, text=f"Location: {install_location}").pack(anchor='w', padx=10, pady=2)
            ttk.Label(install_frame, text=f"Version: {install_version}").pack(anchor='w', padx=10, pady=2)
            ttk.Label(install_frame, text=f"Detected via: {detection_method}").pack(anchor='w', padx=10, pady=2)
            
            # Show installation health if available
            if hasattr(self, 'installation_health') and self.installation_health:
                health_status = self.installation_health.get('status', 'unknown')
                if health_status == 'healthy':
                    health_text = '✓ Installation is healthy'
                    health_color = 'green'
                elif health_status == 'damaged':
                    health_text = '⚠ Installation has issues'
                    health_color = 'orange'
                else:
                    health_text = '? Installation status unknown'
                    health_color = 'gray'
                    
                ttk.Label(install_frame, text=health_text, foreground=health_color).pack(anchor='w', padx=10, pady=2)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.welcome_frame, text="Available Actions")
        options_frame.pack(fill='x', padx=20, pady=10)
        
        # Create radio button variable
        self.action_choice = tk.StringVar(value='repair')
        
        # Repair option
        repair_frame = ttk.Frame(options_frame)
        repair_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Radiobutton(repair_frame, text="Repair Installation", 
                       variable=self.action_choice, value='repair').pack(anchor='w')
        ttk.Label(repair_frame, text="Fix missing files, shortcuts, and registry entries", 
                 font=('Arial', 8), foreground='gray').pack(anchor='w', padx=20)
        
        # Modify option
        modify_frame = ttk.Frame(options_frame)
        modify_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Radiobutton(modify_frame, text="Modify Installation", 
                       variable=self.action_choice, value='modify').pack(anchor='w')
        ttk.Label(modify_frame, text="Change components, shortcuts, or installation location", 
                 font=('Arial', 8), foreground='gray').pack(anchor='w', padx=20)
        
        # Reinstall option
        reinstall_frame = ttk.Frame(options_frame)
        reinstall_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Radiobutton(reinstall_frame, text="Reinstall (Replace Current)", 
                       variable=self.action_choice, value='reinstall').pack(anchor='w')
        ttk.Label(reinstall_frame, text="Remove current installation and install fresh copy", 
                 font=('Arial', 8), foreground='gray').pack(anchor='w', padx=20)
        
        # Uninstall option
        uninstall_frame = ttk.Frame(options_frame)
        uninstall_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Radiobutton(uninstall_frame, text="Uninstall", 
                       variable=self.action_choice, value='uninstall').pack(anchor='w')
        ttk.Label(uninstall_frame, text="Completely remove MetaCLI from your computer", 
                 font=('Arial', 8), foreground='gray').pack(anchor='w', padx=20)
        
        # Update next button to handle action choice
        self.next_button.configure(command=self._handle_existing_installation_choice)
        
    def _handle_existing_installation_choice(self):
        """Handle the user's choice for existing installation"""
        choice = self.action_choice.get()
        
        # Update the installer mode based on choice
        if choice == 'reinstall':
            # For reinstall, we'll uninstall first then install
            self.mode = 'install'
            self._reinstall_mode = True
        else:
            self.mode = choice
            
        # Update window title
        mode_titles = {
            'repair': 'MetaCLI Repair',
            'modify': 'MetaCLI Modify Installation', 
            'uninstall': 'MetaCLI Uninstall',
            'install': 'MetaCLI Reinstall'
        }
        
        if hasattr(self, '_reinstall_mode') and self._reinstall_mode:
            self.root.title('MetaCLI Reinstall')
        else:
            self.root.title(mode_titles.get(self.mode, 'MetaCLI Setup'))
        
        # Reset welcome page and continue with normal flow
        for widget in self.welcome_frame.winfo_children():
            widget.destroy()
            
        self.setup_welcome_page()
        
        # Restore normal next button behavior
        self.next_button.configure(command=self.go_next)
        
        # Move to next page
        self.go_next()
        
    def setup_options_page(self):
        """Setup the installation options page"""
        # Dynamic title based on mode
        mode_titles = {
            'install': 'Installation Options',
            'repair': 'Repair Options',
            'modify': 'Modify Installation',
            'uninstall': 'Uninstall Options'
        }
        
        title_label = ttk.Label(self.options_frame, text=mode_titles.get(self.mode, 'Installation Options'), 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        if self.mode == 'uninstall':
            self._setup_uninstall_options()
        else:
            self._setup_install_modify_repair_options()
    
    def _setup_uninstall_options(self):
        """Setup options for uninstall mode"""
        # Uninstall confirmation
        confirm_frame = ttk.LabelFrame(self.options_frame, text="Uninstall Confirmation")
        confirm_frame.pack(fill='x', padx=20, pady=10)
        
        warning_text = "Are you sure you want to uninstall MetaCLI?\nThis will remove all installed components."
        ttk.Label(confirm_frame, text=warning_text, font=('Arial', 10), 
                 foreground='red', justify='center').pack(pady=10)
        
        # Show what will be removed
        if self.installed_components:
            remove_frame = ttk.LabelFrame(self.options_frame, text="Components to Remove")
            remove_frame.pack(fill='x', padx=20, pady=10)
            
            for component, installed in self.installed_components.items():
                if installed:
                    component_names = {
                        'gui': '✗ MetaCLI GUI Application',
                        'cli': '✗ MetaCLI Command Line Interface',
                        'desktop_shortcuts': '✗ Desktop Shortcuts',
                        'start_menu_shortcuts': '✗ Start Menu Shortcuts',
                        'path_entry': '✗ System PATH Entry'
                    }
                    text = component_names.get(component, f'✗ {component}')
                    ttk.Label(remove_frame, text=text, foreground='red').pack(anchor='w', padx=10, pady=2)
        
        # Uninstall options
        options_frame = ttk.LabelFrame(self.options_frame, text="Uninstall Options")
        options_frame.pack(fill='x', padx=20, pady=10)
        
        self.keep_user_data = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Keep user data and settings", 
                       variable=self.keep_user_data).pack(anchor='w', padx=10, pady=2)
    
    def _setup_install_modify_repair_options(self):
        """Setup options for install, modify, and repair modes"""
        # Installation path (read-only for modify/repair)
        path_frame = ttk.LabelFrame(self.options_frame, text="Installation Directory")
        path_frame.pack(fill='x', padx=20, pady=10)
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill='x', padx=10, pady=10)
        
        self.path_entry = ttk.Entry(path_entry_frame, textvariable=self.install_path, width=50)
        self.path_entry.pack(side='left', fill='x', expand=True)
        
        # Disable path editing for modify/repair modes
        if self.mode in ['modify', 'repair']:
            self.path_entry.config(state='readonly')
        else:
            browse_button = ttk.Button(path_entry_frame, text="Browse...", command=self.browse_install_path)
            browse_button.pack(side='right', padx=(10, 0))
        
        # Admin privileges button (only for install mode)
        if self.mode == 'install':
            admin_frame = ttk.Frame(path_frame)
            admin_frame.pack(fill='x', padx=10, pady=(0, 10))
            
            admin_button = ttk.Button(admin_frame, text="Request Admin Privileges", command=self.manual_admin_request)
            admin_button.pack(side='left')
            
            admin_info = ttk.Label(admin_frame, text="Required for Program Files installation", 
                                  font=('Arial', 8), foreground='gray')
            admin_info.pack(side='left', padx=(10, 0))
        
        # Component information
        comp_frame = ttk.LabelFrame(self.options_frame, text="Components")
        comp_frame.pack(fill='x', padx=20, pady=10)
        
        if self.mode == 'install':
            ttk.Label(comp_frame, text="✓ MetaCLI GUI Application", foreground='green').pack(anchor='w', padx=10, pady=5)
            ttk.Label(comp_frame, text="✓ MetaCLI Command Line Interface", foreground='green').pack(anchor='w', padx=10, pady=5)
            ttk.Label(comp_frame, text="Both components will be installed automatically.", 
                     font=('Arial', 8), foreground='gray').pack(anchor='w', padx=10, pady=(0, 5))
        elif self.mode == 'repair':
            ttk.Label(comp_frame, text="✓ All components will be repaired", foreground='blue').pack(anchor='w', padx=10, pady=5)
            ttk.Label(comp_frame, text="Missing files will be restored and corrupted files will be replaced.", 
                     font=('Arial', 8), foreground='gray').pack(anchor='w', padx=10, pady=(0, 5))
        elif self.mode == 'modify':
            # Show current installation status and allow modification
            if self.installed_components:
                for component, installed in self.installed_components.items():
                    component_names = {
                        'gui': 'MetaCLI GUI Application',
                        'cli': 'MetaCLI Command Line Interface',
                        'desktop_shortcuts': 'Desktop Shortcuts',
                        'start_menu_shortcuts': 'Start Menu Shortcuts',
                        'path_entry': 'System PATH Entry'
                    }
                    name = component_names.get(component, component)
                    status = "✓ Installed" if installed else "✗ Not Installed"
                    color = 'green' if installed else 'red'
                    ttk.Label(comp_frame, text=f"{status} - {name}", foreground=color).pack(anchor='w', padx=10, pady=2)
        
        # Additional options
        options_frame = ttk.LabelFrame(self.options_frame, text="Additional Options")
        options_frame.pack(fill='x', padx=20, pady=10)
        
        # Set default values based on existing installation for modify mode
        if self.mode == 'modify' and self.installed_components:
            self.add_to_path.set(self.installed_components.get('path_entry', False))
            self.create_shortcuts.set(self.installed_components.get('desktop_shortcuts', False))
            self.create_start_menu.set(self.installed_components.get('start_menu_shortcuts', False))
            self.register_uninstaller.set(True)  # Always true if we're modifying
        
        ttk.Checkbutton(options_frame, text="Add MetaCLI to system PATH", variable=self.add_to_path).pack(anchor='w', padx=10, pady=2)
        ttk.Checkbutton(options_frame, text="Create desktop shortcuts", variable=self.create_shortcuts).pack(anchor='w', padx=10, pady=2)
        ttk.Checkbutton(options_frame, text="Create Start Menu shortcuts", variable=self.create_start_menu).pack(anchor='w', padx=10, pady=2)
        
        # Only show uninstaller registration for install mode
        if self.mode == 'install':
            ttk.Checkbutton(options_frame, text="Register in Add/Remove Programs", variable=self.register_uninstaller).pack(anchor='w', padx=10, pady=2)
        
    def setup_progress_page(self):
        """Setup the installation progress page"""
        # Dynamic title based on mode
        mode_titles = {
            'install': 'Installing MetaCLI',
            'repair': 'Repairing MetaCLI',
            'modify': 'Modifying MetaCLI',
            'uninstall': 'Uninstalling MetaCLI'
        }
        
        title_label = ttk.Label(self.progress_frame, text=mode_titles.get(self.mode, 'Installing MetaCLI'), 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(20, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(pady=10)
        
        # Dynamic status label based on mode
        mode_status = {
            'install': 'Preparing installation...',
            'repair': 'Preparing repair...',
            'modify': 'Preparing modification...',
            'uninstall': 'Preparing uninstallation...'
        }
        
        self.status_label = ttk.Label(self.progress_frame, text=mode_status.get(self.mode, 'Preparing installation...'))
        self.status_label.pack(pady=10)
        
        # Detailed log
        log_frame = ttk.LabelFrame(self.progress_frame, text="Installation Log")
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, width=60)
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
        
    def setup_complete_page(self):
        """Setup the installation complete page"""
        # Dynamic title based on mode
        mode_titles = {
            'install': 'Installation Complete',
            'repair': 'Repair Complete',
            'modify': 'Modification Complete',
            'uninstall': 'Uninstall Complete'
        }
        
        title_color = 'green' if self.mode != 'uninstall' else 'blue'
        title_label = ttk.Label(self.complete_frame, text=mode_titles.get(self.mode, 'Installation Complete'), 
                               font=('Arial', 16, 'bold'), foreground=title_color)
        title_label.pack(pady=(30, 20))
        
        # Dynamic success message based on mode
        mode_messages = {
            'install': (
                "MetaCLI has been successfully installed on your computer.\n\n"
                "You can now use MetaCLI from the command line or launch the GUI application\n"
                "from the Start Menu or desktop shortcuts."
            ),
            'repair': (
                "MetaCLI has been successfully repaired.\n\n"
                "All missing files have been restored and corrupted files have been replaced.\n"
                "You can now use MetaCLI normally."
            ),
            'modify': (
                "MetaCLI installation has been successfully modified.\n\n"
                "The requested components have been added or removed as specified.\n"
                "You can now use MetaCLI with the updated configuration."
            ),
            'uninstall': (
                "MetaCLI has been successfully uninstalled from your computer.\n\n"
                "All selected components have been removed.\n"
                "Thank you for using MetaCLI!"
            )
        }
        
        success_text = mode_messages.get(self.mode, mode_messages['install'])
        success_label = ttk.Label(self.complete_frame, text=success_text, justify='center')
        success_label.pack(pady=20)
        
        # Launch options (only for install, repair, and modify modes)
        if self.mode != 'uninstall':
            launch_frame = ttk.LabelFrame(self.complete_frame, text="Launch Options")
            launch_frame.pack(padx=20, pady=20)
            
            self.launch_gui = tk.BooleanVar(value=True)
            ttk.Checkbutton(launch_frame, text="Launch MetaCLI GUI now", variable=self.launch_gui).pack(anchor='w', padx=10, pady=10)
        else:
            # For uninstall mode, don't show launch options
            self.launch_gui = tk.BooleanVar(value=False)
        
    def browse_install_path(self):
        """Browse for installation directory"""
        directory = filedialog.askdirectory(initialdir=self.install_path.get())
        if directory:
            self.install_path.set(directory)
    
    def manual_admin_request(self):
        """Manually request administrator privileges"""
        try:
            import ctypes
            if ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showinfo(
                    "Administrator Privileges",
                    "The installer is already running with administrator privileges."
                )
                return
            
            response = messagebox.askyesno(
                "Request Administrator Privileges",
                "This will restart the installer with administrator privileges.\n\n"
                "This is required for installing to Program Files or system directories.\n\n"
                "Do you want to continue?"
            )
            
            if response:
                # Close current installer and restart with admin privileges
                self.root.quit()
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv + ['--request-admin']), None, 1
                )
                
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to request administrator privileges: {e}"
            )
            
    def go_back(self):
        """Go to previous page"""
        current = self.notebook.index(self.notebook.select())
        if current > 0:
            self.notebook.select(current - 1)
            self.update_buttons()
            
    def go_next(self):
        """Go to next page or start installation"""
        current = self.notebook.index(self.notebook.select())
        
        if current == 0:  # Welcome page
            # Enable and setup options page if not already done
            if not self.pages_setup['options']:
                self.setup_options_page()
                self.pages_setup['options'] = True
            self.notebook.tab(1, state='normal')
            self.notebook.select(1)
        elif current == 1:  # Options page
            if self.validate_options():
                # Enable and setup progress page if not already done
                if not self.pages_setup['progress']:
                    self.setup_progress_page()
                    self.pages_setup['progress'] = True
                self.notebook.tab(2, state='normal')
                self.notebook.select(2)
                # Start installation after a brief delay to ensure UI is ready
                self.root.after(100, self.start_installation)
        elif current == 2:  # Progress page (installation running)
            if self.installation_complete:
                # Enable and setup complete page if not already done
                if not self.pages_setup['complete']:
                    self.setup_complete_page()
                    self.pages_setup['complete'] = True
                self.notebook.tab(3, state='normal')
                self.notebook.select(3)
        elif current == 3:  # Complete page
            self.finish_installation()
            
        self.update_buttons()
        
    def update_buttons(self):
        """Update button states based on current page"""
        current = self.notebook.index(self.notebook.select())
        
        # Back button
        self.back_button.config(state='normal' if current > 0 else 'disabled')
        
        # Next button
        if current == 0:
            self.next_button.config(text="Next >", state='normal')
        elif current == 1:
            self.next_button.config(text="Install", state='normal')
        elif current == 2:
            self.next_button.config(text="Next >", state='normal' if self.installation_complete else 'disabled')
        elif current == 3:
            self.next_button.config(text="Finish", state='normal')
            
    def validate_options(self):
        """Validate the selected installation options"""
        install_path = self.install_path.get().strip()
        
        # Validate installation path
        if not install_path:
            messagebox.showerror("Error", "Please select an installation directory.")
            return False
            
        # Check if path is valid
        try:
            path_obj = Path(install_path)
            # Check if parent directory exists or can be created
            if not path_obj.parent.exists():
                messagebox.showerror("Error", f"Parent directory does not exist: {path_obj.parent}")
                return False
                
            # Check for write permissions
            if path_obj.exists():
                if not os.access(path_obj, os.W_OK):
                    messagebox.showerror("Error", f"No write permission for directory: {install_path}")
                    return False
            else:
                # Check parent directory write permission
                if not os.access(path_obj.parent, os.W_OK):
                    messagebox.showerror("Error", f"No write permission for parent directory: {path_obj.parent}")
                    return False
                    
        except (OSError, ValueError) as e:
            messagebox.showerror("Error", f"Invalid installation path: {str(e)}")
            return False
            
        # Validate component selection
        if not (self.install_gui.get() or self.install_cli.get()):
            messagebox.showerror("Error", "Please select at least one component to install.")
            return False
            
        # Check if source files exist
        missing_files = []
        if self.install_gui.get():
            gui_exe = self.installer_dir / 'MetaCLI_Portable' / 'MetaCLI-GUI.exe'
            if not gui_exe.exists():
                missing_files.append(str(gui_exe))
                
        if self.install_cli.get():
            cli_exe = self.installer_dir / 'dist' / 'metacli.exe'
            if not cli_exe.exists():
                missing_files.append(str(cli_exe))
                
        if missing_files:
            messagebox.showerror("Error", f"Missing application files:\n" + "\n".join(missing_files))
            return False
            
        return True
        
    def start_installation(self):
        """Start the installation process in a separate thread"""
        self.next_button.config(state='disabled')
        self.back_button.config(state='disabled')
        
        # Start installation in separate thread
        install_thread = threading.Thread(target=self.run_installation)
        install_thread.daemon = True
        install_thread.start()
        
    def run_installation(self):
        """Run the actual installation process based on mode"""
        try:
            if self.mode == 'install':
                self._run_install()
            elif self.mode == 'repair':
                self._run_repair()
            elif self.mode == 'modify':
                self._run_modify()
            elif self.mode == 'uninstall':
                self._run_uninstall()
            
        except Exception as e:
            error_msg = f"{self.mode.capitalize()} failed: {str(e)}"
            self.log_message(error_msg)
            self.logger.error(error_msg, exc_info=True)
            self.root.after(0, lambda: messagebox.showerror(f"{self.mode.capitalize()} Error", error_msg))
            # Re-enable buttons on error
            self.root.after(0, lambda: self.next_button.config(state='normal'))
            self.root.after(0, lambda: self.back_button.config(state='normal'))
    
    def _run_install(self):
        """Run installation process"""
        self.log_message("Starting MetaCLI installation...")
        self.logger.info("Installation started")
        
        # Step 1: Check dependencies
        self.update_progress(0, "Checking Python dependencies...")
        self.check_and_install_dependencies()
        
        if self.installation_cancelled:
            return
        
        # Step 2: Create installation directory
        self.update_progress(15, "Creating installation directory...")
        self.create_install_directory()
        
        # Step 3: Add antivirus exclusion
        self.update_progress(25, "Adding antivirus exclusion...")
        self.add_antivirus_exclusion()
        
        # Step 4: Copy files
        self.update_progress(35, "Copying application files...")
        self.copy_application_files()
        
        # Step 5: Update system PATH
        if self.add_to_path.get():
            self.update_progress(55, "Adding to system PATH...")
            self.add_to_system_path()
        
        # Step 6: Create desktop shortcuts
        if self.create_shortcuts.get():
            self.update_progress(70, "Creating desktop shortcuts...")
            self.create_desktop_shortcuts()
            
        # Step 7: Create Start Menu shortcuts
        if self.create_start_menu.get():
            self.update_progress(85, "Creating Start Menu shortcuts...")
            self.create_start_menu_shortcuts()
            
        # Step 8: Register uninstaller
        if self.register_uninstaller.get():
            self.update_progress(95, "Registering application...")
            self.register_application()
            
        # Step 9: Complete
        self.update_progress(100, "Installation completed successfully!")
        self.installation_complete = True
        self.logger.info("Installation completed successfully")
        
        # Enable next button and update button states
        self.root.after(0, lambda: self.next_button.config(state='normal'))
        self.root.after(0, self.update_buttons)
    
    def _run_repair(self):
        """Run repair process"""
        self.log_message("Starting MetaCLI repair...")
        self.logger.info("Repair started")
        
        # Step 1: Check dependencies
        self.update_progress(0, "Checking Python dependencies...")
        self.check_and_install_dependencies()
        
        if self.installation_cancelled:
            return
        
        # Step 2: Verify/create installation directory
        self.update_progress(15, "Verifying installation directory...")
        self.create_install_directory()
        
        # Step 3: Copy/restore files
        self.update_progress(35, "Restoring application files...")
        self.copy_application_files()
        
        # Step 4: Restore system integration based on existing installation
        if self.installed_components.get('path_entry', False):
            self.update_progress(55, "Restoring system PATH...")
            self.add_to_system_path()
        
        if self.installed_components.get('desktop_shortcuts', False):
            self.update_progress(70, "Restoring desktop shortcuts...")
            self.create_desktop_shortcuts()
            
        if self.installed_components.get('start_menu_shortcuts', False):
            self.update_progress(85, "Restoring Start Menu shortcuts...")
            self.create_start_menu_shortcuts()
            
        # Step 5: Re-register application
        self.update_progress(95, "Re-registering application...")
        self.register_application()
            
        # Step 6: Complete
        self.update_progress(100, "Repair completed successfully!")
        self.installation_complete = True
        self.logger.info("Repair completed successfully")
        
        # Enable next button and update button states
        self.root.after(0, lambda: self.next_button.config(state='normal'))
        self.root.after(0, self.update_buttons)
    
    def _run_modify(self):
        """Run modification process"""
        self.log_message("Starting MetaCLI modification...")
        self.logger.info("Modification started")
        
        # Step 1: Handle PATH changes
        self.update_progress(20, "Updating system PATH...")
        current_path = self.installed_components.get('path_entry', False)
        requested_path = self.add_to_path.get()
        
        if current_path and not requested_path:
            # Remove from PATH
            self.system_integration.remove_from_path(str(Path(self.install_path.get())))
            self.log_message("Removed MetaCLI from system PATH")
        elif not current_path and requested_path:
            # Add to PATH
            self.add_to_system_path()
        
        # Step 2: Handle desktop shortcuts
        self.update_progress(40, "Updating desktop shortcuts...")
        current_desktop = self.installed_components.get('desktop_shortcuts', False)
        requested_desktop = self.create_shortcuts.get()
        
        if current_desktop and not requested_desktop:
            # Remove desktop shortcuts
            self.system_integration.remove_desktop_shortcuts()
            self.log_message("Removed desktop shortcuts")
        elif not current_desktop and requested_desktop:
            # Create desktop shortcuts
            self.create_desktop_shortcuts()
        
        # Step 3: Handle Start Menu shortcuts
        self.update_progress(60, "Updating Start Menu shortcuts...")
        current_start_menu = self.installed_components.get('start_menu_shortcuts', False)
        requested_start_menu = self.create_start_menu.get()
        
        if current_start_menu and not requested_start_menu:
            # Remove Start Menu shortcuts
            self.system_integration.remove_start_menu_shortcuts()
            self.log_message("Removed Start Menu shortcuts")
        elif not current_start_menu and requested_start_menu:
            # Create Start Menu shortcuts
            self.create_start_menu_shortcuts()
        
        # Step 4: Update registry
        self.update_progress(80, "Updating registration...")
        self.register_application()
        
        # Step 5: Complete
        self.update_progress(100, "Modification completed successfully!")
        self.installation_complete = True
        self.logger.info("Modification completed successfully")
        
        # Enable next button and update button states
        self.root.after(0, lambda: self.next_button.config(state='normal'))
        self.root.after(0, self.update_buttons)
    
    def _run_uninstall(self):
        """Run uninstallation process"""
        self.log_message("Starting MetaCLI uninstallation...")
        self.logger.info("Uninstallation started")
        
        try:
            # Step 1: Remove shortcuts
            self.update_progress(20, "Removing shortcuts...")
            self.system_integration.remove_all_shortcuts()
            self.log_message("Removed all shortcuts")
            
            # Step 2: Remove from PATH
            self.update_progress(40, "Removing from system PATH...")
            install_path = self.existing_installation.get('install_location', '')
            if install_path:
                self.system_integration.remove_from_path(install_path)
                self.log_message("Removed from system PATH")
            
            # Step 3: Remove registry entries
            self.update_progress(60, "Removing registry entries...")
            self.system_integration.unregister_uninstaller()
            self.log_message("Removed registry entries")
            
            # Step 4: Remove files (unless keeping user data)
            if not getattr(self, 'keep_user_data', tk.BooleanVar()).get():
                self.update_progress(80, "Removing application files...")
                if install_path and Path(install_path).exists():
                    shutil.rmtree(install_path, ignore_errors=True)
                    self.log_message(f"Removed installation directory: {install_path}")
            else:
                self.log_message("Kept user data and settings as requested")
            
            # Step 5: Complete
            self.update_progress(100, "Uninstallation completed successfully!")
            self.installation_complete = True
            self.logger.info("Uninstallation completed successfully")
            
        except Exception as e:
            self.log_message(f"Warning: Some components could not be removed: {str(e)}")
            self.logger.warning(f"Partial uninstallation: {str(e)}")
            # Continue to completion even if some steps fail
            self.update_progress(100, "Uninstallation completed with warnings")
            self.installation_complete = True
        
        # Enable next button and update button states
        self.root.after(0, lambda: self.next_button.config(state='normal'))
        self.root.after(0, self.update_buttons)
            
    def update_progress(self, percentage, status):
        """Update progress bar and status"""
        self.root.after(0, lambda: self.progress_var.set(percentage))
        self.root.after(0, lambda: self.status_label.config(text=status))
        self.log_message(status)
        
    def log_message(self, message):
        """Add message to installation log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())  # Always print to console
        
        # Only update GUI log if it exists
        if hasattr(self, 'log_text') and self.log_text:
            self.root.after(0, lambda: self.log_text.insert(tk.END, log_entry))
            self.root.after(0, lambda: self.log_text.see(tk.END))
        
    def check_and_install_dependencies(self):
        """Check and install required Python dependencies"""
        if self.dependency_manager:
            try:
                # First install regular dependencies
                installed, failed = self.dependency_manager.install_missing_requirements(self.dependencies)
                
                if failed:
                    error_msg = f"Failed to install dependencies: {', '.join(failed)}"
                    self.log_message(error_msg)
                    raise Exception(error_msg)
                    
                if installed:
                    self.log_message(f"Successfully installed: {', '.join(installed)}")
                else:
                    self.log_message("All dependencies are already satisfied")
                
                # Install pywin32 for shortcut creation
                self.log_message("Installing pywin32 for shortcut creation...")
                if self.dependency_manager.install_pywin32():
                    self.log_message("✓ pywin32 installation completed")
                else:
                    self.log_message("⚠️ pywin32 installation failed, shortcuts will use fallback method")
                    
            except Exception as e:
                self.log_message(f"Dependency installation error: {str(e)}")
                raise
        else:
            # Fallback to original method
            self.log_message("Using fallback dependency checking...")
            self._fallback_dependency_check()
            
    def install_dependency(self, dependency):
        """Install a single dependency using pip"""
        self.log_message(f"Installing {dependency}...")
        try:
            # Set creation flags for Windows to hide terminal windows
            creation_flags = 0
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', dependency], 
                                  capture_output=True, text=True, check=True,
                                  creationflags=creation_flags)
            self.log_message(f"✓ Successfully installed {dependency}")
        except subprocess.CalledProcessError as e:
            self.log_message(f"✗ Failed to install {dependency}: {e.stderr}")
            raise Exception(f"Failed to install dependency: {dependency}")
            
    def _requires_admin_privileges(self, install_dir: Path) -> bool:
        """Check if the installation directory requires administrator privileges"""
        # Common system directories that require admin privileges
        admin_dirs = [
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)"),
            Path("C:/Windows"),
            Path("C:/ProgramData")
        ]
        
        try:
            # Check if the install directory is under any admin-required directory
            for admin_dir in admin_dirs:
                try:
                    install_dir.resolve().relative_to(admin_dir.resolve())
                    return True
                except ValueError:
                    continue
            
            # Try to create a test file to check write permissions
            test_dir = install_dir.parent if not install_dir.exists() else install_dir
            test_file = test_dir / f"test_write_{os.getpid()}.tmp"
            
            try:
                test_file.touch()
                test_file.unlink()
                return False
            except (PermissionError, OSError):
                return True
                
        except Exception:
            # If we can't determine, assume admin is required for safety
            return True
            
        return False
    

    
    def create_install_directory(self):
        """Create the installation directory"""
        install_dir = Path(self.install_path.get())
        
        # Verify admin privileges are present
        if not self.system_integration.is_admin():
            self.log_message("ERROR: Administrator privileges are required for installation.")
            raise PermissionError("Administrator privileges are required for MetaCLI installation.")
        
        try:
            install_dir.mkdir(parents=True, exist_ok=True)
            self.log_message(f"Created installation directory: {install_dir}")
        except PermissionError as e:
            self.log_message(f"Permission error: {e}")
            raise PermissionError(f"Cannot create directory '{install_dir}'. Administrator privileges are required.")
        
    def copy_application_files(self):
        """Copy application files to installation directory"""
        install_dir = Path(self.install_path.get())
        copied_files = []
        
        try:
            # Copy executables
            if self.install_cli.get():
                cli_source = self.dist_dir / 'metacli.exe'
                cli_dest = install_dir / 'metacli.exe'
                
                if not cli_source.exists():
                    raise FileNotFoundError(f"CLI executable not found: {cli_source}")
                    
                shutil.copy2(cli_source, cli_dest)
                copied_files.append(str(cli_dest))
                self.log_message("Copied MetaCLI CLI executable")
                
            if self.install_gui.get():
                gui_source = self.dist_dir / 'MetaCLI-GUI.exe'
                gui_dest = install_dir / 'MetaCLI-GUI.exe'
                
                if not gui_source.exists():
                    raise FileNotFoundError(f"GUI executable not found: {gui_source}")
                    
                shutil.copy2(gui_source, gui_dest)
                copied_files.append(str(gui_dest))
                self.log_message("Copied MetaCLI GUI executable")
                
            # Copy license and readme
            additional_files = ['LICENSE', 'README.md', 'requirements.txt', 'CHANGELOG.md']
            for file_name in additional_files:
                source_file = self.installer_dir / file_name
                if source_file.exists():
                    dest_file = install_dir / file_name
                    shutil.copy2(source_file, dest_file)
                    copied_files.append(str(dest_file))
                    self.log_message(f"Copied {file_name}")
                    
            self.log_message(f"Successfully copied {len(copied_files)} files")
            
        except (OSError, IOError, shutil.Error) as e:
            error_msg = f"Failed to copy application files: {str(e)}"
            self.log_message(error_msg)
            
            # Clean up partially copied files
            for file_path in copied_files:
                try:
                    if Path(file_path).exists():
                        Path(file_path).unlink()
                        self.log_message(f"Cleaned up: {file_path}")
                except Exception as cleanup_error:
                    self.log_message(f"Could not clean up {file_path}: {cleanup_error}")
                    
            raise Exception(error_msg)
        
    def add_to_system_path(self):
        """Add installation directory to system PATH"""
        install_dir = self.install_path.get()
        
        if self.system_integration:
            success = self.system_integration.add_to_path(install_dir)
            if not success:
                self.log_message("Warning: Could not modify PATH. You may need to add it manually.")
        else:
            # Fallback to original method
            self._fallback_add_to_path(install_dir)
            
    def create_desktop_shortcuts(self):
        """Create desktop shortcuts for the applications"""
        install_dir = Path(self.install_path.get())
        
        if self.system_integration:
            shortcuts = self.system_integration.create_desktop_shortcuts(
                install_dir, 
                create_gui=self.install_gui.get(),
                create_cli=self.install_cli.get()
            )
            if shortcuts:
                self.log_message(f"Created {len(shortcuts)} desktop shortcuts")
            else:
                self.log_message("Warning: Could not create desktop shortcuts")
        else:
            self._fallback_create_shortcuts(install_dir)
            
    def create_start_menu_shortcuts(self):
        """Create Start Menu shortcuts for the applications"""
        install_dir = Path(self.install_path.get())
        
        if self.system_integration:
            shortcuts = self.system_integration.create_start_menu_shortcuts(
                install_dir,
                create_gui=self.install_gui.get(),
                create_cli=self.install_cli.get()
            )
            if shortcuts:
                self.log_message(f"Created {len(shortcuts)} Start Menu shortcuts")
            else:
                self.log_message("Warning: Could not create Start Menu shortcuts")
        else:
            self.log_message("Start Menu shortcuts not available (system integration disabled)")
            
    def add_antivirus_exclusion(self):
        """Add installation directory to antivirus exclusion list"""
        try:
            install_dir = self.install_path.get()
            if self.system_integration:
                success = self.system_integration.add_antivirus_exclusion(install_dir)
                if success:
                    self.log_message("Installation directory added to antivirus exclusions")
                else:
                    self.log_message("Warning: Could not add antivirus exclusion automatically")
            else:
                self.log_message("System integration not available - skipping antivirus exclusion")
                
        except Exception as e:
            self.log_message(f"Warning: Error adding antivirus exclusion: {str(e)}")
            self.logger.warning(f"Antivirus exclusion error: {str(e)}", exc_info=True)
            # Don't fail installation if antivirus exclusion fails
            
    def register_application(self):
        """Register the application in Add/Remove Programs"""
        install_dir = Path(self.install_path.get())
        
        if self.system_integration:
            success = self.system_integration.register_uninstaller(
                install_dir,
                version="1.0.0"
            )
            if success:
                self.log_message("Application registered in Add/Remove Programs")
            else:
                self.log_message("Warning: Could not register application")
        else:
            self.log_message("Application registration not available (system integration disabled)")
            
    def _fallback_dependency_check(self):
        """Fallback dependency checking method"""
        self.log_message("Checking Python dependencies...")
        
        missing_deps = []
        for dep in self.dependencies:
            try:
                # Try to import the package
                package_name = dep.split('>=')[0].split('==')[0]
                if package_name == 'PyPDF2':
                    import PyPDF2
                elif package_name == 'python-docx':
                    import docx
                elif package_name == 'Pillow':
                    import PIL
                else:
                    __import__(package_name)
                self.log_message(f"✓ {package_name} is available")
            except ImportError:
                missing_deps.append(dep)
                self.log_message(f"✗ {package_name} is missing")
                
        if missing_deps:
            self.log_message(f"Installing {len(missing_deps)} missing dependencies...")
            for dep in missing_deps:
                self.install_dependency(dep)
        else:
            self.log_message("All dependencies are satisfied")
            
    def _fallback_add_to_path(self, install_dir):
        """Fallback method to add directory to PATH"""
        try:
            import winreg
            # Open the registry key for system environment variables
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                # Get current PATH value
                try:
                    current_path, _ = winreg.QueryValueEx(key, 'PATH')
                except FileNotFoundError:
                    current_path = ''
                    
                # Check if our directory is already in PATH
                if install_dir.lower() not in current_path.lower():
                    # Add our directory to PATH
                    new_path = current_path + ';' + install_dir if current_path else install_dir
                    winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)
                    self.log_message("Added installation directory to system PATH")
                else:
                    self.log_message("Installation directory already in system PATH")
                    
        except PermissionError:
            self.log_message("Warning: Could not modify system PATH (insufficient permissions)")
        except Exception as e:
            self.log_message(f"Warning: Could not modify system PATH: {str(e)}")
            
    def _fallback_create_shortcuts(self, install_dir):
        """Fallback method to create desktop shortcuts"""
        try:
            import win32com.client
            
            desktop = Path.home() / 'Desktop'
            shell = win32com.client.Dispatch('WScript.Shell')
            
            if self.install_gui.get():
                shortcut_path = desktop / 'MetaCLI GUI.lnk'
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.Targetpath = str(install_dir / 'MetaCLI-GUI.exe')
                shortcut.WorkingDirectory = str(install_dir)
                shortcut.Description = 'MetaCLI GUI Application'
                shortcut.save()
                self.log_message("Created desktop shortcut for MetaCLI GUI")
                
            if self.install_cli.get():
                shortcut_path = desktop / 'MetaCLI CLI.lnk'
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.Targetpath = 'cmd.exe'
                shortcut.Arguments = f'/k cd /d "{install_dir}" && metacli.exe --help'
                shortcut.WorkingDirectory = str(install_dir)
                shortcut.Description = 'MetaCLI Command Line Interface'
                shortcut.save()
                self.log_message("Created desktop shortcut for MetaCLI CLI")
                
        except ImportError:
            self.log_message("Warning: Could not create shortcuts (pywin32 not available)")
        except Exception as e:
            self.log_message(f"Warning: Could not create shortcuts: {str(e)}")

    def finish_installation(self):
        """Finish the installation and optionally launch the application"""
        if self.launch_gui.get() and self.install_gui.get():
            try:
                gui_path = Path(self.install_path.get()) / 'MetaCLI-GUI.exe'
                if gui_path.exists():
                    # Set creation flags for Windows to prevent console window
                    creation_flags = 0
                    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                        creation_flags = subprocess.CREATE_NO_WINDOW
                    subprocess.Popen([str(gui_path)], creationflags=creation_flags)
            except Exception as e:
                messagebox.showwarning("Launch Error", f"Could not launch MetaCLI GUI: {str(e)}")
                
        self.root.quit()
        
    def cancel_installation(self):
        """Cancel the installation process"""
        current_page = self.notebook.index(self.notebook.select())
        if current_page == 2:  # Progress page
            if messagebox.askyesno("Cancel Installation", 
                                 "Installation is in progress. Cancelling may leave your system in an incomplete state.\n\nAre you sure you want to cancel?"):
                self.installation_cancelled = True
                self.log_message("Installation cancelled by user")
                if hasattr(self, 'logger'):
                    self.logger.warning("Installation cancelled by user")
                self.cleanup_partial_installation()
                self.root.quit()
        else:
            if messagebox.askyesno("Cancel Installation", "Are you sure you want to cancel the installation?"):
                self.log_message("Installation cancelled by user")
                self.root.quit()
                
    def cleanup_partial_installation(self):
        """Clean up any partially installed files"""
        try:
            install_dir = Path(self.install_path.get())
            if install_dir.exists() and install_dir != Path.home():
                # Only clean up if it's our installation directory
                if any(install_dir.glob('metacli*')) or any(install_dir.glob('MetaCLI*')):
                    self.log_message(f"Cleaning up partial installation in {install_dir}")
                    
                    # Remove our files
                    files_to_remove = [
                        'metacli.exe',
                        'MetaCLI-GUI.exe',
                        'requirements.txt',
                        'README.md',
                        'LICENSE',
                        'CHANGELOG.md'
                    ]
                    
                    for file_name in files_to_remove:
                        file_path = install_dir / file_name
                        if file_path.exists():
                            try:
                                file_path.unlink()
                                self.log_message(f"Removed: {file_path}")
                            except Exception as e:
                                self.log_message(f"Could not remove {file_path}: {e}")
                                
                    # Remove directory if empty
                    try:
                        if not any(install_dir.iterdir()):
                            install_dir.rmdir()
                            self.log_message(f"Removed empty directory: {install_dir}")
                    except Exception as e:
                        self.log_message(f"Could not remove directory {install_dir}: {e}")
                        
        except Exception as e:
            self.log_message(f"Error during cleanup: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Cleanup error: {e}", exc_info=True)
            
    def cleanup_singleton(self):
        """Clean up the singleton lock file"""
        try:
            if hasattr(self, 'lock_file') and self.lock_file:
                self.lock_file.close()
            if hasattr(self, 'lock_file_path') and os.path.exists(self.lock_file_path):
                os.unlink(self.lock_file_path)
        except Exception:
            pass  # Ignore cleanup errors
            
    def run(self):
        """Run the installer"""
        try:
            # Force window to front and focus
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after_idle(lambda: self.root.attributes('-topmost', False))
            self.root.focus_force()
            self.root.mainloop()
        finally:
            self.cleanup_singleton()


def request_admin_privileges():
    """Check if current process has administrator privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        print(f"Failed to check admin privileges: {e}")
        return False

def check_admin_needed():
    """Check if admin privileges are needed based on installation requirements"""
    try:
        # Check if we need admin for system-wide PATH modification
        # Check if we need admin for system directories
        # Check if we need admin for Windows Defender exclusions
        
        admin_required_reasons = []
        
        # Check default install path
        default_path = Path.home() / 'AppData' / 'Local' / 'MetaCLI'
        admin_dirs = [
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)"),
            Path("C:/Windows"),
            Path("C:/ProgramData")
        ]
        
        for admin_dir in admin_dirs:
            try:
                default_path.resolve().relative_to(admin_dir.resolve())
                admin_required_reasons.append(f"Installation path requires admin: {default_path}")
                break
            except ValueError:
                continue
        
        # Check if we can write to system PATH
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
                              0, winreg.KEY_READ) as key:
                # If we can't write to system PATH, we might need admin for system-wide installation
                pass
        except PermissionError:
            admin_required_reasons.append("System PATH modification requires admin")
        except Exception:
            pass
        
        # Check Windows Defender exclusion capability
        try:
            import subprocess
            result = subprocess.run(
                ['powershell', '-Command', 'Get-MpPreference -ErrorAction SilentlyContinue'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode != 0:
                admin_required_reasons.append("Windows Defender exclusion requires admin")
        except Exception:
            pass
        
        if admin_required_reasons:
            print(f"Admin privileges needed for: {'; '.join(admin_required_reasons)}")
            return True
        
        return False
    except Exception as e:
        print(f"Error checking admin requirements: {e}")
        return False

def parse_arguments():
    """Parse command line arguments to determine installer mode"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MetaCLI Installer - Install, Repair, Modify, or Uninstall MetaCLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python metacli_installer.py                    # Install MetaCLI
  python metacli_installer.py --repair           # Repair existing installation
  python metacli_installer.py --modify           # Modify installation components
  python metacli_installer.py --uninstall        # Uninstall MetaCLI
  python metacli_installer.py --request-admin    # Internal flag for admin elevation"""
    )
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--repair', action='store_true',
                           help='Repair existing MetaCLI installation')
    mode_group.add_argument('--modify', action='store_true',
                           help='Modify existing MetaCLI installation components')
    mode_group.add_argument('--uninstall', action='store_true',
                           help='Uninstall MetaCLI from the system')
    mode_group.add_argument('--request-admin', action='store_true',
                           help='Internal flag for administrator privilege elevation')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.repair:
        return 'repair'
    elif args.modify:
        return 'modify'
    elif args.uninstall:
        return 'uninstall'
    elif args.request_admin:
        return 'request_admin'
    else:
        return 'install'

def handle_admin_privileges(mode):
    """Handle administrator privilege requests - always require admin privileges"""
    if mode == 'request_admin':
        # This should never be reached in normal operation
        print("Internal admin request flag detected - this should not happen.")
        return
    
    # Always require admin privileges for the installer
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            mode_text = {
                'install': 'installation',
                'repair': 'repair',
                'modify': 'modification',
                'uninstall': 'uninstallation'
            }.get(mode, 'operation')
            
            print(f"MetaCLI Installer requires administrator privileges for {mode_text}.")
            print("Requesting elevated permissions...")
            
            # Create new argument list without --request-admin to avoid loops
            new_args = [arg for arg in sys.argv if arg != '--request-admin']
            args_string = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in new_args)
            
            try:
                # Request elevation and exit immediately
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, args_string, None, 1
                )
                if result > 32:  # Success
                    print("Elevation request sent. Exiting current process...")
                    sys.exit(0)
                else:
                    raise Exception(f"ShellExecuteW failed with code {result}")
            except Exception as shell_error:
                print(f"\nFailed to request administrator privileges: {shell_error}")
                print(f"Administrator privileges are required for MetaCLI Installer.")
                print("Please run the installer as administrator manually.")
                input("Press Enter to exit...")
                sys.exit(1)
        else:
            print("Administrator privileges confirmed.")
    except ImportError:
        print(f"\nCannot check administrator privileges on this system.")
        print(f"Administrator privileges are required for MetaCLI Installer.")
        print("Please ensure you are running as administrator.")
    except Exception as e:
        print(f"\nError checking administrator privileges: {e}")
        print(f"Administrator privileges are required for MetaCLI Installer.")
        print("Please ensure you are running as administrator.")

def main():
    """Main entry point with comprehensive error handling"""
    try:
        print("Starting MetaCLI Installer...")
        
        # Parse command line arguments
        mode = parse_arguments()
        print(f"Installer mode: {mode}")
        
        # Handle admin privileges
        handle_admin_privileges(mode)
        
        # If we reach here, we have the right privileges or don't need them
        if mode != 'request_admin':
            print("Initializing installer...")
            installer = MetaCLIInstaller(mode=mode)
            print("Starting installer UI...")
            installer.run()
            
    except KeyboardInterrupt:
        print("\nInstaller interrupted by user.")
        sys.exit(1)
    except ImportError as e:
        print(f"Critical import error: {e}")
        print("Please ensure all required dependencies are installed.")
        sys.exit(1)
    except PermissionError as e:
        print(f"Permission error: {e}")
        print("Please run the installer as administrator or check file permissions.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Required file not found: {e}")
        print("Please ensure the installer package is complete.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during installer startup: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        
        # Try to show error in GUI if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showerror(
                "MetaCLI Installer Error",
                f"An unexpected error occurred:\n\n{e}\n\nPlease check the console for more details."
            )
            root.destroy()
        except:
            pass  # If GUI error display fails, just continue
            
        sys.exit(1)


if __name__ == '__main__':
    main()