"""
Visualization Generator Module

This module is responsible for generating visual representations of code structure,
dependencies, and execution flows based on the analysis results from the relationship builder.
It supports multiple output formats including Graphviz and Mermaid.
"""

import os
import graphviz
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import shutil
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class VisualizationGenerator:
    """
    Generates visualizations from code analysis results using different formats.
    Supports Graphviz and Mermaid diagram generation.
    """
    
    def __init__(
        self,
        output_dir: Optional[str] = None,
        formats: Optional[List[str]] = None
    ):
        """
        Initialize the visualization generator.
        
        Args:
            output_dir: Directory to save visualization files (defaults to current directory)
            formats: List of output formats to generate (defaults to ['png', 'svg', 'mermaid'])
        """
        self.output_dir = output_dir or os.getcwd()
        self.formats = formats or ['png', 'svg', 'mermaid']
        
        # Check if Graphviz is installed
        self.graphviz_available = self._check_graphviz()
        if not self.graphviz_available:
            print("WARNING: Graphviz not found. Only Mermaid diagrams will be generated.")
            # Filter formats to only include mermaid
            self.formats = [fmt for fmt in self.formats if fmt == 'mermaid']
            if not self.formats:
                self.formats = ['mermaid']
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _check_graphviz(self) -> bool:
        """Check if Graphviz is installed by looking for the 'dot' executable."""
        # Check if 'dot' is in PATH
        if shutil.which('dot'):
            return True
            
        # Try to run dot -V to check if it's available
        try:
            subprocess.run(['dot', '-V'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def generate_function_diagram(self, builder_data: Dict[str, Any], output_name: str = "code_structure") -> Dict[str, str]:
        """
        Generate function call diagrams using the data from the relationship builder.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output files
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_files = {}
        
        # Always generate Mermaid diagrams
        if 'mermaid' in self.formats or not self.graphviz_available:
            mermaid = self._generate_mermaid(builder_data)
            output_path = os.path.join(self.output_dir, f"{output_name}.mmd")
            with open(output_path, 'w') as f:
                f.write(mermaid)
            output_files['mermaid'] = output_path
        
        # Only generate Graphviz diagrams if available
        if self.graphviz_available and any(fmt in self.formats for fmt in ['png', 'svg', 'pdf']):
            try:
                # Create Graphviz diagram
                graph = graphviz.Digraph(
                    name=output_name,
                    comment="Code Structure Visualization",
                    format="png",
                    engine="dot",
                    graph_attr={
                        'rankdir': 'TB',
                        'splines': 'ortho',
                        'nodesep': '0.8',
                        'ranksep': '1.0',
                        'fontname': 'Arial',
                        'fontsize': '12',
                        'concentrate': 'true'
                    },
                    node_attr={
                        'shape': 'box',
                        'style': 'filled',
                        'fillcolor': '#f5f5f5',
                        'fontname': 'Arial',
                        'fontsize': '10'
                    },
                    edge_attr={
                        'fontname': 'Arial',
                        'fontsize': '8'
                    }
                )
                
                # Process functions
                function_details = builder_data.get('function_details', {})
                file_functions = builder_data.get('file_functions', {})
                entry_points = builder_data.get('entry_points', [])
                function_calls = builder_data.get('function_calls', {})
                file_summaries = builder_data.get('file_summaries', {})
                
                # Create subgraphs for each file
                for file_path, functions in file_functions.items():
                    with graph.subgraph(name=f"cluster_{self._sanitize_name(file_path)}") as subgraph:
                        # Set subgraph attributes
                        file_name = os.path.basename(file_path)
                        summary = file_summaries.get(file_path, "")
                        subgraph.attr(
                            label=f"{file_name}\n{summary}",
                            style='filled',
                            fillcolor='#e8e8e8',
                            color='gray'
                        )
                        
                        # Add function nodes for this file
                        for func_name in functions:
                            details = function_details.get(func_name, {})
                            label = f"{func_name}\n{details.get('description', '')}"
                            
                            # Check if function is an entry point
                            shape = 'doublecircle' if func_name in entry_points else 'box'
                            fillcolor = '#d9ead3' if func_name in entry_points else '#f5f5f5'
                            
                            subgraph.node(
                                func_name,
                                label=label,
                                shape=shape,
                                fillcolor=fillcolor
                            )
                
                # Add edges for function calls
                for func_name, callees in function_calls.items():
                    for callee in callees:
                        if callee in function_details:
                            graph.edge(func_name, callee)
                
                # Generate output in all requested formats
                for fmt in self.formats:
                    if fmt in ['png', 'svg', 'pdf']:
                        # Set format and render
                        graph.format = fmt
                        output_path = os.path.join(self.output_dir, f"{output_name}")
                        try:
                            graph.render(filename=output_path, cleanup=True)
                            output_files[fmt] = f"{output_path}.{fmt}"
                        except Exception as e:
                            print(f"Error generating {fmt} diagram: {e}")
            
            except Exception as e:
                print(f"Error generating Graphviz diagrams: {e}")
                print("Falling back to Mermaid diagrams only.")
        
        return output_files
    
    def generate_dependency_diagram(self, builder_data: Dict[str, Any], output_name: str = "code_dependencies") -> Dict[str, str]:
        """
        Generate module/file dependency diagrams using data from the relationship builder.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output files
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_files = {}
        
        # Always generate Mermaid diagrams
        if 'mermaid' in self.formats or not self.graphviz_available:
            mermaid = self._generate_dependency_mermaid(builder_data)
            output_path = os.path.join(self.output_dir, f"{output_name}.mmd")
            with open(output_path, 'w') as f:
                f.write(mermaid)
            output_files['mermaid'] = output_path
        
        # Only generate Graphviz diagrams if available
        if self.graphviz_available and any(fmt in self.formats for fmt in ['png', 'svg', 'pdf']):
            try:
                # Create Graphviz diagram for dependencies
                graph = graphviz.Digraph(
                    name=output_name,
                    comment="Code Dependencies Visualization",
                    format="png",
                    engine="dot",
                    graph_attr={
                        'rankdir': 'LR',
                        'splines': 'true',
                        'nodesep': '0.5',
                        'ranksep': '1.5',
                        'fontname': 'Arial',
                        'fontsize': '12'
                    },
                    node_attr={
                        'shape': 'box',
                        'style': 'filled',
                        'fillcolor': '#e6f3ff',
                        'fontname': 'Arial',
                        'fontsize': '10'
                    }
                )
                
                # Process file dependencies
                file_dependencies = builder_data.get('file_dependencies', {})
                file_summaries = builder_data.get('file_summaries', {})
                
                # Add nodes for each file
                for file_path, summary in file_summaries.items():
                    file_name = os.path.basename(file_path)
                    graph.node(
                        file_path,
                        label=f"{file_name}\n{summary[:30]}...",
                        tooltip=summary
                    )
                
                # Add edges for dependencies
                for file_path, dependencies in file_dependencies.items():
                    for dependency in dependencies:
                        if dependency in file_summaries:
                            graph.edge(file_path, dependency, style='dashed')
                
                # Generate output in all requested formats
                for fmt in self.formats:
                    if fmt in ['png', 'svg', 'pdf']:
                        # Set format and render
                        graph.format = fmt
                        output_path = os.path.join(self.output_dir, f"{output_name}")
                        try:
                            graph.render(filename=output_path, cleanup=True)
                            output_files[fmt] = f"{output_path}.{fmt}"
                        except Exception as e:
                            print(f"Error generating {fmt} diagram: {e}")
            
            except Exception as e:
                print(f"Error generating Graphviz diagrams: {e}")
                print("Falling back to Mermaid diagrams only.")
        
        return output_files
    
    def generate_execution_path_diagram(self, builder_data: Dict[str, Any], output_name: str = "execution_paths") -> Dict[str, str]:
        """
        Generate execution path diagrams from entry points using data from the relationship builder.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output files
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_files = {}
        
        # Always generate Mermaid diagrams
        if 'mermaid' in self.formats or not self.graphviz_available:
            mermaid = self._generate_execution_path_mermaid(builder_data)
            output_path = os.path.join(self.output_dir, f"{output_name}.mmd")
            with open(output_path, 'w') as f:
                f.write(mermaid)
            output_files['mermaid'] = output_path
        
        # Only generate Graphviz diagrams if available
        if self.graphviz_available and any(fmt in self.formats for fmt in ['png', 'svg', 'pdf']):
            try:
                # Create Graphviz diagram for execution paths
                graph = graphviz.Digraph(
                    name=output_name,
                    comment="Execution Paths Visualization",
                    format="png",
                    engine="dot",
                    graph_attr={
                        'rankdir': 'LR',
                        'splines': 'polyline',
                        'nodesep': '0.3',
                        'ranksep': '0.8',
                        'fontname': 'Arial',
                        'fontsize': '12'
                    }
                )
                
                # Process execution paths
                entry_point_paths = builder_data.get('entry_point_paths', [])
                function_details = builder_data.get('function_details', {})
                
                # Create a subgraph for each entry point path
                for i, path in enumerate(entry_point_paths):
                    if not path:
                        continue
                        
                    with graph.subgraph(name=f"cluster_path_{i}") as subgraph:
                        # Set subgraph attributes
                        entry_point = path[0]
                        subgraph.attr(
                            label=f"Path from {entry_point}",
                            style='filled', 
                            fillcolor='#e8f4f8',
                            color='blue'
                        )
                        
                        # Add nodes and edges for this path
                        for j, func_name in enumerate(path):
                            details = function_details.get(func_name, {})
                            label = f"{func_name}\n{details.get('description', '')}"
                            
                            # Style entry point differently
                            if j == 0:
                                subgraph.node(
                                    func_name, 
                                    label=label,
                                    shape='doublecircle',
                                    fillcolor='#d9ead3'
                                )
                            else:
                                subgraph.node(
                                    func_name, 
                                    label=label,
                                    shape='box',
                                    fillcolor='#f5f5f5'
                                )
                            
                            # Add edge to next function in path
                            if j < len(path) - 1:
                                next_func = path[j + 1]
                                subgraph.edge(
                                    func_name, 
                                    next_func,
                                    color='blue',
                                    penwidth='2.0'
                                )
                
                # Generate output in all requested formats
                for fmt in self.formats:
                    if fmt in ['png', 'svg', 'pdf']:
                        # Set format and render
                        graph.format = fmt
                        output_path = os.path.join(self.output_dir, f"{output_name}")
                        try:
                            graph.render(filename=output_path, cleanup=True)
                            output_files[fmt] = f"{output_path}.{fmt}"
                        except Exception as e:
                            print(f"Error generating {fmt} diagram: {e}")
            
            except Exception as e:
                print(f"Error generating Graphviz diagrams: {e}")
                print("Falling back to Mermaid diagrams only.")
        
        return output_files
    
    def _generate_mermaid(self, builder_data: Dict[str, Any]) -> str:
        """Generate Mermaid syntax for function call diagram."""
        function_details = builder_data.get('function_details', {})
        file_functions = builder_data.get('file_functions', {})
        entry_points = builder_data.get('entry_points', [])
        function_calls = builder_data.get('function_calls', {})
        
        # Print diagnostic info
        print(f"Generating Mermaid diagram with {len(function_details)} functions, {len(file_functions)} files, {len(entry_points)} entry points")
        
        mermaid = "```mermaid\ngraph TD;\n"
        
        # If no data, create a simple diagram showing the issue
        if not function_details and not file_functions:
            mermaid += "  noData[\"No function data available\"];\n"
            mermaid += "```"
            return mermaid
            
        # Group functions by file
        for file_path, functions in file_functions.items():
            if not functions:
                continue
                
            file_name = os.path.basename(file_path)
            mermaid += f"  subgraph {self._sanitize_name(file_name)}\n"
            
            for func_name in functions:
                details = function_details.get(func_name, {})
                description = details.get('description', '')
                safe_name = self._sanitize_name(func_name)
                
                # Style entry points differently
                if func_name in entry_points:
                    mermaid += f"    {safe_name}[({func_name})];\n"
                else:
                    mermaid += f"    {safe_name}[{func_name}];\n"
                    
            mermaid += "  end\n"
        
        # Add connections
        for func_name, callees in function_calls.items():
            for callee in callees:
                if callee in function_details:
                    safe_func = self._sanitize_name(func_name)
                    safe_callee = self._sanitize_name(callee)
                    mermaid += f"  {safe_func} --> {safe_callee};\n"
        
        mermaid += "```"
        return mermaid
    
    def _generate_dependency_mermaid(self, builder_data: Dict[str, Any]) -> str:
        """Generate Mermaid syntax for file dependency diagram."""
        file_dependencies = builder_data.get('file_dependencies', {})
        file_summaries = builder_data.get('file_summaries', {})
        
        # Print diagnostic info
        print(f"Generating dependency Mermaid diagram with {len(file_summaries)} files, {len(file_dependencies)} dependencies")
        
        mermaid = "```mermaid\ngraph LR;\n"
        
        # If no data, create a simple diagram showing the issue
        if not file_summaries:
            mermaid += "  noData[\"No file dependency data available\"];\n"
            mermaid += "```"
            return mermaid
            
        # Add nodes for each file
        for file_path in file_summaries:
            file_name = os.path.basename(file_path)
            safe_name = self._sanitize_name(file_path)
            mermaid += f"  {safe_name}[\"{file_name}\"];\n"
        
        # Add connections
        for file_path, dependencies in file_dependencies.items():
            safe_file = self._sanitize_name(file_path)
            for dependency in dependencies:
                if dependency in file_summaries:
                    safe_dep = self._sanitize_name(dependency)
                    mermaid += f"  {safe_file} -.-> {safe_dep};\n"
        
        mermaid += "```"
        return mermaid
    
    def _generate_execution_path_mermaid(self, builder_data: Dict[str, Any]) -> str:
        """Generate Mermaid syntax for execution path diagram."""
        entry_point_paths = builder_data.get('entry_point_paths', [])
        function_details = builder_data.get('function_details', {})
        
        # Print diagnostic info
        print(f"Generating execution path Mermaid diagram with {len(entry_point_paths)} paths, {len(function_details)} functions")
        
        mermaid = "```mermaid\ngraph LR;\n"
        
        # If no data, create a simple diagram showing the issue
        if not entry_point_paths:
            mermaid += "  noData[\"No execution path data available\"];\n"
            mermaid += "```"
            return mermaid
            
        # Process each execution path
        for i, path in enumerate(entry_point_paths):
            if not path:
                continue
                
            mermaid += f"  subgraph Path_{i}\n"
            
            # Add nodes and connections for this path
            for j, func_name in enumerate(path):
                safe_name = f"{self._sanitize_name(func_name)}_{i}"
                
                # Style entry point differently
                if j == 0:
                    mermaid += f"    {safe_name}[({func_name})];\n"
                else:
                    mermaid += f"    {safe_name}[{func_name}];\n"
                
                # Add connection to next function
                if j < len(path) - 1:
                    next_func = path[j + 1]
                    safe_next = f"{self._sanitize_name(next_func)}_{i}"
                    mermaid += f"    {safe_name} ===> {safe_next};\n"
            
            mermaid += "  end\n"
        
        mermaid += "```"
        return mermaid
    
    def _sanitize_name(self, name: str) -> str:
        """
        Convert a function or file name to a valid ID for Graphviz and Mermaid.
        
        Args:
            name: The original name
            
        Returns:
            A sanitized version of the name
        """
        # Replace invalid characters
        sanitized = name.replace('.', '_').replace('/', '_').replace('\\', '_')
        sanitized = sanitized.replace(':', '_').replace(' ', '_').replace('-', '_')
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'n_' + sanitized
            
        return sanitized
    
    def export_data(self, builder_data: Dict[str, Any], output_name: str = "analysis_data") -> str:
        """
        Export the analysis data to a JSON file.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output file
            
        Returns:
            Path to the JSON file
        """
        output_path = os.path.join(self.output_dir, f"{output_name}.json")
        
        with open(output_path, 'w') as f:
            json.dump(builder_data, f, indent=2)
            
        return output_path 