"""
Core modules for the Code Project Analyzer.

This package contains the main components of the Code Project Analyzer:
- Directory Explorer: For traversing directories and identifying code files
- Code Analyzer: For analyzing code with AI
- Relationship Builder: For building cross-file relationships
- Visualization Generator: For generating diagrams
"""

from sourceflow.core.explorer import DirectoryExplorer
from sourceflow.core.analyzer import CodeAnalyzer
from sourceflow.core.builder import RelationshipBuilder
from sourceflow.core.visualizer import VisualizationGenerator

__all__ = [
    'DirectoryExplorer',
    'CodeAnalyzer',
    'RelationshipBuilder',
    'VisualizationGenerator'
]

# Core components for SourceFlow
# Contains the analyzer, visualizer, and other core functionality
