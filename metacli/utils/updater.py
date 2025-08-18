"""Automated update system for MetaCLI."""

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
import requests
from packaging import version
import re

from .hasher import ExecutableHasher


class MetaCLIUpdater:
    """Handles automatic updates for MetaCLI CLI and GUI executables."""
    
    def __init__(self, github_repo: str = "darkiifr/Metacli", installation_path: Optional[Path] = None):
        """Initialize the updater.
        
        Args:
            github_repo: GitHub repository in format 'owner/repo'
            installation_path: Path to MetaCLI installation (auto-detect if None)
        """
        self.github_repo = github_repo
        self.github_api_base = f"https://api.github.com/repos/{github_repo}"
        
        # Executable mappings (must be defined before _detect_installation_path)
        self.executables = {
            'metacli_cli': 'metacli.exe',
            'metacli_gui': 'MetaCLI-GUI.exe'
        }
        
        self.installation_path = installation_path or self._detect_installation_path()
        self.hasher = ExecutableHasher()
        self.temp_dir = None
    
    def _detect_installation_path(self) -> Path:
        """Auto-detect MetaCLI installation path."""
        # Common installation paths
        possible_paths = [
            Path.home() / 'AppData' / 'Local' / 'MetaCLI',
            Path('C:') / 'Program Files' / 'MetaCLI',
            Path('C:') / 'Program Files (x86)' / 'MetaCLI',
            Path.cwd()  # Current directory as fallback
        ]
        
        for path in possible_paths:
            if path.exists() and any((path / exe).exists() for exe in self.executables.values()):
                return path
        
        # Default to current directory if nothing found
        return Path.cwd()
    
    def _is_beta_version(self, tag_name: str) -> bool:
        """Check if a version tag represents a beta release.
        
        Args:
            tag_name: Version tag from GitHub release
            
        Returns:
            True if this is a beta version, False otherwise
        """
        if not tag_name:
            return False
        
        # Common beta indicators
        beta_patterns = [
            r'beta',
            r'alpha',
            r'rc',
            r'pre',
            r'dev',
            r'nightly',
            r'snapshot',
            r'-b\d+',  # -b1, -b2, etc.
            r'-a\d+',  # -a1, -a2, etc.
        ]
        
        tag_lower = tag_name.lower()
        return any(re.search(pattern, tag_lower) for pattern in beta_patterns)
    
    def get_all_releases(self) -> Optional[List[Dict[str, Any]]]:
        """Get all GitHub releases.
        
        Returns:
            List of release information dictionaries or None if failed
        """
        try:
            response = requests.get(f"{self.github_api_base}/releases", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching releases: {e}")
            return None
    
    def get_latest_stable_release(self) -> Optional[Dict[str, Any]]:
        """Get the latest stable (non-beta) release.
        
        Returns:
            Release information dictionary or None if failed
        """
        releases = self.get_all_releases()
        if not releases:
            return None
        
        # Filter out beta releases and find the latest stable
        stable_releases = [
            release for release in releases 
            if not self._is_beta_version(release.get('tag_name', ''))
            and not release.get('prerelease', False)
            and not release.get('draft', False)
        ]
        
        if stable_releases:
            return stable_releases[0]  # GitHub returns releases in descending order by date
        
        return None
    
    def get_latest_beta_release(self) -> Optional[Dict[str, Any]]:
        """Get the latest beta release.
        
        Returns:
            Release information dictionary or None if failed
        """
        releases = self.get_all_releases()
        if not releases:
            return None
        
        # Filter for beta releases and find the latest
        beta_releases = [
            release for release in releases 
            if (self._is_beta_version(release.get('tag_name', '')) or 
                release.get('prerelease', False))
            and not release.get('draft', False)
        ]
        
        if beta_releases:
            return beta_releases[0]  # GitHub returns releases in descending order by date
        
        return None

    def get_latest_release_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the latest stable release.
        
        Returns:
            Release information dictionary or None if failed
        """
        return self.get_latest_stable_release()
    
    def check_for_beta_updates(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if beta updates are available.
        
        Returns:
            Tuple of (updates_available, release_info)
        """
        # Get latest beta release info
        release_info = self.get_latest_beta_release()
        if not release_info:
            return False, None
        
        # Get release hashes
        release_hashes = self.get_release_hashes(release_info)
        if not release_hashes:
            return False, release_info
        
        # Get current installation hashes
        current_hashes = self.hasher.get_current_installation_hashes(self.installation_path)
        if not current_hashes:
            # No current installation or can't read hashes - assume update needed
            return True, release_info
        
        # Compare hashes
        comparison = self.hasher.compare_hashes(current_hashes, release_hashes)
        updates_needed = any(comparison.values())
        
        return updates_needed, release_info
    
    def get_release_hashes(self, release_info: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract executable hashes from release assets.
        
        Args:
            release_info: GitHub release information
            
        Returns:
            Dictionary of executable hashes or None if not found
        """
        # Look for hash manifest in release assets
        for asset in release_info.get('assets', []):
            if asset['name'] == 'hash_manifest.json':
                try:
                    response = requests.get(asset['browser_download_url'], timeout=10)
                    response.raise_for_status()
                    manifest = response.json()
                    return manifest.get('executables', {})
                except requests.RequestException as e:
                    print(f"Error downloading hash manifest: {e}")
                    return None
        
        print("Hash manifest not found in release assets")
        return None
    
    def check_for_updates(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if updates are available.
        
        Returns:
            Tuple of (updates_available, release_info)
        """
        # Get latest release info
        release_info = self.get_latest_release_info()
        if not release_info:
            return False, None
        
        # Get release hashes
        release_hashes = self.get_release_hashes(release_info)
        if not release_hashes:
            return False, release_info
        
        # Get current installation hashes
        current_hashes = self.hasher.get_current_installation_hashes(self.installation_path)
        if not current_hashes:
            # No current installation or can't read hashes - assume update needed
            return True, release_info
        
        # Compare hashes
        comparison = self.hasher.compare_hashes(current_hashes, release_hashes)
        updates_needed = any(comparison.values())
        
        return updates_needed, release_info
    
    def download_release_assets(self, release_info: Dict[str, Any]) -> Optional[Path]:
        """Download release assets to temporary directory.
        
        Args:
            release_info: GitHub release information
            
        Returns:
            Path to temporary directory with downloaded assets or None if failed
        """
        self.temp_dir = Path(tempfile.mkdtemp(prefix='metacli_update_'))
        
        try:
            for asset in release_info.get('assets', []):
                asset_name = asset['name']
                
                # Download executable assets
                if any(exe in asset_name.lower() for exe in ['metacli.exe', 'metacli-gui.exe']):
                    print(f"Downloading {asset_name}...")
                    
                    response = requests.get(asset['browser_download_url'], timeout=30)
                    response.raise_for_status()
                    
                    asset_path = self.temp_dir / asset_name
                    with open(asset_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"Downloaded: {asset_path}")
                
                # Download zip archives that might contain executables
                elif asset_name.endswith('.zip'):
                    print(f"Downloading and extracting {asset_name}...")
                    
                    response = requests.get(asset['browser_download_url'], timeout=30)
                    response.raise_for_status()
                    
                    zip_path = self.temp_dir / asset_name
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Extract zip
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(self.temp_dir)
                    
                    # Remove zip file after extraction
                    zip_path.unlink()
            
            return self.temp_dir
        
        except (requests.RequestException, zipfile.BadZipFile, OSError) as e:
            print(f"Error downloading release assets: {e}")
            self._cleanup_temp_dir()
            return None
    
    def verify_downloaded_assets(self, release_hashes: Dict[str, str]) -> bool:
        """Verify integrity of downloaded assets.
        
        Args:
            release_hashes: Expected hashes for executables
            
        Returns:
            True if all assets are verified, False otherwise
        """
        if not self.temp_dir:
            return False
        
        # Find downloaded executables
        downloaded_executables = {}
        for exe_name, exe_file in self.executables.items():
            # Look for the executable in temp directory
            possible_paths = [
                self.temp_dir / exe_file,
                self.temp_dir / exe_file.lower(),
                self.temp_dir / exe_file.replace('.exe', '').lower() + '.exe'
            ]
            
            for path in possible_paths:
                if path.exists():
                    downloaded_executables[exe_name] = path
                    break
        
        # Verify hashes
        for exe_name, expected_hash in release_hashes.items():
            if exe_name not in downloaded_executables:
                print(f"Warning: {exe_name} not found in downloaded assets")
                continue
            
            exe_path = downloaded_executables[exe_name]
            if not self.hasher.verify_executable_integrity(exe_path, expected_hash):
                print(f"Error: Hash verification failed for {exe_name}")
                return False
        
        print("All downloaded assets verified successfully")
        return True
    
    def backup_current_installation(self) -> Optional[Path]:
        """Create backup of current installation.
        
        Returns:
            Path to backup directory or None if failed
        """
        backup_dir = self.installation_path.parent / f"metacli_backup_{int(time.time())}"
        
        try:
            backup_dir.mkdir(exist_ok=True)
            
            for exe_name, exe_file in self.executables.items():
                src_path = self.installation_path / exe_file
                if src_path.exists():
                    dst_path = backup_dir / exe_file
                    shutil.copy2(src_path, dst_path)
                    print(f"Backed up: {src_path} -> {dst_path}")
            
            return backup_dir
        
        except (OSError, IOError) as e:
            print(f"Error creating backup: {e}")
            return None
    
    def install_updates(self) -> bool:
        """Install downloaded updates.
        
        Returns:
            True if installation successful, False otherwise
        """
        if not self.temp_dir:
            print("Error: No downloaded assets to install")
            return False
        
        try:
            # Ensure installation directory exists
            self.installation_path.mkdir(parents=True, exist_ok=True)
            
            # Find and install executables
            for exe_name, exe_file in self.executables.items():
                # Find the executable in temp directory
                src_path = None
                possible_paths = [
                    self.temp_dir / exe_file,
                    self.temp_dir / exe_file.lower(),
                    self.temp_dir / exe_file.replace('.exe', '').lower() + '.exe'
                ]
                
                for path in possible_paths:
                    if path.exists():
                        src_path = path
                        break
                
                if src_path:
                    dst_path = self.installation_path / exe_file
                    
                    # Remove old executable if it exists
                    if dst_path.exists():
                        dst_path.unlink()
                    
                    # Copy new executable
                    shutil.copy2(src_path, dst_path)
                    print(f"Installed: {src_path} -> {dst_path}")
                else:
                    print(f"Warning: {exe_name} not found in downloaded assets")
            
            return True
        
        except (OSError, IOError) as e:
            print(f"Error installing updates: {e}")
            return False
    
    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
            except OSError as e:
                print(f"Warning: Could not clean up temp directory: {e}")
    
    def perform_update(self) -> Tuple[bool, str]:
        """Perform complete update process.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check for updates
            print("Checking for updates...")
            updates_available, release_info = self.check_for_updates()
            
            if not updates_available:
                if release_info:
                    return True, f"No updates available. Current version: {release_info.get('tag_name', 'unknown')}"
                else:
                    return False, "Could not check for updates"
            
            print(f"Update available: {release_info.get('tag_name', 'unknown')}")
            
            # Get release hashes
            release_hashes = self.get_release_hashes(release_info)
            if not release_hashes:
                return False, "Could not retrieve release hashes"
            
            # Download assets
            print("Downloading update...")
            if not self.download_release_assets(release_info):
                return False, "Failed to download update assets"
            
            # Verify downloads
            print("Verifying downloads...")
            if not self.verify_downloaded_assets(release_hashes):
                return False, "Downloaded assets failed verification"
            
            # Create backup
            print("Creating backup...")
            backup_path = self.backup_current_installation()
            if not backup_path:
                print("Warning: Could not create backup")
            
            # Install updates
            print("Installing updates...")
            if not self.install_updates():
                return False, "Failed to install updates"
            
            # Update hash cache
            self.hasher.save_hashes_to_cache(
                release_hashes,
                {'version': release_info.get('tag_name'), 'updated_at': time.time()}
            )
            
            return True, f"Successfully updated to version {release_info.get('tag_name', 'unknown')}"
        
        except Exception as e:
            return False, f"Update failed: {str(e)}"
        
        finally:
            # Always cleanup
            self._cleanup_temp_dir()
    
    def get_current_version_info(self) -> Dict[str, Any]:
        """Get information about current installation.
        
        Returns:
            Dictionary with version and hash information
        """
        cache_data = self.hasher.load_hashes_from_cache()
        current_hashes = self.hasher.get_current_installation_hashes(self.installation_path)
        
        info = {
            'installation_path': str(self.installation_path),
            'executables_found': list(current_hashes.keys()) if current_hashes else [],
            'current_hashes': current_hashes or {},
        }
        
        if cache_data:
            info.update({
                'cached_version': cache_data.get('metadata', {}).get('version', 'unknown'),
                'last_update_check': cache_data.get('timestamp'),
                'hash_algorithm': cache_data.get('algorithm', 'unknown')
            })
        
        return info


import time


def main():
    """CLI interface for the updater."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MetaCLI Updater')
    parser.add_argument('--check', action='store_true', help='Check for updates only')
    parser.add_argument('--update', action='store_true', help='Perform update if available')
    parser.add_argument('--info', action='store_true', help='Show current installation info')
    parser.add_argument('--repo', default='darkiifr/Metacli', help='GitHub repository')
    parser.add_argument('--path', type=Path, help='Installation path')
    
    args = parser.parse_args()
    
    updater = MetaCLIUpdater(args.repo, args.path)
    
    if args.info:
        info = updater.get_current_version_info()
        print("Current Installation Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    elif args.check:
        updates_available, release_info = updater.check_for_updates()
        if updates_available:
            print(f"Update available: {release_info.get('tag_name', 'unknown')}")
        else:
            if release_info:
                print(f"No updates available. Latest version: {release_info.get('tag_name', 'unknown')}")
            else:
                print("Could not check for updates")
    
    elif args.update:
        success, message = updater.perform_update()
        print(message)
        if not success:
            exit(1)
    
    else:
        # Default: check and update if available
        success, message = updater.perform_update()
        print(message)
        if not success:
            exit(1)


if __name__ == '__main__':
    main()