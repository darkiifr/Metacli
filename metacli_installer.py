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
except ImportError:
    # Fallback if modules are not available
    DependencyManager = None
    SystemIntegration = None


class MetaCLIInstaller:
    def __init__(self):
        # Check for existing instance
        if not self.check_singleton():
            messagebox.showerror("MetaCLI Setup", "Another instance of MetaCLI Setup is already running.")
            sys.exit(1)
            
        # Initialize basic variables first
        self.installation_cancelled = False
        self.current_step = 0
        self.total_steps = 8
        self.installation_complete = False
        
        # Initialize paths and directories
        self.installer_dir = Path(__file__).parent.absolute()
        self.dist_dir = self.installer_dir / 'dist'
        
        # Setup logging early
        self.setup_logging()
        
        # Create and configure main window
        self.root = tk.Tk()
        self.root.title("MetaCLI Setup")
        self.root.geometry("650x500")
        self.root.minsize(650, 500)
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')
        
        # Center window on screen
        self.center_window()
        
        # Installation configuration
        self.install_path = tk.StringVar(value=os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'MetaCLI'))
        self.add_to_path = tk.BooleanVar(value=True)
        self.install_gui = tk.BooleanVar(value=True)
        self.install_cli = tk.BooleanVar(value=True)
        self.create_shortcuts = tk.BooleanVar(value=True)
        self.create_start_menu = tk.BooleanVar(value=True)
        self.register_uninstaller = tk.BooleanVar(value=True)
        
        # Required dependencies
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
        
        # Defer expensive manager initialization
        self.dependency_manager = None
        self.system_integration = None
        
        # Setup UI immediately
        self.setup_ui()
        
        # Initialize managers after UI is ready
        self.root.after(100, self.initialize_managers)
        
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
            self.dependency_manager = DependencyManager() if DependencyManager else None
            self.system_integration = SystemIntegration() if SystemIntegration else None
        except Exception as e:
            self.dependency_manager = None
            self.system_integration = None
            print(f"Warning: Could not initialize installer modules: {e}")
            if hasattr(self, 'logger'):
                self.logger.warning(f"Could not initialize installer modules: {e}")
    
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
        """Setup logging for the installer"""
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
        """Setup the welcome page"""
        # Title
        title_label = ttk.Label(self.welcome_frame, text="Welcome to MetaCLI Setup", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(20, 10))
        
        # Description
        desc_text = (
            "This will install MetaCLI on your computer.\n\n"
            "MetaCLI is a command-line interface for metadata extraction and management.\n\n"
            "It includes both a GUI application and a command-line tool for processing\n"
            "various file types and extracting metadata information.\n\n"
            "Click Next to continue or Cancel to exit Setup."
        )
        desc_label = ttk.Label(self.welcome_frame, text=desc_text, justify='left')
        desc_label.pack(pady=10, padx=20)
        
        # System requirements check
        req_frame = ttk.LabelFrame(self.welcome_frame, text="System Requirements")
        req_frame.pack(fill='x', padx=20, pady=10)
        
        python_version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ttk.Label(req_frame, text=f"✓ {python_version} detected", foreground='green').pack(anchor='w', padx=10, pady=5)
        ttk.Label(req_frame, text=f"✓ Windows {os.name} compatible", foreground='green').pack(anchor='w', padx=10, pady=5)
        
    def setup_options_page(self):
        """Setup the installation options page"""
        # Title
        title_label = ttk.Label(self.options_frame, text="Installation Options", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Installation path
        path_frame = ttk.LabelFrame(self.options_frame, text="Installation Directory")
        path_frame.pack(fill='x', padx=20, pady=10)
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill='x', padx=10, pady=10)
        
        self.path_entry = ttk.Entry(path_entry_frame, textvariable=self.install_path, width=50)
        self.path_entry.pack(side='left', fill='x', expand=True)
        
        browse_button = ttk.Button(path_entry_frame, text="Browse...", command=self.browse_install_path)
        browse_button.pack(side='right', padx=(10, 0))
        
        # Component information (both CLI and GUI will be installed)
        comp_frame = ttk.LabelFrame(self.options_frame, text="Components")
        comp_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(comp_frame, text="✓ MetaCLI GUI Application", foreground='green').pack(anchor='w', padx=10, pady=5)
        ttk.Label(comp_frame, text="✓ MetaCLI Command Line Interface", foreground='green').pack(anchor='w', padx=10, pady=5)
        ttk.Label(comp_frame, text="Both components will be installed automatically.", font=('Arial', 8), foreground='gray').pack(anchor='w', padx=10, pady=(0, 5))
        
        # Additional options
        options_frame = ttk.LabelFrame(self.options_frame, text="Additional Options")
        options_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Checkbutton(options_frame, text="Add MetaCLI to system PATH", variable=self.add_to_path).pack(anchor='w', padx=10, pady=2)
        ttk.Checkbutton(options_frame, text="Create desktop shortcuts", variable=self.create_shortcuts).pack(anchor='w', padx=10, pady=2)
        ttk.Checkbutton(options_frame, text="Create Start Menu shortcuts", variable=self.create_start_menu).pack(anchor='w', padx=10, pady=2)
        ttk.Checkbutton(options_frame, text="Register in Add/Remove Programs", variable=self.register_uninstaller).pack(anchor='w', padx=10, pady=2)
        
    def setup_progress_page(self):
        """Setup the installation progress page"""
        # Title
        title_label = ttk.Label(self.progress_frame, text="Installing MetaCLI", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(20, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(pady=10)
        
        # Status label
        self.status_label = ttk.Label(self.progress_frame, text="Preparing installation...")
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
        # Title
        title_label = ttk.Label(self.complete_frame, text="Installation Complete", 
                               font=('Arial', 16, 'bold'), foreground='green')
        title_label.pack(pady=(30, 20))
        
        # Success message
        success_text = (
            "MetaCLI has been successfully installed on your computer.\n\n"
            "You can now use MetaCLI from the command line or launch the GUI application\n"
            "from the Start Menu or desktop shortcuts."
        )
        success_label = ttk.Label(self.complete_frame, text=success_text, justify='center')
        success_label.pack(pady=20)
        
        # Launch options
        launch_frame = ttk.LabelFrame(self.complete_frame, text="Launch Options")
        launch_frame.pack(padx=20, pady=20)
        
        self.launch_gui = tk.BooleanVar(value=True)
        ttk.Checkbutton(launch_frame, text="Launch MetaCLI GUI now", variable=self.launch_gui).pack(anchor='w', padx=10, pady=10)
        
    def browse_install_path(self):
        """Browse for installation directory"""
        directory = filedialog.askdirectory(initialdir=self.install_path.get())
        if directory:
            self.install_path.set(directory)
            
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
        """Run the actual installation process"""
        try:
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
            
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            self.log_message(error_msg)
            self.logger.error(error_msg, exc_info=True)
            self.root.after(0, lambda: messagebox.showerror("Installation Error", error_msg))
            # Re-enable buttons on error
            self.root.after(0, lambda: self.next_button.config(state='normal'))
            self.root.after(0, lambda: self.back_button.config(state='normal'))
            
    def update_progress(self, percentage, status):
        """Update progress bar and status"""
        self.root.after(0, lambda: self.progress_var.set(percentage))
        self.root.after(0, lambda: self.status_label.config(text=status))
        self.log_message(status)
        
    def log_message(self, message):
        """Add message to installation log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.root.after(0, lambda: self.log_text.insert(tk.END, log_entry))
        self.root.after(0, lambda: self.log_text.see(tk.END))
        
    def check_and_install_dependencies(self):
        """Check and install required Python dependencies"""
        if self.dependency_manager:
            try:
                installed, failed = self.dependency_manager.install_missing_requirements(self.dependencies)
                
                if failed:
                    error_msg = f"Failed to install dependencies: {', '.join(failed)}"
                    self.log_message(error_msg)
                    raise Exception(error_msg)
                    
                if installed:
                    self.log_message(f"Successfully installed: {', '.join(installed)}")
                else:
                    self.log_message("All dependencies are already satisfied")
                    
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
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', dependency], 
                                  capture_output=True, text=True, check=True)
            self.log_message(f"✓ Successfully installed {dependency}")
        except subprocess.CalledProcessError as e:
            self.log_message(f"✗ Failed to install {dependency}: {e.stderr}")
            raise Exception(f"Failed to install dependency: {dependency}")
            
    def create_install_directory(self):
        """Create the installation directory"""
        install_dir = Path(self.install_path.get())
        install_dir.mkdir(parents=True, exist_ok=True)
        self.log_message(f"Created installation directory: {install_dir}")
        
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
                app_name="MetaCLI",
                version="1.0.0",
                publisher="MetaCLI Team",
                uninstall_string=str(install_dir / "uninstall.exe")
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
                    subprocess.Popen([str(gui_path)])
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
            self.root.mainloop()
        finally:
            self.cleanup_singleton()


if __name__ == '__main__':
    installer = MetaCLIInstaller()
    installer.run()