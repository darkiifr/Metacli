"""Output formatting utilities for MetaCLI."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


class OutputFormatter:
    """Handles formatting and display of output data."""
    
    SUPPORTED_FORMATS = ['json', 'yaml', 'table', 'plain']
    
    def __init__(self, format_type: str = 'json', indent: int = 2):
        """Initialize output formatter.
        
        Args:
            format_type: Output format (json, yaml, table, plain)
            indent: Indentation level for structured formats
        """
        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_type}. Supported: {self.SUPPORTED_FORMATS}")
        
        self.format_type = format_type
        self.indent = indent
    
    def format_data(self, data: Any, **kwargs) -> str:
        """Format data according to the specified format.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
            
        Returns:
            Formatted string
        """
        if self.format_type == 'json':
            return self._format_json(data, **kwargs)
        elif self.format_type == 'yaml':
            return self._format_yaml(data, **kwargs)
        elif self.format_type == 'table':
            return self._format_table(data, **kwargs)
        elif self.format_type == 'plain':
            return self._format_plain(data, **kwargs)
        else:
            return str(data)
    
    def _format_json(self, data: Any, **kwargs) -> str:
        """Format data as JSON."""
        try:
            return json.dumps(
                data,
                indent=self.indent,
                ensure_ascii=False,
                default=self._json_serializer,
                **kwargs
            )
        except Exception as e:
            return f"Error formatting JSON: {e}"
    
    def _format_yaml(self, data: Any, **kwargs) -> str:
        """Format data as YAML."""
        if not YAML_AVAILABLE:
            return "YAML formatting requires 'pyyaml' package. Install with: pip install pyyaml"
        
        try:
            return yaml.dump(
                data,
                default_flow_style=False,
                allow_unicode=True,
                indent=self.indent,
                **kwargs
            )
        except Exception as e:
            return f"Error formatting YAML: {e}"
    
    def _format_table(self, data: Any, **kwargs) -> str:
        """Format data as a table."""
        if not TABULATE_AVAILABLE:
            return "Table formatting requires 'tabulate' package. Install with: pip install tabulate"
        
        try:
            if isinstance(data, dict):
                # Convert dict to table format
                table_data = [[k, v] for k, v in data.items()]
                headers = ['Field', 'Value']
            elif isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    # List of dicts - use dict keys as headers
                    headers = list(data[0].keys())
                    table_data = [[item.get(h, '') for h in headers] for item in data]
                else:
                    # List of values
                    headers = ['Value']
                    table_data = [[item] for item in data]
            else:
                # Single value
                headers = ['Value']
                table_data = [[data]]
            
            return tabulate(
                table_data,
                headers=headers,
                tablefmt=kwargs.get('tablefmt', 'grid'),
                **{k: v for k, v in kwargs.items() if k != 'tablefmt'}
            )
        except Exception as e:
            return f"Error formatting table: {e}"
    
    def _format_plain(self, data: Any, **kwargs) -> str:
        """Format data as plain text."""
        try:
            if isinstance(data, dict):
                lines = []
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        lines.append(f"{key}:")
                        lines.append(self._indent_text(str(value), 2))
                    else:
                        lines.append(f"{key}: {value}")
                return '\n'.join(lines)
            elif isinstance(data, list):
                return '\n'.join(str(item) for item in data)
            else:
                return str(data)
        except Exception as e:
            return f"Error formatting plain text: {e}"
    
    def _indent_text(self, text: str, spaces: int) -> str:
        """Indent text by specified number of spaces."""
        indent = ' ' * spaces
        return '\n'.join(indent + line for line in text.split('\n'))
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def print_data(self, data: Any, file=None, **kwargs) -> None:
        """Print formatted data to file or stdout.
        
        Args:
            data: Data to print
            file: File object to write to (default: stdout)
            **kwargs: Additional formatting options
        """
        formatted = self.format_data(data, **kwargs)
        print(formatted, file=file or sys.stdout)
    
    def save_data(self, data: Any, filepath: Union[str, Path], **kwargs) -> None:
        """Save formatted data to file.
        
        Args:
            data: Data to save
            filepath: Path to output file
            **kwargs: Additional formatting options
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        formatted = self.format_data(data, **kwargs)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(formatted)


