#!/usr/bin/env python3
"""
Build script for MetaCLI Installer
This script creates a standalone Windows executable for the installer.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import json

def build_cli_gui_executables():
    """Build CLI and GUI executables before creating installer"""
    print("Building CLI and GUI executables...")
    
    current_dir = Path(__file__).parent.absolute()
    
    # Check if build.py exists
    build_script = current_dir / 'build.py'
    if not build_script.exists():
        print("Warning: build.py not found, skipping CLI/GUI build")
        return False
    
    try:
        # Run the build script
        result = subprocess.run(
            [sys.executable, str(build_script)],
            check=True,
            capture_output=True,
            text=True,
            cwd=current_dir
        )
        
        print("✓ CLI and GUI executables built successfully")
        
        # Verify that the executables were created
        dist_dir = current_dir / 'dist'
        gui_exe = dist_dir / 'MetaCLI-GUI.exe'
        cli_exe = dist_dir / 'metacli.exe'
        
        if gui_exe.exists():
            print(f"✓ GUI executable found: {gui_exe}")
        else:
            print("⚠️ GUI executable not found")
            
        if cli_exe.exists():
            print(f"✓ CLI executable found: {cli_exe}")
        else:
            print("⚠️ CLI executable not found")
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build CLI/GUI executables: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during CLI/GUI build: {e}")
        return False

def main():
    """Build the MetaCLI installer executable"""
    
    # First, build CLI and GUI executables
    print("\n=== Step 1: Building CLI and GUI Executables ===")
    if not build_cli_gui_executables():
        print("⚠️ CLI/GUI build failed or incomplete, continuing with installer build...")
    
    # Get the current directory
    current_dir = Path(__file__).parent.absolute()
    
    # Define paths
    installer_script = current_dir / 'metacli_installer.py'
    dist_dir = current_dir / 'installer_output'
    build_dir = current_dir / 'installer_build'
    
    # Clean previous installer builds
    print("\n=== Step 2: Cleaning Previous Installer Builds ===")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
        
    print("\n=== Step 3: Building Installer Executable ===")
    print("Building MetaCLI Installer...")
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',                    # Create a single executable
        '--windowed',                   # Hide console window
        '--name=MetaCLI_Installer',     # Output executable name
        '--distpath', str(dist_dir),    # Output directory
        '--workpath', str(build_dir),   # Build directory
        '--specpath', str(current_dir), # Spec file location
        '--add-data', f'{current_dir / "installer"};installer',  # Include installer package
    ]
    
    # Add dist directory only if it exists
    if (current_dir / "dist").exists():
        cmd.extend(['--add-data', f'{current_dir / "dist"};dist'])
        print("Including dist directory with CLI/GUI executables")
    else:
        print("Warning: dist directory not found, installer will download executables at runtime")
    
    # Add MetaCLI_Portable directory only if it exists
    if (current_dir / "MetaCLI_Portable").exists():
        cmd.extend(['--add-data', f'{current_dir / "MetaCLI_Portable"};MetaCLI_Portable'])
        print("Including MetaCLI_Portable directory")
    else:
        print("Warning: MetaCLI_Portable directory not found")
    
    cmd.append(str(installer_script))
    
    # Add icon if it exists
    icon_path = current_dir / "icon.ico"
    if icon_path.exists():
        cmd.insert(-1, '--icon')
        cmd.insert(-1, str(icon_path))
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(f"Installer created: {dist_dir / 'MetaCLI_Installer.exe'}")
        
        # Copy additional files to output directory
        print("\n=== Step 4: Organizing Output ===")
        additional_files = [
            'requirements.txt',
            'README.md',
            'INSTALLER_README.md'
        ]
        
        for file_name in additional_files:
            src_file = current_dir / file_name
            if src_file.exists():
                dst_file = dist_dir / file_name
                shutil.copy2(src_file, dst_file)
                print(f"Copied: {file_name}")
                
        # Create a version info file
        version_info = {
            "version": "1.0.0",
            "build_date": str(Path(__file__).stat().st_mtime),
            "description": "MetaCLI Windows Installer"
        }
        
        import json
        with open(dist_dir / 'version_info.json', 'w') as f:
            json.dump(version_info, f, indent=2)
        
        print("\nInstaller package ready in:", dist_dir)
        print("\nContents:")
        for item in dist_dir.iterdir():
            print(f"  - {item.name}")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return 1
    except FileNotFoundError:
        print("Error: PyInstaller not found. Please install it with: pip install pyinstaller")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())