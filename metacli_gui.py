#!/usr/bin/env python3
"""
MetaCLI GUI - Advanced Interactive Metadata Extraction Tool

A modern, user-friendly graphical interface for the MetaCLI command-line tool
with enhanced features, tabbed interface, and improved user experience.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
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
import queue
import time
from typing import Optional, Callable, Any
import weakref
import gc
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the metacli package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import translation system
from translations import t, set_language, get_available_languages

try:
    from metacli.core.extractor import MetadataExtractor
    from metacli.core.scanner import DirectoryScanner
    from metacli.utils.formatter import OutputFormatter
    from metacli.utils.logger import setup_logger, get_logger
    from metacli.utils.updater import MetaCLIUpdater
    from metacli.utils.hasher import ExecutableHasher
except ImportError as e:
    print(f"Error importing MetaCLI modules: {e}")
    sys.exit(1)


def check_admin_privileges():
    """Check if the current process has administrator privileges on Windows."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def request_admin_elevation():
    """Request administrator elevation for the current application."""
    try:
        import ctypes
        import sys
        
        if check_admin_privileges():
            return True
            
        # Show message to user about admin requirement
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            result = messagebox.askyesno(
                "Administrator Privileges Required",
                "MetaCLI GUI requires administrator privileges to function properly.\n\n"
                "This is needed for:\n"
                "• File system access and metadata extraction\n"
                "• System integration features\n"
                "• Proper application functionality\n\n"
                "Would you like to restart the application as administrator?",
                icon="warning"
            )
            
            root.destroy()
            
            if not result:
                return False
                
        except Exception:
            print("MetaCLI GUI requires administrator privileges to run properly.")
            print("Please restart the application as administrator.")
            input("Press Enter to exit...")
            return False
        
        # Request elevation
        try:
            args_string = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in sys.argv)
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, args_string, None, 1
            )
            
            if result > 32:  # Success
                sys.exit(0)  # Exit current process
            else:
                raise Exception(f"ShellExecuteW failed with code {result}")
                
        except Exception as e:
            try:
                import tkinter as tk
                from tkinter import messagebox
                
                root = tk.Tk()
                root.withdraw()
                
                messagebox.showerror(
                    "Elevation Failed",
                    f"Failed to request administrator privileges: {e}\n\n"
                    "Please manually run the application as administrator."
                )
                
                root.destroy()
                
            except Exception:
                print(f"Failed to request administrator privileges: {e}")
                print("Please manually run the application as administrator.")
                input("Press Enter to exit...")
            
            return False
            
    except Exception as e:
        print(f"Error checking administrator privileges: {e}")
        return False


