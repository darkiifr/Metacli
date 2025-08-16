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
from typing import Optional, List, Dict
import shutil


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
        try:
            import win32com.client
            
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
            
        except ImportError:
            self.log("Warning: pywin32 not available, cannot create shortcuts")
            return False
        except Exception as e:
            self.log(f"Error creating shortcut: {str(e)}")
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                self.log(f"Added {directory} to user-level Windows Defender exclusions")
                return True
            else:
                self.log(f"Unable to add antivirus exclusion automatically. Manual exclusion may be required.")
                return False
                
        except Exception as e:
            self.log(f"User-level exclusion failed: {str(e)}")
            return False
            
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