class ProgressDisplay:
    """Display progress information in various formats."""
    
    def __init__(self, total: int, description: str = "Processing", width: int = 50):
        """Initialize progress display.
        
        Args:
            total: Total number of items
            description: Description of the operation
            width: Width of progress bar
        """
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1) -> None:
        """Update progress display.
        
        Args:
            increment: Number of items processed
        """
        self.current += increment
        self._display_progress()
    
    def _display_progress(self) -> None:
        """Display current progress."""
        if self.total == 0:
            return
        
        percent = (self.current / self.total) * 100
        filled = int(self.width * self.current // self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        # Estimate remaining time
        if self.current > 0:
            rate = self.current / elapsed.total_seconds()
            remaining_items = self.total - self.current
            remaining_seconds = remaining_items / rate if rate > 0 else 0
            remaining_str = str(datetime.fromtimestamp(remaining_seconds) - datetime.fromtimestamp(0)).split('.')[0]
        else:
            remaining_str = "--:--:--"
        
        # Print progress line
        progress_line = (
            f"\r{self.description}: {bar} "
            f"{self.current}/{self.total} ({percent:.1f}%) "
            f"[{elapsed_str}<{remaining_str}]"
        )
        
        print(progress_line, end='', flush=True)
        
        # Print newline when complete
        if self.current >= self.total:
            print()
    
    def complete(self) -> None:
        """Mark progress as complete."""
        self.current = self.total
        self._display_progress()


class ColorFormatter:
    """Add color formatting to text output."""
    
    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'underline': '\033[4m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
    }
    
    def __init__(self, enabled: bool = True):
        """Initialize color formatter.
        
        Args:
            enabled: Whether to enable color output
        """
        self.enabled = enabled and self._supports_color()
    
    def _supports_color(self) -> bool:
        """Check if the terminal supports color output."""
        try:
            import os
            return (
                hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.environ.get('TERM') != 'dumb'
            )
        except Exception:
            return False
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text.
        
        Args:
            text: Text to colorize
            color: Color name
            
        Returns:
            Colorized text
        """
        if not self.enabled or color not in self.COLORS:
            return text
        
        return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
    
    def success(self, text: str) -> str:
        """Format text as success (green)."""
        return self.colorize(text, 'bright_green')
    
    def error(self, text: str) -> str:
        """Format text as error (red)."""
        return self.colorize(text, 'bright_red')
    
    def warning(self, text: str) -> str:
        """Format text as warning (yellow)."""
        return self.colorize(text, 'bright_yellow')
    
    def info(self, text: str) -> str:
        """Format text as info (blue)."""
        return self.colorize(text, 'bright_blue')
    
    def highlight(self, text: str) -> str:
        """Format text as highlighted (cyan)."""
        return self.colorize(text, 'bright_cyan')
    
    def bold(self, text: str) -> str:
        """Format text as bold."""
        return self.colorize(text, 'bold')
    
    def dim(self, text: str) -> str:
        """Format text as dim."""
        return self.colorize(text, 'dim')


# Global formatter instances
_color_formatter = ColorFormatter()
_output_formatter = OutputFormatter()


def get_color_formatter() -> ColorFormatter:
    """Get global color formatter instance."""
    return _color_formatter


def get_output_formatter() -> OutputFormatter:
    """Get global output formatter instance."""
    return _output_formatter


def set_output_format(format_type: str, **kwargs) -> None:
    """Set global output format.
    
    Args:
        format_type: Output format type
        **kwargs: Additional formatter options
    """
    global _output_formatter
    _output_formatter = OutputFormatter(format_type, **kwargs)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def format_timestamp(timestamp: Union[datetime, float, int], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp in human-readable format.
    
    Args:
        timestamp: Timestamp to format
        format_str: Format string
        
    Returns:
        Formatted timestamp string
    """
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp)
    
    return timestamp.strftime(format_str)


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix