#!/usr/bin/env python3
"""
Build script for MetaCLI GUI application.

This script compiles the MetaCLI GUI into a standalone executable using PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print("[OK] PyInstaller is already installed")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install PyInstaller: {e}")
            return False


def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/...")
            shutil.rmtree(dir_name)
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"Removing {spec_file}...")
        spec_file.unlink()


def create_spec_files():
    """Create custom PyInstaller spec files for both CLI and GUI."""
    
    # GUI Spec file
    gui_spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['metacli_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('LICENSE', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'mutagen',
        'mutagen.mp3',
        'mutagen.flac',
        'mutagen.mp4',
        'mutagen.oggvorbis',
        'PyPDF2',
        'docx',
        'openpyxl',
        'PIL',
        'PIL.Image',
        'PIL.ExifTags',
        'json',
        'pathlib',
        'threading',
        'webbrowser',
        'datetime',
        'argparse',
        'yaml',
        'logging',
    ],
    hookspath=[],
    hooksconfig={},
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
    name='MetaCLI-GUI',
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
    icon=None,
)
'''
    
    # CLI Spec file
    cli_spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['metacli_cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('LICENSE', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'mutagen',
        'mutagen.mp3',
        'mutagen.flac',
        'mutagen.mp4',
        'mutagen.oggvorbis',
        'PyPDF2',
        'docx',
        'openpyxl',
        'PIL',
        'PIL.Image',
        'PIL.ExifTags',
        'json',
        'pathlib',
        'threading',
        'webbrowser',
        'datetime',
        'argparse',
        'yaml',
        'logging',
    ],
    hookspath=[],
    hooksconfig={},
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
    name='metacli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('metacli_gui.spec', 'w') as f:
        f.write(gui_spec_content)
    print("Created GUI spec file: metacli_gui.spec")
    
    with open('metacli_cli.spec', 'w') as f:
        f.write(cli_spec_content)
    print("Created CLI spec file: metacli_cli.spec")
    
    print("[OK] Created custom build specifications")


def build_executables():
    """Build both CLI and GUI executables using PyInstaller."""
    print("\n[BUILD] Building executables...")
    
    success_count = 0
    
    # Build GUI executable
    print("\nBuilding GUI executable...")
    try:
        result = subprocess.run(
            ['pyinstaller', '--clean', 'metacli_gui.spec'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if GUI executable was created
        gui_exe_path = Path('dist/MetaCLI-GUI.exe')
        if gui_exe_path.exists():
            size_mb = gui_exe_path.stat().st_size / (1024 * 1024)
            print(f"[OK] GUI executable created: {gui_exe_path} ({size_mb:.1f} MB)")
            success_count += 1
        else:
            print("[ERROR] GUI executable not found in expected location")
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] GUI build failed: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"[ERROR] Unexpected error during GUI build: {e}")
    
    # Build CLI executable
    print("\nBuilding CLI executable...")
    try:
        result = subprocess.run(
            ['pyinstaller', '--clean', 'metacli_cli.spec'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if CLI executable was created
        cli_exe_path = Path('dist/metacli.exe')
        if cli_exe_path.exists():
            size_mb = cli_exe_path.stat().st_size / (1024 * 1024)
            print(f"[OK] CLI executable created: {cli_exe_path} ({size_mb:.1f} MB)")
            success_count += 1
        else:
            print("[ERROR] CLI executable not found in expected location")
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] CLI build failed: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"[ERROR] Unexpected error during CLI build: {e}")
    
    if success_count == 2:
        print("\n[OK] Both executables built successfully")
        return True
    elif success_count == 1:
        print("\n[WARNING] One executable built successfully")
        return True
    else:
        print("\n[ERROR] No executables built successfully")
        return False


def create_portable_package():
    """Create a portable package with both executables and documentation."""
    print("\n[PACKAGE] Creating portable package...")
    
    try:
        # Create portable directory
        portable_dir = Path("MetaCLI_Portable")
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        portable_dir.mkdir()
        
        # Copy executables
        executables = [
            ("dist/MetaCLI-GUI.exe", "MetaCLI-GUI.exe"),
            ("dist/metacli.exe", "metacli.exe")
        ]
        
        copied_exes = []
        for exe_source, exe_dest in executables:
            source_path = Path(exe_source)
            if source_path.exists():
                shutil.copy2(source_path, portable_dir / exe_dest)
                print(f"[OK] Copied {exe_dest} to {portable_dir}")
                copied_exes.append(exe_dest)
            else:
                print(f"[WARNING] {exe_source} not found, skipping")
        
        if not copied_exes:
            print("[ERROR] No executables found for portable package")
            return False
        
        # Copy documentation
        docs_to_copy = ["README.md", "LICENSE"]
        for doc in docs_to_copy:
            if Path(doc).exists():
                shutil.copy2(doc, portable_dir / doc)
                print(f"[OK] Copied {doc}")
        
        # Create batch files for easy execution
        if "MetaCLI-GUI.exe" in copied_exes:
            gui_batch_content = """@echo off
