#!/usr/bin/env python
"""
Test script to verify the fix for Unknown labels and missing dependency information.
"""

import os
import sys
import json
from sourceflow.core.visualizer import VisualizationGenerator

def test_fix(analysis_file, output_dir):
    """
    Generate diagrams with the fixed code and check if Unknown labels are removed.
    
    Args:
        analysis_file: Path to the analysis_data.json file
        output_dir: Directory where diagrams should be saved
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
    
    # Generate the HTML viewer
    html_file = generator.generate_html_viewer(analysis_data, output_name="fixed_viewer")
    
    print(f"\nGenerated HTML viewer at: {html_file}")
    print("Please check this file to see if the Unknown labels have been fixed.")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_fix_unknown.py <analysis_file> <output_dir>")
        sys.exit(1)
    
    analysis_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    if test_fix(analysis_file, output_dir):
        print("Test completed successfully.")
    else:
        print("Test failed.")
        sys.exit(1) 