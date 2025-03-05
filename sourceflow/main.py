"""
Code Project Analyzer - Main Orchestrator

This module serves as the main entry point for the Code Project Analyzer application.
It coordinates the workflow between the different components and provides a CLI interface.
"""

import os
import argparse
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import core modules
from sourceflow.core.explorer import DirectoryExplorer
from sourceflow.core.analyzer import CodeAnalyzer
from sourceflow.core.builder import RelationshipBuilder
from sourceflow.core.visualizer import VisualizationGenerator

def analyze_project(
    root_dir: str,
    output_dir: Optional[str] = None,
    formats: Optional[List[str]] = None,
    skip_analysis: bool = False,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    generate_description: bool = True
) -> Dict[str, Any]:
    """
    Analyze a code project and generate visualizations.
    
    Args:
        root_dir: The root directory of the code project to analyze
        output_dir: Directory to save output files (defaults to a 'results' folder in the project root)
        formats: List of output formats to generate (defaults to ['png', 'svg', 'mermaid'])
        skip_analysis: If True, skip code analysis if results exist and load from JSON instead
        api_key: OpenAI API key (override environment variable)
        model: OpenAI model to use (override environment variable)
        generate_description: If True, generate an application description (defaults to True)
        
    Returns:
        Dictionary with paths to generated visualization files
    """
    # Set up output directory
    if not output_dir:
        output_dir = os.path.join(root_dir, 'results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analysis cache path
    analysis_cache = os.path.join(output_dir, 'analysis_data.json')
    
    # Initialize components
    explorer = DirectoryExplorer()
    analyzer = CodeAnalyzer(api_key=api_key, model=model)
    builder = RelationshipBuilder()
    visualizer = VisualizationGenerator(output_dir=output_dir, formats=formats)
    
    # 1. Explore the directory to find code files
    print(f"Exploring directory: {root_dir}")
    code_files = explorer.explore(root_dir)
    if not code_files:
        print("No code files found in the directory.")
        return {}
    
    print(f"Found {len(code_files)} code files.")
    stats = explorer.get_file_stats(code_files)
    print(f"Language distribution: {stats}")
    
    # 2. Try to load cached analysis if requested and available
    if skip_analysis and os.path.exists(analysis_cache):
        import json
        print(f"Loading cached analysis from {analysis_cache}")
        with open(analysis_cache, 'r') as f:
            builder_data = json.load(f)
    else:
        # 3. Analyze each file
        print("\nStarting code analysis...")
        start_time = time.time()
        
        for i, file_path in enumerate(code_files):
            try:
                print(f"\n[{i+1}/{len(code_files)}] Analyzing {file_path}")
                analysis = analyzer.analyze_file(file_path)
                builder.add_file_analysis(file_path, analysis)
            except Exception as e:
                print(f"Error analyzing {file_path}: {str(e)}")
                print("Continuing with next file...")
        
        analysis_time = time.time() - start_time
        print(f"\nAnalysis completed in {analysis_time:.2f} seconds.")
        
        # 4. Get the aggregated results
        builder_data = builder.get_summary()
        
        # 5. Save analysis data to JSON for future use
        visualizer.export_data(builder_data, output_name="analysis_data")
    
    # 6. Generate application description if requested
    if generate_description:
        print("\nGenerating application description...")
        try:
            description_file = visualizer.generate_application_description(analysis_cache)
            print(f"Application description saved to: {description_file}")
        except Exception as e:
            print(f"Error generating application description: {str(e)}")
            print("Continuing with visualization generation...")
    
    # 7. Generate visualizations
    print("\nGenerating visualizations...")
    output_files = {}
    
    # Function call diagram - only if non-HTML formats are requested
    if any(fmt != 'html' for fmt in visualizer.formats):
        print("Creating function call diagram...")
        function_files = visualizer.generate_function_diagram(builder_data, output_name="code_structure")
        output_files["function_diagram"] = function_files
        
        # Dependency diagram
        print("Creating dependency diagram...")
        dependency_files = visualizer.generate_dependency_diagram(builder_data, output_name="code_dependencies")
        output_files["dependency_diagram"] = dependency_files
        
        # Execution path diagram
        print("Creating execution path diagram...")
        path_files = visualizer.generate_execution_path_diagram(builder_data, output_name="execution_paths")
        output_files["execution_path_diagram"] = path_files
    
    # Generate interactive HTML viewer if requested
    if 'html' in visualizer.formats:
        print("Creating interactive HTML viewer...")
        html_path = visualizer.generate_html_viewer(builder_data, output_name="interactive_viewer")
        output_files["interactive_viewer"] = {"html": html_path}
    
    print(f"\nAll visualizations saved to {output_dir}")
    for diagram_type, files in output_files.items():
        print(f"  - {diagram_type}:")
        for fmt, file_path in files.items():
            print(f"    - {fmt}: {file_path}")
    
    return output_files

def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(description="Code Project Analyzer")
    parser.add_argument("root_dir", help="Root directory of the code project to analyze")
    parser.add_argument(
        "--output-dir", "-o", 
        help="Directory to save output files (defaults to a 'results' folder in the project root)"
    )
    parser.add_argument(
        "--formats", "-f", 
        nargs="+", 
        choices=["png", "svg", "pdf", "mermaid", "html"],
        default=["png", "svg", "mermaid", "html"],
        help="Output formats to generate (including 'html' for interactive viewer)"
    )
    parser.add_argument(
        "--skip-analysis", "-s",
        action="store_true",
        help="Skip code analysis if results exist and load from JSON instead"
    )
    parser.add_argument(
        "--html-only", 
        action="store_true",
        help="Generate only the interactive HTML viewer (implies --skip-analysis if analysis data exists)"
    )
    parser.add_argument(
        "--no-description", 
        action="store_true",
        help="Skip generating the application description"
    )
    
    args = parser.parse_args()
    
    # If html-only is specified, adjust the formats and enable skip-analysis if possible
    if args.html_only:
        args.formats = ["html"]
        # Only skip analysis if the analysis data exists
        analysis_cache = os.path.join(args.output_dir or os.path.join(args.root_dir, 'results'), 'analysis_data.json')
        if os.path.exists(analysis_cache):
            args.skip_analysis = True
    
    analyze_project(
        root_dir=args.root_dir,
        output_dir=args.output_dir,
        formats=args.formats,
        skip_analysis=args.skip_analysis,
        generate_description=not args.no_description
    )

if __name__ == "__main__":
    main() 