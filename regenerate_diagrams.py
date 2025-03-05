#!/usr/bin/env python
"""
Script to regenerate diagrams from existing analysis data.
This allows testing the max_nodes parameter without rerunning the full analysis.
"""

import os
import sys
import json
import argparse
from sourceflow.core.visualizer import VisualizationGenerator

def regenerate_diagrams(analysis_file, output_dir, max_nodes=None):
    """
    Regenerate diagrams using the existing analysis data with optional node limiting.
    
    Args:
        analysis_file: Path to the analysis_data.json file
        output_dir: Directory where diagrams should be saved
        max_nodes: Optional limit on the number of nodes to include in diagrams
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the analysis data
    print(f"Loading analysis data from: {analysis_file}")
    try:
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
    except Exception as e:
        print(f"Error loading analysis data: {e}")
        return False
    
    print(f"Loaded analysis data with {len(analysis_data.get('file_summaries', {}))} files")
    
    # Create visualization generator
    generator = VisualizationGenerator(output_dir=output_dir)
    
    # Generate dependency diagram with max_nodes limit
    if max_nodes:
        print(f"Generating dependency diagram with max_nodes={max_nodes}")
    else:
        print("Generating dependency diagram with no node limit")
        
    dependency_files = generator.generate_dependency_diagram(
        analysis_data, 
        output_name="code_dependencies", 
        max_nodes=max_nodes
    )
    
    # Generate other diagrams
    structure_files = generator.generate_function_diagram(
        analysis_data, 
        output_name="code_structure", 
        max_nodes=max_nodes
    )
    execution_files = generator.generate_execution_path_diagram(analysis_data, output_name="execution_paths")
    
    # Generate HTML viewer
    html_file = generator.generate_html_viewer(analysis_data, output_name="interactive_viewer")
    
    print("\nDiagram generation complete.")
    print(f"Dependency diagram: {dependency_files.get('mermaid')}")
    print(f"Interactive viewer: {html_file}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Regenerate diagrams from existing analysis data")
    parser.add_argument("analysis_file", help="Path to analysis_data.json file")
    parser.add_argument("--output-dir", "-o", default="./diagram_output", 
                        help="Directory to save generated diagrams")
    parser.add_argument("--max-nodes", "-m", type=int, default=None, 
                        help="Maximum number of nodes to include in dependency diagrams")
    
    args = parser.parse_args()
    
    regenerate_diagrams(args.analysis_file, args.output_dir, args.max_nodes)

if __name__ == "__main__":
    main() 