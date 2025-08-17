"""Executable hashing utility for update verification."""

import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json
import time


class ExecutableHasher:
    """Utility class for hashing executables and managing hash verification."""
    
    def __init__(self, hash_algorithm: str = 'sha256'):
        """Initialize the hasher with specified algorithm.
        
        Args:
            hash_algorithm: Hash algorithm to use (default: sha256)
        """
        self.hash_algorithm = hash_algorithm
        self.hash_cache_file = Path.home() / '.metacli' / 'executable_hashes.json'
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        self.hash_cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate hash of a file.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            Hex digest of the file hash, or None if file doesn't exist
        """
        if not file_path.exists() or not file_path.is_file():
            return None
        
        try:
            hasher = hashlib.new(self.hash_algorithm)
            
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        
        except (OSError, IOError) as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def get_executable_hashes(self, executable_paths: Dict[str, Path]) -> Dict[str, str]:
        """Get hashes for multiple executables.
        
        Args:
            executable_paths: Dictionary mapping executable names to their paths
            
        Returns:
            Dictionary mapping executable names to their hashes
        """
        hashes = {}
        
        for name, path in executable_paths.items():
            file_hash = self.calculate_file_hash(path)
            if file_hash:
                hashes[name] = file_hash
            else:
                print(f"Warning: Could not calculate hash for {name} at {path}")
        
        return hashes
    
    def save_hashes_to_cache(self, hashes: Dict[str, str], metadata: Optional[Dict[str, Any]] = None):
        """Save hashes to cache file.
        
        Args:
            hashes: Dictionary of executable hashes
            metadata: Optional metadata to include (e.g., version info)
        """
        cache_data = {
            'hashes': hashes,
            'timestamp': time.time(),
            'algorithm': self.hash_algorithm,
            'metadata': metadata or {}
        }
        
        try:
            with open(self.hash_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except (OSError, IOError) as e:
            print(f"Error saving hash cache: {e}")
    
    def load_hashes_from_cache(self) -> Optional[Dict[str, Any]]:
        """Load hashes from cache file.
        
        Returns:
            Cache data dictionary or None if cache doesn't exist or is invalid
        """
        if not self.hash_cache_file.exists():
            return None
        
        try:
            with open(self.hash_cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate cache structure
            if not all(key in cache_data for key in ['hashes', 'timestamp', 'algorithm']):
                return None
            
            return cache_data
        
        except (OSError, IOError, json.JSONDecodeError) as e:
            print(f"Error loading hash cache: {e}")
            return None
    
    def compare_hashes(self, current_hashes: Dict[str, str], reference_hashes: Dict[str, str]) -> Dict[str, bool]:
        """Compare current hashes with reference hashes.
        
        Args:
            current_hashes: Current executable hashes
            reference_hashes: Reference hashes (e.g., from GitHub release)
            
        Returns:
            Dictionary mapping executable names to whether they need updating (True = needs update)
        """
        comparison_result = {}
        
        for name in current_hashes.keys():
            if name not in reference_hashes:
                # New executable or missing from reference
                comparison_result[name] = False
            else:
                # Compare hashes
                comparison_result[name] = current_hashes[name] != reference_hashes[name]
        
        # Check for new executables in reference that don't exist locally
        for name in reference_hashes.keys():
            if name not in current_hashes:
                comparison_result[name] = True  # New executable needs to be downloaded
        
        return comparison_result
    
    def get_current_installation_hashes(self, installation_path: Optional[Path] = None) -> Dict[str, str]:
        """Get hashes of currently installed executables.
        
        Args:
            installation_path: Path to installation directory (auto-detect if None)
            
        Returns:
            Dictionary of current executable hashes
        """
        if installation_path is None:
            # Auto-detect installation path
            installation_path = Path.home() / 'AppData' / 'Local' / 'MetaCLI'
        
        executable_paths = {
            'metacli_cli': installation_path / 'metacli.exe',
            'metacli_gui': installation_path / 'MetaCLI-GUI.exe'
        }
        
        return self.get_executable_hashes(executable_paths)
    
    def verify_executable_integrity(self, executable_path: Path, expected_hash: str) -> bool:
        """Verify the integrity of an executable against expected hash.
        
        Args:
            executable_path: Path to the executable
            expected_hash: Expected hash value
            
        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self.calculate_file_hash(executable_path)
        return actual_hash == expected_hash if actual_hash else False
    
    def generate_hash_manifest(self, executable_paths: Dict[str, Path], output_path: Path):
        """Generate a hash manifest file for distribution.
        
        Args:
            executable_paths: Dictionary mapping executable names to paths
            output_path: Path where to save the manifest
        """
        hashes = self.get_executable_hashes(executable_paths)
        
        manifest = {
            'version': '1.0',
            'algorithm': self.hash_algorithm,
            'generated_at': time.time(),
            'executables': hashes
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"Hash manifest generated: {output_path}")
        except (OSError, IOError) as e:
            print(f"Error generating hash manifest: {e}")


def main():
    """CLI interface for the hasher utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MetaCLI Executable Hasher')
    parser.add_argument('--file', '-f', type=Path, help='Calculate hash for a single file')
    parser.add_argument('--installation', '-i', type=Path, help='Get hashes for installation directory')
    parser.add_argument('--manifest', '-m', type=Path, help='Generate hash manifest for directory')
    parser.add_argument('--algorithm', '-a', default='sha256', help='Hash algorithm to use')
    
    args = parser.parse_args()
    
    hasher = ExecutableHasher(args.algorithm)
    
    if args.file:
        file_hash = hasher.calculate_file_hash(args.file)
        if file_hash:
            print(f"{args.algorithm.upper()}: {file_hash}")
        else:
            print(f"Error: Could not calculate hash for {args.file}")
    
    elif args.installation:
        hashes = hasher.get_current_installation_hashes(args.installation)
        print("Installation Hashes:")
        for name, hash_value in hashes.items():
            print(f"  {name}: {hash_value}")
    
    elif args.manifest:
        executable_paths = {
            'metacli_cli': args.manifest / 'metacli.exe',
            'metacli_gui': args.manifest / 'MetaCLI-GUI.exe'
        }
        manifest_path = args.manifest / 'hash_manifest.json'
        hasher.generate_hash_manifest(executable_paths, manifest_path)
    
    else:
        # Default: show current installation hashes
        hashes = hasher.get_current_installation_hashes()
        if hashes:
            print("Current Installation Hashes:")
            for name, hash_value in hashes.items():
                print(f"  {name}: {hash_value}")
        else:
            print("No MetaCLI installation found or no executables to hash.")


if __name__ == '__main__':
    main()