echo MetaCLI GUI - Metadata Extraction Tool
echo =========================================
echo.
start "" "%~dp0MetaCLI-GUI.exe"
"""
            
            with open(portable_dir / "run_gui.bat", "w") as f:
                f.write(gui_batch_content)
            print("[OK] Created run_gui.bat")
        
        if "metacli.exe" in copied_exes:
            cli_batch_content = """@echo off
echo MetaCLI CLI - Metadata Extraction Tool
echo ========================================
echo.
echo Usage: metacli [command] [options]
echo Commands: extract, scan, batch, compare, gui
echo.
echo Examples:
echo   metacli extract file.jpg
echo   metacli scan C:\\path\\to\\directory
echo   metacli gui
echo.
"%~dp0metacli.exe" %*
if not "%1"=="" pause
"""
            
            with open(portable_dir / "run_cli.bat", "w") as f:
                f.write(cli_batch_content)
            print("[OK] Created run_cli.bat")
        
        # Create a README for the portable package
        readme_content = f"""# MetaCLI Portable Package

This portable package contains the MetaCLI metadata extraction tool.

## Contents

{chr(10).join([f"- {exe}" for exe in copied_exes])}
- Documentation files
- Batch files for easy execution

## Usage

### GUI Version
Double-click `run_gui.bat` or `MetaCLI-GUI.exe` to launch the graphical interface.

### CLI Version
Double-click `run_cli.bat` for help, or use Command Prompt:
```
metacli extract file.jpg
metacli scan C:\\path\\to\\directory
metacli gui
```

## Features

- Extract metadata from images, documents, audio, and video files
- Scan directories recursively
- Batch processing capabilities
- Multiple output formats (JSON, YAML, table)
- Compare metadata between files
- User-friendly GUI interface

For more information, see README.md
"""
        
        with open(portable_dir / "PORTABLE_README.txt", "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("[OK] Created PORTABLE_README.txt")
        
        print(f"\n[OK] Portable package created in {portable_dir}/")
        print(f"[OK] Package contains {len(copied_exes)} executable(s)")
        return portable_dir
        
    except Exception as e:
        print(f"❌ Error creating portable package: {e}")
        return False


def main():
    """Main build process."""
    print("MetaCLI Build Script")
    print("=" * 40)
    
    # Check current directory
    if not Path("metacli_gui.py").exists():
        print("✗ Error: metacli_gui.py not found in current directory")
        print("Please run this script from the MetaCLI project root.")
        sys.exit(1)
    
    # Check and install PyInstaller
    if not check_pyinstaller():
        print("✗ Cannot proceed without PyInstaller")
        sys.exit(1)
    
    # Clean previous builds
    print("\nCleaning previous builds...")
    clean_build_dirs()
    
    # Create build specification
    print("\nPreparing build configuration...")
    create_spec_files()
    
    # Build executables
    print("\nBuilding executables...")
    if not build_executables():
        print("\n✗ Build failed. Please check the error messages above.")
        sys.exit(1)
    
    # Create portable package
    print("\nCreating portable package...")
    package_result = create_portable_package()
    
    if package_result:
        print(f"\n[SUCCESS] Build completed successfully!")
        print(f"[FILE] CLI Executable: dist/metacli.exe")
        print(f"[FILE] GUI Executable: dist/MetaCLI-GUI.exe")
        print(f"[PACKAGE] Portable package: {package_result}/")
        print("\n[INFO] You can now run the installation script with: python install.py")
    else:
        print("\n[WARNING] Build completed but portable package creation failed")


if __name__ == "__main__":
    main()