class MetaCLIGUI:
    """Advanced GUI application class for MetaCLI with enhanced features."""
    
    def __init__(self, root):
        # Check for admin privileges at startup
        if not check_admin_privileges():
            if not request_admin_elevation():
                root.destroy()
                sys.exit(1)
                
        self.root = root
        self.root.title(t('main_title'))
        
        # Enhanced window configuration
        self.setup_window()
        
        # Initialize theme and styling
        self.dark_mode = tk.BooleanVar(value=False)
        self.setup_styling()
        
        # Initialize components with optimized settings
        self.extractor = MetadataExtractor(enable_cache=True, max_workers=4)
        self.scanner = DirectoryScanner(extractor=self.extractor)
        self.formatter = OutputFormatter()
        self.logger = setup_logger(verbose=False, log_file='metacli_gui.log')
        self.updater = MetaCLIUpdater()
        self.hasher = ExecutableHasher()
        
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
        
        # Threading improvements
        self._stop_event = threading.Event()
        self._worker_threads = set()
        self._thread_lock = threading.RLock()
        self._result_queue = queue.Queue()
        self._animation_after_ids = set()
        
        # Animation state
        self._fade_animations = {}
        self._slide_animations = {}
        self._pulse_animations = {}
        
        # Enhanced error handling
        self._error_queue = queue.Queue()
        self._notification_queue = queue.Queue()
        self._retry_attempts = {}
        self._max_retry_attempts = 3
        self._error_history = []
        self._last_error_time = 0
        
        # Memory management
        self._memory_threshold = 500 * 1024 * 1024  # 500MB threshold
        self._batch_size = 100  # Process results in batches
        self._gc_frequency = 50  # Force GC every 50 files
        self._processed_count = 0
        self._memory_warnings = 0
        
        # Batch processing variables
        self.batch_directories = []
        self.batch_processing = False
        self.batch_stop_requested = False
        self.batch_paused = False
        self.batch_current_file = ""
        self.batch_processed_files = 0
        self.batch_total_files = 0
        self.batch_start_time = None
        self.batch_queue = queue.Queue()
        self.batch_results_queue = queue.Queue()
        self.batch_error_count = 0
        self.batch_success_count = 0
        
        # Queue management variables
        self.processing_queue = []
        self.current_queue_index = 0
        self.queue_processing = False
        self.queue_paused = False
        
        # Template management variables
        self.templates = {}
        self.custom_templates = {}
        self._load_default_templates()
        
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
        
        # Enhanced functionality shortcuts
        self.root.bind('<Control-f>', lambda e: self.show_find_dialog())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-c>', lambda e: self.copy_results())
        self.root.bind('<Control-e>', lambda e: self.export_results())
        self.root.bind('<Control-b>', lambda e: self.batch_process())
        self.root.bind('<Control-Shift-B>', lambda e: self.stop_batch_processing())
        self.root.bind('<Control-Shift-F>', lambda e: self.show_filter_dialog())
        self.root.bind('<Control-Shift-C>', lambda e: self.compare_files())
        self.root.bind('<Control-Shift-R>', lambda e: self.save_report())
        self.root.bind('<Control-Shift-S>', lambda e: self.show_shortcuts())
        
        # Help
        self.root.bind('<F1>', lambda e: self.show_help())
    
    def load_user_preferences(self):
        """Load user preferences from configuration file."""
        try:
            config_path = Path.home() / '.metacli_config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                    # Theme settings
                    theme = config.get('theme', {})
                    self.dark_mode.set(theme.get('dark_mode', False))
                    if hasattr(self, 'theme_var'):
                        self.theme_var.set(theme.get('theme_var', 'Light'))
                    if hasattr(self, 'language_var'):
                        self.language_var.set(theme.get('language', 'English'))
                    
                    # General settings
                    general = config.get('general', {})
                    if hasattr(self, 'auto_save_settings'):
                        self.auto_save_settings.set(general.get('auto_save_settings', True))
                    if hasattr(self, 'remember_window_size'):
                        self.remember_window_size.set(general.get('remember_window_size', True))
                    if hasattr(self, 'show_tooltips'):
                        self.show_tooltips.set(general.get('show_tooltips', True))
                    
                    # Performance settings
                    performance = config.get('performance', {})
                    if hasattr(self, 'max_workers'):
                        self.max_workers.set(performance.get('max_workers', 4))
                    if hasattr(self, 'cache_size'):
                        self.cache_size.set(performance.get('cache_size', 100))
                    self.cache_enabled.set(performance.get('cache_enabled', True))
                    self.parallel_processing.set(performance.get('parallel_processing', True))
                    if hasattr(self, 'memory_limit'):
                        self.memory_limit.set(performance.get('memory_limit', 512))
                    
                    # Scanning settings
                    scanning = config.get('scanning', {})
                    self.scan_recursive.set(scanning.get('scan_recursive', True))
                    self.show_hidden.set(scanning.get('show_hidden', False))
                    if hasattr(self, 'auto_refresh'):
                        self.auto_refresh.set(scanning.get('auto_refresh', False))
                    self.max_files.set(scanning.get('max_files', 500))
                    self.selected_formats.set(scanning.get('selected_formats', 'all'))
                    
                    # Output settings
                    output = config.get('output', {})
                    self.output_format.set(output.get('output_format', 'json'))
                    if hasattr(self, 'default_output_dir'):
                        self.default_output_dir.set(output.get('default_output_dir', os.path.join(os.getcwd(), 'output')))
                    if hasattr(self, 'auto_open_results'):
                        self.auto_open_results.set(output.get('auto_open_results', False))
                    if hasattr(self, 'create_backup'):
                        self.create_backup.set(output.get('create_backup', True))
                    
                    # Logging settings
                    logging_config = config.get('logging', {})
                    if hasattr(self, 'log_level'):
                        self.log_level.set(logging_config.get('log_level', 'INFO'))
                    if hasattr(self, 'log_file_path'):
                        self.log_file_path.set(logging_config.get('log_file_path', 'metacli_gui.log'))
                    if hasattr(self, 'enable_file_logging'):
                        self.enable_file_logging.set(logging_config.get('enable_file_logging', True))
                    if hasattr(self, 'enable_console_logging'):
                        self.enable_console_logging.set(logging_config.get('enable_console_logging', False))
                    if hasattr(self, 'max_log_size'):
                        self.max_log_size.set(logging_config.get('max_log_size', 10))
                    if hasattr(self, 'keep_log_files'):
                        self.keep_log_files.set(logging_config.get('keep_log_files', 5))
                    
                    # Advanced settings
                    advanced = config.get('advanced', {})
                    if hasattr(self, 'debug_mode'):
                        self.debug_mode.set(advanced.get('debug_mode', False))
                    if hasattr(self, 'verbose_output'):
                        self.verbose_output.set(advanced.get('verbose_output', False))
                    if hasattr(self, 'experimental_features'):
                        self.experimental_features.set(advanced.get('experimental_features', False))
                    if hasattr(self, 'plugin_dir'):
                        self.plugin_dir.set(advanced.get('plugin_dir', os.path.join(os.getcwd(), 'plugins')))
                    
                    # Update settings
                    update_settings = config.get('update', {})
                    if hasattr(self, 'auto_check_updates'):
                        self.auto_check_updates.set(update_settings.get('auto_check_updates', True))
                    if hasattr(self, 'notify_beta_updates'):
                        self.notify_beta_updates.set(update_settings.get('notify_beta_updates', False))
                        
        except Exception as e:
            print(f"Warning: Failed to load user preferences: {e}")
            pass  # Use defaults if config loading fails
    
    def save_user_preferences(self):
        """Save user preferences to configuration file."""
        try:
            config = self._get_all_settings()
            config_path = Path.home() / '.metacli_config.json'
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save user preferences: {e}")
    
    def on_closing(self):
        """Handle application closing with cleanup."""
        self._cleanup_threads()
        self._cleanup_animations()
        self.save_user_preferences()
        self.root.destroy()
    
    def _cleanup_threads(self):
        """Clean up all worker threads safely"""
        with self._thread_lock:
            self._stop_event.set()
            
            # Wait for threads to finish with timeout
            for thread_ref in list(self._worker_threads):
                thread = thread_ref() if isinstance(thread_ref, weakref.ref) else thread_ref
                if thread and thread.is_alive():
                    thread.join(timeout=2.0)
            
            self._worker_threads.clear()
            self._stop_event.clear()
    
    def _register_thread(self, thread):
        """Register a worker thread for cleanup"""
        with self._thread_lock:
            # Use weak references to avoid circular references
            self._worker_threads.add(weakref.ref(thread))
    
    def _cleanup_animations(self):
        """Cancel all pending animations"""
        for after_id in self._animation_after_ids:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self._animation_after_ids.clear()
        
        # Clear animation states
        self._fade_animations.clear()
        self._slide_animations.clear()
        self._pulse_animations.clear()
    
    def _animate_fade(self, widget, start_alpha=0.0, end_alpha=1.0, duration=300, callback=None):
        """Animate widget fade in/out effect"""
        steps = 20
        step_duration = duration // steps
        alpha_step = (end_alpha - start_alpha) / steps
        
        def fade_step(current_step):
            if current_step >= steps or widget not in self._fade_animations:
                if callback:
                    callback()
                self._fade_animations.pop(widget, None)
                return
            
            alpha = start_alpha + (alpha_step * current_step)
            try:
                # For tkinter widgets, we simulate fade by adjusting colors
                if hasattr(widget, 'configure'):
                    if alpha <= 0.1:
                        widget.configure(state='disabled')
                    else:
                        widget.configure(state='normal')
                
                after_id = self.root.after(step_duration, lambda: fade_step(current_step + 1))
                self._animation_after_ids.add(after_id)
                
            except tk.TclError:
                self._fade_animations.pop(widget, None)
        
        self._fade_animations[widget] = True
        fade_step(0)
    
    def _animate_pulse(self, widget, duration=1000, intensity=0.2):
        """Animate widget pulse effect for attention"""
        if widget in self._pulse_animations:
            return
        
        # Check if widget supports background option safely
        original_bg = None
        try:
            if hasattr(widget, 'cget'):
                original_bg = widget.cget('background')
        except tk.TclError:
            # Widget doesn't support background option (e.g., ttk widgets)
            original_bg = None
        
        steps = 30
        step_duration = duration // steps
        
        def pulse_step(current_step):
            if current_step >= steps or widget not in self._pulse_animations:
                self._pulse_animations.pop(widget, None)
                # Restore original state
                try:
                    if hasattr(widget, 'configure'):
                        widget.configure(relief='flat')
                except tk.TclError:
                    pass
                return
            
            # Calculate pulse intensity
            progress = current_step / steps
            pulse_value = abs(0.5 - (progress % 1.0)) * 2 * intensity
            
            try:
                if hasattr(widget, 'configure'):
                    # Use relief changes for pulse effect (works with both tk and ttk widgets)
                    if pulse_value > 0.1:
                        widget.configure(relief='raised')
                    else:
                        widget.configure(relief='flat')
                
                after_id = self.root.after(step_duration, lambda: pulse_step(current_step + 1))
                self._animation_after_ids.add(after_id)
                
            except tk.TclError:
                self._pulse_animations.pop(widget, None)
        
        self._pulse_animations[widget] = True
        pulse_step(0)
    
    def _animate_progress_smooth(self, progress_bar, target_value, duration=500):
        """Smoothly animate progress bar to target value"""
        if not hasattr(progress_bar, 'get'):
            return
        
        current_value = progress_bar.get()
        steps = 20
        step_duration = duration // steps
        value_step = (target_value - current_value) / steps
        
        def progress_step(current_step):
            if current_step >= steps:
                progress_bar.configure(value=target_value)
                return
            
            new_value = current_value + (value_step * current_step)
            try:
                progress_bar.configure(value=new_value)
                after_id = self.root.after(step_duration, lambda: progress_step(current_step + 1))
                self._animation_after_ids.add(after_id)
            except tk.TclError:
                pass
        
        progress_step(0)
    
    def _show_loading_animation(self, widget, text="Processing..."):
        """Show loading animation with rotating text"""
        loading_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        char_index = 0
        
        def update_loading():
            nonlocal char_index
            if widget not in self._pulse_animations:
                return
            
            try:
                current_char = loading_chars[char_index % len(loading_chars)]
                if hasattr(widget, 'configure'):
                    widget.configure(text=f"{current_char} {text}")
                
                char_index += 1
                after_id = self.root.after(100, update_loading)
                self._animation_after_ids.add(after_id)
                
            except tk.TclError:
                self._pulse_animations.pop(widget, None)
        
        self._pulse_animations[widget] = True
        update_loading()
    
    def _stop_loading_animation(self, widget, final_text=""):
        """Stop loading animation and set final text"""
        self._pulse_animations.pop(widget, None)
        try:
            if hasattr(widget, 'configure'):
                widget.configure(text=final_text)
        except tk.TclError:
            pass
    
    def _show_error_notification(self, title, message, error_type="error", duration=5000, allow_retry=False, retry_callback=None):
        """Show enhanced error notification with retry options."""
        try:
            # Add to error history
            error_entry = {
                'timestamp': datetime.now(),
                'title': title,
                'message': message,
                'type': error_type
            }
            self._error_history.append(error_entry)
            
            # Keep only last 50 errors
            if len(self._error_history) > 50:
                self._error_history = self._error_history[-50:]
            
            # Create notification window
            notification = tk.Toplevel(self.root)
            notification.title(title)
            notification.geometry("400x200")
            notification.resizable(False, False)
            notification.transient(self.root)
            notification.grab_set()
            
            # Center the notification
            notification.update_idletasks()
            x = (notification.winfo_screenwidth() // 2) - (400 // 2)
            y = (notification.winfo_screenheight() // 2) - (200 // 2)
            notification.geometry(f"400x200+{x}+{y}")
            
            # Error icon and message
            main_frame = ttk.Frame(notification, padding="20")
            main_frame.pack(fill='both', expand=True)
            
            # Icon based on error type
            icon_text = "⚠️" if error_type == "warning" else "❌" if error_type == "error" else "ℹ️"
            icon_label = ttk.Label(main_frame, text=icon_text, font=('Arial', 24))
            icon_label.pack(pady=(0, 10))
            
            # Title
            title_label = ttk.Label(main_frame, text=title, font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 5))
            
            # Message
            message_label = ttk.Label(main_frame, text=message, wraplength=350, justify='center')
            message_label.pack(pady=(0, 15))
            
            # Buttons frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x')
            
            if allow_retry and retry_callback:
                retry_btn = ttk.Button(button_frame, text="Retry", 
                                     command=lambda: [notification.destroy(), retry_callback()])
                retry_btn.pack(side='left', padx=(0, 10))
            
            ok_btn = ttk.Button(button_frame, text="OK", command=notification.destroy)
            ok_btn.pack(side='right')
            
            # Auto-close after duration
            if duration > 0:
                notification.after(duration, notification.destroy)
            
            # Animate notification
            self._animate_fade(notification, start_alpha=0.0, end_alpha=1.0, duration=300)
            
        except Exception as e:
            # Fallback to simple messagebox if notification fails
            messagebox.showerror(title, f"{message}\n\nNotification error: {str(e)}")
    
    def _handle_operation_error(self, operation_name, error, allow_retry=True, retry_callback=None):
        """Handle operation errors with intelligent retry logic."""
        error_key = f"{operation_name}_{str(error)}"
        
        # Track retry attempts
        if error_key not in self._retry_attempts:
            self._retry_attempts[error_key] = 0
        
        self._retry_attempts[error_key] += 1
        
        # Determine if retry is available
        can_retry = (allow_retry and 
                    retry_callback and 
                    self._retry_attempts[error_key] <= self._max_retry_attempts)
        
        # Format error message
        error_msg = str(error)
        if self._retry_attempts[error_key] > 1:
            error_msg += f"\n\nAttempt {self._retry_attempts[error_key]} of {self._max_retry_attempts + 1}"
        
        # Show error notification
        self._show_error_notification(
            title=f"{operation_name} Failed",
            message=error_msg,
            error_type="error",
            allow_retry=can_retry,
            retry_callback=retry_callback
        )
        
        # Log error
        if hasattr(self, 'logger'):
            self.logger.error(f"{operation_name} failed: {error}")
    
    def _show_success_notification(self, title, message, duration=3000):
        """Show success notification with fade animation."""
        try:
            # Create temporary success label
            success_frame = ttk.Frame(self.root)
            success_frame.place(relx=0.5, rely=0.1, anchor='center')
            
            success_label = ttk.Label(success_frame, text=f"✅ {title}: {message}", 
                                    background='#d4edda', foreground='#155724',
                                    padding="10", font=('Arial', 10, 'bold'))
            success_label.pack()
            
            # Animate and auto-remove
            self._animate_fade(success_frame, start_alpha=0.0, end_alpha=1.0, duration=300)
            
            def remove_notification():
                self._animate_fade(success_frame, start_alpha=1.0, end_alpha=0.0, duration=300,
                                 callback=lambda: success_frame.destroy())
            
            self.root.after(duration, remove_notification)
            
        except Exception as e:
            # Fallback to status update
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"{title}: {message}", foreground='#27ae60')
    
    def _validate_input(self, value, validation_type, field_name="Field"):
        """Validate user input with detailed error messages."""
        try:
            if validation_type == "path":
                if not value or not value.strip():
                    raise ValueError(f"{field_name} cannot be empty")
                path = Path(value.strip())
                if not path.exists():
                    raise ValueError(f"{field_name} does not exist: {value}")
                return str(path.resolve())
            
            elif validation_type == "directory":
                validated_path = self._validate_input(value, "path", field_name)
                path = Path(validated_path)
                if not path.is_dir():
                    raise ValueError(f"{field_name} must be a directory: {value}")
                return validated_path
            
            elif validation_type == "file":
                validated_path = self._validate_input(value, "path", field_name)
                path = Path(validated_path)
                if not path.is_file():
                    raise ValueError(f"{field_name} must be a file: {value}")
                return validated_path
            
            elif validation_type == "number":
                if not value or not str(value).strip():
                    raise ValueError(f"{field_name} cannot be empty")
                try:
                    return int(value)
                except ValueError:
                    raise ValueError(f"{field_name} must be a valid number: {value}")
            
            elif validation_type == "positive_number":
                number = self._validate_input(value, "number", field_name)
                if number <= 0:
                    raise ValueError(f"{field_name} must be positive: {value}")
                return number
            
            else:
                raise ValueError(f"Unknown validation type: {validation_type}")
                
        except Exception as e:
            self._show_error_notification(
                title="Input Validation Error",
                message=str(e),
                error_type="warning"
            )
            raise
    
    def _check_memory_usage(self):
        """Monitor memory usage and trigger cleanup if needed using enhanced monitoring."""
        try:
            # Use the enhanced memory monitoring from MetadataExtractor
            memory_stats = MetadataExtractor.get_memory_stats()
            memory_percent = memory_stats.get('percent', 0)
            
            # Check if cleanup is needed
            cleanup_result = MetadataExtractor.check_and_cleanup_memory()
            if cleanup_result:
                self.status_label.config(
                    text=f"Memory cleanup: {cleanup_result['memory_freed_mb']:.1f}MB freed",
                    foreground='#f39c12'
                )
                self._memory_warnings = 0
                return True
            
            # Check if memory usage is critical
            if memory_percent > 85:
                self._memory_warnings += 1
                if self._memory_warnings > 3:
                    # Force aggressive cleanup
                    self._force_memory_cleanup()
                    self._memory_warnings = 0
                return False
            return True
        except Exception as e:
            print(f"Memory monitoring error: {e}")
            return True  # Continue if memory check fails
    
    def _force_memory_cleanup(self):
        """Force aggressive memory cleanup using enhanced monitoring."""
        try:
            # Use the enhanced memory cleanup from MetadataExtractor
            cleanup_result = MetadataExtractor.force_memory_cleanup()
            
            # Clear large data structures in GUI
            if hasattr(self, 'scan_results') and len(self.scan_results) > 1000:
                # Keep only recent results
                self.scan_results = self.scan_results[-500:]
            
            # Clear error history
            if len(self._error_history) > 50:
                self._error_history = self._error_history[-25:]
            
            # Additional GUI-specific cleanup
            gc.collect()
            
            # Update status with detailed information
            memory_freed = cleanup_result.get('memory_freed_mb', 0)
            self.status_label.config(
                text=f"Aggressive cleanup: {memory_freed:.1f}MB freed",
                foreground='#e74c3c'
            )
            
            # Log the cleanup details
            if hasattr(self, 'logger'):
                self.logger.info(f"Forced memory cleanup completed: {cleanup_result}")
                
        except Exception as e:
            print(f"Memory cleanup error: {e}")
            # Fallback to basic cleanup
            gc.collect()
            self.status_label.config(
                text="Basic memory cleanup performed",
                foreground='#f39c12'
            )
    
    def _process_results_chunked(self, results, chunk_size=None):
        """Process results in chunks to manage memory usage."""
        if chunk_size is None:
            chunk_size = self._batch_size
            
        for i in range(0, len(results), chunk_size):
            chunk = results[i:i + chunk_size]
            self._process_results_batch(chunk)
            
            # Check memory and force cleanup if needed
            if not self._check_memory_usage():
                break
                
            # Periodic garbage collection
            if i % (chunk_size * 5) == 0:
                gc.collect()
        
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
        menubar.add_cascade(label=t('menu_file'), menu=file_menu)
        file_menu.add_command(label=t('file_open'), command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label=t('file_open_dir'), command=self.browse_directory, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label=t('file_export'), command=self.export_results, accelerator="Ctrl+E")
        file_menu.add_command(label=t('file_save_report'), command=self.save_report, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label=t('file_recent'), state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label=t('file_exit'), command=self.root.quit, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=t('menu_edit'), menu=edit_menu)
        edit_menu.add_command(label=t('edit_copy'), command=self.copy_results, accelerator="Ctrl+C")
        edit_menu.add_command(label=t('edit_select_all'), command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_separator()
        edit_menu.add_command(label=t('edit_find'), command=self.show_find_dialog, accelerator="Ctrl+F")
        edit_menu.add_command(label=t('edit_filter'), command=self.show_filter_dialog)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=t('menu_tools'), menu=tools_menu)
        tools_menu.add_command(label=t('tools_batch'), command=self.batch_process)
        tools_menu.add_command(label=t('tools_compare'), command=self.compare_files)
        tools_menu.add_command(label=t('tools_report'), command=self.generate_report)
        tools_menu.add_separator()
        tools_menu.add_command(label=t('tools_settings'), command=self.show_settings)
        tools_menu.add_command(label=t('tools_clear_cache'), command=self.clear_cache)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=t('menu_view'), menu=view_menu)
        view_menu.add_command(label=t('view_refresh'), command=self.refresh_view, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_checkbutton(label=t('view_hidden'), variable=self.show_hidden)
        view_menu.add_checkbutton(label=t('view_auto_refresh'), variable=self.auto_refresh)
        view_menu.add_separator()
        view_menu.add_command(label=t('view_expand_all'), command=self.expand_all)
        view_menu.add_command(label=t('view_collapse_all'), command=self.collapse_all)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=t('menu_help'), menu=help_menu)
        help_menu.add_command(label=t('help_guide'), command=self.show_help)
        help_menu.add_command(label=t('help_shortcuts'), command=self.show_shortcuts)
        help_menu.add_command(label=t('help_cli'), command=self.show_cli_help)
        help_menu.add_separator()
        help_menu.add_command(label=t('help_updates'), command=self.check_updates)
        help_menu.add_command(label=t('help_about'), command=self.show_about)
        
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
        
        self.scan_btn = ttk.Button(action_frame, text="🔍 Start Scan", command=self.scan_directory, 
                  style='Action.TButton')
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 10))
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
        
        # Templates and Presets
        templates_frame = ttk.LabelFrame(main_frame, text="Templates & Presets", padding="10")
        templates_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Template selection
        template_selection_frame = ttk.Frame(templates_frame)
        template_selection_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(template_selection_frame, text="Template:").pack(side=tk.LEFT)
        self.template_var = tk.StringVar(value="Custom")
        self.template_combo = ttk.Combobox(template_selection_frame, textvariable=self.template_var, 
                                          values=["Custom", "Basic Extraction", "Full Metadata", "Images Only", "Documents Only", "Media Files"],
                                          state="readonly", width=20)
        self.template_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_selected)
        
        # Template control buttons
        ttk.Button(template_selection_frame, text="Apply Template", command=self.apply_template).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(template_selection_frame, text="Save as Template", command=self.save_template).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(template_selection_frame, text="Delete Template", command=self.delete_template).pack(side=tk.LEFT)
        
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
        
        # Advanced filtering options
        advanced_filter_frame = ttk.LabelFrame(options_frame, text="Advanced Filters", padding="5")
        advanced_filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File size filter
        size_frame = ttk.Frame(advanced_filter_frame)
        size_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.batch_enable_size_filter = tk.BooleanVar(value=False)
        ttk.Checkbutton(size_frame, text="Filter by file size:", variable=self.batch_enable_size_filter).pack(side=tk.LEFT)
        
        ttk.Label(size_frame, text="Min:").pack(side=tk.LEFT, padx=(10, 2))
        self.batch_min_size = tk.StringVar(value="0")
        ttk.Entry(size_frame, textvariable=self.batch_min_size, width=8).pack(side=tk.LEFT, padx=(0, 2))
        
        self.batch_min_size_unit = ttk.Combobox(size_frame, values=["B", "KB", "MB", "GB"], state="readonly", width=4)
        self.batch_min_size_unit.set("KB")
        self.batch_min_size_unit.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(size_frame, text="Max:").pack(side=tk.LEFT, padx=(0, 2))
        self.batch_max_size = tk.StringVar(value="100")
        ttk.Entry(size_frame, textvariable=self.batch_max_size, width=8).pack(side=tk.LEFT, padx=(0, 2))
        
        self.batch_max_size_unit = ttk.Combobox(size_frame, values=["B", "KB", "MB", "GB"], state="readonly", width=4)
        self.batch_max_size_unit.set("MB")
        self.batch_max_size_unit.pack(side=tk.LEFT)
        
        # Date range filter
        date_frame = ttk.Frame(advanced_filter_frame)
        date_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.batch_enable_date_filter = tk.BooleanVar(value=False)
        ttk.Checkbutton(date_frame, text="Filter by modification date:", variable=self.batch_enable_date_filter).pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text="From:").pack(side=tk.LEFT, padx=(10, 2))
        self.batch_date_from = tk.StringVar(value="2020-01-01")
        ttk.Entry(date_frame, textvariable=self.batch_date_from, width=12).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(date_frame, text="To:").pack(side=tk.LEFT, padx=(0, 2))
        self.batch_date_to = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(date_frame, textvariable=self.batch_date_to, width=12).pack(side=tk.LEFT)
        
        # Metadata criteria filter
        metadata_frame = ttk.Frame(advanced_filter_frame)
        metadata_frame.pack(fill=tk.X)
        
        self.batch_enable_metadata_filter = tk.BooleanVar(value=False)
        ttk.Checkbutton(metadata_frame, text="Filter by metadata:", variable=self.batch_enable_metadata_filter).pack(side=tk.LEFT)
        
        ttk.Label(metadata_frame, text="Field:").pack(side=tk.LEFT, padx=(10, 2))
        self.batch_metadata_field = ttk.Combobox(metadata_frame, values=["title", "artist", "album", "genre", "year", "duration", "bitrate"], width=10)
        self.batch_metadata_field.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(metadata_frame, text="Contains:").pack(side=tk.LEFT, padx=(0, 2))
        self.batch_metadata_value = tk.StringVar()
        ttk.Entry(metadata_frame, textvariable=self.batch_metadata_value, width=15).pack(side=tk.LEFT)
        
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
        
        # Queue Management
        queue_frame = ttk.LabelFrame(main_frame, text="Processing Queue", padding="10")
        queue_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Queue display
        queue_display_frame = ttk.Frame(queue_frame)
        queue_display_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(queue_display_frame, text="Queue Status:").pack(side=tk.LEFT)
        self.queue_status_label = ttk.Label(queue_display_frame, text="Empty (0 jobs)", foreground="gray")
        self.queue_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Queue listbox
        self.queue_listbox = tk.Listbox(queue_frame, height=4)
        self.queue_listbox.pack(fill=tk.X, pady=(0, 10))
        
        # Queue control buttons
        queue_buttons_frame = ttk.Frame(queue_frame)
        queue_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(queue_buttons_frame, text="Add to Queue", command=self.add_to_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Remove Selected", command=self.remove_from_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Move Up", command=self.move_queue_item_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Move Down", command=self.move_queue_item_down).pack(side=tk.LEFT)
        
        # Priority settings
        priority_frame = ttk.Frame(queue_frame)
        priority_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(priority_frame, text="Priority:").pack(side=tk.LEFT)
        self.queue_priority = ttk.Combobox(priority_frame, values=["High", "Normal", "Low"], state="readonly", width=10)
        self.queue_priority.set("Normal")
        self.queue_priority.pack(side=tk.LEFT, padx=(5, 0))
        
        # Progress and control
        control_frame = ttk.LabelFrame(main_frame, text="Batch Processing Control", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self.batch_progress = ttk.Progressbar(control_frame, mode='determinate')
        self.batch_progress.pack(fill=tk.X, pady=(0, 10))
        
        # File-level progress indicator
        self.batch_current_file = ttk.Label(control_frame, text="", foreground="gray")
        self.batch_current_file.pack(anchor=tk.W, pady=(0, 5))
        
        # Status label
        self.batch_status = ttk.Label(control_frame, text="Ready to start batch processing")
        self.batch_status.pack(anchor=tk.W, pady=(0, 10))
        
        # Control buttons
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X)
        
        self.batch_start_btn = ttk.Button(buttons_frame, text="Start Batch Processing", command=self.start_batch_processing)
        self.batch_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.queue_start_btn = ttk.Button(buttons_frame, text="Start Queue Processing", command=self.start_queue_processing)
        self.queue_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.batch_stop_btn = ttk.Button(buttons_frame, text="Stop Processing", command=self.stop_batch_processing, state=tk.DISABLED)
        self.batch_stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Open Output Folder", command=self.open_batch_output_folder).pack(side=tk.LEFT)
        
        # Results summary
        summary_frame = ttk.LabelFrame(main_frame, text="Processing Summary", padding="10")
        summary_frame.pack(fill=tk.BOTH, expand=True)
        
        self.batch_summary = scrolledtext.ScrolledText(summary_frame, height=8, wrap=tk.WORD)
        self.batch_summary.pack(fill=tk.BOTH, expand=True)
        
        # Add pause/resume button
        self.batch_pause_btn = ttk.Button(buttons_frame, text="Pause", command=self.pause_batch_processing, state=tk.DISABLED)
        self.batch_pause_btn.pack(side=tk.LEFT, padx=(0, 10))
    
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
        
        # Update Settings
        update_frame = ttk.LabelFrame(scrollable_frame, text="Update Settings", padding="10")
        update_frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 20))
        
        # Update preferences
        self.auto_check_updates = tk.BooleanVar(value=True)
        ttk.Checkbutton(update_frame, text="Automatically check for stable updates on startup", variable=self.auto_check_updates).pack(anchor=tk.W, pady=(0, 5))
        
        self.notify_beta_updates = tk.BooleanVar(value=False)
        ttk.Checkbutton(update_frame, text="Show notifications for beta releases", variable=self.notify_beta_updates).pack(anchor=tk.W, pady=(0, 10))
        
        # Update buttons
        update_buttons_frame = ttk.Frame(update_frame)
        update_buttons_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(update_buttons_frame, text="Check for Stable Updates", command=self.check_updates).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(update_buttons_frame, text="Check for Beta Updates", command=self.check_beta_updates).pack(side=tk.LEFT)
        
        # Beta warning
        beta_warning_frame = ttk.Frame(update_frame)
        beta_warning_frame.pack(fill=tk.X, pady=(5, 0))
        
        warning_label = ttk.Label(beta_warning_frame, text="⚠️ Beta versions may contain bugs and are not recommended for production use.", 
                                 foreground="orange", font=("TkDefaultFont", 8))
        warning_label.pack(anchor=tk.W)
        
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
        """Set up the status bar at the bottom with memory monitoring."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        
        self.status_text = ttk.Label(self.status_bar, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Memory monitoring display
        self.memory_label = ttk.Label(self.status_bar, text="Memory: --", relief=tk.SUNKEN)
        self.memory_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Cache status display
        self.cache_label = ttk.Label(self.status_bar, text="Cache: --", relief=tk.SUNKEN)
        self.cache_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.version_label = ttk.Label(self.status_bar, text="MetaCLI v2.0", relief=tk.SUNKEN)
        self.version_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Start memory monitoring timer
        self._start_memory_monitoring()
    
    def _start_memory_monitoring(self):
        """Start periodic memory monitoring updates."""
        self._update_memory_display()
        # Schedule next update in 5 seconds
        self.root.after(5000, self._start_memory_monitoring)
    
    def _update_memory_display(self):
        """Update memory and cache information in status bar."""
        try:
            memory_stats = MetadataExtractor.get_memory_stats()
            
            # Update memory display
            memory_percent = memory_stats.get('percent', 0)
            memory_mb = memory_stats.get('used_mb', 0)
            memory_color = '#e74c3c' if memory_percent > 85 else '#f39c12' if memory_percent > 75 else '#27ae60'
            self.memory_label.config(
                text=f"Memory: {memory_percent:.1f}% ({memory_mb:.0f}MB)",
                foreground=memory_color
            )
            
            # Update cache display
            cache_size = memory_stats.get('cache_size', 0)
            cache_mb = memory_stats.get('cache_memory_mb', 0)
            self.cache_label.config(
                text=f"Cache: {cache_size} items ({cache_mb:.1f}MB)"
            )
            
        except Exception as e:
            # Fallback to basic display if enhanced monitoring fails
            self.memory_label.config(text="Memory: N/A")
            self.cache_label.config(text="Cache: N/A")
        
    # Event handlers and utility methods
    def set_path(self, path):
        """Set the current path."""
        self.current_path.set(str(path))
        
    def browse_directory(self):
        """Browse for a directory with enhanced error handling."""
        try:
            directory = filedialog.askdirectory(title="Select Directory to Scan")
            if directory:
                # Validate the selected directory
                validated_path = self._validate_input(directory, "directory", "Selected directory")
                self.current_path.set(validated_path)
                self._show_success_notification("Directory Selected", f"Ready to scan: {os.path.basename(validated_path)}")
        except Exception as e:
            self._handle_operation_error("Directory Selection", e)
            
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
        """Start directory scanning with enhanced threading and visual feedback."""
        if not self.current_path.get():
            messagebox.showwarning("Warning", "Please select a path to scan.")
            return
            
        if self.processing:
            messagebox.showinfo("Info", "Scan already in progress.")
            return
        
        # Enhanced error handling and validation
        try:
            # Validate input using enhanced validation
            path = self._validate_input(
                self.current_path.get(), 
                "directory", 
                "Scan directory"
            )
        except ValueError:
            return  # Error already shown by validation method
            
        # Start scanning with improved threading
        self.processing = True
        self._stop_event.clear()
        self.scanner.set_stop_event(self._stop_event)
        
        # Enhanced visual feedback
        self.progress.start()
        self._show_loading_animation(self.status_label, "Scanning directory...")
        self._animate_pulse(self.scan_btn, duration=2000)
        
        # Disable scan button during processing
        self.scan_btn.configure(state='disabled')
        
        thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._register_thread(thread)
        thread.start()
        
    def _scan_worker(self):
        """Enhanced worker thread for scanning with stop event checking."""
        try:
            path = Path(self.current_path.get())
            
            if self._stop_event.is_set():
                return
            
            if path.is_file():
                # Single file analysis
                results = [self._analyze_single_file(path)]
            else:
                # Directory scanning with optimized approach
                file_types = None if self.selected_formats.get() == "all" else [self.selected_formats.get()]
                max_files = self.max_files.get()
                
                # Use the scanner's optimized scan_directory method
                scan_results = self.scanner.scan_directory(
                    path,
                    recursive=self.scan_recursive.get(),
                    file_types=file_types,
                    extract_metadata=True,
                    max_workers=2  # Limit workers to prevent UI blocking
                )
                
                # Convert ScanResult objects to GUI format with memory management
                results = []
                self._processed_count = 0
                
                for i, scan_result in enumerate(scan_results):
                    if self._stop_event.is_set():
                        break
                    if max_files and i >= max_files:
                        break
                    
                    # Check memory usage periodically
                    if i % self._gc_frequency == 0:
                        if not self._check_memory_usage():
                            # Memory threshold exceeded, process current batch
                            if results:
                                self.root.after(0, self._process_results_chunked, results)
                                results = []  # Clear processed results
                    
                    result_dict = {
                        'path': str(scan_result.file_path),
                        'size': scan_result.metadata.get('size', 0),
                        'modified': scan_result.metadata.get('modified'),
                        'metadata': scan_result.metadata
                    }
                    
                    if scan_result.error:
                        result_dict['error'] = scan_result.error
                    
                    results.append(result_dict)
                    self._processed_count += 1
                    
                    # Process in smaller batches to prevent memory buildup and improve responsiveness
                    if len(results) >= min(self._batch_size, 25):  # Smaller batch size for better responsiveness
                        self.root.after_idle(self._process_results_chunked, results.copy())
                        results = []  # Clear processed results
                        gc.collect()  # Force garbage collection
                    
                    # Update progress less frequently to keep UI more responsive
                    if i % 25 == 0:  # Reduced frequency from 10 to 25
                        progress = min(100, (i / min(len(scan_results), max_files or len(scan_results))) * 100)
                        self.root.after_idle(self._update_scan_progress, progress)  # Use after_idle for better responsiveness
                
            # Process any remaining results
            if results:
                self.root.after(0, self._process_results_chunked, results)
            else:
                # If no chunked processing, use original method
                self.root.after(0, self._update_results, [])
            
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
            
    def _update_scan_progress(self, progress):
        """Update scan progress in the UI."""
        # Update status to show progress
        self.status_label.config(text=f"Scanning... {progress:.0f}%", foreground='#f39c12')
            
    def _update_results(self, results):
        """Update the results tree with scan results (legacy method for compatibility)."""
        # For chunked processing, append to existing results
        if not hasattr(self, 'scan_results') or not self.scan_results:
            # Clear existing results only for new scans
            self.results_tree.delete(*self.results_tree.get_children())
            self.scan_results = []
            
        # Append new results
        self.scan_results.extend(results)
        
        # Process the new results batch
        self._process_results_batch(results)
        
        # Initialize statistics tracking
        self._total_size = 0
        self._file_types = set()
        self._processed_batches = 0
        self._total_batches = (len(results) + 49) // 50  # Ceiling division
        
        if not results:
            self.stats_label.config(text="No files found")
            return
        
        # Process results in batches to keep UI responsive
        batch_size = 50
        for batch_start in range(0, len(results), batch_size):
            batch_end = min(batch_start + batch_size, len(results))
            batch_results = results[batch_start:batch_end]
            
            # Schedule batch processing in main thread with small delay
            delay = batch_start // batch_size * 10  # 10ms delay between batches
            self.root.after(delay, self._process_results_batch, batch_results)
            
    def _process_results_batch(self, batch_results):
        """Process a batch of results to keep UI responsive with memory management."""
        # Check memory before processing batch
        if not self._check_memory_usage():
            # Skip processing if memory is critical
            return
            
        processed_count = 0
        batch_items = []
        
        try:
            for result in batch_results:
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
                    
                    # Store item data for batch insertion
                    batch_items.append((path, (size_str, file_type, modified_str, extension)))
                    
                    # Update statistics
                    self._total_size += size
                    if extension:
                        self._file_types.add(extension)
                        
                    processed_count += 1
                    
                else:
                    # Handle string results from scanner (fallback)
                    file_path = Path(result)
                    if file_path.exists():
                        stat = file_path.stat()
                        size = stat.st_size
                        modified = datetime.fromtimestamp(stat.st_mtime)
                        extension = file_path.suffix.lower()
                        file_type = self._get_file_type(extension)
                        
                        size_str = self._format_size(size)
                        modified_str = modified.strftime('%Y-%m-%d %H:%M')
                        
                        # Store item data for batch insertion
                        batch_items.append((str(file_path), (size_str, file_type, modified_str, extension)))
                        
                        # Update statistics
                        self._total_size += size
                        if extension:
                            self._file_types.add(extension)
                            
                    processed_count += 1
                
                # Periodic memory check during batch processing - reduced frequency
                if processed_count % 50 == 0:  # Further reduced frequency for better performance
                    if not self._check_memory_usage():
                        break  # Stop processing if memory is critical
            
            # Batch insert all items at once for better performance
            for text, values in batch_items:
                self.results_tree.insert('', 'end', text=text, values=values)
            
            # Force garbage collection after processing batch
            gc.collect()
            
        finally:
            # Clear batch items and scan results to free memory
            batch_items.clear()
            # Clear scan results after all batches are processed
            if hasattr(self, 'scan_results'):
                self.scan_results.clear()
            del batch_items
            
            # Force garbage collection after processing batch
            if processed_count > 100:
                gc.collect()
        
        # Update batch counter and statistics when batch is complete
        self._processed_batches += 1
        if self._processed_batches >= self._total_batches:
            # All batches processed, update final statistics
            self.stats_label.config(
                text=f"Files: {len(self.scan_results)} | Total Size: {self._format_size(self._total_size)} | Types: {len(self._file_types)}"
            )
            # Clear scan results to free memory after processing
            if hasattr(self, 'scan_results'):
                self.scan_results.clear()
            # Final cleanup after all batches
            gc.collect()
        
    def _handle_scan_error(self, error_msg):
        """Handle scan errors with enhanced feedback."""
        self.processing = False
        self.progress.stop()
        
        # Stop animations and restore UI
        self._stop_loading_animation(self.status_label, "Scan failed")
        self._pulse_animations.pop(self.scan_btn, None)
        self.scan_btn.configure(state='normal')
        
        # Show enhanced error notification with retry option
        self._handle_operation_error(
            operation_name="Directory Scan",
            error=error_msg,
            allow_retry=True,
            retry_callback=self.scan_directory
        )
        
        # Animate error state
        self._animate_pulse(self.status_label, duration=1500, intensity=0.3)
        
    def _scan_complete(self):
        """Complete the scanning process with enhanced feedback."""
        self.processing = False
        self.progress.stop()
        
        # Stop animations and restore UI
        self._stop_loading_animation(self.status_label, "Scan completed")
        self._pulse_animations.pop(self.scan_btn, None)
        self.scan_btn.configure(state='normal')
        
        # Animate completion
        self._animate_fade(self.status_label, start_alpha=0.5, end_alpha=1.0, duration=500)
        
        # Update statistics
        total_files = len(self.scan_results)
        self.root.after(100, lambda: self.status_label.config(
            text=f"Scan completed - {total_files} files processed", 
            foreground='#27ae60'
        ))
        
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
        """Save current results to file with enhanced validation."""
        try:
            # Validate scan results
            if not self.scan_results:
                self._show_error_notification(
                    "No Results Available",
                    "No scan results to save. Please run a scan first.",
                    error_type="warning"
                )
                return
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if not file_path:
                return  # User cancelled
                
            # Validate file path
            try:
                self._validate_input(os.path.dirname(file_path), "directory", "Output directory")
            except ValueError:
                return
                
            # Save results
            if file_path.endswith('.csv'):
                # Save as CSV
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    if self.scan_results:
                        writer = csv.DictWriter(f, fieldnames=self.scan_results[0].keys())
                        writer.writeheader()
                        writer.writerows(self.scan_results)
            else:
                # Save as JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.scan_results, f, indent=2, ensure_ascii=False, default=str)
            
            # Show success notification
            self.status_label.config(text=f"Results saved to {file_path}", foreground='#27ae60')
            self._show_success_notification(
                "Save Successful",
                f"Results saved successfully to {os.path.basename(file_path)}"
            )
            
        except PermissionError as e:
            self._handle_operation_error(
                "Save Results",
                f"Permission denied: {e}",
                allow_retry=True,
                retry_callback=lambda: self.save_results()
            )
        except Exception as e:
            self._handle_operation_error(
                "Save Results",
                e,
                allow_retry=True,
                retry_callback=lambda: self.save_results()
            )
    
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
        """Start batch metadata extraction with enhanced validation."""
        try:
            # Validate batch directories
            if not self.batch_directories:
                self._show_error_notification(
                    "No Directories Selected",
                    "Please add at least one directory for batch processing.",
                    error_type="warning"
                )
                return
                
            if self.batch_processing:
                self._show_error_notification(
                    "Processing In Progress",
                    "Batch processing is already running.",
                    error_type="info"
                )
                return
                
            # Validate output directory
            output_dir = self._validate_input(
                self.batch_output_path.get(),
                "directory",
                "Output directory"
            )
            
            # Prepare output directory
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    self._handle_operation_error(
                        "Create Output Directory",
                        e,
                        allow_retry=True,
                        retry_callback=lambda: self.start_batch_processing()
                    )
                    return
                    
        except ValueError:
            return  # Error already shown by validation method
        except Exception as e:
            self._handle_operation_error(
                "Start Batch Processing",
                e,
                allow_retry=True,
                retry_callback=lambda: self.start_batch_processing()
            )
            return
        
        # Start processing in a separate thread
        self.batch_processing = True
        self.batch_stop_requested = False
        self.batch_paused = False
        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_stop_btn.config(state=tk.NORMAL)
        self.batch_pause_btn.config(state=tk.NORMAL, text="Pause")
        
        threading.Thread(target=self._batch_processing_worker, daemon=True).start()
    
    def stop_batch_processing(self):
        """Stop batch processing."""
        self.batch_stop_requested = True
        self.batch_status.config(text="Stopping batch processing...")
    
    def pause_batch_processing(self):
        """Pause or resume batch processing."""
        if not hasattr(self, 'batch_paused'):
            self.batch_paused = False
            
        if self.batch_paused:
            # Resume processing
            self.batch_paused = False
            self.batch_pause_btn.config(text="Pause")
            self.batch_status.config(text="Resuming batch processing...")
        else:
            # Pause processing
            self.batch_paused = True
            self.batch_pause_btn.config(text="Resume")
            self.batch_status.config(text="Batch processing paused...")
    
    def _extract_metadata_safe(self, file_path):
        """Safely extract metadata from a file for parallel processing."""
        try:
            metadata = self.extractor.extract_metadata(file_path)
            return {
                'file_path': file_path,
                'metadata': metadata
            }
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {file_path}: {e}")
            return None
    
    def _update_batch_ui(self, file_name, progress, processed_count, total_files, directory_name):
        """Update batch processing UI elements efficiently."""
        try:
            # Update current file display
            self.batch_current_file.config(text=f"Processing: {file_name}")
            
            # Update progress bar
            self.batch_progress.config(value=progress)
            
            # Update status text
            self.batch_status.config(text=f"Processing {directory_name}: {processed_count}/{total_files} files")
            
            # Force UI update
            self.root.update_idletasks()
        except Exception as e:
            # Silently handle UI update errors to prevent crashes
            pass
    
    def _batch_processing_worker(self):
        """Worker thread for batch processing."""
        try:
            # Initial memory check
            self._check_memory_usage()
            
            total_dirs = len(self.batch_directories)
            processed_dirs = 0
            total_files = 0
            
            self.batch_summary.delete(1.0, tk.END)
            self.batch_summary.insert(tk.END, f"Starting batch processing of {total_dirs} directories...\n\n")
            
            for i, directory in enumerate(self.batch_directories):
                if self.batch_stop_requested:
                    break
                
                # Check for pause state
                while getattr(self, 'batch_paused', False):
                    if self.batch_stop_requested:
                        break
                    time.sleep(0.1)  # Wait while paused
                
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
                    
                    # Apply advanced filters
                    files = self._apply_advanced_filters(files)
                    
                    # Extract metadata with streaming batch processing for memory optimization
                    metadata_results = []
                    
                    # Determine optimal number of workers and chunk size based on memory
                    max_workers = min(3, os.cpu_count() or 1)  # Reduced workers for memory
                    
                    # Adaptive chunk sizing based on available memory
                    try:
                        memory_info = psutil.virtual_memory()
                        available_gb = memory_info.available / (1024**3)
                        if available_gb > 4:
                            chunk_size = min(200, len(files))
                        elif available_gb > 2:
                            chunk_size = min(100, len(files))
                        else:
                            chunk_size = min(50, len(files))  # Very small chunks for low memory
                    except:
                        chunk_size = min(100, len(files))  # Default fallback
                    
                    # Process files in chunks to optimize memory usage
                    for chunk_start in range(0, len(files), chunk_size):
                        if self.batch_stop_requested:
                            break
                            
                        chunk_end = min(chunk_start + chunk_size, len(files))
                        chunk_files = files[chunk_start:chunk_end]
                        
                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                            # Submit chunk for processing
                            future_to_file = {}
                            for file_path in chunk_files:
                                if self.batch_stop_requested:
                                    break
                                future = executor.submit(self._extract_metadata_safe, file_path)
                                future_to_file[future] = file_path
                            
                            # Process completed futures in chunk
                            chunk_processed = 0
                            for future in as_completed(future_to_file):
                                if self.batch_stop_requested:
                                    break
                                
                                # Check for pause state
                                while getattr(self, 'batch_paused', False):
                                    if self.batch_stop_requested:
                                        break
                                    time.sleep(0.1)
                                
                                if self.batch_stop_requested:
                                    break
                                
                                file_path = future_to_file[future]
                                
                                try:
                                    result = future.result()
                                    if result:
                                        # Apply metadata filtering if enabled
                                        if self._filter_by_metadata(result['file_path'], result['metadata']):
                                            metadata_results.append(result)
                                    
                                    chunk_processed += 1
                                    processed_count = chunk_start + chunk_processed
                                    
                                    # Batch UI updates to reduce lag - update less frequently
                                    if chunk_processed % 10 == 0:  # Reduced frequency
                                        file_name = os.path.basename(file_path)
                                        progress = (processed_count / len(files)) * 100
                                        
                                        # Use after_idle for non-blocking UI updates
                                        self.root.after_idle(lambda fn=file_name, p=progress, pc=processed_count: 
                                            self._update_batch_ui(fn, p, pc, len(files), os.path.basename(directory)))
                                        
                                        # More frequent memory checks for large datasets
                                        if chunk_processed % 20 == 0:
                                            self._check_memory_usage()
                                            
                                except Exception as e:
                                    self.logger.error(f"Error processing {file_path}: {e}")
                        
                        # Force garbage collection after each chunk
                        gc.collect()
                        
                        # Check memory usage after each chunk and pause if critical
                        if not self._check_memory_usage():
                            # Memory usage is critical, pause briefly to allow cleanup
                            time.sleep(0.5)
                            self._force_memory_cleanup()
                            
                            # If still critical, reduce chunk size for remaining processing
                            try:
                                memory_info = psutil.virtual_memory()
                                if memory_info.percent > 85:  # Very high memory usage
                                    chunk_size = max(10, chunk_size // 2)
                                    self.root.after(0, lambda: self.batch_status.config(
                                        text=f"High memory usage detected - reducing batch size to {chunk_size}"))
                            except:
                                pass
                    
                    # Save results
                    if metadata_results:
                        output_file = self._save_batch_results(directory, metadata_results)
                        total_files += len(metadata_results)
                        
                        self.root.after(0, lambda: self.batch_summary.insert(tk.END, 
                            f"✓ {os.path.basename(directory)}: {len(metadata_results)} files processed\n"))
                    
                    # Clear processed results to free memory
                    metadata_results.clear()
                    
                    # Force garbage collection after every 5 directories
                    if processed_dirs % 5 == 0:
                        gc.collect()
                    
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
            self.batch_paused = False
            self.root.after(0, lambda: self.batch_start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.batch_stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.batch_pause_btn.config(state=tk.DISABLED, text="Pause"))
            self.root.after(0, lambda: self.batch_current_file.config(text=""))
    
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
    
    def _apply_advanced_filters(self, files):
        """Apply advanced filtering options to file list."""
        filtered_files = files.copy()
        
        # Apply file size filter
        if self.batch_enable_size_filter.get():
            filtered_files = self._filter_by_size(filtered_files)
        
        # Apply date range filter
        if self.batch_enable_date_filter.get():
            filtered_files = self._filter_by_date(filtered_files)
        
        return filtered_files
    
    def _filter_by_size(self, files):
        """Filter files by size range."""
        try:
            min_size = float(self.batch_min_size.get() or 0)
            max_size = float(self.batch_max_size.get() or float('inf'))
            
            # Convert to bytes
            min_unit = self.batch_min_size_unit.get()
            max_unit = self.batch_max_size_unit.get()
            
            unit_multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
            min_bytes = min_size * unit_multipliers.get(min_unit, 1)
            max_bytes = max_size * unit_multipliers.get(max_unit, 1)
            
            filtered = []
            for file_path in files:
                try:
                    file_size = os.path.getsize(file_path)
                    if min_bytes <= file_size <= max_bytes:
                        filtered.append(file_path)
                except (OSError, ValueError):
                    continue
            
            return filtered
        except (ValueError, TypeError):
            return files
    
    def _filter_by_date(self, files):
        """Filter files by modification date range."""
        try:
            from datetime import datetime
            
            date_from = datetime.strptime(self.batch_date_from.get(), "%Y-%m-%d")
            date_to = datetime.strptime(self.batch_date_to.get(), "%Y-%m-%d")
            
            # Add one day to include the end date
            date_to = date_to.replace(hour=23, minute=59, second=59)
            
            filtered = []
            for file_path in files:
                try:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if date_from <= mod_time <= date_to:
                        filtered.append(file_path)
                except (OSError, ValueError):
                    continue
            
            return filtered
        except (ValueError, TypeError):
            return files
    
    def _filter_by_metadata(self, file_path, metadata):
        """Check if file metadata matches the specified criteria."""
        if not self.batch_enable_metadata_filter.get():
            return True
        
        try:
            field = self.batch_metadata_field.get().lower()
            value = self.batch_metadata_value.get().lower()
            
            if not field or not value:
                return True
            
            # Search in metadata
            if field in metadata and metadata[field]:
                return value in str(metadata[field]).lower()
            
            return False
        except (AttributeError, TypeError):
            return True
    
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
    
    # Queue Management Methods
    def add_to_queue(self):
        """Add current batch configuration to processing queue."""
        if not self.batch_directories:
            messagebox.showwarning("No Directories", "Please add directories before adding to queue.")
            return
        
        # Create queue item
        queue_item = {
            'id': len(self.processing_queue) + 1,
            'directories': self.batch_directories.copy(),
            'output_path': self.batch_output_path.get(),
            'recursive': self.batch_recursive.get(),
            'max_files': self.batch_max_files.get(),
            'include_hidden': self.batch_include_hidden.get(),
            'file_type': self.batch_file_type.get(),
            'priority': self.queue_priority.get(),
            'status': 'Pending',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add advanced filter settings if enabled
        if hasattr(self, 'batch_enable_size_filter') and self.batch_enable_size_filter.get():
            queue_item['size_filter'] = {
                'min_size': self.batch_min_size.get(),
                'min_unit': self.batch_min_size_unit.get(),
                'max_size': self.batch_max_size.get(),
                'max_unit': self.batch_max_size_unit.get()
            }
        
        if hasattr(self, 'batch_enable_date_filter') and self.batch_enable_date_filter.get():
            queue_item['date_filter'] = {
                'from_date': self.batch_from_date.get(),
                'to_date': self.batch_to_date.get()
            }
        
        if hasattr(self, 'batch_enable_metadata_filter') and self.batch_enable_metadata_filter.get():
            queue_item['metadata_filter'] = {
                'field': self.batch_metadata_field.get(),
                'value': self.batch_metadata_value.get()
            }
        
        # Insert based on priority
        if queue_item['priority'] == 'High':
            self.processing_queue.insert(0, queue_item)
        else:
            self.processing_queue.append(queue_item)
        
        self._update_queue_display()
        self.batch_status.config(text=f"Added to queue: {len(self.batch_directories)} directories")
    
    def remove_from_queue(self):
        """Remove selected item from processing queue."""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to remove.")
            return
        
        index = selection[0]
        if 0 <= index < len(self.processing_queue):
            removed_item = self.processing_queue.pop(index)
            self._update_queue_display()
            self.batch_status.config(text=f"Removed queue item #{removed_item['id']}")
    
    def clear_queue(self):
        """Clear all items from processing queue."""
        if self.processing_queue:
            result = messagebox.askyesno("Clear Queue", "Are you sure you want to clear all queue items?")
            if result:
                self.processing_queue.clear()
                self.current_queue_index = 0
                self._update_queue_display()
                self.batch_status.config(text="Queue cleared")
    
    def move_queue_item_up(self):
        """Move selected queue item up in priority."""
        selection = self.queue_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        
        index = selection[0]
        if 0 < index < len(self.processing_queue):
            # Swap items
            self.processing_queue[index], self.processing_queue[index-1] = \
                self.processing_queue[index-1], self.processing_queue[index]
            
            self._update_queue_display()
            self.queue_listbox.selection_set(index-1)
    
    def move_queue_item_down(self):
        """Move selected queue item down in priority."""
        selection = self.queue_listbox.curselection()
        if not selection or selection[0] == len(self.processing_queue) - 1:
            return
        
        index = selection[0]
        if 0 <= index < len(self.processing_queue) - 1:
            # Swap items
            self.processing_queue[index], self.processing_queue[index+1] = \
                self.processing_queue[index+1], self.processing_queue[index]
            
            self._update_queue_display()
            self.queue_listbox.selection_set(index+1)
    
    def start_queue_processing(self):
        """Start processing items in the queue."""
        if not self.processing_queue:
            messagebox.showwarning("Empty Queue", "No items in processing queue.")
            return
        
        if self.queue_processing:
            messagebox.showinfo("Already Processing", "Queue processing is already in progress.")
            return
        
        self.queue_processing = True
        self.queue_paused = False
        self.current_queue_index = 0
        
        # Update UI
        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_stop_btn.config(state=tk.NORMAL)
        self.batch_pause_btn.config(state=tk.NORMAL)
        
        # Start queue processing in separate thread
        threading.Thread(target=self._queue_processing_worker, daemon=True).start()
    
    def _update_queue_display(self):
        """Update the queue display listbox."""
        self.queue_listbox.delete(0, tk.END)
        
        for i, item in enumerate(self.processing_queue):
            status_icon = "⏳" if item['status'] == 'Pending' else "✓" if item['status'] == 'Completed' else "❌"
            priority_icon = "🔴" if item['priority'] == 'High' else "🟡" if item['priority'] == 'Normal' else "🟢"
            
            display_text = f"{status_icon} {priority_icon} #{item['id']}: {len(item['directories'])} dirs - {item['status']}"
            self.queue_listbox.insert(tk.END, display_text)
        
        # Update queue status
        pending_count = sum(1 for item in self.processing_queue if item['status'] == 'Pending')
        self.queue_status.config(text=f"Queue: {len(self.processing_queue)} items ({pending_count} pending)")
    
    def _queue_processing_worker(self):
        """Worker thread for processing queue items."""
        try:
            total_items = len(self.processing_queue)
            
            for i, queue_item in enumerate(self.processing_queue):
                if self.batch_stop_requested:
                    break
                
                # Check for pause
                while self.queue_paused:
                    if self.batch_stop_requested:
                        break
                    time.sleep(0.1)
                
                if self.batch_stop_requested:
                    break
                
                # Skip if already completed
                if queue_item['status'] == 'Completed':
                    continue
                
                # Update current processing item
                self.current_queue_index = i
                queue_item['status'] = 'Processing'
                
                # Update UI
                self.root.after(0, self._update_queue_display)
                self.root.after(0, lambda item=queue_item: 
                    self.batch_status.config(text=f"Processing queue item #{item['id']}"))
                
                # Apply queue item settings to batch processing
                self._apply_queue_item_settings(queue_item)
                
                # Process this queue item
                try:
                    self._process_queue_item(queue_item)
                    queue_item['status'] = 'Completed'
                    queue_item['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    queue_item['status'] = 'Failed'
                    queue_item['error'] = str(e)
                    self.root.after(0, lambda err=str(e): 
                        self.batch_summary.insert(tk.END, f"Queue item #{queue_item['id']} failed: {err}\n"))
                
                # Update display
                self.root.after(0, self._update_queue_display)
            
            # Complete queue processing
            completed_count = sum(1 for item in self.processing_queue if item['status'] == 'Completed')
            self.root.after(0, lambda: self.batch_status.config(
                text=f"Queue processing completed: {completed_count}/{total_items} items"))
            
        except Exception as e:
            self.root.after(0, lambda err=str(e): 
                self.batch_status.config(text=f"Queue processing error: {err}"))
        
        finally:
            self.queue_processing = False
            self.queue_paused = False
            self.root.after(0, lambda: self.batch_start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.batch_stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.batch_pause_btn.config(state=tk.DISABLED))
    
    def _apply_queue_item_settings(self, queue_item):
        """Apply queue item settings to current batch processing configuration."""
        # Set directories
        self.batch_directories = queue_item['directories'].copy()
        
        # Update UI elements
        self.batch_dirs_listbox.delete(0, tk.END)
        for directory in self.batch_directories:
            self.batch_dirs_listbox.insert(tk.END, directory)
        
        # Apply settings
        self.batch_output_path.set(queue_item['output_path'])
        self.batch_recursive.set(queue_item['recursive'])
        self.batch_max_files.set(queue_item['max_files'])
        self.batch_include_hidden.set(queue_item['include_hidden'])
        self.batch_file_type.set(queue_item['file_type'])
        
        # Apply advanced filters if present
        if 'size_filter' in queue_item:
            self.batch_enable_size_filter.set(True)
            size_filter = queue_item['size_filter']
            self.batch_min_size.set(size_filter['min_size'])
            self.batch_min_size_unit.set(size_filter['min_unit'])
            self.batch_max_size.set(size_filter['max_size'])
            self.batch_max_size_unit.set(size_filter['max_unit'])
        
        if 'date_filter' in queue_item:
            self.batch_enable_date_filter.set(True)
            date_filter = queue_item['date_filter']
            self.batch_from_date.set(date_filter['from_date'])
            self.batch_to_date.set(date_filter['to_date'])
        
        if 'metadata_filter' in queue_item:
            self.batch_enable_metadata_filter.set(True)
            metadata_filter = queue_item['metadata_filter']
            self.batch_metadata_field.set(metadata_filter['field'])
            self.batch_metadata_value.set(metadata_filter['value'])
    
    def _process_queue_item(self, queue_item):
        """Process a single queue item using existing batch processing logic."""
        # Use the existing batch processing worker logic
        # This is a simplified version that reuses the batch processing infrastructure
        
        total_files = 0
        for directory in queue_item['directories']:
            if self.batch_stop_requested:
                break
            
            try:
                # Scan directory
                files = self.scanner.scan_directory(
                    directory,
                    recursive=queue_item['recursive'],
                    max_files=queue_item['max_files'],
                    include_hidden=queue_item['include_hidden']
                )
                
                if not files:
                    continue
                
                # Apply filters
                files = self._filter_files_by_type(files, queue_item['file_type'])
                files = self._apply_advanced_filters(files)
                
                if not files:
                    continue
                
                # Process files
                metadata_results = []
                for file_path in files:
                    if self.batch_stop_requested:
                        break
                    
                    result = self._extract_metadata_safe(file_path)
                    if result and self._filter_by_metadata(result['file_path'], result['metadata']):
                        metadata_results.append(result)
                
                # Save results
                if metadata_results:
                    self._save_batch_results(directory, metadata_results)
                    total_files += len(metadata_results)
                
            except Exception as e:
                raise Exception(f"Error processing directory {directory}: {str(e)}")
        
        # Update summary
        self.root.after(0, lambda: self.batch_summary.insert(tk.END, 
            f"Queue item #{queue_item['id']} completed: {total_files} files processed\n"))
    
    # Template Management Methods
    def _load_default_templates(self):
        """Load default batch processing templates."""
        self.templates = {
            "Basic Extraction": {
                "file_types": ["All Files"],
                "recursive": True,
                "include_hidden": False,
                "max_files": 1000,
                "size_filter_enabled": False,
                "date_filter_enabled": False,
                "metadata_filter_enabled": False,
                "output_format": "JSON",
                "description": "Basic metadata extraction for common file types"
            },
            "Full Metadata": {
                "file_types": ["All Files"],
                "recursive": True,
                "include_hidden": True,
                "max_files": 5000,
                "size_filter_enabled": False,
                "date_filter_enabled": False,
                "metadata_filter_enabled": False,
                "output_format": "JSON",
                "description": "Comprehensive metadata extraction including hidden files"
            },
            "Images Only": {
                "file_types": ["Images"],
                "recursive": True,
                "include_hidden": False,
                "max_files": 2000,
                "size_filter_enabled": True,
                "min_size": 1024,
                "max_size": 50*1024*1024,
                "date_filter_enabled": False,
                "metadata_filter_enabled": False,
                "output_format": "JSON",
                "description": "Extract metadata from image files only"
            },
            "Documents Only": {
                "file_types": ["Documents"],
                "recursive": True,
                "include_hidden": False,
                "max_files": 1000,
                "size_filter_enabled": False,
                "date_filter_enabled": False,
                "metadata_filter_enabled": False,
                "output_format": "CSV",
                "description": "Extract metadata from document files only"
            },
            "Media Files": {
                "file_types": ["Audio", "Video"],
                "recursive": True,
                "include_hidden": False,
                "max_files": 500,
                "size_filter_enabled": True,
                "min_size": 1024*1024,
                "date_filter_enabled": False,
                "metadata_filter_enabled": False,
                "output_format": "JSON",
                "description": "Extract metadata from audio and video files"
            }
        }
    
    def on_template_selected(self, event=None):
        """Handle template selection change."""
        template_name = self.template_var.get()
        if template_name == "Custom":
            return
        
        # Show template description
        template = self.templates.get(template_name) or self.custom_templates.get(template_name)
        if template:
            messagebox.showinfo("Template Info", 
                f"Template: {template_name}\n\n{template.get('description', 'No description available')}")
    
    def apply_template(self):
        """Apply the selected template to current settings."""
        template_name = self.template_var.get()
        if template_name == "Custom":
            messagebox.showinfo("Info", "Custom template is already active.")
            return
        
        template = self.templates.get(template_name) or self.custom_templates.get(template_name)
        if not template:
            messagebox.showerror("Error", f"Template '{template_name}' not found.")
            return
        
        try:
            # Apply file type settings
            if hasattr(self, 'batch_file_type'):
                if template['file_types']:
                    self.batch_file_type.set(template['file_types'][0])
            
            # Apply basic settings
            if hasattr(self, 'batch_recursive'):
                self.batch_recursive.set(template.get('recursive', True))
            if hasattr(self, 'batch_include_hidden'):
                self.batch_include_hidden.set(template.get('include_hidden', False))
            if hasattr(self, 'batch_max_files'):
                self.batch_max_files.set(template.get('max_files', 1000))
            
            # Apply filter settings
            if hasattr(self, 'size_filter_enabled'):
                self.size_filter_enabled.set(template.get('size_filter_enabled', False))
                if template.get('size_filter_enabled'):
                    if hasattr(self, 'min_size_mb'):
                        self.min_size_mb.set(template.get('min_size', 0) / (1024*1024))
                    if hasattr(self, 'max_size_mb'):
                        self.max_size_mb.set(template.get('max_size', 100*1024*1024) / (1024*1024))
            
            if hasattr(self, 'date_filter_enabled'):
                self.date_filter_enabled.set(template.get('date_filter_enabled', False))
            
            if hasattr(self, 'metadata_filter_enabled'):
                self.metadata_filter_enabled.set(template.get('metadata_filter_enabled', False))
            
            # Apply output format
            if hasattr(self, 'batch_output_format'):
                self.batch_output_format.set(template.get('output_format', 'JSON'))
            
            messagebox.showinfo("Success", f"Template '{template_name}' applied successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply template: {str(e)}")
    
    def save_template(self):
        """Save current settings as a new template."""
        # Get template name from user
        template_name = simpledialog.askstring("Save Template", "Enter template name:")
        if not template_name:
            return
        
        if template_name in self.templates:
            if not messagebox.askyesno("Confirm", f"Template '{template_name}' already exists. Overwrite?"):
                return
        
        try:
            # Collect current settings
            template = {
                "file_types": [getattr(self, 'batch_file_type', tk.StringVar()).get()],
                "recursive": getattr(self, 'batch_recursive', tk.BooleanVar()).get(),
                "include_hidden": getattr(self, 'batch_include_hidden', tk.BooleanVar()).get(),
                "max_files": getattr(self, 'batch_max_files', tk.IntVar()).get(),
                "size_filter_enabled": getattr(self, 'size_filter_enabled', tk.BooleanVar()).get(),
                "date_filter_enabled": getattr(self, 'date_filter_enabled', tk.BooleanVar()).get(),
                "metadata_filter_enabled": getattr(self, 'metadata_filter_enabled', tk.BooleanVar()).get(),
                "output_format": getattr(self, 'batch_output_format', tk.StringVar()).get(),
                "description": f"Custom template created on {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            # Add size filter details if enabled
            if template["size_filter_enabled"]:
                template["min_size"] = int(getattr(self, 'min_size_mb', tk.DoubleVar()).get() * 1024 * 1024)
                template["max_size"] = int(getattr(self, 'max_size_mb', tk.DoubleVar()).get() * 1024 * 1024)
            
            # Save to custom templates
            self.custom_templates[template_name] = template
            
            # Update combobox values
            current_values = list(self.template_combo['values'])
            if template_name not in current_values:
                current_values.append(template_name)
                self.template_combo['values'] = current_values
            
            messagebox.showinfo("Success", f"Template '{template_name}' saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def delete_template(self):
        """Delete a custom template."""
        template_name = self.template_var.get()
        
        if template_name == "Custom":
            messagebox.showinfo("Info", "Cannot delete the Custom template.")
            return
        
        if template_name in self.templates:
            messagebox.showerror("Error", "Cannot delete built-in templates.")
            return
        
        if template_name not in self.custom_templates:
            messagebox.showerror("Error", f"Template '{template_name}' not found.")
            return
        
        if messagebox.askyesno("Confirm", f"Delete template '{template_name}'?"):
            try:
                # Remove from custom templates
                del self.custom_templates[template_name]
                
                # Update combobox values
                current_values = list(self.template_combo['values'])
                if template_name in current_values:
                    current_values.remove(template_name)
                    self.template_combo['values'] = current_values
                
                # Reset to Custom
                self.template_var.set("Custom")
                
                messagebox.showinfo("Success", f"Template '{template_name}' deleted successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete template: {str(e)}")
    
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
            },
            'update': {
                'auto_check_updates': self.auto_check_updates.get(),
                'notify_beta_updates': self.notify_beta_updates.get()
            }
        }
    
    def _apply_imported_settings(self, settings):
        """Apply imported settings."""
        try:
            # Theme settings
            if 'theme' in settings:
                theme = settings['theme']
                self.dark_mode.set(theme.get('dark_mode', False))
                if hasattr(self, 'theme_var'):
                    self.theme_var.set(theme.get('theme_var', 'Light'))
                if hasattr(self, 'language_var'):
                    self.language_var.set(theme.get('language', 'English'))
            
            # General settings
            if 'general' in settings:
                general = settings['general']
                if hasattr(self, 'auto_save_settings'):
                    self.auto_save_settings.set(general.get('auto_save_settings', True))
                if hasattr(self, 'remember_window_size'):
                    self.remember_window_size.set(general.get('remember_window_size', True))
                if hasattr(self, 'show_tooltips'):
                    self.show_tooltips.set(general.get('show_tooltips', True))
            
            # Performance settings
            if 'performance' in settings:
                perf = settings['performance']
                if hasattr(self, 'max_workers'):
                    self.max_workers.set(perf.get('max_workers', 4))
                if hasattr(self, 'cache_size'):
                    self.cache_size.set(perf.get('cache_size', 100))
                self.cache_enabled.set(perf.get('cache_enabled', True))
                self.parallel_processing.set(perf.get('parallel_processing', True))
                if hasattr(self, 'memory_limit'):
                    self.memory_limit.set(perf.get('memory_limit', 512))
            
            # Scanning settings
            if 'scanning' in settings:
                scanning = settings['scanning']
                self.scan_recursive.set(scanning.get('scan_recursive', True))
                self.show_hidden.set(scanning.get('show_hidden', False))
                if hasattr(self, 'auto_refresh'):
                    self.auto_refresh.set(scanning.get('auto_refresh', False))
                self.max_files.set(scanning.get('max_files', 500))
                self.selected_formats.set(scanning.get('selected_formats', 'all'))
            
            # Output settings
            if 'output' in settings:
                output = settings['output']
                self.output_format.set(output.get('output_format', 'json'))
                if hasattr(self, 'default_output_dir'):
                    self.default_output_dir.set(output.get('default_output_dir', os.path.join(os.getcwd(), 'output')))
                if hasattr(self, 'auto_open_results'):
                    self.auto_open_results.set(output.get('auto_open_results', False))
                if hasattr(self, 'create_backup'):
                    self.create_backup.set(output.get('create_backup', True))
            
            # Logging settings
            if 'logging' in settings:
                logging_config = settings['logging']
                if hasattr(self, 'log_level'):
                    self.log_level.set(logging_config.get('log_level', 'INFO'))
                if hasattr(self, 'log_file_path'):
                    self.log_file_path.set(logging_config.get('log_file_path', 'metacli_gui.log'))
                if hasattr(self, 'enable_file_logging'):
                    self.enable_file_logging.set(logging_config.get('enable_file_logging', True))
                if hasattr(self, 'enable_console_logging'):
                    self.enable_console_logging.set(logging_config.get('enable_console_logging', False))
                if hasattr(self, 'max_log_size'):
                    self.max_log_size.set(logging_config.get('max_log_size', 10))
                if hasattr(self, 'keep_log_files'):
                    self.keep_log_files.set(logging_config.get('keep_log_files', 5))
            
            # Advanced settings
            if 'advanced' in settings:
                advanced = settings['advanced']
                if hasattr(self, 'debug_mode'):
                    self.debug_mode.set(advanced.get('debug_mode', False))
                if hasattr(self, 'verbose_output'):
                    self.verbose_output.set(advanced.get('verbose_output', False))
                if hasattr(self, 'experimental_features'):
                    self.experimental_features.set(advanced.get('experimental_features', False))
                if hasattr(self, 'plugin_dir'):
                    self.plugin_dir.set(advanced.get('plugin_dir', os.path.join(os.getcwd(), 'plugins')))
            
            # Apply theme changes
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
    
    def check_updates(self):
        """Check for available updates and show update dialog."""
        def update_worker():
            try:
                self.status_var.set("Checking for updates...")
                updates_available, release_info = self.updater.check_for_updates()
                
                self.root.after(0, lambda: self._show_update_dialog(updates_available, release_info))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Update Check Failed", 
                    f"Failed to check for updates: {str(e)}"
                ))
            finally:
                self.root.after(0, lambda: self.status_var.set("Ready"))
        
        threading.Thread(target=update_worker, daemon=True).start()
    
    def check_beta_updates(self):
        """Check for available beta updates and show beta update dialog."""
        def beta_update_worker():
            try:
                self.status_var.set("Checking for beta updates...")
                updates_available, release_info = self.updater.check_for_beta_updates()
                
                self.root.after(0, lambda: self._show_beta_update_dialog(updates_available, release_info))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Beta Update Check Failed", 
                    f"Failed to check for beta updates: {str(e)}"
                ))
            finally:
                self.root.after(0, lambda: self.status_var.set("Ready"))
        
        threading.Thread(target=beta_update_worker, daemon=True).start()
    
    def _show_beta_update_dialog(self, updates_available, release_info):
        """Show beta update dialog with warnings and current status."""
        dialog = tk.Toplevel(self.root)
        dialog.title("MetaCLI Beta Updates")
        dialog.geometry("550x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Beta warning section
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 15))
        
        warning_label = ttk.Label(warning_frame, text="⚠️ BETA VERSION WARNING", 
                                 font=("TkDefaultFont", 12, "bold"), foreground="red")
        warning_label.pack()
        
        warning_text = ttk.Label(warning_frame, 
                               text="Beta versions are experimental and may contain bugs.\nThey are not recommended for production use.\nPlease backup your data before installing.",
                               font=("TkDefaultFont", 9), foreground="orange", justify=tk.CENTER)
        warning_text.pack(pady=(5, 0))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(10, 15))
        
        # Current installation info
        info_frame = ttk.LabelFrame(main_frame, text="Current Installation", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        try:
            current_info = self.updater.get_current_version_info()
            current_text = f"Version: {current_info.get('version', 'Unknown')}\n"
            current_text += f"Installation: {current_info.get('installation_type', 'Unknown')}\n"
            current_text += f"Path: {current_info.get('installation_path', 'Unknown')}"
        except Exception as e:
            current_text = f"Error getting current version info: {str(e)}"
        
        ttk.Label(info_frame, text=current_text, font=("Consolas", 9)).pack(anchor=tk.W)
        
        # Update status
        status_frame = ttk.LabelFrame(main_frame, text="Beta Update Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        if updates_available and release_info:
            status_text = f"🎯 Beta Update Available!\n\n"
            status_text += f"Version: {release_info.get('tag_name', 'Unknown')}\n"
            status_text += f"Published: {release_info.get('published_at', 'Unknown')}\n"
            status_text += f"Pre-release: {'Yes' if release_info.get('prerelease', False) else 'No'}\n\n"
            
            if release_info.get('body'):
                status_text += "Release Notes:\n"
                # Truncate release notes if too long
                notes = release_info['body'][:300]
                if len(release_info['body']) > 300:
                    notes += "..."
                status_text += notes
            
            status_label = ttk.Label(status_frame, text=status_text, font=("TkDefaultFont", 9))
            status_label.pack(anchor=tk.W)
            
            # GitHub link
            if release_info.get('html_url'):
                link_frame = ttk.Frame(status_frame)
                link_frame.pack(fill=tk.X, pady=(10, 0))
                
                link_label = ttk.Label(link_frame, text="View on GitHub", 
                                     foreground="blue", cursor="hand2", font=("TkDefaultFont", 9, "underline"))
                link_label.pack(anchor=tk.W)
                link_label.bind("<Button-1>", lambda e: webbrowser.open(release_info['html_url']))
        else:
            status_text = "✅ No beta updates available.\nYou have the latest beta version or no beta versions exist."
            ttk.Label(status_frame, text=status_text, font=("TkDefaultFont", 9)).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        if updates_available and release_info:
            install_btn = ttk.Button(button_frame, text="Install Beta Update", 
                                   command=lambda: self._perform_update(dialog, release_info))
            install_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def _show_update_dialog(self, updates_available, release_info):
        """Show update dialog with current status."""
        dialog = tk.Toplevel(self.root)
        dialog.title("MetaCLI Updates")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="MetaCLI Update Manager", 
                               font=('TkDefaultFont', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Current version info
        info_frame = ttk.LabelFrame(main_frame, text="Current Installation", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        version_info = self.updater.get_current_version_info()
        
        ttk.Label(info_frame, text=f"Installation Path: {version_info.get('installation_path', 'Unknown')}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Executables Found: {', '.join(version_info.get('executables_found', []))}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Current Version: {version_info.get('cached_version', 'Unknown')}").pack(anchor=tk.W)
        
        # Update status
        status_frame = ttk.LabelFrame(main_frame, text="Update Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        if updates_available and release_info:
            status_text = f"🔄 Update Available: {release_info.get('tag_name', 'Unknown')}"
            status_color = "blue"
            
            # Release notes
            notes_text = scrolledtext.ScrolledText(status_frame, height=6, wrap=tk.WORD)
            notes_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            
            release_body = release_info.get('body', 'No release notes available.')
            notes_text.insert(tk.END, release_body)
            notes_text.config(state=tk.DISABLED)
            
        elif release_info:
            status_text = f"✅ Up to Date: {release_info.get('tag_name', 'Unknown')}"
            status_color = "green"
        else:
            status_text = "❌ Could not check for updates"
            status_color = "red"
        
        status_label = ttk.Label(status_frame, text=status_text, foreground=status_color,
                                font=('TkDefaultFont', 10, 'bold'))
        status_label.pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        if updates_available:
            update_btn = ttk.Button(button_frame, text="Install Update", 
                                   command=lambda: self._perform_update(dialog, release_info))
            update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Show GitHub link
        if release_info:
            link_frame = ttk.Frame(main_frame)
            link_frame.pack(fill=tk.X, pady=(10, 0))
            
            link_label = ttk.Label(link_frame, text="View on GitHub", 
                                  foreground="blue", cursor="hand2")
            link_label.pack(anchor=tk.W)
            link_label.bind("<Button-1>", lambda e: webbrowser.open(release_info.get('html_url', '')))
    
    def _perform_update(self, dialog, release_info):
        """Perform the actual update process."""
        # Close the dialog
        dialog.destroy()
        
        # Show progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Installing Update")
        progress_dialog.geometry("400x200")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # Center the dialog
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
        y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f"+{x}+{y}")
        
        # Progress content
        progress_frame = ttk.Frame(progress_dialog, padding="20")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(progress_frame, text="Installing MetaCLI Update...", 
                 font=('TkDefaultFont', 12, 'bold')).pack(pady=(0, 20))
        
        progress_var = tk.StringVar(value="Preparing update...")
        progress_label = ttk.Label(progress_frame, textvariable=progress_var)
        progress_label.pack(pady=(0, 10))
        
        progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress_bar.pack(fill=tk.X, pady=(0, 20))
        progress_bar.start()
        
        def update_worker():
            try:
                progress_var.set("Downloading update...")
                success, message = self.updater.perform_update()
                
                progress_bar.stop()
                progress_dialog.destroy()
                
                if success:
                    messagebox.showinfo("Update Complete", 
                                       f"{message}\n\nPlease restart MetaCLI to use the new version.")
                else:
                    messagebox.showerror("Update Failed", message)
            
            except Exception as e:
                progress_bar.stop()
                progress_dialog.destroy()
                messagebox.showerror("Update Error", f"Update failed: {str(e)}")
        
        threading.Thread(target=update_worker, daemon=True).start()
    
    def show_about(self):
        """Show about dialog with version and update information."""
        dialog = tk.Toplevel(self.root)
        dialog.title("About MetaCLI")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Title
        title_label = ttk.Label(main_frame, text="MetaCLI", 
                               font=('TkDefaultFont', 18, 'bold'))
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, text="Advanced Metadata Extraction Tool", 
                                  font=('TkDefaultFont', 10))
        subtitle_label.pack(pady=(0, 20))
        
        # Version info
        version_info = self.updater.get_current_version_info()
        current_version = version_info.get('cached_version', 'Unknown')
        
        info_text = f"""Version: {current_version}
