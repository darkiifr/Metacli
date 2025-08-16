#!/usr/bin/env python3
"""
Dependency Manager for MetaCLI Installer
Handles checking and installing Python dependencies
"""

import subprocess
import sys
import importlib
import pkg_resources
from typing import List, Dict, Tuple, Optional
import re
from pathlib import Path
import platform


class DependencyManager:
    """Manages Python package dependencies for MetaCLI installation"""
    
    def __init__(self, logger_callback=None):
        self.logger_callback = logger_callback or print
        self.pip_executable = self._find_pip_executable()
        
    def _find_pip_executable(self) -> str:
        """Find the appropriate pip executable"""
        # Try different pip commands
        pip_commands = [
            [sys.executable, '-m', 'pip'],
            ['pip'],
            ['pip3'],
            ['python', '-m', 'pip'],
            ['python3', '-m', 'pip']
        ]
        
        # Set creation flags for Windows to hide terminal windows
        creation_flags = 0
        if platform.system() == 'Windows':
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        for cmd in pip_commands:
            try:
                result = subprocess.run(cmd + ['--version'], 
                                      capture_output=True, text=True, timeout=10,
                                      creationflags=creation_flags)
                if result.returncode == 0:
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        raise RuntimeError("Could not find pip executable")
        
    def log(self, message: str):
        """Log a message using the callback"""
        if self.logger_callback:
            self.logger_callback(message)
            
    def parse_requirement(self, requirement: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Parse a requirement string into package name, operator, and version"""
        # Handle requirements like 'package>=1.0.0', 'package==1.0.0', 'package'
        match = re.match(r'^([a-zA-Z0-9_-]+)([><=!]+)?([0-9.]+.*)?$', requirement.strip())
        if match:
            package_name = match.group(1)
            operator = match.group(2)
            version = match.group(3)
            return package_name, operator, version
        else:
            return requirement.strip(), None, None
            
    def is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        try:
            # Handle special package name mappings
            import_name = self._get_import_name(package_name)
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
            
    def _get_import_name(self, package_name: str) -> str:
        """Get the import name for a package (some packages have different import names)"""
        name_mappings = {
            'python-docx': 'docx',
            'Pillow': 'PIL',
            'PyPDF2': 'PyPDF2',
            'pyyaml': 'yaml',
            'beautifulsoup4': 'bs4',
        }
        return name_mappings.get(package_name, package_name)
        
    def get_installed_version(self, package_name: str) -> Optional[str]:
        """Get the installed version of a package"""
        try:
            distribution = pkg_resources.get_distribution(package_name)
            return distribution.version
        except pkg_resources.DistributionNotFound:
            return None
            
    def version_satisfies_requirement(self, installed_version: str, operator: str, required_version: str) -> bool:
        """Check if installed version satisfies the requirement"""
        try:
            from packaging import version
            installed = version.parse(installed_version)
            required = version.parse(required_version)
            
            if operator == '>=':
                return installed >= required
            elif operator == '>':
                return installed > required
            elif operator == '==':
                return installed == required
            elif operator == '<=':
                return installed <= required
            elif operator == '<':
                return installed < required
            elif operator == '!=':
                return installed != required
            else:
                return True  # No operator means any version is fine
        except ImportError:
            # Fallback to string comparison if packaging is not available
            if operator == '>=':
                return installed_version >= required_version
            elif operator == '==':
                return installed_version == required_version
            else:
                return True
                
    def check_requirement(self, requirement: str) -> Dict[str, any]:
        """Check if a requirement is satisfied"""
        package_name, operator, required_version = self.parse_requirement(requirement)
        
        result = {
            'package': package_name,
            'requirement': requirement,
            'installed': False,
            'version': None,
            'satisfied': False,
            'needs_install': True
        }
        
        if self.is_package_installed(package_name):
            result['installed'] = True
            installed_version = self.get_installed_version(package_name)
            result['version'] = installed_version
            
            if operator and required_version and installed_version:
                result['satisfied'] = self.version_satisfies_requirement(
                    installed_version, operator, required_version
                )
                result['needs_install'] = not result['satisfied']
            else:
                result['satisfied'] = True
                result['needs_install'] = False
        
        return result
        
    def check_all_requirements(self, requirements: List[str]) -> Dict[str, Dict[str, any]]:
        """Check all requirements and return detailed status"""
        results = {}
        
        self.log("Checking Python dependencies...")
        
        for requirement in requirements:
            package_name, _, _ = self.parse_requirement(requirement)
            result = self.check_requirement(requirement)
            results[package_name] = result
            
            if result['satisfied']:
                self.log(f"✓ {package_name} {result['version']} is satisfied")
            elif result['installed']:
                self.log(f"⚠ {package_name} {result['version']} needs upgrade (requires {requirement})")
            else:
                self.log(f"✗ {package_name} is not installed (requires {requirement})")
                
        return results
        
    def install_package(self, requirement: str, upgrade: bool = False) -> bool:
        """Install a single package"""
        package_name, _, _ = self.parse_requirement(requirement)
        
        try:
            cmd = self.pip_executable + ['install']
            if upgrade:
                cmd.append('--upgrade')
            cmd.append(requirement)
            
            self.log(f"Installing {requirement}...")
            
            # Set creation flags for Windows to hide terminal windows
            creation_flags = 0
            if platform.system() == 'Windows':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                                  creationflags=creation_flags)
            
            if result.returncode == 0:
                self.log(f"✓ Successfully installed {package_name}")
                if result.stdout:
                    self.log(f"  Output: {result.stdout.strip()[:200]}...")  # Log first 200 chars
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.log(f"✗ Failed to install {package_name}")
                self.log(f"  Error: {error_msg[:300]}...")  # Log first 300 chars of error
                if result.stdout:
                    self.log(f"  Output: {result.stdout.strip()[:200]}...")  # Also log stdout if available
                return False
                
        except subprocess.TimeoutExpired:
            self.log(f"✗ Installation of {package_name} timed out after 300 seconds")
            self.log(f"  Command: {' '.join(cmd)}")
            return False
        except FileNotFoundError:
            self.log(f"✗ pip executable not found: {' '.join(self.pip_executable)}")
            return False
        except PermissionError:
            self.log(f"✗ Permission denied when installing {package_name}")
            self.log(f"  Try running the installer as Administrator")
            return False
        except Exception as e:
            self.log(f"✗ Unexpected error installing {package_name}: {str(e)}")
            self.log(f"  Command: {' '.join(cmd)}")
            return False
            
    def install_missing_requirements(self, requirements: List[str]) -> Tuple[List[str], List[str]]:
        """Install all missing requirements"""
        check_results = self.check_all_requirements(requirements)
        
        installed = []
        failed = []
        
        for package_name, result in check_results.items():
            if result['needs_install']:
                requirement = result['requirement']
                upgrade = result['installed'] and not result['satisfied']
                
                if self.install_package(requirement, upgrade=upgrade):
                    installed.append(package_name)
                else:
                    failed.append(package_name)
                    
        return installed, failed
        
    def upgrade_pip(self) -> bool:
        """Upgrade pip to the latest version"""
        try:
            self.log("Upgrading pip...")
            cmd = self.pip_executable + ['install', '--upgrade', 'pip']
            
            # Set creation flags for Windows to hide terminal windows
            creation_flags = 0
            if platform.system() == 'Windows':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                  creationflags=creation_flags)
            
            if result.returncode == 0:
                self.log("✓ pip upgraded successfully")
                if result.stdout:
                    self.log(f"  Output: {result.stdout.strip()[:200]}...")  # Log first 200 chars
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.log(f"⚠ pip upgrade failed")
                self.log(f"  Error: {error_msg[:300]}...")  # Log first 300 chars of error
                # pip upgrade failure is not critical, continue with installation
                return False
                
        except subprocess.TimeoutExpired:
            self.log(f"⚠ pip upgrade timed out after 120 seconds")
            return False
        except FileNotFoundError:
            self.log(f"⚠ pip executable not found: {' '.join(self.pip_executable)}")
            return False
        except Exception as e:
            self.log(f"⚠ Unexpected error upgrading pip: {str(e)}")
            self.log(f"  Command: {' '.join(cmd)}")
            return False
            
    def install_from_requirements_file(self, requirements_file: Path) -> Tuple[List[str], List[str]]:
        """Install requirements from a requirements.txt file"""
        if not requirements_file.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_file}")
            
        requirements = []
        with open(requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
                    
        return self.install_missing_requirements(requirements)
        
    def create_virtual_environment(self, venv_path: Path) -> bool:
        """Create a virtual environment (optional feature)"""
        try:
            self.log(f"Creating virtual environment at {venv_path}...")
            
            # Set creation flags for Windows to hide terminal windows
            creation_flags = 0
            if platform.system() == 'Windows':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], 
                                  capture_output=True, text=True, timeout=120,
                                  creationflags=creation_flags)
            
            if result.returncode == 0:
                self.log("✓ Virtual environment created successfully")
                return True
            else:
                self.log(f"✗ Failed to create virtual environment: {result.stderr}")
                return False
                
        except Exception as e:
            self.log(f"✗ Error creating virtual environment: {str(e)}")
            return False
            
    def get_system_info(self) -> Dict[str, str]:
        """Get system information for debugging"""
        info = {
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'python_executable': sys.executable,
            'pip_executable': ' '.join(self.pip_executable) if isinstance(self.pip_executable, list) else str(self.pip_executable)
        }
        
        try:
            result = subprocess.run(self.pip_executable + ['--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                info['pip_version'] = result.stdout.strip()
        except:
            info['pip_version'] = 'Unknown'
            
        return info