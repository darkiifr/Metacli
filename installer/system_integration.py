#!/usr/bin/env python3
"""
System Integration Module for MetaCLI Installer
Handles Windows system integration including PATH modification and shortcuts
"""

import os
import sys
import winreg
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import shutil
import re

# Try to import pywin32 components
try:
    import win32com.client
    import win32api
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class SystemIntegration:
    """Handles Windows system integration for MetaCLI"""
    
    def __init__(self, logger_callback=None):
        self.logger_callback = logger_callback or print
        
    def log(self, message: str):
        """Log a message using the callback"""
        if self.logger_callback:
            self.logger_callback(message)
            
    def is_admin(self) -> bool:
        """Check if the current process has administrator privileges"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
            
    def get_current_path(self, system_wide: bool = True) -> str:
        """Get the current PATH environment variable"""
        try:
            if system_wide:
                # Get system PATH
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                  r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
                                  0, winreg.KEY_READ) as key:
                    path_value, _ = winreg.QueryValueEx(key, 'PATH')
                    return path_value
            else:
                # Get user PATH
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                  r'Environment',
                                  0, winreg.KEY_READ) as key:
                    try:
                        path_value, _ = winreg.QueryValueEx(key, 'PATH')
                        return path_value
                    except FileNotFoundError:
                        return ''
        except Exception as e:
            self.log(f"Error reading PATH: {str(e)}")
            return ''
            
    def add_to_path(self, directory: str, system_wide: bool = None) -> bool:
        """Add directory to PATH environment variable"""
        if system_wide is None:
            system_wide = self.is_admin()
            
        directory = os.path.normpath(directory)
        
        try:
            if system_wide:
                return self._add_to_system_path(directory)
            else:
                return self._add_to_user_path(directory)
        except Exception as e:
            self.log(f"Error adding to PATH: {str(e)}")
            return False
            
    def _add_to_system_path(self, directory: str) -> bool:
        """Add directory to system PATH"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                # Get current PATH
                try:
                    current_path, _ = winreg.QueryValueEx(key, 'PATH')
                except FileNotFoundError:
                    current_path = ''
                    
                # Check if directory is already in PATH
                path_dirs = [os.path.normpath(p.strip()) for p in current_path.split(';') if p.strip()]
                if directory not in path_dirs:
                    # Add directory to PATH
                    new_path = current_path + ';' + directory if current_path else directory
                    winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)
                    self.log(f"Added {directory} to system PATH")
                    
                    # Notify system of environment change
                    self._broadcast_environment_change()
                    return True
                else:
                    self.log(f"Directory {directory} already in system PATH")
                    return True
                    
        except PermissionError:
            self.log("Permission denied: Cannot modify system PATH (run as administrator)")
            return False
        except Exception as e:
            self.log(f"Error modifying system PATH: {str(e)}")
            return False
            
    def _add_to_user_path(self, directory: str) -> bool:
        """Add directory to user PATH"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r'Environment',
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                # Get current user PATH
                try:
                    current_path, _ = winreg.QueryValueEx(key, 'PATH')
                except FileNotFoundError:
                    current_path = ''
                    
                # Check if directory is already in PATH
                path_dirs = [os.path.normpath(p.strip()) for p in current_path.split(';') if p.strip()]
                if directory not in path_dirs:
                    # Add directory to PATH
                    new_path = current_path + ';' + directory if current_path else directory
                    winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)
                    self.log(f"Added {directory} to user PATH")
                    
                    # Notify system of environment change
                    self._broadcast_environment_change()
                    return True
                else:
                    self.log(f"Directory {directory} already in user PATH")
                    return True
                    
        except Exception as e:
            self.log(f"Error modifying user PATH: {str(e)}")
            return False
            
    def _broadcast_environment_change(self):
        """Notify Windows that environment variables have changed"""
        try:
            import ctypes
            from ctypes import wintypes
            
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            
            result = ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
                SMTO_ABORTIFHUNG, 5000, ctypes.byref(wintypes.DWORD())
            )
            
            if result:
                self.log("Environment change notification sent")
            else:
                self.log("Failed to send environment change notification")
                
        except Exception as e:
            self.log(f"Error broadcasting environment change: {str(e)}")
            
    def remove_from_path(self, directory: str, system_wide: bool = None) -> bool:
        """Remove directory from PATH environment variable"""
        if system_wide is None:
            system_wide = self.is_admin()
            
        directory = os.path.normpath(directory)
        
        try:
            if system_wide:
                return self._remove_from_system_path(directory)
            else:
                return self._remove_from_user_path(directory)
        except Exception as e:
            self.log(f"Error removing from PATH: {str(e)}")
            return False
            
    def _remove_from_system_path(self, directory: str) -> bool:
        """Remove directory from system PATH"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                # Get current PATH
                current_path, _ = winreg.QueryValueEx(key, 'PATH')
                
                # Remove directory from PATH
                path_dirs = [p.strip() for p in current_path.split(';') if p.strip()]
                path_dirs = [p for p in path_dirs if os.path.normpath(p) != directory]
                
                new_path = ';'.join(path_dirs)
                winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)
                self.log(f"Removed {directory} from system PATH")
                
                self._broadcast_environment_change()
                return True
                
        except Exception as e:
            self.log(f"Error removing from system PATH: {str(e)}")
            return False
            
    def _remove_from_user_path(self, directory: str) -> bool:
        """Remove directory from user PATH"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r'Environment',
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                # Get current user PATH
                try:
                    current_path, _ = winreg.QueryValueEx(key, 'PATH')
                except FileNotFoundError:
                    return True  # Nothing to remove
                    
                # Remove directory from PATH
                path_dirs = [p.strip() for p in current_path.split(';') if p.strip()]
                path_dirs = [p for p in path_dirs if os.path.normpath(p) != directory]
                
                new_path = ';'.join(path_dirs)
                winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)
                self.log(f"Removed {directory} from user PATH")
                
                self._broadcast_environment_change()
                return True
                
        except Exception as e:
            self.log(f"Error removing from user PATH: {str(e)}")
            return False
            
    def create_shortcut(self, target_path: str, shortcut_path: str, 
                       description: str = "", arguments: str = "", 
                       working_directory: str = "", icon_path: str = "") -> bool:
        """Create a Windows shortcut (.lnk file)"""
        if PYWIN32_AVAILABLE:
            return self._create_shortcut_pywin32(target_path, shortcut_path, description, arguments, working_directory, icon_path)
        else:
            return self._create_shortcut_fallback(target_path, shortcut_path, description, arguments, working_directory, icon_path)
    
    def _create_shortcut_pywin32(self, target_path: str, shortcut_path: str, 
                                description: str = "", arguments: str = "", 
                                working_directory: str = "", icon_path: str = "") -> bool:
        """Create shortcut using pywin32"""
        try:
            shell = win32com.client.Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            
            shortcut.Targetpath = target_path
            if description:
                shortcut.Description = description
            if arguments:
                shortcut.Arguments = arguments
            if working_directory:
                shortcut.WorkingDirectory = working_directory
            else:
                shortcut.WorkingDirectory = str(Path(target_path).parent)
            if icon_path:
                shortcut.IconLocation = icon_path
                
            shortcut.save()
            self.log(f"Created shortcut: {shortcut_path}")
            return True
            
        except Exception as e:
            self.log(f"Error creating shortcut with pywin32: {str(e)}")
            return False
    
    def _create_shortcut_fallback(self, target_path: str, shortcut_path: str, 
                                 description: str = "", arguments: str = "", 
                                 working_directory: str = "", icon_path: str = "") -> bool:
        """Create shortcut using PowerShell as fallback"""
        try:
            # Use PowerShell to create shortcut
            ps_script = f"""
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path}"
$Shortcut.WorkingDirectory = "{working_directory or str(Path(target_path).parent)}"
$Shortcut.Description = "{description}"
$Shortcut.Arguments = "{arguments}"
{f'$Shortcut.IconLocation = "{icon_path}"' if icon_path else ''}
$Shortcut.Save()
"""
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                self.log(f"Created shortcut (PowerShell): {shortcut_path}")
                return True
            else:
                self.log(f"PowerShell shortcut creation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log(f"Error creating shortcut with PowerShell: {str(e)}")
            return False
            
    def create_desktop_shortcuts(self, install_dir: Path, 
                                create_gui: bool = True, create_cli: bool = True) -> List[str]:
        """Create desktop shortcuts for MetaCLI applications"""
        created_shortcuts = []
        desktop = Path.home() / 'Desktop'
        
        if create_gui:
            gui_exe = install_dir / 'MetaCLI-GUI.exe'
            if gui_exe.exists():
                shortcut_path = desktop / 'MetaCLI GUI.lnk'
                if self.create_shortcut(
                    str(gui_exe),
                    str(shortcut_path),
                    description='MetaCLI GUI Application - Metadata extraction and management',
                    working_directory=str(install_dir)
                ):
                    created_shortcuts.append(str(shortcut_path))
                    
        if create_cli:
            cli_exe = install_dir / 'metacli.exe'
            if cli_exe.exists():
                shortcut_path = desktop / 'MetaCLI CLI.lnk'
                if self.create_shortcut(
                    'cmd.exe',
                    str(shortcut_path),
                    description='MetaCLI Command Line Interface',
                    arguments=f'/k cd /d "{install_dir}" && metacli.exe --help',
                    working_directory=str(install_dir)
                ):
                    created_shortcuts.append(str(shortcut_path))
                    
        return created_shortcuts
        
    def create_start_menu_shortcuts(self, install_dir: Path, 
                                   create_gui: bool = True, create_cli: bool = True) -> List[str]:
        """Create Start Menu shortcuts for MetaCLI applications"""
        created_shortcuts = []
        
        # Create Start Menu folder
        start_menu = Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'MetaCLI'
        start_menu.mkdir(parents=True, exist_ok=True)
        
        if create_gui:
            gui_exe = install_dir / 'MetaCLI-GUI.exe'
            if gui_exe.exists():
                shortcut_path = start_menu / 'MetaCLI GUI.lnk'
                if self.create_shortcut(
                    str(gui_exe),
                    str(shortcut_path),
                    description='MetaCLI GUI Application',
                    working_directory=str(install_dir)
                ):
                    created_shortcuts.append(str(shortcut_path))
                    
        if create_cli:
            cli_exe = install_dir / 'metacli.exe'
            if cli_exe.exists():
                shortcut_path = start_menu / 'MetaCLI CLI.lnk'
                if self.create_shortcut(
                    'cmd.exe',
                    str(shortcut_path),
                    description='MetaCLI Command Line Interface',
                    arguments=f'/k cd /d "{install_dir}" && metacli.exe --help',
                    working_directory=str(install_dir)
                ):
                    created_shortcuts.append(str(shortcut_path))
                    
        # Create uninstaller shortcut
        uninstaller = install_dir / 'uninstall.exe'
        if uninstaller.exists():
            shortcut_path = start_menu / 'Uninstall MetaCLI.lnk'
            if self.create_shortcut(
                str(uninstaller),
                str(shortcut_path),
                description='Uninstall MetaCLI',
                working_directory=str(install_dir)
            ):
                created_shortcuts.append(str(shortcut_path))
                
        return created_shortcuts
        
    def register_uninstaller(self, install_dir: Path, version: str = "1.0.0") -> bool:
        """Register the application in Windows Add/Remove Programs"""
        try:
            uninstall_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MetaCLI'
            
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
                winreg.SetValueEx(key, 'DisplayName', 0, winreg.REG_SZ, 'MetaCLI')
                winreg.SetValueEx(key, 'DisplayVersion', 0, winreg.REG_SZ, version)
                winreg.SetValueEx(key, 'Publisher', 0, winreg.REG_SZ, 'MetaCLI Team')
                winreg.SetValueEx(key, 'InstallLocation', 0, winreg.REG_SZ, str(install_dir))
                winreg.SetValueEx(key, 'UninstallString', 0, winreg.REG_SZ, str(install_dir / 'uninstall.exe'))
                winreg.SetValueEx(key, 'NoModify', 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, 'NoRepair', 0, winreg.REG_DWORD, 1)
                
                # Calculate estimated size
                try:
                    size_kb = sum(f.stat().st_size for f in install_dir.rglob('*') if f.is_file()) // 1024
                    winreg.SetValueEx(key, 'EstimatedSize', 0, winreg.REG_DWORD, size_kb)
                except:
                    pass
                    
            self.log("Registered application in Add/Remove Programs")
            return True
            
        except PermissionError:
            self.log("Permission denied: Cannot register uninstaller (run as administrator)")
            return False
        except Exception as e:
            self.log(f"Error registering uninstaller: {str(e)}")
            return False
            
    def unregister_uninstaller(self) -> bool:
        """Unregister the application from Windows Add/Remove Programs"""
        try:
            uninstall_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MetaCLI'
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key)
            self.log("Unregistered application from Add/Remove Programs")
            return True
        except FileNotFoundError:
            self.log("Application not found in Add/Remove Programs")
            return True
        except Exception as e:
            self.log(f"Error unregistering application: {str(e)}")
            return False
            
    def add_antivirus_exclusion(self, directory: str) -> bool:
        """Add directory to Windows Defender exclusion list"""
        directory = os.path.normpath(directory)
        
        try:
            # Add to Windows Defender exclusions using PowerShell
            cmd = [
                'powershell.exe', '-Command',
                f'Add-MpPreference -ExclusionPath "{directory}"'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            if result.returncode == 0:
                self.log(f"Successfully added {directory} to Windows Defender exclusions")
                return True
            else:
                self.log(f"Failed to add antivirus exclusion: {result.stderr}")
                # Try alternative method for older Windows versions
                return self._add_defender_exclusion_registry(directory)
                
        except Exception as e:
            self.log(f"Error adding antivirus exclusion: {str(e)}")
            return self._add_defender_exclusion_registry(directory)
            
    def _add_defender_exclusion_registry(self, directory: str) -> bool:
        """Add directory to Windows Defender exclusions via registry (fallback method)"""
        try:
            # Registry path for Windows Defender exclusions
            defender_key = r'SOFTWARE\Microsoft\Windows Defender\Exclusions\Paths'
            
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, defender_key) as key:
                # Add the directory as an exclusion (value 0 means excluded)
                winreg.SetValueEx(key, directory, 0, winreg.REG_DWORD, 0)
                self.log(f"Added {directory} to Windows Defender exclusions via registry")
                return True
                
        except Exception as e:
            self.log(f"Registry method failed: {str(e)}")
            # Try user-level exclusion as last resort
            return self._add_user_defender_exclusion(directory)
            
    def _add_user_defender_exclusion(self, directory: str) -> bool:
        """Add directory to user-level Windows Defender exclusions"""
        try:
            # Try using Windows Security API if available
            cmd = [
                'powershell.exe', '-Command',
                f'Set-MpPreference -ExclusionPath @((Get-MpPreference).ExclusionPath + "{directory}")'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            if result.returncode == 0:
                self.log(f"Added {directory} to user-level Windows Defender exclusions")
                return True
            else:
                self.log(f"Unable to add antivirus exclusion automatically. Manual exclusion may be required.")
                return False
                
        except Exception as e:
            self.log(f"User-level exclusion failed: {str(e)}")
            return False
            
    def remove_desktop_shortcuts(self, install_dir: Path) -> List[str]:
        """Remove desktop shortcuts for MetaCLI applications"""
        removed_shortcuts = []
        desktop_path = Path.home() / 'Desktop'
        
        shortcuts_to_remove = [
            'MetaCLI GUI.lnk',
            'MetaCLI CLI.lnk',
            'MetaCLI.lnk'
        ]
        
        for shortcut_name in shortcuts_to_remove:
            shortcut_path = desktop_path / shortcut_name
            if shortcut_path.exists():
                try:
                    shortcut_path.unlink()
                    removed_shortcuts.append(str(shortcut_path))
                    self.log(f"Removed desktop shortcut: {shortcut_path}")
                except Exception as e:
                    self.log(f"Failed to remove desktop shortcut {shortcut_path}: {str(e)}")
                    
        return removed_shortcuts
        
    def remove_start_menu_shortcuts(self, install_dir: Path) -> List[str]:
        """Remove Start Menu shortcuts for MetaCLI applications"""
        removed_shortcuts = []
        
        # Try both user and system start menu locations
        start_menu_paths = [
            Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'MetaCLI',
            Path('C:') / 'ProgramData' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'MetaCLI'
        ]
        
        for start_menu_path in start_menu_paths:
            if start_menu_path.exists():
                try:
                    # Remove all shortcuts in the MetaCLI folder
                    for shortcut_file in start_menu_path.glob('*.lnk'):
                        shortcut_file.unlink()
                        removed_shortcuts.append(str(shortcut_file))
                        self.log(f"Removed start menu shortcut: {shortcut_file}")
                    
                    # Remove the MetaCLI folder if it's empty
                    if not any(start_menu_path.iterdir()):
                        start_menu_path.rmdir()
                        self.log(f"Removed empty start menu folder: {start_menu_path}")
                        
                except Exception as e:
                    self.log(f"Failed to remove start menu shortcuts from {start_menu_path}: {str(e)}")
                    
        return removed_shortcuts
        
    def remove_all_shortcuts(self, install_dir: Path) -> Dict[str, List[str]]:
        """Remove all shortcuts (desktop and start menu)"""
        return {
            'desktop': self.remove_desktop_shortcuts(install_dir),
            'start_menu': self.remove_start_menu_shortcuts(install_dir)
        }
        
    def get_installation_info(self) -> Optional[Dict[str, str]]:
        """Get information about existing MetaCLI installation using multiple detection methods"""
        # Method 1: Registry detection (primary)
        registry_info = self._get_registry_installation_info()
        if registry_info:
            return registry_info
            
        # Method 2: File system detection (fallback)
        filesystem_info = self._get_filesystem_installation_info()
        if filesystem_info:
            return filesystem_info
            
        # Method 3: PATH-based detection (fallback)
        path_info = self._get_path_installation_info()
        if path_info:
            return path_info
            
        return None
        
    def _get_registry_installation_info(self) -> Optional[Dict[str, str]]:
        """Get installation info from Windows registry"""
        registry_locations = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MetaCLI'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MetaCLI'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\MetaCLI')
        ]
        
        for hkey, subkey in registry_locations:
            try:
                with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                    info = {}
                    
                    # Read all available registry values
                    registry_values = ['DisplayName', 'InstallLocation', 'DisplayVersion', 
                                     'UninstallString', 'InstallDate', 'Publisher']
                    
                    for value_name in registry_values:
                        try:
                            info[value_name], _ = winreg.QueryValueEx(key, value_name)
                        except FileNotFoundError:
                            pass
                            
                    if info:
                        info['DetectionMethod'] = 'Registry'
                        info['RegistryLocation'] = f"{hkey}\\{subkey}"
                        return info
            except Exception as e:
                self.log(f"Error reading registry {hkey}\\{subkey}: {str(e)}")
                continue
                
        return None
    
    def parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse version string into tuple of integers for comparison"""
        try:
            # Handle various version formats: "1.0.0", "1.0", "1.0.0.0"
            version_str = version_str.strip()
            # Remove any non-numeric prefixes (like 'v')
            version_str = re.sub(r'^[^\d]*', '', version_str)
            
            # Split by dots and take first 3 components
            parts = version_str.split('.')[:3]
            
            # Pad with zeros if needed
            while len(parts) < 3:
                parts.append('0')
                
            # Convert to integers
            major = int(parts[0]) if parts[0].isdigit() else 0
            minor = int(parts[1]) if parts[1].isdigit() else 0
            patch = int(parts[2]) if parts[2].isdigit() else 0
            
            return (major, minor, patch)
        except (ValueError, IndexError):
            return (0, 0, 0)
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings.
        Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        v1_tuple = self.parse_version(version1)
        v2_tuple = self.parse_version(version2)
        
        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    
    def is_version_outdated(self, installed_version: str, current_version: str) -> bool:
        """Check if the installed version is outdated compared to current version"""
        return self.compare_versions(installed_version, current_version) < 0
    
    def get_version_status(self, installed_version: str, current_version: str = "1.0.0") -> Dict[str, any]:
        """Get detailed version status information"""
        comparison = self.compare_versions(installed_version, current_version)
        
        status = {
            'installed_version': installed_version,
            'current_version': current_version,
            'is_outdated': comparison < 0,
            'is_newer': comparison > 0,
            'is_current': comparison == 0,
            'comparison_result': comparison,
            'recommendation': ''
        }
        
        if status['is_outdated']:
            status['recommendation'] = f"Update recommended: {installed_version} → {current_version}"
        elif status['is_newer']:
            status['recommendation'] = f"Newer version installed: {installed_version} (current: {current_version})"
        else:
            status['recommendation'] = "Installation is up to date"
            
        return status
        
    def _get_filesystem_installation_info(self) -> Optional[Dict[str, str]]:
        """Detect installation by scanning common installation directories"""
        common_install_paths = [
            Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'MetaCLI',
            Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'MetaCLI',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'MetaCLI',
            Path(os.environ.get('APPDATA', '')) / 'MetaCLI',
            Path.home() / 'MetaCLI',
            Path('C:\\MetaCLI'),
            Path('D:\\MetaCLI')
        ]
        
        for install_path in common_install_paths:
            if not install_path or not install_path.exists():
                continue
                
            # Check for MetaCLI executables
            gui_exe = install_path / 'MetaCLI-GUI.exe'
            cli_exe = install_path / 'metacli.exe'
            
            if gui_exe.exists() or cli_exe.exists():
                info = {
                    'InstallLocation': str(install_path),
                    'DetectionMethod': 'FileSystem',
                    'DisplayName': 'MetaCLI (Detected from filesystem)'
                }
                
                # Try to get version from executable
                try:
                    if gui_exe.exists():
                        version = self._get_executable_version(gui_exe)
                        if version:
                            info['DisplayVersion'] = version
                except Exception:
                    pass
                    
                return info
                
        return None
        
    def _get_path_installation_info(self) -> Optional[Dict[str, str]]:
        """Detect installation by checking PATH environment variable"""
        system_path = self.get_current_path(system_wide=True)
        user_path = self.get_current_path(system_wide=False)
        
        for path_var in [system_path, user_path]:
            if not path_var:
                continue
                
            path_dirs = [p.strip() for p in path_var.split(';') if p.strip()]
            
            for path_dir in path_dirs:
                try:
                    path_obj = Path(path_dir)
                    if not path_obj.exists():
                        continue
                        
                    # Check for MetaCLI executables in PATH
                    gui_exe = path_obj / 'MetaCLI-GUI.exe'
                    cli_exe = path_obj / 'metacli.exe'
                    
                    if gui_exe.exists() or cli_exe.exists():
                        info = {
                            'InstallLocation': str(path_obj),
                            'DetectionMethod': 'PATH',
                            'DisplayName': 'MetaCLI (Detected from PATH)'
                        }
                        
                        # Try to get version
                        try:
                            if gui_exe.exists():
                                version = self._get_executable_version(gui_exe)
                                if version:
                                    info['DisplayVersion'] = version
                        except Exception:
                            pass
                            
                        return info
                        
                except Exception:
                    continue
                    
        return None
        
    def _get_executable_version(self, exe_path: Path) -> Optional[str]:
        """Extract version information from executable file"""
        try:
            # Try to get version using Windows API
            import ctypes
            from ctypes import wintypes, windll
            
            # Get file version info
            size = windll.version.GetFileVersionInfoSizeW(str(exe_path), None)
            if size == 0:
                return None
                
            res = ctypes.create_string_buffer(size)
            windll.version.GetFileVersionInfoW(str(exe_path), None, size, res)
            
            # Extract version numbers
            r = ctypes.c_uint()
            l = ctypes.c_uint()
            windll.version.VerQueryValueW(res, '\\', ctypes.byref(r), ctypes.byref(l))
            
            if l.value:
                version_struct = ctypes.cast(r, ctypes.POINTER(ctypes.c_uint * 4)).contents
                version = f"{version_struct[0] >> 16}.{version_struct[0] & 0xFFFF}.{version_struct[1] >> 16}.{version_struct[1] & 0xFFFF}"
                return version
                
            return None
        except Exception:
            # Fallback: try to extract version from filename or use default
            try:
                # Look for version pattern in filename
                version_match = re.search(r'(\d+\.\d+\.\d+)', str(exe_path))
                if version_match:
                    return version_match.group(1)
            except:
                pass
            return "1.0.0"  # Default fallback
            
    def is_metacli_installed(self) -> bool:
        """Check if MetaCLI is currently installed using comprehensive detection"""
        installation_info = self.get_installation_info()
        return installation_info is not None
        
    def get_installation_health(self, install_dir: Path) -> Dict[str, any]:
        """Analyze the health of an existing installation"""
        health = {
            'is_healthy': True,
            'issues': [],
            'missing_files': [],
            'corrupted_files': [],
            'missing_components': [],
            'registry_issues': []
        }
        
        if not install_dir.exists():
            health['is_healthy'] = False
            health['issues'].append('Installation directory does not exist')
            return health
            
        # Check for required executables
        required_files = {
            'MetaCLI-GUI.exe': 'GUI Application',
            'metacli.exe': 'CLI Application'
        }
        
        for filename, description in required_files.items():
            file_path = install_dir / filename
            if not file_path.exists():
                health['missing_files'].append(filename)
                health['missing_components'].append(description)
                health['is_healthy'] = False
            elif not file_path.is_file():
                health['corrupted_files'].append(filename)
                health['is_healthy'] = False
                
        # Check registry consistency
        registry_info = self._get_registry_installation_info()
        if registry_info:
            registry_location = registry_info.get('InstallLocation')
            if registry_location and Path(registry_location) != install_dir:
                health['registry_issues'].append('Registry install location mismatch')
                health['is_healthy'] = False
        else:
            health['registry_issues'].append('No registry entry found')
            
        # Check components
        components = self.get_installed_components(install_dir)
        for component, installed in components.items():
            if not installed and component in ['gui', 'cli']:
                health['missing_components'].append(component)
                health['is_healthy'] = False
                
        return health
        
    def get_installed_components(self, install_dir: Path) -> Dict[str, bool]:
        """Check which components are currently installed"""
        components = {
            'gui': False,
            'cli': False,
            'desktop_shortcuts': False,
            'start_menu_shortcuts': False,
            'path_entry': False
        }
        
        # Check for executables
        if install_dir.exists():
            gui_exe = install_dir / 'MetaCLI-GUI.exe'
            cli_exe = install_dir / 'metacli.exe'
            
            components['gui'] = gui_exe.exists() and gui_exe.is_file()
            components['cli'] = cli_exe.exists() and cli_exe.is_file()
            
        # Check for desktop shortcuts
        desktop_path = Path.home() / 'Desktop'
        public_desktop = Path('C:') / 'Users' / 'Public' / 'Desktop'
        desktop_shortcuts = [
            desktop_path / 'MetaCLI GUI.lnk',
            desktop_path / 'MetaCLI CLI.lnk',
            desktop_path / 'MetaCLI.lnk',
            public_desktop / 'MetaCLI GUI.lnk',
            public_desktop / 'MetaCLI CLI.lnk',
            public_desktop / 'MetaCLI.lnk'
        ]
        components['desktop_shortcuts'] = any(shortcut.exists() and shortcut.is_file() for shortcut in desktop_shortcuts)
        
        # Check start menu shortcuts
        start_menu_paths = [
            Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'MetaCLI',
            Path('C:') / 'ProgramData' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'MetaCLI'
        ]
        components['start_menu_shortcuts'] = any(
            path.exists() and path.is_dir() and any(path.glob('*.lnk')) 
            for path in start_menu_paths
        )
        
        # Check PATH entry with more robust detection
        system_path = self.get_current_path(system_wide=True)
        user_path = self.get_current_path(system_wide=False)
        install_dir_str = str(install_dir.resolve())
        install_dir_normalized = os.path.normpath(install_dir_str)
        
        # Check both original and normalized paths
        path_found = False
        for path_var in [system_path, user_path]:
            if path_var:
                path_dirs = [os.path.normpath(p.strip()) for p in path_var.split(';') if p.strip()]
                if install_dir_str in path_dirs or install_dir_normalized in path_dirs:
                    path_found = True
                    break
        
        components['path_entry'] = path_found
        
        return components
        
    def detect_multiple_installations(self) -> List[Dict[str, str]]:
        """Detect multiple MetaCLI installations on the system"""
        installations = []
        detected_paths = set()
        
        # Check registry entries
        registry_info = self._get_registry_installation_info()
        if registry_info and registry_info.get('InstallLocation'):
            install_path = registry_info['InstallLocation']
            if install_path not in detected_paths:
                detected_paths.add(install_path)
                installations.append(registry_info)
                
        # Check filesystem
        filesystem_info = self._get_filesystem_installation_info()
        if filesystem_info and filesystem_info.get('InstallLocation'):
            install_path = filesystem_info['InstallLocation']
            if install_path not in detected_paths:
                detected_paths.add(install_path)
                installations.append(filesystem_info)
                
        # Check PATH
        path_info = self._get_path_installation_info()
        if path_info and path_info.get('InstallLocation'):
            install_path = path_info['InstallLocation']
            if install_path not in detected_paths:
                detected_paths.add(install_path)
                installations.append(path_info)
                
        return installations
        
    def complete_uninstall(self, install_dir: Path) -> Dict[str, bool]:
        """Perform complete uninstallation of MetaCLI"""
        results = {
            'files_removed': False,
            'shortcuts_removed': False,
            'path_removed': False,
            'registry_removed': False
        }
        
        # Remove shortcuts
        try:
            removed_shortcuts = self.remove_all_shortcuts(install_dir)
            results['shortcuts_removed'] = True
            self.log(f"Removed shortcuts: {removed_shortcuts}")
        except Exception as e:
            self.log(f"Failed to remove shortcuts: {str(e)}")
            
        # Remove from PATH
        try:
            if self.remove_from_path(str(install_dir)):
                results['path_removed'] = True
                self.log(f"Removed {install_dir} from PATH")
        except Exception as e:
            self.log(f"Failed to remove from PATH: {str(e)}")
            
        # Remove registry entries
        try:
            if self.unregister_uninstaller():
                results['registry_removed'] = True
                self.log("Removed registry entries")
        except Exception as e:
            self.log(f"Failed to remove registry entries: {str(e)}")
            
        # Remove installation files
        try:
            if install_dir.exists():
                shutil.rmtree(install_dir)
                results['files_removed'] = True
                self.log(f"Removed installation directory: {install_dir}")
        except Exception as e:
            self.log(f"Failed to remove installation files: {str(e)}")
            
        return results

    def get_system_info(self) -> Dict[str, str]:
        """Get system information"""
        info = {
            'os': f"{os.name} {sys.platform}",
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'architecture': 'x64' if sys.maxsize > 2**32 else 'x86',
            'admin_privileges': str(self.is_admin()),
            'current_user': os.getenv('USERNAME', 'Unknown'),
            'computer_name': os.getenv('COMPUTERNAME', 'Unknown')
        }
        
        return info