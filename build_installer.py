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
    
    # Create custom spec file with admin privileges
    spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Determine data files to include
datas = [
    (r'{current_dir / "installer"}', 'installer'),
]

# Add dist directory if it exists
import os
if os.path.exists(r'{current_dir / "dist"}'):
    datas.append((r'{current_dir / "dist"}', 'dist'))
    
# Add MetaCLI_Portable directory if it exists
if os.path.exists(r'{current_dir / "MetaCLI_Portable"}'):
    datas.append((r'{current_dir / "MetaCLI_Portable"}', 'MetaCLI_Portable'))

a = Analysis(
    [r'{installer_script}'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'winreg',
        'ctypes',
        'subprocess',
        'threading',
        'pathlib',
        'json',
        'logging',
        'tempfile',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MetaCLI_Installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={f"r'{current_dir / 'icon.ico'}" if (current_dir / "icon.ico").exists() else "None"},
     uac_admin=True,
     uac_uiaccess=False,
)
'''
    
    # Write spec file
    spec_file = current_dir / 'MetaCLI_Installer.spec'
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print("Created installer spec file with admin privileges")
    
    # Check what directories exist
    if (current_dir / "dist").exists():
        print("Including dist directory with CLI/GUI executables")
    else:
        print("Warning: dist directory not found, installer will download executables at runtime")
    
    if (current_dir / "MetaCLI_Portable").exists():
        print("Including MetaCLI_Portable directory")
    else:
        print("Warning: MetaCLI_Portable directory not found")
    
    # PyInstaller command using spec file
    cmd = [
        'pyinstaller',
        '--distpath', str(dist_dir),    # Output directory
        '--workpath', str(build_dir),   # Build directory
        str(spec_file)                  # Use our custom spec file
    ]
    
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