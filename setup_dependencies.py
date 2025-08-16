#!/usr/bin/env python3
"""
MetaCLI Dependency Setup Script
Automatically downloads and configures all necessary dependencies
and sets up system environment paths.
"""

import os
import sys
import subprocess
import json
import urllib.request
import zipfile
import shutil
from pathlib import Path
import platform
import tempfile
from typing import Dict, List, Optional

class DependencyManager:
    """Manages automatic dependency installation and configuration."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.machine().lower()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.dependencies_path = self.project_root / "dependencies"
        
        # Create directories
        self.dependencies_path.mkdir(exist_ok=True)
        
        # Dependency configurations
        self.python_packages = [
            "pillow>=9.0.0",
            "mutagen>=1.45.0",
            "PyPDF2>=3.0.0",
            "python-docx>=0.8.11",
            "chardet>=5.0.0",
            "psutil>=5.9.0",
            "requests>=2.28.0",
            "tqdm>=4.64.0",
            "colorama>=0.4.5",
            "pyinstaller>=5.0.0"
        ]
        
        self.system_tools = {
            "windows": {
                "ffmpeg": {
                    "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
                    "extract_to": "ffmpeg",
                    "executable": "bin/ffmpeg.exe"
                },
                "exiftool": {
                    "url": "https://exiftool.org/exiftool-12.70.zip",
                    "extract_to": "exiftool",
                    "executable": "exiftool.exe"
                }
            },
            "linux": {
                "ffmpeg": {
                    "install_cmd": ["sudo", "apt-get", "install", "-y", "ffmpeg"],
                    "check_cmd": ["ffmpeg", "-version"]
                },
                "exiftool": {
                    "install_cmd": ["sudo", "apt-get", "install", "-y", "libimage-exiftool-perl"],
                    "check_cmd": ["exiftool", "-ver"]
                }
            },
            "darwin": {
                "ffmpeg": {
                    "install_cmd": ["brew", "install", "ffmpeg"],
                    "check_cmd": ["ffmpeg", "-version"]
                },
                "exiftool": {
                    "install_cmd": ["brew", "install", "exiftool"],
                    "check_cmd": ["exiftool", "-ver"]
                }
            }
        }
    
    def print_status(self, message: str, status: str = "INFO"):
        """Print colored status messages."""
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "RESET": "\033[0m"
        }
        
        color = colors.get(status, colors["INFO"])
        reset = colors["RESET"]
        print(f"{color}[{status}]{reset} {message}")
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        min_version = (3, 8)
        current_version = (sys.version_info.major, sys.version_info.minor)
        
        if current_version >= min_version:
            self.print_status(f"Python {self.python_version} is compatible", "SUCCESS")
            return True
        else:
            self.print_status(f"Python {self.python_version} is not compatible. Minimum required: {min_version[0]}.{min_version[1]}", "ERROR")
            return False
    
    def create_virtual_environment(self) -> bool:
        """Create a virtual environment for the project."""
        try:
            if self.venv_path.exists():
                self.print_status("Virtual environment already exists", "INFO")
                return True
            
            self.print_status("Creating virtual environment...", "INFO")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], check=True)
            self.print_status("Virtual environment created successfully", "SUCCESS")
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_status(f"Failed to create virtual environment: {e}", "ERROR")
            return False
    
    def get_venv_python(self) -> str:
        """Get the path to the virtual environment Python executable."""
        if self.system == "windows":
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")
    
    def get_venv_pip(self) -> str:
        """Get the path to the virtual environment pip executable."""
        if self.system == "windows":
            return str(self.venv_path / "Scripts" / "pip.exe")
        else:
            return str(self.venv_path / "bin" / "pip")
    
    def install_python_packages(self) -> bool:
        """Install required Python packages."""
        try:
            pip_path = self.get_venv_pip()
            
            # Upgrade pip first
            self.print_status("Upgrading pip...", "INFO")
            subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
            
            # Install packages
            for package in self.python_packages:
                self.print_status(f"Installing {package}...", "INFO")
                subprocess.run([pip_path, "install", package], check=True)
            
            self.print_status("All Python packages installed successfully", "SUCCESS")
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_status(f"Failed to install Python packages: {e}", "ERROR")
            return False
    
    def download_file(self, url: str, destination: Path) -> bool:
        """Download a file from URL to destination."""
        try:
            self.print_status(f"Downloading {url}...", "INFO")
            
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(destination, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end="", flush=True)
            
            print()  # New line after progress
            self.print_status(f"Downloaded {destination.name}", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to download {url}: {e}", "ERROR")
            return False
    
    def extract_archive(self, archive_path: Path, extract_to: Path) -> bool:
        """Extract archive to specified directory."""
        try:
            self.print_status(f"Extracting {archive_path.name}...", "INFO")
            
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            else:
                self.print_status(f"Unsupported archive format: {archive_path.suffix}", "ERROR")
                return False
            
            self.print_status(f"Extracted to {extract_to}", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to extract {archive_path}: {e}", "ERROR")
            return False
    
    def install_system_tools(self) -> bool:
        """Install system-specific tools."""
        if self.system not in self.system_tools:
            self.print_status(f"No system tools configured for {self.system}", "WARNING")
            return True
        
        tools = self.system_tools[self.system]
        success = True
        
        for tool_name, config in tools.items():
            self.print_status(f"Installing {tool_name}...", "INFO")
            
            if "url" in config:  # Download and extract
                tool_dir = self.dependencies_path / config["extract_to"]
                tool_dir.mkdir(exist_ok=True)
                
                # Download
                archive_name = config["url"].split("/")[-1]
                archive_path = self.dependencies_path / archive_name
                
                if not self.download_file(config["url"], archive_path):
                    success = False
                    continue
                
                # Extract
                if not self.extract_archive(archive_path, tool_dir):
                    success = False
                    continue
                
                # Clean up archive
                archive_path.unlink()
                
            elif "install_cmd" in config:  # System package manager
                try:
                    # Check if already installed
                    if "check_cmd" in config:
                        try:
                            subprocess.run(config["check_cmd"], 
                                         stdout=subprocess.DEVNULL, 
                                         stderr=subprocess.DEVNULL, 
                                         check=True)
                            self.print_status(f"{tool_name} is already installed", "SUCCESS")
                            continue
                        except subprocess.CalledProcessError:
                            pass
                    
                    # Install using system package manager
                    subprocess.run(config["install_cmd"], check=True)
                    self.print_status(f"{tool_name} installed successfully", "SUCCESS")
                    
                except subprocess.CalledProcessError as e:
                    self.print_status(f"Failed to install {tool_name}: {e}", "ERROR")
                    success = False
        
        return success
    
    def configure_environment_paths(self) -> bool:
        """Configure environment paths for tools."""
        try:
            env_config = {
                "METACLI_ROOT": str(self.project_root),
                "METACLI_VENV": str(self.venv_path),
                "METACLI_DEPS": str(self.dependencies_path)
            }
            
            # Add tool paths for Windows
            if self.system == "windows":
                ffmpeg_path = self.dependencies_path / "ffmpeg" / "bin"
                exiftool_path = self.dependencies_path / "exiftool"
                
                if ffmpeg_path.exists():
                    env_config["METACLI_FFMPEG"] = str(ffmpeg_path)
                if exiftool_path.exists():
                    env_config["METACLI_EXIFTOOL"] = str(exiftool_path)
            
            # Save environment configuration
            env_file = self.project_root / "environment.json"
            with open(env_file, 'w') as f:
                json.dump(env_config, f, indent=2)
            
            # Create activation script
            self.create_activation_script(env_config)
            
            self.print_status("Environment paths configured", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to configure environment: {e}", "ERROR")
            return False
    
    def create_activation_script(self, env_config: Dict[str, str]):
        """Create activation script for easy environment setup."""
        if self.system == "windows":
            script_path = self.project_root / "activate_metacli.bat"
            script_content = "@echo off\n"
            script_content += "echo Activating MetaCLI Environment...\n"
            
            # Set environment variables
            for key, value in env_config.items():
                script_content += f"set {key}={value}\n"
            
            # Add tool paths to PATH
            if "METACLI_FFMPEG" in env_config:
                script_content += f"set PATH=%PATH%;{env_config['METACLI_FFMPEG']}\n"
            if "METACLI_EXIFTOOL" in env_config:
                script_content += f"set PATH=%PATH%;{env_config['METACLI_EXIFTOOL']}\n"
            
            # Activate virtual environment
            script_content += f"call {self.venv_path}\\Scripts\\activate.bat\n"
            script_content += "echo MetaCLI Environment activated!\n"
            script_content += "cmd /k\n"
            
        else:
            script_path = self.project_root / "activate_metacli.sh"
            script_content = "#!/bin/bash\n"
            script_content += "echo 'Activating MetaCLI Environment...'\n"
            
            # Set environment variables
            for key, value in env_config.items():
                script_content += f"export {key}='{value}'\n"
            
            # Activate virtual environment
            script_content += f"source {self.venv_path}/bin/activate\n"
            script_content += "echo 'MetaCLI Environment activated!'\n"
            script_content += "exec $SHELL\n"
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable on Unix systems
        if self.system != "windows":
            script_path.chmod(0o755)
        
        self.print_status(f"Activation script created: {script_path}", "SUCCESS")
    
    def verify_installation(self) -> bool:
        """Verify that all dependencies are properly installed."""
        self.print_status("Verifying installation...", "INFO")
        
        success = True
        python_path = self.get_venv_python()
        
        # Test Python packages
        test_imports = [
            "PIL", "mutagen", "PyPDF2", "docx", "chardet", "psutil"
        ]
        
        for module in test_imports:
            try:
                subprocess.run([python_path, "-c", f"import {module}"], 
                             check=True, 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
                self.print_status(f"✓ {module} import successful", "SUCCESS")
            except subprocess.CalledProcessError:
                self.print_status(f"✗ {module} import failed", "ERROR")
                success = False
        
        # Test MetaCLI modules
        try:
            subprocess.run([python_path, "-c", "from metacli.core.extractor import MetadataExtractor"], 
                         check=True, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            self.print_status("✓ MetaCLI modules accessible", "SUCCESS")
        except subprocess.CalledProcessError:
            self.print_status("✗ MetaCLI modules not accessible", "ERROR")
            success = False
        
        return success
    
    def run_setup(self) -> bool:
        """Run the complete dependency setup process."""
        self.print_status("Starting MetaCLI Dependency Setup", "INFO")
        self.print_status(f"System: {self.system} ({self.architecture})", "INFO")
        self.print_status(f"Python: {self.python_version}", "INFO")
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Creating virtual environment", self.create_virtual_environment),
            ("Installing Python packages", self.install_python_packages),
            ("Installing system tools", self.install_system_tools),
            ("Configuring environment paths", self.configure_environment_paths),
            ("Verifying installation", self.verify_installation)
        ]
        
        for step_name, step_func in steps:
            self.print_status(f"Step: {step_name}", "INFO")
            if not step_func():
                self.print_status(f"Setup failed at step: {step_name}", "ERROR")
                return False
            print()  # Add spacing between steps
        
        self.print_status("MetaCLI setup completed successfully!", "SUCCESS")
        self.print_status(f"To activate the environment, run: {self.project_root / ('activate_metacli.bat' if self.system == 'windows' else 'activate_metacli.sh')}", "INFO")
        
        return True

def main():
    """Main entry point for the dependency setup script."""
    try:
        manager = DependencyManager()
        success = manager.run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()