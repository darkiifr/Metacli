#!/usr/bin/env python3
"""
MetaCLI GUI - Advanced Interactive Metadata Extraction Tool

A modern, user-friendly graphical interface for the MetaCLI command-line tool
with enhanced features, tabbed interface, and improved user experience.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import json
import threading
from pathlib import Path
import webbrowser
from datetime import datetime
import subprocess
import shutil
import hashlib
import csv
import re

# Add the metacli package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from metacli.core.extractor import MetadataExtractor
    from metacli.core.scanner import DirectoryScanner
    from metacli.utils.formatter import OutputFormatter
    from metacli.utils.logger import setup_logger, get_logger
except ImportError as e:
    print(f"Error importing MetaCLI modules: {e}")
    sys.exit(1)


class MetaCLIGUI:
    """Advanced GUI application class for MetaCLI with enhanced features."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("MetaCLI - Advanced Metadata Extraction Tool v3.0")
        
        # Enhanced window configuration
        self.setup_window()
        
        # Initialize theme and styling
        self.dark_mode = tk.BooleanVar(value=False)
        self.setup_styling()
        
        # Initialize components with optimized settings
        self.extractor = MetadataExtractor(enable_cache=True, max_workers=4)
        self.scanner = DirectoryScanner()
        self.formatter = OutputFormatter()
        self.logger = setup_logger(verbose=False, log_file='metacli_gui.log')
        
        # Enhanced GUI state variables
        self.current_path = tk.StringVar()
        self.scan_recursive = tk.BooleanVar(value=True)
        self.selected_formats = tk.StringVar(value="all")
        self.output_format = tk.StringVar(value="json")
        self.max_files = tk.IntVar(value=500)
        self.show_hidden = tk.BooleanVar(value=False)
        self.auto_refresh = tk.BooleanVar(value=False)
        self.parallel_processing = tk.BooleanVar(value=True)
        self.cache_enabled = tk.BooleanVar(value=True)
        self.show_progress = tk.BooleanVar(value=True)
        
        # Results storage and performance tracking
        self.scan_results = []
        self.current_metadata = {}
        self.processing = False
        self.last_scan_time = 0
        self.total_files_processed = 0
        
        # Setup UI components
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_enhanced_keyboard_shortcuts()
        
        # Set initial path to current directory
        self.current_path.set(os.getcwd())
        
        # Auto-save settings
        self.load_user_preferences()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_window(self):
        """Configure enhanced window properties and responsiveness."""
        # Get screen dimensions for responsive sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate optimal window size (80% of screen)
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Center window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(1000, 700)
        
        # Set application icon (if available)
        try:
            # You can add an icon file here
            # self.root.iconbitmap('icon.ico')
            pass
        except:
            pass
        
        # Configure window state
        self.root.state('normal')
        
        # Make window resizable
        self.root.resizable(True, True)
        
    def setup_enhanced_keyboard_shortcuts(self):
        """Setup enhanced keyboard shortcuts for improved usability."""
        # File operations
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-d>', lambda e: self.browse_directory())
        self.root.bind('<Control-s>', lambda e: self.save_results())
        self.root.bind('<Control-r>', lambda e: self.scan_directory())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        
        # View operations
        self.root.bind('<F5>', lambda e: self.refresh_current_view())
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        
        # Font size
        self.root.bind('<Control-plus>', lambda e: self.increase_font_size())
        self.root.bind('<Control-equal>', lambda e: self.increase_font_size())  # For keyboards without numpad
        self.root.bind('<Control-minus>', lambda e: self.decrease_font_size())
        
        # Navigation
        self.root.bind('<Control-1>', lambda e: self.notebook.select(0))
        self.root.bind('<Control-2>', lambda e: self.notebook.select(1))
        self.root.bind('<Control-3>', lambda e: self.notebook.select(2))
        self.root.bind('<Control-4>', lambda e: self.notebook.select(3))
        
        # Clear operations
        self.root.bind('<Control-Delete>', lambda e: self.clear_results())
        
        # Help
        self.root.bind('<F1>', lambda e: self.show_help())
    
    def load_user_preferences(self):
        """Load user preferences from configuration file."""
        try:
            config_path = Path.home() / '.metacli_config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.dark_mode.set(config.get('dark_mode', False))
                    self.max_files.set(config.get('max_files', 500))
                    self.parallel_processing.set(config.get('parallel_processing', True))
                    self.cache_enabled.set(config.get('cache_enabled', True))
        except Exception:
            pass  # Use defaults if config loading fails
    
    def save_user_preferences(self):
        """Save user preferences to configuration file."""
        try:
            config = {
                'dark_mode': self.dark_mode.get(),
                'max_files': self.max_files.get(),
                'parallel_processing': self.parallel_processing.get(),
                'cache_enabled': self.cache_enabled.get()
            }
            config_path = Path.home() / '.metacli_config.json'
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass  # Fail silently if saving fails
    
    def on_closing(self):
        """Handle application closing with cleanup."""
        self.save_user_preferences()
        self.root.destroy()
        
    def setup_styling(self):
        """Configure modern styling and themes with enhanced visual appeal."""
        style = ttk.Style()
        
        # Use modern theme if available
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        
        # Configure enhanced custom styles
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 16, 'bold'), 
                       foreground='#2c3e50',
                       background='#ecf0f1')
        
        style.configure('Subtitle.TLabel', 
                       font=('Segoe UI', 11), 
                       foreground='#7f8c8d')
        
        style.configure('Heading.TLabel', 
                       font=('Segoe UI', 10, 'bold'), 
                       foreground='#34495e')
        
        style.configure('Action.TButton', 
                       padding=(15, 8), 
                       font=('Segoe UI', 9, 'bold'),
                       relief='flat')
        
        style.configure('Primary.TButton', 
                       padding=(15, 8), 
                       font=('Segoe UI', 9, 'bold'),
                       foreground='white')
        
        style.configure('Success.TLabel', 
                       foreground='#27ae60', 
                       font=('Segoe UI', 9, 'bold'))
        
        style.configure('Error.TLabel', 
                       foreground='#e74c3c', 
                       font=('Segoe UI', 9, 'bold'))
        
        style.configure('Warning.TLabel', 
                       foreground='#f39c12', 
                       font=('Segoe UI', 9, 'bold'))
        
        style.configure('Info.TLabel', 
                       foreground='#3498db', 
                       font=('Segoe UI', 9))
        
        style.configure('Card.TFrame', 
                       relief='solid', 
                       borderwidth=1)
        
        style.configure('Highlight.TFrame', 
                       relief='solid', 
                       borderwidth=2)
        
        # Configure treeview for better appearance
        style.configure('Treeview', 
                       font=('Segoe UI', 9),
                       rowheight=25)
        
        style.configure('Treeview.Heading', 
                       font=('Segoe UI', 9, 'bold'),
                       relief='flat')
        
        # Configure notebook tabs
        style.configure('TNotebook.Tab', 
                       padding=(20, 10),
                       font=('Segoe UI', 10))
        
        # Set root background
        self.root.configure(bg='#ecf0f1')
        
    def setup_menu(self):
        """Set up comprehensive menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Open Directory...", command=self.browse_directory, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="Export Results...", command=self.export_results, accelerator="Ctrl+E")
        file_menu.add_command(label="Save Report...", command=self.save_report, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Recent Files", state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy Results", command=self.copy_results, accelerator="Ctrl+C")
        edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", command=self.show_find_dialog, accelerator="Ctrl+F")
        edit_menu.add_command(label="Filter Results...", command=self.show_filter_dialog)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Batch Process...", command=self.batch_process)
        tools_menu.add_command(label="Compare Files...", command=self.compare_files)
        tools_menu.add_command(label="Generate Report...", command=self.generate_report)
        tools_menu.add_separator()
        tools_menu.add_command(label="Settings...", command=self.show_settings)
        tools_menu.add_command(label="Clear Cache", command=self.clear_cache)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_view, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Hidden Files", variable=self.show_hidden)
        view_menu.add_checkbutton(label="Auto Refresh", variable=self.auto_refresh)
        view_menu.add_separator()
        view_menu.add_command(label="Expand All", command=self.expand_all)
        view_menu.add_command(label="Collapse All", command=self.collapse_all)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_help)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="Command Line Usage", command=self.show_cli_help)
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=self.check_updates)
        help_menu.add_command(label="About MetaCLI", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-d>', lambda e: self.browse_directory())
        self.root.bind('<Control-e>', lambda e: self.export_results())
        self.root.bind('<Control-s>', lambda e: self.save_report())
        self.root.bind('<Control-c>', lambda e: self.copy_results())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-f>', lambda e: self.show_find_dialog())
        self.root.bind('<F5>', lambda e: self.refresh_view())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        
    def setup_ui(self):
        """Set up the enhanced tabbed user interface."""
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.scanner_tab = ttk.Frame(self.notebook)
        self.metadata_tab = ttk.Frame(self.notebook)
        self.batch_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.scanner_tab, text="📁 File Scanner")
        self.notebook.add(self.metadata_tab, text="🔍 Metadata Viewer")
        self.notebook.add(self.batch_tab, text="⚙️ Batch Operations")
        self.notebook.add(self.settings_tab, text="🛠️ Settings")
        
        # Setup individual tabs
        self.setup_scanner_tab()
        self.setup_metadata_tab()
        self.setup_batch_tab()
        self.setup_settings_tab()
        
    def setup_scanner_tab(self):
        """Set up the main file scanner tab."""
        # Main frame with padding
        main_frame = ttk.Frame(self.scanner_tab, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Title section
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(title_frame, text="Directory & File Scanner", style='Title.TLabel').pack(side=tk.LEFT)
        ttk.Label(title_frame, text="Scan directories and files to extract metadata", 
                 foreground='#7f8c8d').pack(side=tk.LEFT, padx=(10, 0))
        
        # Path selection section
        path_frame = ttk.LabelFrame(main_frame, text="Target Selection", padding="10")
        path_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        path_frame.columnconfigure(1, weight=1)
        
        ttk.Label(path_frame, text="Path:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        path_entry_frame.columnconfigure(0, weight=1)
        
        self.path_entry = ttk.Entry(path_entry_frame, textvariable=self.current_path, 
                                   font=('Consolas', 9), width=60)
        self.path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(path_entry_frame, text="📁 Browse Directory", 
                  command=self.browse_directory).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(path_entry_frame, text="📄 Select File", 
                  command=self.open_file).grid(row=0, column=2)
        
        # Quick access buttons
        quick_frame = ttk.Frame(path_frame)
        quick_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        ttk.Button(quick_frame, text="🏠 Home", command=lambda: self.set_path(Path.home()), 
                  width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="💻 Desktop", command=lambda: self.set_path(Path.home() / "Desktop"), 
                  width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="📁 Documents", command=lambda: self.set_path(Path.home() / "Documents"), 
                  width=10).pack(side=tk.LEFT)
        
        # Scan options section
        options_frame = ttk.LabelFrame(main_frame, text="Scan Configuration", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        options_frame.columnconfigure(2, weight=1)
        
        # First row of options
        ttk.Checkbutton(options_frame, text="Recursive scan subdirectories", 
                       variable=self.scan_recursive).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Checkbutton(options_frame, text="Include hidden files", 
                       variable=self.show_hidden).grid(row=0, column=1, sticky=tk.W, padx=(20, 0), pady=(0, 5))
        
        # Second row of options
        ttk.Label(options_frame, text="File types:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        format_combo = ttk.Combobox(options_frame, textvariable=self.selected_formats,
                                   values=["all", "images", "documents", "audio", "video", "archives", "code"],
                                   state="readonly", width=12)
        format_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 20), pady=(5, 0))
        
        ttk.Label(options_frame, text="Max files:").grid(row=1, column=2, sticky=tk.W, pady=(5, 0))
        
        max_files_frame = ttk.Frame(options_frame)
        max_files_frame.grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        
        max_files_spin = ttk.Spinbox(max_files_frame, from_=1, to=10000, textvariable=self.max_files, 
                                    width=8, font=('Consolas', 9))
        max_files_spin.pack(side=tk.LEFT)
        
        ttk.Label(max_files_frame, text="files", foreground='#7f8c8d').pack(side=tk.LEFT, padx=(5, 0))
        
        # Action buttons section
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=3, pady=(0, 15))
        
        ttk.Button(action_frame, text="🔍 Start Scan", command=self.scan_directory, 
                  style='Action.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="📊 View Details", command=self.view_selected_metadata, 
                  style='Action.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="💾 Export Results", command=self.export_results, 
                  style='Action.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="🗑️ Clear Results", command=self.clear_results).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="⏹️ Stop", command=self.stop_processing, state="disabled").pack(side=tk.LEFT)
        
        # Progress and status section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Ready to scan", foreground='#27ae60')
        self.status_label.grid(row=0, column=1)
        
        # Statistics frame
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.stats_label = ttk.Label(stats_frame, text="Files: 0 | Total Size: 0 B | Types: 0", 
                                    foreground='#7f8c8d')
        self.stats_label.pack(side=tk.LEFT)
        
        # Results section with enhanced treeview
        results_frame = ttk.LabelFrame(main_frame, text="Scan Results", padding="5")
        results_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Create enhanced treeview
        columns = ('Size', 'Type', 'Modified', 'Extension')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings', height=15)
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure treeview columns
        self.results_tree.heading('#0', text='📁 File Path')
        self.results_tree.heading('Size', text='📏 Size')
        self.results_tree.heading('Type', text='📋 Type')
        self.results_tree.heading('Modified', text='📅 Modified')
        self.results_tree.heading('Extension', text='🏷️ Extension')
        
        self.results_tree.column('#0', width=400, minwidth=200)
        self.results_tree.column('Size', width=100, minwidth=80)
        self.results_tree.column('Type', width=120, minwidth=100)
        self.results_tree.column('Modified', width=150, minwidth=120)
        self.results_tree.column('Extension', width=80, minwidth=60)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.results_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Bind events
        self.results_tree.bind('<Double-1>', self.on_tree_double_click)
        self.results_tree.bind('<Button-3>', self.show_context_menu)
        
    def setup_metadata_tab(self):
        """Set up the metadata viewer tab."""
        main_frame = ttk.Frame(self.metadata_tab, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        ttk.Label(main_frame, text="Detailed Metadata Viewer", style='Title.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        file_entry_frame = ttk.Frame(file_frame)
        file_entry_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        file_entry_frame.columnconfigure(0, weight=1)
        
        self.metadata_file_var = tk.StringVar()
        metadata_file_entry = ttk.Entry(file_entry_frame, textvariable=self.metadata_file_var, font=('Consolas', 9))
        metadata_file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(file_entry_frame, text="Browse...", command=self.browse_metadata_file).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(file_entry_frame, text="Analyze", command=self.analyze_metadata).grid(row=0, column=2)
        
        # Metadata display
        metadata_frame = ttk.LabelFrame(main_frame, text="Metadata Information", padding="5")
        metadata_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        metadata_frame.columnconfigure(0, weight=1)
        metadata_frame.rowconfigure(0, weight=1)
        
        # Create notebook for different metadata views
        self.metadata_notebook = ttk.Notebook(metadata_frame)
        self.metadata_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Raw metadata tab
        self.raw_metadata_frame = ttk.Frame(self.metadata_notebook)
        self.metadata_notebook.add(self.raw_metadata_frame, text="Raw Data")
        
        self.metadata_text = scrolledtext.ScrolledText(self.raw_metadata_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.metadata_text.pack(fill=tk.BOTH, expand=True)
        
        # Formatted metadata tab
        self.formatted_metadata_frame = ttk.Frame(self.metadata_notebook)
        self.metadata_notebook.add(self.formatted_metadata_frame, text="Formatted View")
        
        self.formatted_tree = ttk.Treeview(self.formatted_metadata_frame, columns=('Value',), show='tree headings')
        self.formatted_tree.pack(fill=tk.BOTH, expand=True)
        self.formatted_tree.heading('#0', text='Property')
        self.formatted_tree.heading('Value', text='Value')
        
    def setup_batch_tab(self):
        """Set up the batch operations tab."""
        main_frame = ttk.Frame(self.batch_tab, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Batch Operations", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 20))
        
        # Create notebook for batch sub-tabs
        batch_notebook = ttk.Notebook(main_frame)
        batch_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Batch Extraction Tab
        extraction_frame = ttk.Frame(batch_notebook)
        batch_notebook.add(extraction_frame, text="📦 Batch Extraction")
        self.setup_batch_extraction_tab(extraction_frame)
        
        # Batch Operations Tab
        operations_frame = ttk.Frame(batch_notebook)
        batch_notebook.add(operations_frame, text="🔧 File Operations")
        self.setup_batch_operations_tab(operations_frame)
        
        # Batch Export Tab
        export_frame = ttk.Frame(batch_notebook)
        batch_notebook.add(export_frame, text="📤 Batch Export")
        self.setup_batch_export_tab(export_frame)
    
    def setup_batch_extraction_tab(self, parent):
        """Set up batch metadata extraction interface."""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Source selection
        source_frame = ttk.LabelFrame(main_frame, text="Source Selection", padding="10")
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Multiple directory selection
        ttk.Label(source_frame, text="Selected Directories:").pack(anchor=tk.W)
        
        # Listbox for selected directories
        self.batch_dirs_frame = ttk.Frame(source_frame)
        self.batch_dirs_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.batch_dirs_listbox = tk.Listbox(self.batch_dirs_frame, height=4)
        self.batch_dirs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        dirs_scrollbar = ttk.Scrollbar(self.batch_dirs_frame, orient=tk.VERTICAL, command=self.batch_dirs_listbox.yview)
        dirs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_dirs_listbox.config(yscrollcommand=dirs_scrollbar.set)
        
        # Directory control buttons
        dirs_buttons_frame = ttk.Frame(source_frame)
        dirs_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(dirs_buttons_frame, text="Add Directory", command=self.add_batch_directory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dirs_buttons_frame, text="Remove Selected", command=self.remove_batch_directory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dirs_buttons_frame, text="Clear All", command=self.clear_batch_directories).pack(side=tk.LEFT)
        
        # Batch processing options
        options_frame = ttk.LabelFrame(main_frame, text="Processing Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File type filters
        filter_frame = ttk.Frame(options_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="File Types:").pack(side=tk.LEFT)
        self.batch_file_types = ttk.Combobox(filter_frame, values=["All Files", "Images Only", "Audio Only", "Video Only", "Documents Only"], state="readonly")
        self.batch_file_types.set("All Files")
        self.batch_file_types.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        # Processing settings
        settings_frame = ttk.Frame(options_frame)
        settings_frame.pack(fill=tk.X)
        
        self.batch_recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Recursive scan", variable=self.batch_recursive).pack(side=tk.LEFT, padx=(0, 20))
        
        self.batch_include_hidden = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Include hidden files", variable=self.batch_include_hidden).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(settings_frame, text="Max files per directory:").pack(side=tk.LEFT, padx=(0, 5))
        self.batch_max_files = tk.IntVar(value=1000)
        ttk.Spinbox(settings_frame, from_=10, to=10000, textvariable=self.batch_max_files, width=8).pack(side=tk.LEFT)
        
        # Output settings
        output_frame = ttk.LabelFrame(main_frame, text="Output Settings", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        output_path_frame = ttk.Frame(output_frame)
        output_path_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_path_frame, text="Output Directory:").pack(side=tk.LEFT)
        self.batch_output_path = tk.StringVar(value=os.path.join(os.getcwd(), "batch_results"))
        ttk.Entry(output_path_frame, textvariable=self.batch_output_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        ttk.Button(output_path_frame, text="Browse", command=self.browse_batch_output).pack(side=tk.LEFT)
        
        format_frame = ttk.Frame(output_frame)
        format_frame.pack(fill=tk.X)
        
        ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT)
        self.batch_output_format = ttk.Combobox(format_frame, values=["JSON", "CSV", "XML", "HTML"], state="readonly")
        self.batch_output_format.set("JSON")
        self.batch_output_format.pack(side=tk.LEFT, padx=(10, 20))
        
        self.batch_separate_files = tk.BooleanVar(value=False)
        ttk.Checkbutton(format_frame, text="Separate file per directory", variable=self.batch_separate_files).pack(side=tk.LEFT)
        
        # Progress and control
        control_frame = ttk.LabelFrame(main_frame, text="Batch Processing Control", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self.batch_progress = ttk.Progressbar(control_frame, mode='determinate')
        self.batch_progress.pack(fill=tk.X, pady=(0, 10))
        
        # Status label
        self.batch_status = ttk.Label(control_frame, text="Ready to start batch processing")
        self.batch_status.pack(anchor=tk.W, pady=(0, 10))
        
        # Control buttons
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X)
        
        self.batch_start_btn = ttk.Button(buttons_frame, text="Start Batch Processing", command=self.start_batch_processing)
        self.batch_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.batch_stop_btn = ttk.Button(buttons_frame, text="Stop Processing", command=self.stop_batch_processing, state=tk.DISABLED)
        self.batch_stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Open Output Folder", command=self.open_batch_output_folder).pack(side=tk.LEFT)
        
        # Results summary
        summary_frame = ttk.LabelFrame(main_frame, text="Processing Summary", padding="10")
        summary_frame.pack(fill=tk.BOTH, expand=True)
        
        self.batch_summary = scrolledtext.ScrolledText(summary_frame, height=6, wrap=tk.WORD)
        self.batch_summary.pack(fill=tk.BOTH, expand=True)
        
        # Initialize batch processing variables
        self.batch_processing = False
        self.batch_stop_requested = False
        self.batch_directories = []
    
    def setup_batch_operations_tab(self, parent):
        """Set up batch file operations interface."""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File operations
        ops_frame = ttk.LabelFrame(main_frame, text="File Operations", padding="10")
        ops_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Operation selection
        op_frame = ttk.Frame(ops_frame)
        op_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(op_frame, text="Operation:").pack(side=tk.LEFT)
        self.batch_operation = ttk.Combobox(op_frame, values=[
            "Copy files with metadata", 
            "Move files with metadata", 
            "Rename files based on metadata", 
            "Organize by date", 
            "Organize by file type",
            "Remove duplicate files",
            "Generate file reports"
        ], state="readonly")
        self.batch_operation.set("Copy files with metadata")
        self.batch_operation.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        # Source and destination
        paths_frame = ttk.Frame(ops_frame)
        paths_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Source
        src_frame = ttk.Frame(paths_frame)
        src_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(src_frame, text="Source:").pack(side=tk.LEFT, anchor=tk.W, padx=(0, 10))
        self.ops_source_path = tk.StringVar()
        ttk.Entry(src_frame, textvariable=self.ops_source_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(src_frame, text="Browse", command=self.browse_ops_source).pack(side=tk.LEFT)
        
        # Destination
        dst_frame = ttk.Frame(paths_frame)
        dst_frame.pack(fill=tk.X)
        ttk.Label(dst_frame, text="Destination:").pack(side=tk.LEFT, anchor=tk.W, padx=(0, 10))
        self.ops_dest_path = tk.StringVar()
        ttk.Entry(dst_frame, textvariable=self.ops_dest_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(dst_frame, text="Browse", command=self.browse_ops_dest).pack(side=tk.LEFT)
        
        # Operation options
        options_frame = ttk.LabelFrame(main_frame, text="Operation Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.ops_preserve_structure = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Preserve directory structure", variable=self.ops_preserve_structure).pack(anchor=tk.W)
        
        self.ops_overwrite = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Overwrite existing files", variable=self.ops_overwrite).pack(anchor=tk.W)
        
        self.ops_create_log = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Create operation log", variable=self.ops_create_log).pack(anchor=tk.W)
        
        # Execute button
        ttk.Button(options_frame, text="Execute Operation", command=self.execute_batch_operation).pack(pady=(10, 0))
        
        # Results
        results_frame = ttk.LabelFrame(main_frame, text="Operation Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.ops_results = scrolledtext.ScrolledText(results_frame, height=8, wrap=tk.WORD)
        self.ops_results.pack(fill=tk.BOTH, expand=True)
    
    def setup_batch_export_tab(self, parent):
        """Set up batch export interface."""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Export templates
        template_frame = ttk.LabelFrame(main_frame, text="Export Templates", padding="10")
        template_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(template_frame, text="Template:").pack(side=tk.LEFT)
        self.export_template = ttk.Combobox(template_frame, values=[
            "Complete Metadata Report",
            "Image Gallery with EXIF",
            "Audio Library Report",
            "Video Catalog",
            "Document Index",
            "Custom Template"
        ], state="readonly")
        self.export_template.set("Complete Metadata Report")
        self.export_template.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        # Export options
        export_options_frame = ttk.LabelFrame(main_frame, text="Export Options", padding="10")
        export_options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Format selection
        format_frame = ttk.Frame(export_options_frame)
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(format_frame, text="Export Format:").pack(side=tk.LEFT)
        self.export_format = ttk.Combobox(format_frame, values=["HTML Report", "PDF Report", "Excel Spreadsheet", "CSV Data", "JSON Data"], state="readonly")
        self.export_format.set("HTML Report")
        self.export_format.pack(side=tk.LEFT, padx=(10, 0))
        
        # Include options
        include_frame = ttk.Frame(export_options_frame)
        include_frame.pack(fill=tk.X)
        
        self.export_include_thumbnails = tk.BooleanVar(value=True)
        ttk.Checkbutton(include_frame, text="Include thumbnails", variable=self.export_include_thumbnails).pack(side=tk.LEFT, padx=(0, 20))
        
        self.export_include_stats = tk.BooleanVar(value=True)
        ttk.Checkbutton(include_frame, text="Include statistics", variable=self.export_include_stats).pack(side=tk.LEFT, padx=(0, 20))
        
        self.export_include_charts = tk.BooleanVar(value=False)
        ttk.Checkbutton(include_frame, text="Include charts", variable=self.export_include_charts).pack(side=tk.LEFT)
        
        # Custom fields
        fields_frame = ttk.LabelFrame(main_frame, text="Custom Fields", padding="10")
        fields_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(fields_frame, text="Additional metadata fields (comma-separated):").pack(anchor=tk.W)
        self.export_custom_fields = tk.Text(fields_frame, height=3, wrap=tk.WORD)
        self.export_custom_fields.pack(fill=tk.X, pady=(5, 0))
        
        # Export button
        ttk.Button(fields_frame, text="Generate Export", command=self.generate_batch_export).pack(pady=(10, 0))
        
    def setup_settings_tab(self):
        """Set up the settings tab."""
        main_frame = ttk.Frame(self.settings_tab, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Application Settings", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 20))
        
        # Create scrollable frame for settings
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # General Settings
        general_frame = ttk.LabelFrame(scrollable_frame, text="General Settings", padding="10")
        general_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Theme settings
        theme_frame = ttk.Frame(general_frame)
        theme_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT)
        self.theme_var = tk.StringVar(value="Light")
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=["Light", "Dark", "Auto"], state="readonly")
        theme_combo.pack(side=tk.LEFT, padx=(10, 0))
        theme_combo.bind('<<ComboboxSelected>>', self.on_theme_change)
        
        ttk.Checkbutton(theme_frame, text="Enable dark mode", variable=self.dark_mode, command=self.toggle_dark_mode).pack(side=tk.LEFT, padx=(20, 0))
        
        # Language settings
        lang_frame = ttk.Frame(general_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(lang_frame, text="Language:").pack(side=tk.LEFT)
        self.language_var = tk.StringVar(value="English")
        ttk.Combobox(lang_frame, textvariable=self.language_var, values=["English", "French", "Spanish", "German"], state="readonly").pack(side=tk.LEFT, padx=(10, 0))
        
        # Auto-save settings
        self.auto_save_settings = tk.BooleanVar(value=True)
        ttk.Checkbutton(general_frame, text="Auto-save settings on exit", variable=self.auto_save_settings).pack(anchor=tk.W, pady=(0, 5))
        
        self.remember_window_size = tk.BooleanVar(value=True)
        ttk.Checkbutton(general_frame, text="Remember window size and position", variable=self.remember_window_size).pack(anchor=tk.W, pady=(0, 5))
        
        self.show_tooltips = tk.BooleanVar(value=True)
        ttk.Checkbutton(general_frame, text="Show tooltips", variable=self.show_tooltips).pack(anchor=tk.W)
        
        # Performance Settings
        performance_frame = ttk.LabelFrame(scrollable_frame, text="Performance Settings", padding="10")
        performance_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Threading settings
        thread_frame = ttk.Frame(performance_frame)
        thread_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(thread_frame, text="Max worker threads:").pack(side=tk.LEFT)
        self.max_workers = tk.IntVar(value=4)
        ttk.Spinbox(thread_frame, from_=1, to=16, textvariable=self.max_workers, width=5).pack(side=tk.LEFT, padx=(10, 0))
        
        # Cache settings
        cache_frame = ttk.Frame(performance_frame)
        cache_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(cache_frame, text="Cache size (MB):").pack(side=tk.LEFT)
        self.cache_size = tk.IntVar(value=100)
        ttk.Spinbox(cache_frame, from_=10, to=1000, textvariable=self.cache_size, width=8).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Checkbutton(performance_frame, text="Enable metadata caching", variable=self.cache_enabled).pack(anchor=tk.W, pady=(0, 5))
        ttk.Checkbutton(performance_frame, text="Enable parallel processing", variable=self.parallel_processing).pack(anchor=tk.W, pady=(0, 5))
        
        # Memory management
        memory_frame = ttk.Frame(performance_frame)
        memory_frame.pack(fill=tk.X)
        
        ttk.Label(memory_frame, text="Memory limit (MB):").pack(side=tk.LEFT)
        self.memory_limit = tk.IntVar(value=512)
        ttk.Spinbox(memory_frame, from_=128, to=4096, textvariable=self.memory_limit, width=8).pack(side=tk.LEFT, padx=(10, 0))
        
        # Scanning Settings
        scanning_frame = ttk.LabelFrame(scrollable_frame, text="Scanning Settings", padding="10")
        scanning_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Default scan options
        ttk.Checkbutton(scanning_frame, text="Recursive scan by default", variable=self.scan_recursive).pack(anchor=tk.W, pady=(0, 5))
        ttk.Checkbutton(scanning_frame, text="Show hidden files by default", variable=self.show_hidden).pack(anchor=tk.W, pady=(0, 5))
        ttk.Checkbutton(scanning_frame, text="Auto-refresh results", variable=self.auto_refresh).pack(anchor=tk.W, pady=(0, 10))
        
        # File limits
        limits_frame = ttk.Frame(scanning_frame)
        limits_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(limits_frame, text="Default max files:").pack(side=tk.LEFT)
        ttk.Spinbox(limits_frame, from_=10, to=10000, textvariable=self.max_files, width=8).pack(side=tk.LEFT, padx=(10, 0))
        
        # File type associations
        types_frame = ttk.Frame(scanning_frame)
        types_frame.pack(fill=tk.X)
        
        ttk.Label(types_frame, text="Default file types:").pack(side=tk.LEFT)
        ttk.Combobox(types_frame, textvariable=self.selected_formats, values=["all", "images", "audio", "video", "documents"], state="readonly").pack(side=tk.LEFT, padx=(10, 0))
        
        # Output Settings
        output_settings_frame = ttk.LabelFrame(scrollable_frame, text="Output Settings", padding="10")
        output_settings_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Default output format
        format_frame = ttk.Frame(output_settings_frame)
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(format_frame, text="Default output format:").pack(side=tk.LEFT)
        ttk.Combobox(format_frame, textvariable=self.output_format, values=["json", "csv", "xml", "html"], state="readonly").pack(side=tk.LEFT, padx=(10, 0))
        
        # Output directory
        output_dir_frame = ttk.Frame(output_settings_frame)
        output_dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_dir_frame, text="Default output directory:").pack(side=tk.LEFT)
        self.default_output_dir = tk.StringVar(value=os.path.join(os.getcwd(), "output"))
        ttk.Entry(output_dir_frame, textvariable=self.default_output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        ttk.Button(output_dir_frame, text="Browse", command=self.browse_default_output_dir).pack(side=tk.LEFT)
        
        # Export options
        self.auto_open_results = tk.BooleanVar(value=False)
        ttk.Checkbutton(output_settings_frame, text="Auto-open results after export", variable=self.auto_open_results).pack(anchor=tk.W, pady=(0, 5))
        
        self.create_backup = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_settings_frame, text="Create backup of existing files", variable=self.create_backup).pack(anchor=tk.W)
        
        # Logging Settings
        logging_frame = ttk.LabelFrame(scrollable_frame, text="Logging Settings", padding="10")
        logging_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Log level
        log_level_frame = ttk.Frame(logging_frame)
        log_level_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(log_level_frame, text="Log level:").pack(side=tk.LEFT)
        self.log_level = tk.StringVar(value="INFO")
        ttk.Combobox(log_level_frame, textvariable=self.log_level, values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly").pack(side=tk.LEFT, padx=(10, 0))
        
        # Log file settings
        log_file_frame = ttk.Frame(logging_frame)
        log_file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(log_file_frame, text="Log file:").pack(side=tk.LEFT)
        self.log_file_path = tk.StringVar(value="metacli_gui.log")
        ttk.Entry(log_file_frame, textvariable=self.log_file_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        ttk.Button(log_file_frame, text="Browse", command=self.browse_log_file).pack(side=tk.LEFT)
        
        # Log options
        self.enable_file_logging = tk.BooleanVar(value=True)
        ttk.Checkbutton(logging_frame, text="Enable file logging", variable=self.enable_file_logging).pack(anchor=tk.W, pady=(0, 5))
        
        self.enable_console_logging = tk.BooleanVar(value=False)
        ttk.Checkbutton(logging_frame, text="Enable console logging", variable=self.enable_console_logging).pack(anchor=tk.W, pady=(0, 5))
        
        # Log rotation
        rotation_frame = ttk.Frame(logging_frame)
        rotation_frame.pack(fill=tk.X)
        
        ttk.Label(rotation_frame, text="Max log file size (MB):").pack(side=tk.LEFT)
        self.max_log_size = tk.IntVar(value=10)
        ttk.Spinbox(rotation_frame, from_=1, to=100, textvariable=self.max_log_size, width=5).pack(side=tk.LEFT, padx=(10, 20))
        
        ttk.Label(rotation_frame, text="Keep log files:").pack(side=tk.LEFT)
        self.keep_log_files = tk.IntVar(value=5)
        ttk.Spinbox(rotation_frame, from_=1, to=20, textvariable=self.keep_log_files, width=5).pack(side=tk.LEFT, padx=(10, 0))
        
        # Advanced Settings
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="Advanced Settings", padding="10")
        advanced_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Debug options
        self.debug_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="Enable debug mode", variable=self.debug_mode).pack(anchor=tk.W, pady=(0, 5))
        
        self.verbose_output = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="Verbose output", variable=self.verbose_output).pack(anchor=tk.W, pady=(0, 5))
        
        self.experimental_features = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="Enable experimental features", variable=self.experimental_features).pack(anchor=tk.W, pady=(0, 10))
        
        # Plugin settings
        plugin_frame = ttk.Frame(advanced_frame)
        plugin_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(plugin_frame, text="Plugin directory:").pack(side=tk.LEFT)
        self.plugin_dir = tk.StringVar(value=os.path.join(os.getcwd(), "plugins"))
        ttk.Entry(plugin_frame, textvariable=self.plugin_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        ttk.Button(plugin_frame, text="Browse", command=self.browse_plugin_dir).pack(side=tk.LEFT)
        
        # Reset and apply buttons
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0), padx=(0, 20))
        
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_settings_to_defaults).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Apply Settings", command=self.apply_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Export Settings", command=self.export_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Import Settings", command=self.import_settings).pack(side=tk.LEFT)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def setup_status_bar(self):
        """Set up the status bar at the bottom."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        
        self.status_text = ttk.Label(self.status_bar, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.version_label = ttk.Label(self.status_bar, text="MetaCLI v2.0", relief=tk.SUNKEN)
        self.version_label.pack(side=tk.RIGHT)
        
    # Event handlers and utility methods
    def set_path(self, path):
        """Set the current path."""
        self.current_path.set(str(path))
        
    def browse_directory(self):
        """Browse for a directory."""
        directory = filedialog.askdirectory(title="Select Directory to Scan")
        if directory:
            self.current_path.set(directory)
            
    def open_file(self):
        """Open a single file."""
        file_path = filedialog.askopenfilename(title="Select File to Analyze")
        if file_path:
            self.current_path.set(file_path)
            
    def browse_metadata_file(self):
        """Browse for a file to analyze metadata."""
        file_path = filedialog.askopenfilename(title="Select File for Metadata Analysis")
        if file_path:
            self.metadata_file_var.set(file_path)
            
    def scan_directory(self):
        """Start directory scanning in a separate thread."""
        if not self.current_path.get():
            messagebox.showwarning("Warning", "Please select a path to scan.")
            return
            
        if self.processing:
            messagebox.showinfo("Info", "Scan already in progress.")
            return
            
        # Start scanning in background thread
        self.processing = True
        self.progress.start()
        self.status_label.config(text="Scanning...", foreground='#f39c12')
        
        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()
        
    def _scan_worker(self):
        """Worker thread for scanning."""
        try:
            path = Path(self.current_path.get())
            
            if path.is_file():
                # Single file analysis
                results = [self._analyze_single_file(path)]
            else:
                # Directory scanning
                file_types = None if self.selected_formats.get() == "all" else [self.selected_formats.get()]
                results = self.scanner.find_files_list(
                    str(path),
                    recursive=self.scan_recursive.get(),
                    file_types=file_types,
                    max_files=self.max_files.get()
                )
                
            # Update UI in main thread
            self.root.after(0, self._update_results, results)
            
        except Exception as e:
            self.root.after(0, self._handle_scan_error, str(e))
        finally:
            self.root.after(0, self._scan_complete)
            
    def _analyze_single_file(self, file_path):
        """Analyze a single file."""
        try:
            metadata = self.extractor.extract_metadata(str(file_path))
            return {
                'path': str(file_path),
                'metadata': metadata,
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime) if file_path.exists() else None
            }
        except Exception as e:
            return {
                'path': str(file_path),
                'error': str(e),
                'size': 0,
                'modified': None
            }
            
    def _update_results(self, results):
        """Update the results tree with scan results."""
        # Clear existing results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        self.scan_results = results
        total_size = 0
        file_types = set()
        
        for result in results:
            if isinstance(result, dict) and 'path' in result:
                path = result['path']
                size = result.get('size', 0)
                modified = result.get('modified')
                
                # Extract file info
                file_path = Path(path)
                extension = file_path.suffix.lower()
                file_type = self._get_file_type(extension)
                
                # Format values
                size_str = self._format_size(size)
                modified_str = modified.strftime('%Y-%m-%d %H:%M') if modified else 'Unknown'
                
                # Insert into tree
                self.results_tree.insert('', 'end', text=path, values=(
                    size_str, file_type, modified_str, extension
                ))
                
                total_size += size
                if extension:
                    file_types.add(extension)
            else:
                # Handle string results from scanner
                file_path = Path(result)
                if file_path.exists():
                    stat = file_path.stat()
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    extension = file_path.suffix.lower()
                    file_type = self._get_file_type(extension)
                    
                    size_str = self._format_size(size)
                    modified_str = modified.strftime('%Y-%m-%d %H:%M')
                    
                    self.results_tree.insert('', 'end', text=str(file_path), values=(
                        size_str, file_type, modified_str, extension
                    ))
                    
                    total_size += size
                    if extension:
                        file_types.add(extension)
                        
        # Update statistics
        self.stats_label.config(
            text=f"Files: {len(results)} | Total Size: {self._format_size(total_size)} | Types: {len(file_types)}"
        )
        
    def _handle_scan_error(self, error_msg):
        """Handle scan errors."""
        messagebox.showerror("Scan Error", f"An error occurred during scanning:\n{error_msg}")
        self.status_label.config(text="Scan failed", foreground='#e74c3c')
        
    def _scan_complete(self):
        """Complete the scanning process."""
        self.processing = False
        self.progress.stop()
        self.status_label.config(text="Scan completed", foreground='#27ae60')
        
    def _get_file_type(self, extension):
        """Get file type from extension."""
        type_map = {
            '.jpg': 'Image', '.jpeg': 'Image', '.png': 'Image', '.gif': 'Image', '.bmp': 'Image',
            '.pdf': 'Document', '.doc': 'Document', '.docx': 'Document', '.txt': 'Document',
            '.mp3': 'Audio', '.wav': 'Audio', '.flac': 'Audio', '.aac': 'Audio',
            '.mp4': 'Video', '.avi': 'Video', '.mkv': 'Video', '.mov': 'Video',
            '.zip': 'Archive', '.rar': 'Archive', '.7z': 'Archive', '.tar': 'Archive',
            '.py': 'Code', '.js': 'Code', '.html': 'Code', '.css': 'Code', '.cpp': 'Code'
        }
        return type_map.get(extension, 'Unknown')
        
    def _format_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
        
    def on_tree_double_click(self, event):
        """Handle double-click on tree item."""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            file_path = item['text']
            self.metadata_file_var.set(file_path)
            self.notebook.select(1)  # Switch to metadata tab
            self.analyze_metadata()
            
    def analyze_metadata(self):
        """Analyze metadata for the selected file."""
        file_path = self.metadata_file_var.get()
        if not file_path:
            messagebox.showwarning("Warning", "Please select a file to analyze.")
            return
            
        try:
            metadata = self.extractor.extract_metadata(file_path)
            
            # Update raw metadata view
            self.metadata_text.delete(1.0, tk.END)
            formatted_metadata = json.dumps(metadata, indent=2, default=str)
            self.metadata_text.insert(1.0, formatted_metadata)
            
            # Update formatted tree view
            for item in self.formatted_tree.get_children():
                self.formatted_tree.delete(item)
                
            self._populate_metadata_tree('', metadata)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze metadata:\n{str(e)}")
            
    def _populate_metadata_tree(self, parent, data, prefix=''):
        """Populate the metadata tree recursively."""
        if isinstance(data, dict):
            for key, value in data.items():
                node_id = self.formatted_tree.insert(parent, 'end', text=key, values=(''))
                self._populate_metadata_tree(node_id, value, f"{prefix}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                node_id = self.formatted_tree.insert(parent, 'end', text=f"[{i}]", values=(''))
                self._populate_metadata_tree(node_id, item, f"{prefix}[{i}]")
        else:
            # Leaf node
            if parent:
                self.formatted_tree.set(parent, 'Value', str(data))
                
    # Placeholder methods for menu actions
    def export_results(self): pass
    def save_report(self): pass
    def copy_results(self): pass
    def select_all(self): pass
    def show_find_dialog(self): pass
    def show_filter_dialog(self): pass
    def batch_process(self): pass
    def compare_files(self): pass
    def generate_report(self): pass
    def show_settings(self): pass
    def clear_cache(self): pass
    def refresh_view(self): pass
    def expand_all(self): pass
    def collapse_all(self): pass
    def show_help(self):
        """Show help dialog with keyboard shortcuts."""
        help_text = """
MetaCLI v3.0 - Keyboard Shortcuts

File Operations:
  Ctrl+O    - Open file
  Ctrl+D    - Browse directory
  Ctrl+S    - Save results
  Ctrl+R    - Start scan
  Ctrl+Q    - Quit application

View Operations:
  F5        - Refresh current view
  F11       - Toggle fullscreen

Font Size:
  Ctrl++    - Increase font size
  Ctrl+-    - Decrease font size

Navigation:
  Ctrl+1    - File Scanner tab
  Ctrl+2    - Metadata Viewer tab
  Ctrl+3    - Batch Operations tab
  Ctrl+4    - Settings tab

Other:
  Ctrl+Del  - Clear results
  F1        - Show this help
"""
        messagebox.showinfo("Keyboard Shortcuts", help_text)
    def show_shortcuts(self): pass
    def show_cli_help(self): pass
    def check_updates(self): pass
    def show_about(self): pass
    def show_context_menu(self, event): pass
    def view_selected_metadata(self): pass
    def clear_results(self):
        """Clear all results and reset the interface."""
        self.scan_results = []
        self.current_metadata = {}
        
        # Clear the results tree
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Clear metadata displays
        self.metadata_text.delete(1.0, tk.END)
        for item in self.formatted_tree.get_children():
            self.formatted_tree.delete(item)
        
        # Update status
        self.stats_label.config(text="Files: 0 | Total Size: 0 B | Types: 0")
        self.status_label.config(text="Results cleared", foreground='#27ae60')
    
    def save_results(self):
        """Save current results to file."""
        if not self.scan_results:
            messagebox.showwarning("No Results", "No scan results to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    # Save as CSV
                    import csv
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        if self.scan_results:
                            writer = csv.DictWriter(f, fieldnames=self.scan_results[0].keys())
                            writer.writeheader()
                            writer.writerows(self.scan_results)
                else:
                    # Save as JSON
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.scan_results, f, indent=2, ensure_ascii=False, default=str)
                
                self.status_label.config(text=f"Results saved to {file_path}", foreground='#27ae60')
                messagebox.showinfo("Success", f"Results saved successfully to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save results: {str(e)}")
    
    def refresh_current_view(self):
        """Refresh the current view/tab."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Scanner tab
            if self.current_path.get() and Path(self.current_path.get()).exists():
                self.scan_directory()
        elif current_tab == 1:  # Metadata tab
            if self.metadata_file_var.get():
                self.analyze_metadata()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        try:
            current_state = self.root.attributes('-fullscreen')
            self.root.attributes('-fullscreen', not current_state)
        except:
            # Fallback for systems that don't support fullscreen
            if self.root.state() == 'zoomed':
                self.root.state('normal')
            else:
                self.root.state('zoomed')
    
    def increase_font_size(self):
        """Increase application font size."""
        self._adjust_font_size(1)
    
    def decrease_font_size(self):
        """Decrease application font size."""
        self._adjust_font_size(-1)
    
    def _adjust_font_size(self, delta):
        """Adjust font size by delta amount."""
        try:
            style = ttk.Style()
            # Get current font from a label
            current_font = style.lookup('TLabel', 'font')
            if current_font:
                if isinstance(current_font, tuple) and len(current_font) >= 2:
                    font_family, font_size = current_font[0], int(current_font[1])
                else:
                    font_family, font_size = 'Segoe UI', 9
                    
                new_size = max(8, min(20, font_size + delta))
                
                # Update various style fonts
                style.configure('TLabel', font=(font_family, new_size))
                style.configure('TButton', font=(font_family, new_size))
                style.configure('Treeview', font=(font_family, new_size))
                
                self.status_label.config(text=f"Font size: {new_size}", foreground='#3498db')
        except Exception:
            pass  # Fail silently if font adjustment fails
    
    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        self.dark_mode.set(not self.dark_mode.get())
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the current theme (light/dark mode)."""
        style = ttk.Style()
        
        if self.dark_mode.get():
            # Dark mode colors
            bg_color = '#2c3e50'
            fg_color = '#ecf0f1'
            select_bg = '#34495e'
            select_fg = '#ffffff'
            
            self.root.configure(bg=bg_color)
            
            style.configure('TLabel', background=bg_color, foreground=fg_color)
            style.configure('TFrame', background=bg_color)
            style.configure('TNotebook', background=bg_color)
            style.configure('TNotebook.Tab', background=select_bg, foreground=fg_color)
            
        else:
            # Light mode colors
            bg_color = '#ecf0f1'
            fg_color = '#2c3e50'
            select_bg = '#bdc3c7'
            select_fg = '#2c3e50'
            
            self.root.configure(bg=bg_color)
            
            style.configure('TLabel', background=bg_color, foreground=fg_color)
            style.configure('TFrame', background=bg_color)
            style.configure('TNotebook', background=bg_color)
            style.configure('TNotebook.Tab', background=select_bg, foreground=fg_color)
    
    # Batch Operations Methods
    def add_batch_directory(self):
        """Add a directory to the batch processing list."""
        directory = filedialog.askdirectory(title="Select Directory for Batch Processing")
        if directory and directory not in self.batch_directories:
            self.batch_directories.append(directory)
            self.batch_dirs_listbox.insert(tk.END, directory)
            self.batch_status.config(text=f"Added directory: {os.path.basename(directory)}")
    
    def remove_batch_directory(self):
        """Remove selected directory from batch processing list."""
        selection = self.batch_dirs_listbox.curselection()
        if selection:
            index = selection[0]
            directory = self.batch_directories.pop(index)
            self.batch_dirs_listbox.delete(index)
            self.batch_status.config(text=f"Removed directory: {os.path.basename(directory)}")
    
    def clear_batch_directories(self):
        """Clear all directories from batch processing list."""
        self.batch_directories.clear()
        self.batch_dirs_listbox.delete(0, tk.END)
        self.batch_status.config(text="Cleared all directories")
    
    def browse_batch_output(self):
        """Browse for batch output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.batch_output_path.set(directory)
    
    def start_batch_processing(self):
        """Start batch metadata extraction."""
        if not self.batch_directories:
            messagebox.showwarning("No Directories", "Please add at least one directory for batch processing.")
            return
        
        if self.batch_processing:
            messagebox.showinfo("Already Processing", "Batch processing is already in progress.")
            return
        
        # Prepare output directory
        output_dir = self.batch_output_path.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output directory: {e}")
                return
        
        # Start processing in a separate thread
        self.batch_processing = True
        self.batch_stop_requested = False
        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_stop_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=self._batch_processing_worker, daemon=True).start()
    
    def stop_batch_processing(self):
        """Stop batch processing."""
        self.batch_stop_requested = True
        self.batch_status.config(text="Stopping batch processing...")
    
    def _batch_processing_worker(self):
        """Worker thread for batch processing."""
        try:
            total_dirs = len(self.batch_directories)
            processed_dirs = 0
            total_files = 0
            
            self.batch_summary.delete(1.0, tk.END)
            self.batch_summary.insert(tk.END, f"Starting batch processing of {total_dirs} directories...\n\n")
            
            for i, directory in enumerate(self.batch_directories):
                if self.batch_stop_requested:
                    break
                
                self.root.after(0, lambda d=directory: self.batch_status.config(text=f"Processing: {os.path.basename(d)}"))
                
                try:
                    # Scan directory
                    files = self.scanner.scan_directory(
                        directory,
                        recursive=self.batch_recursive.get(),
                        max_files=self.batch_max_files.get(),
                        include_hidden=self.batch_include_hidden.get()
                    )
                    
                    # Filter by file type if specified
                    file_type = self.batch_file_types.get()
                    if file_type != "All Files":
                        files = self._filter_files_by_type(files, file_type)
                    
                    # Extract metadata
                    metadata_results = []
                    for file_path in files:
                        if self.batch_stop_requested:
                            break
                        
                        try:
                            metadata = self.extractor.extract_metadata(file_path)
                            metadata_results.append({
                                'file_path': file_path,
                                'metadata': metadata
                            })
                        except Exception as e:
                            self.logger.error(f"Error extracting metadata from {file_path}: {e}")
                    
                    # Save results
                    if metadata_results:
                        output_file = self._save_batch_results(directory, metadata_results)
                        total_files += len(metadata_results)
                        
                        self.root.after(0, lambda: self.batch_summary.insert(tk.END, 
                            f"✓ {os.path.basename(directory)}: {len(metadata_results)} files processed\n"))
                    
                except Exception as e:
                    self.root.after(0, lambda d=directory, err=str(e): self.batch_summary.insert(tk.END, 
                        f"✗ {os.path.basename(d)}: Error - {err}\n"))
                
                processed_dirs += 1
                progress = (processed_dirs / total_dirs) * 100
                self.root.after(0, lambda p=progress: self.batch_progress.config(value=p))
            
            # Complete
            if self.batch_stop_requested:
                self.root.after(0, lambda: self.batch_status.config(text="Batch processing stopped by user"))
                self.root.after(0, lambda: self.batch_summary.insert(tk.END, "\nBatch processing stopped by user.\n"))
            else:
                self.root.after(0, lambda: self.batch_status.config(text=f"Completed: {processed_dirs} directories, {total_files} files"))
                self.root.after(0, lambda: self.batch_summary.insert(tk.END, f"\nBatch processing completed successfully!\nProcessed {processed_dirs} directories and {total_files} files.\n"))
            
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.batch_status.config(text=f"Error: {err}"))
            self.root.after(0, lambda err=str(e): self.batch_summary.insert(tk.END, f"\nError during batch processing: {err}\n"))
        
        finally:
            self.batch_processing = False
            self.root.after(0, lambda: self.batch_start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.batch_stop_btn.config(state=tk.DISABLED))
    
    def _filter_files_by_type(self, files, file_type):
        """Filter files by type."""
        if file_type == "Images Only":
            extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        elif file_type == "Audio Only":
            extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        elif file_type == "Video Only":
            extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        elif file_type == "Documents Only":
            extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}
        else:
            return files
        
        return [f for f in files if Path(f).suffix.lower() in extensions]
    
    def _save_batch_results(self, directory, results):
        """Save batch processing results."""
        output_dir = self.batch_output_path.get()
        format_type = self.batch_output_format.get().lower()
        
        if self.batch_separate_files.get():
            # Separate file per directory
            dir_name = os.path.basename(directory)
            output_file = os.path.join(output_dir, f"{dir_name}_metadata.{format_type}")
        else:
            # Single combined file
            output_file = os.path.join(output_dir, f"batch_metadata.{format_type}")
        
        # Format and save data
        if format_type == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
        elif format_type == 'csv':
            # Flatten metadata for CSV
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if results:
                    fieldnames = ['file_path'] + list(results[0]['metadata'].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for result in results:
                        row = {'file_path': result['file_path']}
                        row.update(result['metadata'])
                        writer.writerow(row)
        
        return output_file
    
    def open_batch_output_folder(self):
        """Open the batch output folder."""
        output_dir = self.batch_output_path.get()
        if os.path.exists(output_dir):
            if sys.platform == "win32":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", output_dir])
            else:
                subprocess.run(["xdg-open", output_dir])
        else:
            messagebox.showwarning("Directory Not Found", "Output directory does not exist.")
    
    # Batch File Operations Methods
    def browse_ops_source(self):
        """Browse for operations source directory."""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.ops_source_path.set(directory)
    
    def browse_ops_dest(self):
        """Browse for operations destination directory."""
        directory = filedialog.askdirectory(title="Select Destination Directory")
        if directory:
            self.ops_dest_path.set(directory)
    
    def execute_batch_operation(self):
        """Execute the selected batch operation."""
        operation = self.batch_operation.get()
        source = self.ops_source_path.get()
        destination = self.ops_dest_path.get()
        
        if not source or not os.path.exists(source):
            messagebox.showerror("Error", "Please select a valid source directory.")
            return
        
        if not destination:
            messagebox.showerror("Error", "Please select a destination directory.")
            return
        
        self.ops_results.delete(1.0, tk.END)
        self.ops_results.insert(tk.END, f"Starting operation: {operation}\n")
        self.ops_results.insert(tk.END, f"Source: {source}\n")
        self.ops_results.insert(tk.END, f"Destination: {destination}\n\n")
        
        # Execute operation in a separate thread
        threading.Thread(target=self._execute_operation_worker, 
                        args=(operation, source, destination), daemon=True).start()
    
    def _execute_operation_worker(self, operation, source, destination):
        """Worker thread for batch operations."""
        try:
            if operation == "Copy files with metadata":
                self._copy_files_with_metadata(source, destination)
            elif operation == "Move files with metadata":
                self._move_files_with_metadata(source, destination)
            elif operation == "Rename files based on metadata":
                self._rename_files_by_metadata(source)
            elif operation == "Organize by date":
                self._organize_by_date(source, destination)
            elif operation == "Organize by file type":
                self._organize_by_type(source, destination)
            elif operation == "Remove duplicate files":
                self._remove_duplicates(source)
            elif operation == "Generate file reports":
                self._generate_file_reports(source, destination)
            
            self.root.after(0, lambda: self.ops_results.insert(tk.END, "\nOperation completed successfully!\n"))
            
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.ops_results.insert(tk.END, f"\nError: {err}\n"))
    
    def _copy_files_with_metadata(self, source, destination):
        """Copy files and their metadata."""
        import shutil
        
        files = self.scanner.scan_directory(source, recursive=True)
        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, source)
                dest_path = os.path.join(destination, rel_path)
                
                # Create destination directory
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Copy file
                if not os.path.exists(dest_path) or self.ops_overwrite.get():
                    shutil.copy2(file_path, dest_path)
                    
                    # Extract and save metadata
                    metadata = self.extractor.extract_metadata(file_path)
                    metadata_file = dest_path + '.metadata.json'
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2, default=str)
                    
                    self.root.after(0, lambda f=file_path: self.ops_results.insert(tk.END, f"Copied: {os.path.basename(f)}\n"))
                
            except Exception as e:
                self.root.after(0, lambda f=file_path, err=str(e): self.ops_results.insert(tk.END, f"Error copying {os.path.basename(f)}: {err}\n"))
    
    def _organize_by_date(self, source, destination):
        """Organize files by creation date."""
        files = self.scanner.scan_directory(source, recursive=True)
        for file_path in files:
            try:
                # Get file creation date
                stat = os.stat(file_path)
                date = datetime.fromtimestamp(stat.st_ctime)
                
                # Create date-based directory structure
                date_dir = os.path.join(destination, str(date.year), f"{date.month:02d}-{date.strftime('%B')}")
                os.makedirs(date_dir, exist_ok=True)
                
                # Move or copy file
                dest_path = os.path.join(date_dir, os.path.basename(file_path))
                if not os.path.exists(dest_path) or self.ops_overwrite.get():
                    if self.ops_preserve_structure.get():
                        import shutil
                        shutil.copy2(file_path, dest_path)
                    else:
                        os.rename(file_path, dest_path)
                    
                    self.root.after(0, lambda f=file_path: self.ops_results.insert(tk.END, f"Organized: {os.path.basename(f)}\n"))
                
            except Exception as e:
                self.root.after(0, lambda f=file_path, err=str(e): self.ops_results.insert(tk.END, f"Error organizing {os.path.basename(f)}: {err}\n"))
    
    def _organize_by_type(self, source, destination):
        """Organize files by type."""
        files = self.scanner.scan_directory(source, recursive=True)
        for file_path in files:
            try:
                ext = Path(file_path).suffix.lower()
                file_type = self._get_file_type(ext)
                
                # Create type-based directory
                type_dir = os.path.join(destination, file_type)
                os.makedirs(type_dir, exist_ok=True)
                
                # Move or copy file
                dest_path = os.path.join(type_dir, os.path.basename(file_path))
                if not os.path.exists(dest_path) or self.ops_overwrite.get():
                    if self.ops_preserve_structure.get():
                        import shutil
                        shutil.copy2(file_path, dest_path)
                    else:
                        os.rename(file_path, dest_path)
                    
                    self.root.after(0, lambda f=file_path: self.ops_results.insert(tk.END, f"Organized: {os.path.basename(f)}\n"))
                
            except Exception as e:
                self.root.after(0, lambda f=file_path, err=str(e): self.ops_results.insert(tk.END, f"Error organizing {os.path.basename(f)}: {err}\n"))
    
    def generate_batch_export(self):
        """Generate batch export based on template."""
        template = self.export_template.get()
        format_type = self.export_format.get()
        
        messagebox.showinfo("Export", f"Generating {template} in {format_type} format...\nThis feature will be implemented in the next update.")
    
    # Settings Methods
    def on_theme_change(self, event=None):
        """Handle theme change."""
        theme = self.theme_var.get()
        if theme == "Dark":
            self.dark_mode.set(True)
        elif theme == "Light":
            self.dark_mode.set(False)
        self.apply_theme()
    
    def browse_default_output_dir(self):
        """Browse for default output directory."""
        directory = filedialog.askdirectory(title="Select Default Output Directory")
        if directory:
            self.default_output_dir.set(directory)
    
    def browse_log_file(self):
        """Browse for log file location."""
        file_path = filedialog.asksaveasfilename(
            title="Select Log File Location",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        if file_path:
            self.log_file_path.set(file_path)
    
    def browse_plugin_dir(self):
        """Browse for plugin directory."""
        directory = filedialog.askdirectory(title="Select Plugin Directory")
        if directory:
            self.plugin_dir.set(directory)
    
    def reset_settings_to_defaults(self):
        """Reset all settings to default values."""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            # Reset all variables to default values
            self.dark_mode.set(False)
            self.theme_var.set("Light")
            self.language_var.set("English")
            self.auto_save_settings.set(True)
            self.remember_window_size.set(True)
            self.show_tooltips.set(True)
            self.max_workers.set(4)
            self.cache_size.set(100)
            self.cache_enabled.set(True)
            self.parallel_processing.set(True)
            self.memory_limit.set(512)
            self.scan_recursive.set(True)
            self.show_hidden.set(False)
            self.auto_refresh.set(False)
            self.max_files.set(500)
            self.selected_formats.set("all")
            self.output_format.set("json")
            self.default_output_dir.set(os.path.join(os.getcwd(), "output"))
            self.auto_open_results.set(False)
            self.create_backup.set(True)
            self.log_level.set("INFO")
            self.log_file_path.set("metacli_gui.log")
            self.enable_file_logging.set(True)
            self.enable_console_logging.set(False)
            self.max_log_size.set(10)
            self.keep_log_files.set(5)
            self.debug_mode.set(False)
            self.verbose_output.set(False)
            self.experimental_features.set(False)
            self.plugin_dir.set(os.path.join(os.getcwd(), "plugins"))
            
            self.apply_theme()
            messagebox.showinfo("Settings Reset", "All settings have been reset to defaults.")
    
    def apply_settings(self):
        """Apply current settings."""
        try:
            # Update extractor settings
            self.extractor = MetadataExtractor(
                enable_cache=self.cache_enabled.get(),
                max_workers=self.max_workers.get()
            )
            
            # Update logger settings
            if hasattr(self, 'logger'):
                self.logger = setup_logger(
                    verbose=self.verbose_output.get(),
                    log_file=self.log_file_path.get()
                )
            
            # Apply theme
            self.apply_theme()
            
            # Save settings
            self.save_user_preferences()
            
            messagebox.showinfo("Settings Applied", "Settings have been applied successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {e}")
    
    def export_settings(self):
        """Export current settings to a file."""
        file_path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                settings = self._get_all_settings()
                with open(file_path, 'w') as f:
                    json.dump(settings, f, indent=2)
                messagebox.showinfo("Export Successful", f"Settings exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export settings: {e}")
    
    def import_settings(self):
        """Import settings from a file."""
        file_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    settings = json.load(f)
                self._apply_imported_settings(settings)
                messagebox.showinfo("Import Successful", "Settings imported successfully.")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import settings: {e}")
    
    def _get_all_settings(self):
        """Get all current settings as a dictionary."""
        return {
            'theme': {
                'dark_mode': self.dark_mode.get(),
                'theme_var': self.theme_var.get(),
                'language': self.language_var.get()
            },
            'general': {
                'auto_save_settings': self.auto_save_settings.get(),
                'remember_window_size': self.remember_window_size.get(),
                'show_tooltips': self.show_tooltips.get()
            },
            'performance': {
                'max_workers': self.max_workers.get(),
                'cache_size': self.cache_size.get(),
                'cache_enabled': self.cache_enabled.get(),
                'parallel_processing': self.parallel_processing.get(),
                'memory_limit': self.memory_limit.get()
            },
            'scanning': {
                'scan_recursive': self.scan_recursive.get(),
                'show_hidden': self.show_hidden.get(),
                'auto_refresh': self.auto_refresh.get(),
                'max_files': self.max_files.get(),
                'selected_formats': self.selected_formats.get()
            },
            'output': {
                'output_format': self.output_format.get(),
                'default_output_dir': self.default_output_dir.get(),
                'auto_open_results': self.auto_open_results.get(),
                'create_backup': self.create_backup.get()
            },
            'logging': {
                'log_level': self.log_level.get(),
                'log_file_path': self.log_file_path.get(),
                'enable_file_logging': self.enable_file_logging.get(),
                'enable_console_logging': self.enable_console_logging.get(),
                'max_log_size': self.max_log_size.get(),
                'keep_log_files': self.keep_log_files.get()
            },
            'advanced': {
                'debug_mode': self.debug_mode.get(),
                'verbose_output': self.verbose_output.get(),
                'experimental_features': self.experimental_features.get(),
                'plugin_dir': self.plugin_dir.get()
            }
        }
    
    def _apply_imported_settings(self, settings):
        """Apply imported settings."""
        try:
            # Theme settings
            if 'theme' in settings:
                theme = settings['theme']
                self.dark_mode.set(theme.get('dark_mode', False))
                self.theme_var.set(theme.get('theme_var', 'Light'))
                self.language_var.set(theme.get('language', 'English'))
            
            # General settings
            if 'general' in settings:
                general = settings['general']
                self.auto_save_settings.set(general.get('auto_save_settings', True))
                self.remember_window_size.set(general.get('remember_window_size', True))
                self.show_tooltips.set(general.get('show_tooltips', True))
            
            # Performance settings
            if 'performance' in settings:
                perf = settings['performance']
                self.max_workers.set(perf.get('max_workers', 4))
                self.cache_size.set(perf.get('cache_size', 100))
                self.cache_enabled.set(perf.get('cache_enabled', True))
                self.parallel_processing.set(perf.get('parallel_processing', True))
                self.memory_limit.set(perf.get('memory_limit', 512))
            
            # Apply other settings similarly...
            self.apply_theme()
            
        except Exception as e:
            raise Exception(f"Error applying imported settings: {e}")
    
    def _move_files_with_metadata(self, source, destination):
        """Move files and their metadata."""
        import shutil
        
        files = self.scanner.scan_directory(source, recursive=True)
        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, source)
                dest_path = os.path.join(destination, rel_path)
                
                # Create destination directory
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Move file
                if not os.path.exists(dest_path) or self.ops_overwrite.get():
                    shutil.move(file_path, dest_path)
                    
                    # Extract and save metadata
                    metadata = self.extractor.extract_metadata(dest_path)
                    metadata_file = dest_path + '.metadata.json'
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2, default=str)
                    
                    self.root.after(0, lambda f=file_path: self.ops_results.insert(tk.END, f"Moved: {os.path.basename(f)}\n"))
                
            except Exception as e:
                self.root.after(0, lambda f=file_path, err=str(e): self.ops_results.insert(tk.END, f"Error moving {os.path.basename(f)}: {err}\n"))
    
    def _rename_files_by_metadata(self, source):
        """Rename files based on their metadata."""
        files = self.scanner.scan_directory(source, recursive=True)
        for file_path in files:
            try:
                metadata = self.extractor.extract_metadata(file_path)
                
                # Generate new name based on metadata
                new_name = self._generate_filename_from_metadata(metadata, file_path)
                if new_name and new_name != os.path.basename(file_path):
                    new_path = os.path.join(os.path.dirname(file_path), new_name)
                    
                    if not os.path.exists(new_path) or self.ops_overwrite.get():
                        os.rename(file_path, new_path)
                        self.root.after(0, lambda old=os.path.basename(file_path), new=new_name: 
                                      self.ops_results.insert(tk.END, f"Renamed: {old} → {new}\n"))
                
            except Exception as e:
                self.root.after(0, lambda f=file_path, err=str(e): self.ops_results.insert(tk.END, f"Error renaming {os.path.basename(f)}: {err}\n"))
    
    def _remove_duplicates(self, source):
        """Remove duplicate files based on hash comparison."""
        import hashlib
        
        files = self.scanner.scan_directory(source, recursive=True)
        file_hashes = {}
        duplicates_removed = 0
        
        for file_path in files:
            try:
                # Calculate file hash
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                if file_hash in file_hashes:
                    # Duplicate found, remove it
                    os.remove(file_path)
                    duplicates_removed += 1
                    self.root.after(0, lambda f=file_path: self.ops_results.insert(tk.END, f"Removed duplicate: {os.path.basename(f)}\n"))
                else:
                    file_hashes[file_hash] = file_path
                
            except Exception as e:
                self.root.after(0, lambda f=file_path, err=str(e): self.ops_results.insert(tk.END, f"Error processing {os.path.basename(f)}: {err}\n"))
        
        self.root.after(0, lambda count=duplicates_removed: self.ops_results.insert(tk.END, f"\nRemoved {count} duplicate files.\n"))
    
    def _generate_file_reports(self, source, destination):
        """Generate comprehensive file reports."""
        files = self.scanner.scan_directory(source, recursive=True)
        report_data = []
        
        for file_path in files:
            try:
                metadata = self.extractor.extract_metadata(file_path)
                stat = os.stat(file_path)
                
                report_data.append({
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'file_size': stat.st_size,
                    'created_date': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_type': Path(file_path).suffix.lower(),
                    'metadata': metadata
                })
                
            except Exception as e:
                self.logger.error(f"Error generating report for {file_path}: {e}")
        
        # Save report
        report_file = os.path.join(destination, 'file_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Generate summary
        summary_file = os.path.join(destination, 'file_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"File Report Summary\n")
            f.write(f"==================\n\n")
            f.write(f"Total files processed: {len(report_data)}\n")
            f.write(f"Total size: {sum(item['file_size'] for item in report_data):,} bytes\n")
            
            # File type breakdown
            type_counts = {}
            for item in report_data:
                file_type = item['file_type'] or 'no extension'
                type_counts[file_type] = type_counts.get(file_type, 0) + 1
            
            f.write(f"\nFile types:\n")
            for file_type, count in sorted(type_counts.items()):
                f.write(f"  {file_type}: {count} files\n")
        
        self.root.after(0, lambda: self.ops_results.insert(tk.END, f"\nGenerated reports:\n- {report_file}\n- {summary_file}\n"))
    
    def _generate_filename_from_metadata(self, metadata, original_path):
        """Generate a new filename based on metadata."""
        try:
            # Get file extension
            ext = Path(original_path).suffix
            
            # Try to use creation date if available
            if 'created_date' in metadata and metadata['created_date']:
                try:
                    date_str = metadata['created_date'][:10].replace('-', '_')  # YYYY_MM_DD
                    return f"{date_str}_{os.path.basename(original_path)}"
                except:
                    pass
            
            # Try to use title or name from metadata
            for key in ['title', 'name', 'filename']:
                if key in metadata and metadata[key]:
                    clean_name = self._clean_filename(str(metadata[key]))
                    if clean_name:
                        return f"{clean_name}{ext}"
            
            # Fallback to original name
            return None
            
        except Exception:
            return None
    
    def _clean_filename(self, filename):
        """Clean filename by removing invalid characters."""
        import re
        # Remove invalid characters for Windows filenames
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        # Trim and limit length
        cleaned = cleaned.strip('_')[:100]
        return cleaned if cleaned else None
    
    def _get_file_type(self, extension):
        """Get file type category from extension."""
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
        audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
        video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        document_exts = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'}
        archive_exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        
        if extension in image_exts:
            return 'Images'
        elif extension in audio_exts:
            return 'Audio'
        elif extension in video_exts:
            return 'Video'
        elif extension in document_exts:
            return 'Documents'
        elif extension in archive_exts:
            return 'Archives'
        else:
            return 'Other'
        
    def stop_processing(self): pass


def main():
    """Main application entry point."""
    root = tk.Tk()
    app = MetaCLIGUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()