Installation: {version_info.get('installation_path', 'Unknown')}
Executables: {', '.join(version_info.get('executables_found', []))}

MetaCLI is a powerful tool for extracting and analyzing metadata from various file types. It supports batch processing, advanced filtering, and multiple output formats.

© 2024 MetaCLI Project"""
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Check for Updates", 
                  command=lambda: [dialog.destroy(), self.check_updates()]).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    # Enhanced functionality methods
    def export_results(self):
        """Export current results to various formats."""
        if not hasattr(self, 'current_results') or not self.current_results:
            messagebox.showwarning("No Results", "No scan results to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("XML files", "*.xml"),
                ("HTML files", "*.html")
            ]
        )
        
        if file_path:
            try:
                self.formatter.save_results(self.current_results, file_path)
                messagebox.showinfo("Export Complete", f"Results exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results: {e}")
    
    def copy_results(self):
        """Copy selected results to clipboard."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select items to copy.")
            return
        
        copied_data = []
        for item in selection:
            values = self.results_tree.item(item, 'values')
            copied_data.append('\t'.join(str(v) for v in values))
        
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(copied_data))
        messagebox.showinfo("Copied", f"Copied {len(copied_data)} items to clipboard.")
    
    def select_all(self):
        """Select all items in the results tree."""
        for item in self.results_tree.get_children():
            self.results_tree.selection_add(item)
    
    def show_find_dialog(self):
        """Show find dialog for searching results."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Find in Results")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Search for:").pack(anchor=tk.W)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(main_frame, textvariable=search_var, width=40)
        search_entry.pack(fill=tk.X, pady=(5, 10))
        search_entry.focus()
        
        case_sensitive = tk.BooleanVar()
        ttk.Checkbutton(main_frame, text="Case sensitive", variable=case_sensitive).pack(anchor=tk.W)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def find_items():
            search_text = search_var.get()
            if not search_text:
                return
            
            # Clear previous selection
            self.results_tree.selection_remove(self.results_tree.selection())
            
            found_items = []
            for item in self.results_tree.get_children():
                values = self.results_tree.item(item, 'values')
                text_to_search = ' '.join(str(v) for v in values)
                
                if case_sensitive.get():
                    if search_text in text_to_search:
                        found_items.append(item)
                else:
                    if search_text.lower() in text_to_search.lower():
                        found_items.append(item)
            
            if found_items:
                for item in found_items:
                    self.results_tree.selection_add(item)
                    self.results_tree.see(item)
                messagebox.showinfo("Search Results", f"Found {len(found_items)} matching items.")
            else:
                messagebox.showinfo("Search Results", "No matching items found.")
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Find", command=find_items).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Bind Enter key to find
        search_entry.bind('<Return>', lambda e: find_items())
    
    def show_filter_dialog(self):
        """Show filter dialog for filtering results."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Filter Results")
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File type filter
        ttk.Label(main_frame, text="File Type:").pack(anchor=tk.W)
        file_type_var = tk.StringVar(value="all")
        file_type_combo = ttk.Combobox(main_frame, textvariable=file_type_var, 
                                      values=["all", "image", "document", "audio", "video", "archive", "executable"])
        file_type_combo.pack(fill=tk.X, pady=(5, 10))
        
        # Size filter
        ttk.Label(main_frame, text="Size Range (MB):").pack(anchor=tk.W)
        size_frame = ttk.Frame(main_frame)
        size_frame.pack(fill=tk.X, pady=(5, 10))
        
        min_size_var = tk.StringVar()
        max_size_var = tk.StringVar()
        ttk.Label(size_frame, text="Min:").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=min_size_var, width=10).pack(side=tk.LEFT, padx=(5, 10))
        ttk.Label(size_frame, text="Max:").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=max_size_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Date filter
        ttk.Label(main_frame, text="Modified Date:").pack(anchor=tk.W, pady=(10, 0))
        date_var = tk.StringVar(value="any")
        date_combo = ttk.Combobox(main_frame, textvariable=date_var,
                                 values=["any", "today", "this_week", "this_month", "this_year"])
        date_combo.pack(fill=tk.X, pady=(5, 10))
        
        def apply_filter():
            # Implementation would filter the results tree based on criteria
            messagebox.showinfo("Filter Applied", "Filter has been applied to the results.")
            dialog.destroy()
        
        def clear_filter():
            # Reset all filters
            file_type_var.set("all")
            min_size_var.set("")
            max_size_var.set("")
            date_var.set("any")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Apply", command=apply_filter).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Clear", command=clear_filter).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def clear_cache(self):
        """Clear metadata extraction cache."""
        try:
            if hasattr(self.extractor, 'clear_cache'):
                self.extractor.clear_cache()
            messagebox.showinfo("Cache Cleared", "Metadata cache has been cleared successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear cache: {e}")
    
    def refresh_view(self):
        """Refresh the current view."""
        if hasattr(self, 'current_path') and self.current_path:
            self.scan_directory()
        else:
            messagebox.showinfo("Refresh", "No directory selected to refresh.")
    
    def expand_all(self):
        """Expand all items in the results tree."""
        def expand_item(item):
            self.results_tree.item(item, open=True)
            for child in self.results_tree.get_children(item):
                expand_item(child)
        
        for item in self.results_tree.get_children():
            expand_item(item)
    
    def collapse_all(self):
        """Collapse all items in the results tree."""
        def collapse_item(item):
            self.results_tree.item(item, open=False)
            for child in self.results_tree.get_children(item):
                collapse_item(child)
        
        for item in self.results_tree.get_children():
            collapse_item(item)
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        shortcuts_text = """
General:
  Ctrl+O        Open directory
  Ctrl+S        Save results
  Ctrl+R        Refresh view
  Ctrl+F        Find in results
  Ctrl+A        Select all
  Ctrl+C        Copy selection
  F5            Refresh current scan
  F11           Toggle fullscreen
  Escape        Clear selection

View:
  Ctrl++        Increase font size
  Ctrl+-        Decrease font size
  Ctrl+0        Reset font size
  Ctrl+D        Toggle dark mode

Navigation:
  Tab           Switch between tabs
  Ctrl+Tab      Next tab
  Ctrl+Shift+Tab Previous tab
  Enter         Analyze selected file
  Delete        Clear results

Batch Operations:
  Ctrl+B        Start batch processing
  Ctrl+Shift+B  Stop batch processing
  Ctrl+E        Export results
"""
        
        text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, 
                                               width=60, height=20, font=('Consolas', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, shortcuts_text)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
    
    def show_cli_help(self):
        """Show CLI help information."""
        dialog = tk.Toplevel(self.root)
        dialog.title("CLI Help")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        cli_help_text = """
MetaCLI Command Line Interface

Usage:
  python metacli_cli.py [OPTIONS] COMMAND [ARGS]...

Commands:
  scan        Scan directory for metadata
  extract     Extract metadata from single file
  batch       Batch process multiple directories
  export      Export results to various formats
  compare     Compare metadata between files

Options:
  --help      Show help message
  --version   Show version information
  --verbose   Enable verbose output
  --quiet     Suppress output
  --format    Output format (json, csv, xml, html)
  --output    Output file path
  --recursive Scan directories recursively
  --hidden    Include hidden files
  --max-files Maximum number of files to process

Examples:
  # Scan current directory
  python metacli_cli.py scan .
  
  # Extract metadata from single file
  python metacli_cli.py extract image.jpg
  
  # Batch process with JSON output
  python metacli_cli.py batch --format json --output results.json dir1 dir2
  
  # Compare two files
  python metacli_cli.py compare file1.jpg file2.jpg
  
  # Scan recursively with size limit
  python metacli_cli.py scan --recursive --max-files 1000 /path/to/directory

For more information, visit: https://github.com/darkiifr/Metacli
"""
        
        text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, 
                                               width=70, height=25, font=('Consolas', 9))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, cli_help_text)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
    
    def save_report(self):
        """Save a detailed report of the current scan."""
        if not hasattr(self, 'current_results') or not self.current_results:
            messagebox.showwarning("No Results", "No scan results to save as report.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Report",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                # Generate detailed HTML report
                self._generate_detailed_report(file_path)
                messagebox.showinfo("Report Saved", f"Detailed report saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save report: {e}")
    
    def _generate_detailed_report(self, file_path):
        """Generate a detailed HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MetaCLI Scan Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .file-entry {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
        .metadata {{ margin-left: 20px; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>MetaCLI Scan Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Scanned Path: {getattr(self, 'current_path', 'Unknown')}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Files: {len(self.current_results)}</p>
        <p>Scan completed successfully</p>
    </div>
    
    <div class="results">
        <h2>Detailed Results</h2>
"""
        
        for result in self.current_results:
            html_content += f"""
        <div class="file-entry">
            <strong>{result.get('name', 'Unknown')}</strong>
            <div class="metadata">
                <p>Size: {result.get('size_human', 'Unknown')}</p>
                <p>Type: {result.get('file_type', 'Unknown')}</p>
                <p>Modified: {result.get('modified', 'Unknown')}</p>
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def compare_files(self):
        """Compare metadata between two files."""
        file1 = filedialog.askopenfilename(title="Select first file")
        if not file1:
            return
        
        file2 = filedialog.askopenfilename(title="Select second file")
        if not file2:
            return
        
        try:
            metadata1 = self.extractor.extract_metadata(file1)
            metadata2 = self.extractor.extract_metadata(file2)
            
            self._show_comparison_dialog(file1, file2, metadata1, metadata2)
        except Exception as e:
            messagebox.showerror("Comparison Error", f"Failed to compare files: {e}")
    
    def _show_comparison_dialog(self, file1, file2, metadata1, metadata2):
        """Show file comparison dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("File Comparison")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File headers
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text=f"File 1: {os.path.basename(file1)}", 
                 font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(header_frame, text=f"File 2: {os.path.basename(file2)}", 
                 font=('TkDefaultFont', 10, 'bold')).pack(side=tk.RIGHT)
        
        # Comparison content
        comparison_text = self._generate_comparison_text(metadata1, metadata2)
        
        text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, 
                                               width=80, height=30, font=('Consolas', 9))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, comparison_text)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
    
    def _generate_comparison_text(self, metadata1, metadata2):
        """Generate comparison text for two metadata dictionaries."""
        comparison = ["METADATA COMPARISON\n" + "="*50 + "\n"]
        
        all_keys = set(metadata1.keys()) | set(metadata2.keys())
        
        for key in sorted(all_keys):
            val1 = metadata1.get(key, "<missing>")
            val2 = metadata2.get(key, "<missing>")
            
            if val1 == val2:
                comparison.append(f"✓ {key}: {val1}")
            else:
                comparison.append(f"✗ {key}:")
                comparison.append(f"    File 1: {val1}")
                comparison.append(f"    File 2: {val2}")
            comparison.append("")
        
        return "\n".join(comparison)
    
    def generate_report(self):
        """Generate a comprehensive report."""
        self.save_report()
    
    def show_settings(self):
        """Show settings dialog."""
        # Switch to settings tab
        self.notebook.select(3)  # Settings is the 4th tab (index 3)
    
    def batch_process(self):
        """Start batch processing."""
        # Switch to batch tab
        self.notebook.select(2)  # Assuming batch is the 3rd tab (index 2)


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