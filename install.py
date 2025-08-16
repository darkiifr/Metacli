#!/usr/bin/env python3
"""
MetaCLI Installation Script

Comprehensive installation script for MetaCLI that handles both CLI and GUI executables,
path management, and system integration.
"""

import os
import sys
import shutil
import subprocess
import winreg
from pathlib import Path
import argparse
from typing import Optional, List, Tuple


class MetaCLIInstaller:
    """MetaCLI installation manager."""
    
    def __init__(self):
        self.is_windows = sys.platform.startswith('win')
        self.is_admin = self._check_admin_privileges()
        
        # Installation paths
        if self.is_windows:
            if self.is_admin:
                self.install_dir = Path("C:/Program Files/MetaCLI")
            else:
                self.install_dir = Path(os.path.expanduser("~/AppData/Local/MetaCLI"))
        else:
            if os.geteuid() == 0:  # Root user
                self.install_dir = Path("/usr/local/bin")
            else:
                self.install_dir = Path(os.path.expanduser("~/.local/bin"))
        
        # Executable paths
        self.executables = {
            'cli': {
                'source': 'dist/metacli.exe' if self.is_windows else 'dist/metacli',
                'target': 'metacli.exe' if self.is_windows else 'metacli',
                'symlink': 'metacli'
            },
            'gui': {
                'source': 'dist/MetaCLI-GUI.exe' if self.is_windows else 'dist/MetaCLI-GUI',
                'target': 'MetaCLI-GUI.exe' if self.is_windows else 'MetaCLI-GUI',
                'symlink': 'metacli-gui'
            }
        }
        
    def _check_admin_privileges(self) -> bool:
        """Check if running with administrator privileges."""
        if self.is_windows:
            try:
                return os.getuid() == 0
            except AttributeError:
                # Windows doesn't have getuid, use alternative method
                try:
                    import ctypes
                    return ctypes.windll.shell32.IsUserAnAdmin() != 0
                except:
                    return False
        else:
            return os.geteuid() == 0
            
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        
        # Check if executables exist
        missing_files = []
        available_executables = []
        
        for exe_type, exe_info in self.executables.items():
            source_path = Path(exe_info['source'])
            if source_path.exists():
                print(f"✓ Found {exe_type.upper()} executable: {source_path}")
                available_executables.append(exe_type)
            else:
                print(f"⚠️ {exe_type.upper()} executable not found: {source_path}")
                missing_files.append(source_path)
        
        if not available_executables:
            print("❌ No executables found. Please run 'python build.py' first.")
            return False
            
        if missing_files:
            print(f"⚠️ Some executables are missing, but installation can continue with available ones.")
            
        # Update executables dict to only include available ones
        self.executables = {k: v for k, v in self.executables.items() if k in available_executables}
        
        print(f"✓ Prerequisites check completed. {len(self.executables)} executable(s) available.")
        return True
        
    def create_installation_directory(self) -> bool:
        """Create the installation directory."""
        try:
            print(f"📁 Creating installation directory: {self.install_dir}")
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify directory was created and is writable
            if not self.install_dir.exists():
                print(f"❌ Failed to create directory: {self.install_dir}")
                return False
                
            # Test write permissions
            test_file = self.install_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                print(f"✓ Installation directory created and writable")
                return True
            except PermissionError:
                print(f"❌ No write permission to: {self.install_dir}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating installation directory: {e}")
            return False
            
    def copy_executables(self) -> bool:
        """Copy executables to installation directory."""
        print("📋 Copying executables...")
        
        success_count = 0
        
        for exe_type, exe_info in self.executables.items():
            source_path = Path(exe_info['source'])
            target_path = self.install_dir / exe_info['target']
            
            try:
                print(f"  Copying {exe_type.upper()}: {source_path} -> {target_path}")
                shutil.copy2(source_path, target_path)
                
                # Make executable on Unix-like systems
                if not self.is_windows:
                    os.chmod(target_path, 0o755)
                    
                # Verify copy
                if target_path.exists():
                    size_mb = target_path.stat().st_size / (1024 * 1024)
                    print(f"  ✓ {exe_type.upper()} copied successfully ({size_mb:.1f} MB)")
                    success_count += 1
                else:
                    print(f"  ❌ {exe_type.upper()} copy verification failed")
                    
            except Exception as e:
                print(f"  ❌ Error copying {exe_type.upper()}: {e}")
                
        if success_count == len(self.executables):
            print(f"✓ All {success_count} executable(s) copied successfully")
            return True
        elif success_count > 0:
            print(f"⚠️ {success_count}/{len(self.executables)} executable(s) copied successfully")
            return True
        else:
            print("❌ No executables copied successfully")
            return False
            
    def add_to_path(self) -> bool:
        """Add installation directory to system PATH."""
        print("🛤️ Adding to system PATH...")
        
        if self.is_windows:
            return self._add_to_windows_path()
        else:
            return self._add_to_unix_path()
            
    def _add_to_windows_path(self) -> bool:
        """Add to Windows PATH via registry."""
        try:
            install_dir_str = str(self.install_dir)
            
            # Try system PATH first (if admin), then user PATH
            if self.is_admin:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                       r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                                       0, winreg.KEY_ALL_ACCESS)
                    current_path, _ = winreg.QueryValueEx(key, "Path")
                    
                    if install_dir_str not in current_path:
                        new_path = current_path + ";" + install_dir_str
                        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                        print("✓ Added to system PATH (requires restart or new terminal)")
                    else:
                        print("✓ Already in system PATH")
                        
                    winreg.CloseKey(key)
                    return True
                    
                except Exception as e:
                    print(f"⚠️ Failed to add to system PATH: {e}")
                    print("Falling back to user PATH...")
            
            # User PATH
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
                
                try:
                    current_path, _ = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    current_path = ""
                    
                if install_dir_str not in current_path:
                    new_path = current_path + ";" + install_dir_str if current_path else install_dir_str
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    print("✓ Added to user PATH (requires restart or new terminal)")
                else:
                    print("✓ Already in user PATH")
                    
                winreg.CloseKey(key)
                
                # Notify system of environment change
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
                        print("✓ Notified system of PATH change")
                        
                except Exception as e:
                    print(f"⚠️ Could not notify system of PATH change: {e}")
                    
                return True
                
            except Exception as e:
                print(f"❌ Failed to add to user PATH: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding to PATH: {e}")
            return False
            
    def _add_to_unix_path(self) -> bool:
        """Add to Unix PATH via shell configuration files."""
        try:
            install_dir_str = str(self.install_dir)
            
            # Shell configuration files to update
            shell_configs = [
                Path.home() / ".bashrc",
                Path.home() / ".zshrc",
                Path.home() / ".profile"
            ]
            
            path_line = f'export PATH="{install_dir_str}:$PATH"'
            
            updated_files = []
            for config_file in shell_configs:
                if config_file.exists():
                    try:
                        content = config_file.read_text()
                        if install_dir_str not in content:
                            with open(config_file, 'a') as f:
                                f.write(f"\n# Added by MetaCLI installer\n{path_line}\n")
                            updated_files.append(config_file.name)
                    except Exception as e:
                        print(f"⚠️ Could not update {config_file}: {e}")
                        
            if updated_files:
                print(f"✓ Updated shell configs: {', '.join(updated_files)}")
                print("  Please restart your terminal or run 'source ~/.bashrc' (or equivalent)")
            else:
                print("⚠️ No shell configuration files found or already configured")
                
            return True
            
        except Exception as e:
            print(f"❌ Error adding to Unix PATH: {e}")
            return False
            
    def create_uninstaller(self) -> bool:
        """Create an uninstaller script."""
        print("🗑️ Creating uninstaller...")
        
        try:
            if self.is_windows:
                uninstaller_path = self.install_dir / "uninstall.bat"
                uninstaller_content = f"""@echo off
echo Uninstalling MetaCLI...
echo.

:: Remove executables
{chr(10).join([f'if exist "{self.install_dir / exe_info["target"]}" del "{self.install_dir / exe_info["target"]}"' for exe_info in self.executables.values()])}

:: Remove installation directory
cd /d "%USERPROFILE%"
rmdir /s /q "{self.install_dir}"

echo.
echo MetaCLI has been uninstalled.
echo Note: You may need to manually remove the PATH entry.
pause
"""
            else:
                uninstaller_path = self.install_dir / "uninstall.sh"
                uninstaller_content = f"""#!/bin/bash
echo "Uninstalling MetaCLI..."
echo

# Remove executables
{chr(10).join([f'rm -f "{self.install_dir / exe_info["target"]}"' for exe_info in self.executables.values()])}

# Remove installation directory if empty
rmdir "{self.install_dir}" 2>/dev/null || true

echo
echo "MetaCLI has been uninstalled."
echo "Note: You may need to manually remove the PATH entry from your shell config."
"""
                
            uninstaller_path.write_text(uninstaller_content)
            
            if not self.is_windows:
                os.chmod(uninstaller_path, 0o755)
                
            print(f"✓ Uninstaller created: {uninstaller_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating uninstaller: {e}")
            return False
            
    def test_installation(self) -> bool:
        """Test the installation by trying to run the executables."""
        print("🧪 Testing installation...")
        
        # Test CLI executable
        if 'cli' in self.executables:
            try:
                result = subprocess.run(
                    ['metacli', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print("✓ CLI executable test passed")
                else:
                    print(f"⚠️ CLI executable test failed (exit code: {result.returncode})")
                    print(f"  Error: {result.stderr}")
                    
            except FileNotFoundError:
                print("⚠️ CLI executable not found in PATH (may need terminal restart)")
            except subprocess.TimeoutExpired:
                print("⚠️ CLI executable test timed out")
            except Exception as e:
                print(f"⚠️ CLI executable test error: {e}")
        
        # Test direct executable access
        success_count = 0
        for exe_type, exe_info in self.executables.items():
            target_path = self.install_dir / exe_info['target']
            if target_path.exists():
                print(f"✓ {exe_type.upper()} executable exists: {target_path}")
                success_count += 1
            else:
                print(f"❌ {exe_type.upper()} executable missing: {target_path}")
                
        if success_count == len(self.executables):
            print("✓ All executables are properly installed")
            return True
        else:
            print(f"⚠️ {success_count}/{len(self.executables)} executables properly installed")
            return success_count > 0
            
    def install(self, force: bool = False) -> bool:
        """Perform the complete installation process."""
        print("🚀 Starting MetaCLI installation...")
        print(f"📍 Installation directory: {self.install_dir}")
        print(f"👤 Running as: {'Administrator' if self.is_admin else 'User'}")
        print()
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
            
        # Create installation directory
        if not self.create_installation_directory():
            return False
            
        # Copy executables
        if not self.copy_executables():
            return False
            
        # Add to PATH
        if not self.add_to_path():
            print("⚠️ Failed to add to PATH, but installation can continue")
            
        # Create uninstaller
        if not self.create_uninstaller():
            print("⚠️ Failed to create uninstaller, but installation can continue")
            
        # Test installation
        print()
        self.test_installation()
        
        print()
        print("🎉 MetaCLI installation completed!")
        print()
        print("📋 Installation Summary:")
        print(f"  📁 Installation directory: {self.install_dir}")
        print(f"  📦 Executables installed: {len(self.executables)}")
        
        for exe_type, exe_info in self.executables.items():
            print(f"    - {exe_type.upper()}: {exe_info['target']}")
            
        print()
        print("🔧 Usage:")
        if 'cli' in self.executables:
            print("  CLI: metacli --help")
            print("       metacli extract file.jpg")
            print("       metacli scan /path/to/directory")
        if 'gui' in self.executables:
            print("  GUI: metacli gui")
            print(f"       Or run directly: {self.install_dir / self.executables['gui']['target']}")
            
        print()
        print("💡 Note: You may need to restart your terminal or command prompt")
        print("   for the PATH changes to take effect.")
        
        return True
        
    def uninstall(self) -> bool:
        """Uninstall MetaCLI."""
        print("🗑️ Uninstalling MetaCLI...")
        
        if not self.install_dir.exists():
            print(f"⚠️ Installation directory not found: {self.install_dir}")
            return False
            
        try:
            # Remove executables
            removed_count = 0
            for exe_type, exe_info in self.executables.items():
                target_path = self.install_dir / exe_info['target']
                if target_path.exists():
                    target_path.unlink()
                    print(f"✓ Removed {exe_type.upper()} executable")
                    removed_count += 1
                    
            # Remove installation directory if empty
            try:
                if not any(self.install_dir.iterdir()):
                    self.install_dir.rmdir()
                    print(f"✓ Removed installation directory: {self.install_dir}")
                else:
                    print(f"⚠️ Installation directory not empty, keeping: {self.install_dir}")
            except OSError:
                pass
                
            print(f"\n✓ Uninstallation completed. Removed {removed_count} executable(s).")
            print("💡 Note: PATH entries may need to be manually removed.")
            return True
            
        except Exception as e:
            print(f"❌ Error during uninstallation: {e}")
            return False


def main():
    """Main entry point for the installation script."""
    parser = argparse.ArgumentParser(
        description="MetaCLI Installation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install.py                    # Install MetaCLI
  python install.py --force            # Force reinstall
  python install.py --uninstall        # Uninstall MetaCLI
  python install.py --test             # Test existing installation
        """
    )
    
    parser.add_argument('--force', action='store_true',
                       help='Force installation even if already installed')
    parser.add_argument('--uninstall', action='store_true',
                       help='Uninstall MetaCLI')
    parser.add_argument('--test', action='store_true',
                       help='Test existing installation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    installer = MetaCLIInstaller()
    
    try:
        if args.uninstall:
            success = installer.uninstall()
        elif args.test:
            success = installer.test_installation()
        else:
            success = installer.install(force=args.force)
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()