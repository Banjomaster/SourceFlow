"""
Directory Explorer Module

This module is responsible for traversing the directory structure of a code project,
identifying relevant code files, and filtering out non-code files and irrelevant directories.
"""

import os
from pathlib import Path
from typing import List, Set, Dict, Optional

# Default file extensions to consider as code files
DEFAULT_CODE_EXTENSIONS = {
    '.py',    # Python
    '.js',    # JavaScript
    '.ts',    # TypeScript
    '.java',  # Java
    '.cpp',   # C++
    '.c',     # C
    '.h',     # C/C++ header
    '.hpp',   # C++ header
    '.cs',    # C#
    '.go',    # Go
    '.rs',    # Rust
    '.rb',    # Ruby
    '.php',   # PHP
    '.swift'  # Swift
}

# Default directories to skip
DEFAULT_SKIP_DIRS = {
    '.git',
    'node_modules',
    'venv',
    '.env',
    '__pycache__',
    'dist',
    'build',
    '.idea',
    '.vscode'
}

class DirectoryExplorer:
    """
    A class for exploring directory structures and identifying code files.
    """
    
    def __init__(
        self,
        code_extensions: Optional[Set[str]] = None,
        skip_dirs: Optional[Set[str]] = None
    ):
        """
        Initialize the DirectoryExplorer with configurable settings.
        
        Args:
            code_extensions: Set of file extensions to consider as code files.
                            Defaults to DEFAULT_CODE_EXTENSIONS if None.
            skip_dirs: Set of directory names to skip during traversal.
                      Defaults to DEFAULT_SKIP_DIRS if None.
        """
        self.code_extensions = code_extensions or DEFAULT_CODE_EXTENSIONS
        self.skip_dirs = skip_dirs or DEFAULT_SKIP_DIRS
        
    def explore(self, root_dir: str) -> List[str]:
        """
        Recursively explore the directory structure starting from root_dir.
        
        Args:
            root_dir: The root directory to start exploration from.
            
        Returns:
            A list of paths to code files found during exploration.
            
        Raises:
            ValueError: If root_dir is not a valid directory.
        """
        if not os.path.isdir(root_dir):
            raise ValueError(f"'{root_dir}' is not a valid directory")
        
        code_files = []
        root_path = Path(root_dir).resolve()  # Get absolute path
        
        for subdir, dirs, files in os.walk(root_path):
            # Skip irrelevant directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in self.code_extensions:
                    file_path = os.path.join(subdir, file)
                    code_files.append(file_path)
        
        print(f"Found {len(code_files)} code files in {root_dir}")
        return code_files
    
    def get_file_stats(self, code_files: List[str]) -> Dict[str, int]:
        """
        Generate statistics about the identified code files.
        
        Args:
            code_files: List of paths to code files.
            
        Returns:
            A dictionary with file extension counts.
        """
        stats = {}
        for file_path in code_files:
            file_ext = os.path.splitext(file_path)[1].lower()
            stats[file_ext] = stats.get(file_ext, 0) + 1
        
        return stats 