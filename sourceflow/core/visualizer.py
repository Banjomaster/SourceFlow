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
import re
import webbrowser

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
        self.formats = formats or ['png', 'svg', 'mermaid', 'html']
        
        # Check if Graphviz is installed
        self.graphviz_available = self._check_graphviz()
        if not self.graphviz_available:
            print("WARNING: Graphviz not found. Only Mermaid diagrams and HTML viewer will be generated.")
            # Filter formats to only include mermaid and html
            self.formats = [fmt for fmt in self.formats if fmt in ['mermaid', 'html']]
            if not self.formats:
                self.formats = ['mermaid', 'html']
        
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
        file_summaries = builder_data.get('file_summaries', {})
        
        # Print diagnostic info
        print(f"Generating Mermaid diagram with {len(function_details)} functions, {len(file_functions)} files, {len(entry_points)} entry points")
        
        # Use LR (left to right) layout for better readability with many nodes
        mermaid = "```mermaid\ngraph LR\n"
        
        # Add Mermaid directives for improved layout
        mermaid += "  %% Configuration for better readability\n"
        mermaid += "  linkStyle default stroke:#666,stroke-width:1px\n"
        
        # Define node styling classes for better readability
        mermaid += "  classDef default fill:#f9f9f9,stroke:#999,color:black\n"
        mermaid += "  classDef entryPoint fill:#d4f1d4,stroke:#5ca75c,stroke-width:2px,color:black\n"
        mermaid += "  classDef utilityFunc fill:#e6f3ff,stroke:#4d8bc9,color:black\n"
        mermaid += "  classDef privateFunc fill:#f9f9f9,stroke:#999,stroke-dasharray:5 5,color:black\n"
        mermaid += "  classDef moduleHeader fill:#f0f0f0,stroke:#666,color:black,text-align:center\n"
        
        # If no data, create a simple diagram showing the issue
        if not function_details and not file_functions:
            mermaid += "  noData[\"No function data available\"]\n"
            mermaid += "```"
            return mermaid
            
        # Group functions by file
        for file_path, functions in file_functions.items():
            if not functions:
                continue
                
            file_name = os.path.basename(file_path)
            file_summary = file_summaries.get(file_path, "")
            
            # Wrap and format the file summary for better readability
            wrapped_summary = self._wrap_text(file_summary, 35)  # Slightly wider to reduce height
            
            # Add file subgraph with description - sanitize the file name even more for Mermaid
            safe_file_name = self._sanitize_name(file_name)
            
            mermaid += f"  subgraph {safe_file_name}[\"{file_name}<br><i>{wrapped_summary}</i>\"]\n"
            mermaid += f"    style {safe_file_name} fill:#f0f0f0,stroke:#666,color:black\n"
            
            for func_name in functions:
                details = function_details.get(func_name, {})
                description = details.get('description', '')
                safe_name = self._sanitize_name(func_name)
                
                # Wrap function description - wider width for less vertical space
                wrapped_desc = ""
                if description:
                    wrapped_desc = "<br><i>" + self._wrap_text(description, 30) + "</i>"
                
                # Apply styling based on function type
                is_private = func_name.startswith('_') and not func_name.startswith('__')
                is_dunder = func_name.startswith('__') and func_name.endswith('__')
                
                # Style entry points with highest visibility
                if func_name in entry_points:
                    mermaid += f"    {safe_name}[\"{func_name}{wrapped_desc}\"]:::entryPoint\n"
                # Private utility functions get a distinct style
                elif is_private and not is_dunder:
                    mermaid += f"    {safe_name}[\"{func_name}{wrapped_desc}\"]:::privateFunc\n"
                # Dunder methods get a utility style
                elif is_dunder:
                    mermaid += f"    {safe_name}[\"{func_name}{wrapped_desc}\"]:::utilityFunc\n"
                # Regular functions get the default style
                else:
                    mermaid += f"    {safe_name}[\"{func_name}{wrapped_desc}\"]\n"
                    
            mermaid += "  end\n"
        
        # Add connections with labels for the type of relationship
        for func_name, callees in function_calls.items():
            for callee in callees:
                if callee in function_details:
                    safe_func = self._sanitize_name(func_name)
                    safe_callee = self._sanitize_name(callee)
                    mermaid += f"  {safe_func} -->|calls| {safe_callee}\n"
        
        # Add comprehensive legend with all node types
        mermaid += "  subgraph Legend[\"Legend\"]\n"
        mermaid += "    style Legend fill:#f9f9f9,stroke:#999,color:black\n"
        mermaid += "    entry[\"Entry Point\"]:::entryPoint\n"
        mermaid += "    regular[\"Regular Function\"]\n"
        mermaid += "    utility[\"Special Method\"]:::utilityFunc\n"
        mermaid += "    private[\"Private Helper\"]:::privateFunc\n"
        mermaid += "    entry -->|calls| regular\n"
        mermaid += "  end\n"
        
        mermaid += "```"
        return mermaid
    
    def _generate_dependency_mermaid(self, builder_data: Dict[str, Any]) -> str:
        """Generate Mermaid syntax for file dependency diagram."""
        file_dependencies = builder_data.get('file_dependencies', {})
        file_summaries = builder_data.get('file_summaries', {})
        
        # Print diagnostic info
        print(f"Generating dependency Mermaid diagram with {len(file_summaries)} files, {len(file_dependencies)} dependencies")
        
        # Use LR layout for better readability
        mermaid = "```mermaid\ngraph LR;\n"
        
        # Add Mermaid directives for improved layout
        mermaid += "  %% Configuration for better readability\n"
        mermaid += "  linkStyle default stroke:#999,stroke-width:1.5px,stroke-dasharray:5 5;\n"
        
        # Define styling classes
        mermaid += "  classDef default fill:#f9f9f9,stroke:#999,color:black;\n"
        mermaid += "  classDef pythonModule fill:#e6f3ff,stroke:#4d8bc9,color:black;\n"
        mermaid += "  classDef configFile fill:#fff7e6,stroke:#d9b38c,color:black;\n"
        mermaid += "  classDef mainFile fill:#d4f1d4,stroke:#5ca75c,color:black;\n"
        
        # If no data, create a simple diagram showing the issue
        if not file_summaries:
            mermaid += "  noData[\"No file dependency data available\"];\n"
            mermaid += "```"
            return mermaid
            
        # Add nodes for each file with wrapped module descriptions
        for file_path in file_summaries:
            file_name = os.path.basename(file_path)
            safe_name = self._sanitize_name(file_path)
            summary = file_summaries.get(file_path, "")
            
            # Create a wrapped description for better readability
            wrapped_summary = self._wrap_text(summary, 30)  # Wider for less vertical space
            label = f"<b>{file_name}</b><br>{wrapped_summary}"
            
            # Style nodes based on file type
            if file_name.startswith('__') and file_name.endswith('__.py'):
                mermaid += f"  {safe_name}[\"{label}\"]:::pythonModule;\n"
            elif file_name in ['main.py', 'run_analyzer.py']:
                mermaid += f"  {safe_name}[\"{label}\"]:::mainFile;\n"
            elif file_name.endswith('.py'):
                mermaid += f"  {safe_name}[\"{label}\"]:::pythonModule;\n"
            else:
                mermaid += f"  {safe_name}[\"{label}\"]:::configFile;\n"
        
        # Add connections with relationship type (dependency)
        for file_path, dependencies in file_dependencies.items():
            safe_file = self._sanitize_name(file_path)
            for dependency in dependencies:
                if dependency in file_summaries:
                    safe_dep = self._sanitize_name(dependency)
                    # Use a different arrow style with a small label
                    mermaid += f"  {safe_file} -.-|\"imports\"| {safe_dep};\n"
        
        # Add legend with improved styling
        mermaid += "  subgraph Legend[\"Legend\"]\n"
        mermaid += "    style Legend fill:#f9f9f9,stroke:#999,color:black;\n"
        mermaid += "    mainLegend[\"Entry Point\"]:::mainFile;\n"
        mermaid += "    moduleLegend[\"Python Module\"]:::pythonModule;\n"
        mermaid += "    configLegend[\"Configuration\"]:::configFile;\n"
        mermaid += "    mainLegend -.-|\"imports\"| moduleLegend;\n"
        mermaid += "  end\n"
        
        mermaid += "```"
        return mermaid
    
    def _generate_execution_path_mermaid(self, builder_data: Dict[str, Any]) -> str:
        """Generate Mermaid syntax for execution path diagram."""
        function_details = builder_data.get('function_details', {})
        execution_paths = builder_data.get('entry_point_paths', [])  # Use entry_point_paths from builder data
        
        # Print diagnostic info
        total_funcs = sum(len(path) for path in execution_paths)
        print(f"Generating execution path Mermaid diagram with {len(execution_paths)} paths, {len(function_details)} functions")
        
        # Use LR layout for better readability
        mermaid = "```mermaid\ngraph LR;\n"
        
        # Add Mermaid directives for improved layout
        mermaid += "  %% Configuration for better readability\n"
        mermaid += "  linkStyle default stroke:#666,stroke-width:2px,stroke-dasharray:3 2;\n"
        
        # If no data, create a simple diagram showing the issue
        if not execution_paths:
            mermaid += "  noData[\"No execution path data available\"];\n"
            mermaid += "```"
            return mermaid
        
        # Define styling classes
        mermaid += "  classDef default fill:#f9f9f9,stroke:#999,color:black;\n"
        mermaid += "  classDef entryPoint fill:#d4f1d4,stroke:#5ca75c,stroke-width:2px,color:black;\n"
        mermaid += "  classDef pathFunc fill:#f5f5f5,stroke:#666666,color:black;\n"
        mermaid += "  classDef pathHeader fill:#eaeaea,stroke:#555,color:black,text-align:center;\n"
        
        # Create subgraphs for each execution path
        for i, path in enumerate(execution_paths):
            if not path:
                continue
                
            mermaid += f"  subgraph Path_{i}[\"<b>Execution Path {i+1}</b>\"]\n"
            mermaid += f"    style Path_{i} fill:#eaeaea,stroke:#555,color:black;\n"
            
            # Add nodes for functions in this path
            for j, func_name in enumerate(path):
                details = function_details.get(func_name, {})
                description = details.get('description', '')
                safe_name = f"{self._sanitize_name(func_name)}_{i}"
                
                # Wrap function description - wider width for less vertical space
                wrapped_desc = ""
                if description:
                    wrapped_desc = "<br><i>" + self._wrap_text(description, 30) + "</i>"
                
                # First function in path is an entry point
                if j == 0:
                    mermaid += f"    {safe_name}[\"<b>{func_name}</b>{wrapped_desc}\"]:::entryPoint;\n"
                else:
                    mermaid += f"    {safe_name}[\"{func_name}{wrapped_desc}\"]:::pathFunc;\n"
                
                # Add connection to next function in path with numbered sequence
                if j < len(path) - 1:
                    next_func = path[j + 1]
                    safe_next = f"{self._sanitize_name(next_func)}_{i}"
                    mermaid += f"    {safe_name} ===>|\"step {j+1}\"| {safe_next};\n"
                
            mermaid += "  end\n"
        
        # Add legend with improved styling
        mermaid += "  subgraph Legend[\"Legend\"]\n"
        mermaid += "    style Legend fill:#f9f9f9,stroke:#999,color:black;\n"
        mermaid += "    entryLegend[\"Entry Point\"]:::entryPoint;\n"
        mermaid += "    funcLegend[\"Function Call\"]:::pathFunc;\n"
        mermaid += "    entryLegend ===>|\"execution step\"| funcLegend;\n"
        mermaid += "  end\n"
        
        mermaid += "```"
        return mermaid
    
    def _wrap_text(self, text: str, width: int) -> str:
        """
        Wrap text to a specified width with HTML line breaks for Mermaid diagrams.
        
        Args:
            text: The text to wrap
            width: Maximum width in characters
            
        Returns:
            Wrapped text with HTML <br> tags
        """
        if not text:
            return "No description available"
            
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            # Check if adding this word would exceed the width
            if current_width + len(word) + (1 if current_width > 0 else 0) > width:
                # Line is full, add it to lines and start a new line
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_width = len(word)
            else:
                # Add word to current line
                current_line.append(word)
                current_width += len(word) + (1 if current_width > 0 else 0)
        
        # Add the last line if not empty
        if current_line:
            lines.append(' '.join(current_line))
            
        # Join lines with HTML line breaks
        return '<br>'.join(lines)
    
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
        sanitized = sanitized.replace('(', '_').replace(')', '_').replace('[', '_').replace(']', '_')
        sanitized = sanitized.replace('{', '_').replace('}', '_').replace('<', '_').replace('>', '_')
        sanitized = sanitized.replace('?', '_').replace('!', '_').replace('=', '_').replace('@', '_')
        sanitized = sanitized.replace('&', '_').replace('*', '_').replace('+', '_').replace('~', '_')
        sanitized = sanitized.replace('`', '_').replace('\'', '_').replace('"', '_').replace('|', '_')
        sanitized = sanitized.replace(',', '_').replace(';', '_')
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'n_' + sanitized
            
        # Ensure uniqueness by adding a prefix
        sanitized = 'node_' + sanitized
            
        return sanitized
    
    def export_data(self, builder_data: Dict[str, Any], output_name: str = "analysis_data") -> str:
        """
        Export the analysis data to a JSON file.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output file
            
        Returns:
            Path to the output file
        """
        output_path = os.path.join(self.output_dir, f"{output_name}.json")
        with open(output_path, 'w') as f:
            json.dump(builder_data, f, indent=2)
        return output_path
        
    def generate_html_viewer(self, builder_data: Dict[str, Any], output_name: str = "interactive_viewer") -> str:
        """
        Generates an interactive HTML viewer for all diagram types that allows
        zooming, panning, and exploring different levels of detail.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output HTML file
            
        Returns:
            Path to the generated HTML file
        """
        # Generate all Mermaid diagrams
        mermaid_structure = self._generate_mermaid(builder_data)
        mermaid_dependencies = self._generate_dependency_mermaid(builder_data)
        mermaid_execution = self._generate_execution_path_mermaid(builder_data)
        
        # Save raw diagram content to files for debugging
        def save_debug_file(content, name):
            debug_path = os.path.join(self.output_dir, f"{name}_raw.md")
            with open(debug_path, 'w') as f:
                f.write(content)
            print(f"Saved raw {name} content to {debug_path}")
        
        # Save the original content before processing
        save_debug_file(mermaid_structure, "structure")
        save_debug_file(mermaid_dependencies, "dependencies")
        save_debug_file(mermaid_execution, "execution")
        
        # Process each diagram and ensure valid Mermaid syntax
        structure_content = self._ensure_valid_mermaid_syntax(mermaid_structure, default_type="graph TD")
        dependencies_content = self._ensure_valid_mermaid_syntax(mermaid_dependencies, default_type="graph LR")
        execution_content = self._ensure_valid_mermaid_syntax(mermaid_execution, default_type="graph LR")
        
        # Generate individual HTML files for each diagram
        self._generate_individual_diagram_html(structure_content, "code_structure_diagram", "Code Structure Diagram",
            "This diagram shows the overall structure of the codebase, including functions, classes, and their relationships.")
        self._generate_individual_diagram_html(dependencies_content, "dependencies_diagram", "Module Dependencies Diagram",
            "This diagram illustrates the relationships between modules in the codebase, showing how files depend on one another and the overall architecture of the system.")
        self._generate_individual_diagram_html(execution_content, "execution_paths_diagram", "Execution Paths Diagram",
            "This diagram shows the major execution paths from entry points, illustrating the flow of execution through different functions and modules.")
        
        # Create a simplified HTML template with links to each diagram
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Source Flow Analysis</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            line-height: 1.6;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 15px 20px;
            background-color: #333;
            color: white;
        }
        .title {
            font-size: 1.8em;
            margin: 0;
        }
        .search-box {
            margin: 20px;
            padding: 10px;
        }
        .search-box input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .tab-container {
            display: flex;
            padding: 0 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f0f0f0;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            margin-right: 5px;
        }
        .tab:hover {
            background-color: #e0e0e0;
        }
        .tab.active {
            background-color: white;
            border-bottom: 1px solid white;
            margin-bottom: -1px;
            font-weight: bold;
        }
        .content {
            padding: 20px;
            flex: 1;
        }
        .card {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h3 {
            margin-top: 0;
            color: #333;
        }
        .card p {
            color: #666;
        }
        .button {
            display: inline-block;
            background-color: #4d8bc9;
            color: white;
            padding: 10px 15px;
            border-radius: 4px;
            text-decoration: none;
            margin-top: 10px;
        }
        .button:hover {
            background-color: #3a6d99;
        }
        .legend {
            display: flex;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin-right: 20px;
            margin-bottom: 10px;
        }
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">Source Flow Analysis</h1>
    </div>
    
    <div class="search-box">
        <input type="text" placeholder="Search for functions, modules, or descriptions...">
    </div>
    
    <div class="tab-container">
        <div class="tab active">Code Structure</div>
        <div class="tab">Dependencies</div>
        <div class="tab">Execution Paths</div>
    </div>
    
    <div class="content">
        <div class="card">
            <h3>Dependencies Overview</h3>
            <p>This view illustrates the relationships between modules in the codebase, showing how files depend on one another and how they interact. This hierarchy helps understand how changes in one module might affect others and identifies the core components.</p>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #d4f1d4;"></div>
                    <span>Entry Point File</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #e6f3ff;"></div>
                    <span>Python Module</span>
                </div>
            </div>
            
            <a href="./code_structure_diagram.html" class="button">Visualize Full Diagram</a>
        </div>
        
        <div class="card">
            <h3>Code Structure</h3>
            <p>This diagram shows the overall structure of the codebase, including functions, classes, and their relationships.</p>
            <a href="./code_structure_diagram.html" class="button">Visualize Full Diagram</a>
        </div>
        
        <div class="card">
            <h3>Module Dependencies</h3>
            <p>This diagram illustrates the relationships between modules in the codebase, showing how files depend on one another and the overall architecture of the system.</p>
            <a href="./dependencies_diagram.html" class="button">Visualize Full Diagram</a>
        </div>
        
        <div class="card">
            <h3>Execution Paths</h3>
            <p>This diagram shows the major execution paths from entry points, illustrating the flow of execution through different functions and modules.</p>
            <a href="./execution_paths_diagram.html" class="button">Visualize Full Diagram</a>
        </div>
    </div>
    
    <script>
        // Simple search functionality
        document.querySelector('input').addEventListener('keyup', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            document.querySelectorAll('.card').forEach(card => {
                const text = card.textContent.toLowerCase();
                if (text.includes(searchTerm) || searchTerm === '') {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
        
        // Tab switching functionality
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            });
        });
    </script>
</body>
</html>"""
        
        # Replace the placeholders with the actual content
        html_template = html_template.replace("STRUCTURE_CONTENT_PLACEHOLDER", structure_content)
        html_template = html_template.replace("DEPENDENCIES_CONTENT_PLACEHOLDER", dependencies_content)
        html_template = html_template.replace("EXECUTION_CONTENT_PLACEHOLDER", execution_content)
        
        # Save the HTML content to a file
        output_path = os.path.join(self.output_dir, f"{output_name}.html")
        self.save_html_visualization(html_template, output_path)
        
        return output_path

    def save_html_visualization(self, html_content, output_path):
        """
        Save the HTML visualization to a file.
        
        Args:
            html_content: The HTML content to save
            output_path: The path to save the HTML file to
        """
        try:
            with open(output_path, 'w') as f:
                f.write(html_content)
            print(f"Visualization saved to {output_path}")
            return True
        except Exception as e:
            print(f"Error saving visualization: {e}")
            return False

    def visualize_codebase(self, output_name="codebase_visualization", open_browser=True):
        """
        Generate a visualization of the codebase and save it as an HTML file.
        
        Args:
            output_name: The base name for the output file (without extension)
            open_browser: Whether to open the visualization in a browser
            
        Returns:
            str: The path to the generated visualization file
        """
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate the structure diagram
        structure_content = self._generate_structure_diagram()
        
        # Generate the dependencies diagram
        dependencies_content = self._generate_dependencies_diagram()
        
        # Generate the execution paths diagram
        execution_content = self._generate_execution_paths_diagram()
        
        # Ensure all diagrams have the proper syntax
        structure_content = self._ensure_valid_mermaid_syntax(structure_content, "graph TD")
        dependencies_content = self._ensure_valid_mermaid_syntax(dependencies_content, "graph LR")
        execution_content = self._ensure_valid_mermaid_syntax(execution_content, "flowchart TD")
        
        # Generate the HTML visualization
        html_content = self.generate_html_visualization(
            structure_content,
            dependencies_content,
            execution_content
        )
        
        # Save the HTML content to a file
        output_path = os.path.join(self.output_dir, f"{output_name}.html")
        self.save_html_visualization(html_content, output_path)
        
        # Open the visualization in a browser if requested
        if open_browser:
            try:
                webbrowser.open(f"file://{os.path.abspath(output_path)}")
                print(f"Opened visualization in browser: {output_path}")
            except Exception as e:
                print(f"Error opening visualization in browser: {e}")
        
        return output_path
        
    def _ensure_valid_mermaid_syntax(self, diagram_content, default_type):
        """
        Ensure the diagram content has valid Mermaid syntax.
        
        Args:
            diagram_content: The diagram content to validate
            default_type: The default diagram type to use if none is specified
            
        Returns:
            str: The validated diagram content
        """
        # Trim whitespace
        diagram_content = diagram_content.strip()
        
        # If empty, return a simple valid diagram
        if not diagram_content:
            return f"{default_type}\n    A[No data available]"
        
        # Check if the content starts with a valid diagram type
        valid_starts = ["graph ", "flowchart ", "sequenceDiagram", "classDiagram", "stateDiagram", "gantt", "pie", "erDiagram"]
        has_valid_start = any(diagram_content.startswith(start) for start in valid_starts)
        
        # If not, add the default type
        if not has_valid_start:
            diagram_content = f"{default_type}\n{diagram_content}"
        
        # Fix common syntax errors
        # 1. Ensure nodes have valid names (alphanumeric or enclosed in quotes)
        # 2. Add missing edge types (-- or -->)
        # This is a basic implementation and may need enhancement for more complex issues
        
        return diagram_content

    def _generate_structure_diagram(self):
        """
        Generate a Mermaid diagram representing the structure of the codebase.
        
        Returns:
            str: The Mermaid diagram content as a string
        """
        if not self.codebase or not hasattr(self.codebase, 'modules') or not self.codebase.modules:
            return "graph TD\n    A[No module data available]"
        
        diagram = "graph TD\n"
        
        # Create nodes for each module
        for module in self.codebase.modules:
            module_id = self._sanitize_id(module.name)
            diagram += f"    {module_id}[{module.name}]\n"
        
        # Add connections between modules
        for module in self.codebase.modules:
            if hasattr(module, 'imports') and module.imports:
                module_id = self._sanitize_id(module.name)
                for imported_module in module.imports:
                    imported_id = self._sanitize_id(imported_module)
                    diagram += f"    {module_id} --> {imported_id}\n"
        
        return diagram
    
    def _generate_dependencies_diagram(self):
        """
        Generate a Mermaid diagram representing the dependencies between modules.
        
        Returns:
            str: The Mermaid diagram content as a string
        """
        if not self.codebase or not hasattr(self.codebase, 'modules') or not self.codebase.modules:
            return "graph LR\n    A[No dependency data available]"
        
        diagram = "graph LR\n"
        
        # Group modules by package/directory
        packages = {}
        for module in self.codebase.modules:
            parts = module.name.split('.')
            if len(parts) > 1:
                package = parts[0]
                if package not in packages:
                    packages[package] = []
                packages[package].append(module)
            else:
                if "root" not in packages:
                    packages["root"] = []
                packages["root"].append(module)
        
        # Create subgraphs for each package
        for package, modules in packages.items():
            package_id = self._sanitize_id(package)
            diagram += f"    subgraph {package_id}[{package}]\n"
            
            for module in modules:
                module_id = self._sanitize_id(module.name)
                diagram += f"        {module_id}[{module.name.split('.')[-1]}]\n"
            
            diagram += "    end\n"
        
        # Add connections between modules
        for module in self.codebase.modules:
            if hasattr(module, 'imports') and module.imports:
                module_id = self._sanitize_id(module.name)
                for imported_module in module.imports:
                    imported_id = self._sanitize_id(imported_module)
                    diagram += f"    {module_id} --> {imported_id}\n"
        
        return diagram
    
    def _generate_execution_paths_diagram(self):
        """
        Generate a Mermaid diagram representing the execution paths in the codebase.
        
        Returns:
            str: The Mermaid diagram content as a string
        """
        if not self.codebase or not hasattr(self.codebase, 'entry_points') or not self.codebase.entry_points:
            return "flowchart TD\n    A[No execution path data available]"
        
        diagram = "flowchart TD\n"
        
        # Create nodes for each entry point
        for i, entry_point in enumerate(self.codebase.entry_points):
            entry_id = f"entry{i}"
            diagram += f"    {entry_id}[{entry_point}]\n"
        
            # If we have function calls for this entry point, add them
            if hasattr(self.codebase, 'function_calls') and entry_point in self.codebase.function_calls:
                calls = self.codebase.function_calls[entry_point]
                for j, call in enumerate(calls):
                    call_id = f"{entry_id}_call{j}"
                    call_name = call if isinstance(call, str) else call.get('name', f"Call {j}")
                    diagram += f"    {entry_id} --> {call_id}[{call_name}]\n"
        
        return diagram
    
    def _sanitize_id(self, id_str):
        """
        Sanitize a string to be used as a Mermaid node ID.
        
        Args:
            id_str: The string to sanitize
            
        Returns:
            str: The sanitized string
        """
        # Replace dots and other invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', str(id_str))
        
        # If the ID starts with a number, prepend an underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        return sanitized

    def _generate_individual_diagram_html(self, diagram_content, output_name, title, description):
        """
        Generates an individual HTML file for a specific diagram with simplified styling.
        
        Args:
            diagram_content: The Mermaid diagram content
            output_name: Base name for the output HTML file
            title: The title to display in the HTML file
            description: A description of the diagram
            
        Returns:
            Path to the generated HTML file
        """
        output_path = os.path.join(self.output_dir, f"{output_name}.html")
        
        # Create HTML template with minimal styling that lets Mermaid handle the display
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Source Flow - {title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            line-height: 1.6;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            padding: 10px 20px;
            background-color: #333;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .title {{
            font-size: 1.2em;
            margin: 0;
        }}
        .back-button {{
            background-color: #4d8bc9;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }}
        .back-button:hover {{
            background-color: #3a6d99;
        }}
        .controls-container {{
            padding: 10px 20px;
            background-color: white;
            border-bottom: 1px solid #ddd;
            display: flex;
            align-items: center;
        }}
        .info-box {{
            background-color: #e6f3ff;
            border-left: 4px solid #4d8bc9;
            padding: 10px 15px;
            margin-right: 20px;
            border-radius: 0 4px 4px 0;
            flex: 1;
        }}
        .zoom-controls {{
            display: flex;
            align-items: center;
            white-space: nowrap;
        }}
        .zoom-button {{
            background-color: #4d8bc9;
            color: white;
            border: none;
            width: 30px;
            height: 30px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }}
        .diagram-container {{
            flex: 1;
            overflow: auto;
            padding: 0;
            margin: 0;
            background-color: white;
            display: flex;
            justify-content: center;
        }}
        #mermaid-diagram {{
            transform-origin: center top;
            padding: 0;
            min-width: 100px;
            max-width: 95%;
            margin: 20px auto;
        }}
        /* Very minimal Mermaid styling */
        :root {{
            --mermaid-font-family: Arial, sans-serif;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">{title}</h1>
        <a href="./custom_viewer.html" class="back-button">Back to Overview</a>
    </div>
    
    <div class="controls-container">
        <div class="info-box">
            <div>{description}</div>
        </div>
        
        <div class="zoom-controls">
            <button class="zoom-button" id="zoom-out">-</button>
            <span id="zoom-level">150%</span>
            <button class="zoom-button" id="zoom-in">+</button>
            <button class="zoom-button" id="zoom-reset">R</button>
        </div>
    </div>
    
    <div class="diagram-container">
        <div id="mermaid-diagram" class="mermaid">
{diagram_content}
        </div>
    </div>
    
    <script>
        // Initialize Mermaid with better configurations
        function configureMermaidByDiagramType() {{
            const mermaidText = document.querySelector('.mermaid').textContent;
            
            // Count nodes and subgraphs to determine complexity
            const nodeCount = (mermaidText.match(/\\["/g) || []).length;
            const subgraphCount = (mermaidText.match(/subgraph/g) || []).length;
            
            console.log(`Diagram complexity: ${{nodeCount}} nodes, ${{subgraphCount}} subgraphs`);
            
            // Adjust settings based on complexity
            let rankSpacing = 200;
            let nodeSpacing = 150;
            let padding = 80;
            
            if (nodeCount > 50 || subgraphCount > 10) {{
                // Very complex diagram
                rankSpacing = 250;
                nodeSpacing = 180;
                padding = 100;
            }} else if (nodeCount < 10 && subgraphCount < 3) {{
                // Simple diagram
                rankSpacing = 150;
                nodeSpacing = 100;
                padding = 60;
            }}
            
            return {{
                startOnLoad: true,
                securityLevel: 'loose',
                flowchart: {{
                    useMaxWidth: false,
                    htmlLabels: true,
                    curve: 'basis',
                    rankSpacing: rankSpacing,
                    nodeSpacing: nodeSpacing,
                    padding: padding,
                    rankDir: 'LR'
                }}
            }};
        }}

        // Initialize Mermaid
        mermaid.initialize(configureMermaidByDiagramType());

        // Render the diagram after the page loads
        document.addEventListener('DOMContentLoaded', function() {{
            // Initialize mermaid rendering with robust error handling
            try {{
                mermaid.init(undefined, '.mermaid');
            }} catch (e) {{
                console.error("Mermaid initialization error:", e);
            }}
            
            // Add zoom and pan functionality
            const diagram = document.getElementById('mermaid-diagram');
            let scale = 2.0; // Start with higher zoom level
            let dragEnabled = false;
            let dragStartX, dragStartY, scrollLeft, scrollTop;
            
            function updateZoom() {{
                if (diagram) {{
                    diagram.style.transform = `scale(${{scale}})`;
                }}
                const zoomLevelEl = document.getElementById('zoom-level');
                if (zoomLevelEl) {{
                    zoomLevelEl.textContent = `${{Math.round(scale * 100)}}%`;
                }}
            }}
            
            // Set initial zoom
            updateZoom();
            
            // Add event listeners for zoom controls with explicit null checks
            const zoomInButton = document.getElementById('zoom-in');
            if (zoomInButton) {{
                zoomInButton.addEventListener('click', function() {{
                    scale = Math.min(scale + 0.1, 4.0);
                    updateZoom();
                }});
            }}
            
            const zoomOutButton = document.getElementById('zoom-out');
            if (zoomOutButton) {{
                zoomOutButton.addEventListener('click', function() {{
                    scale = Math.max(scale - 0.1, 0.1);
                    updateZoom();
                }});
            }}
            
            const zoomResetButton = document.getElementById('zoom-reset');
            if (zoomResetButton) {{
                zoomResetButton.addEventListener('click', function() {{
                    scale = 2.0;
                    updateZoom();
                }});
            }}
        }});
    </script>
</body>
</html>"""
        
        # Save the HTML content to a file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        return output_path

class Visualizer:
    """
    A class for visualizing codebase structure and relationships.
    """
    
    def __init__(self, codebase=None, output_dir="./output"):
        """
        Initialize the Visualizer.
        
        Args:
            codebase: The CodebaseAnalyzer object containing analyzed codebase data
            output_dir: The directory to save visualizations to
        """
        self.codebase = codebase
        self.output_dir = output_dir
        
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_html_visualization(self, structure_content, dependencies_content, execution_content):
        """
        Generate an HTML visualization of the codebase using the provided mermaid diagrams.
        
        Args:
            structure_content: The mermaid content for the structure diagram
            dependencies_content: The mermaid content for the dependencies diagram
            execution_content: The mermaid content for the execution paths diagram
            
        Returns:
            str: The HTML content as a string
        """
        # Create a super simple HTML template that's guaranteed to work
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Source Flow Diagrams</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        h1, h2 {
            color: #333;
        }
        h2 {
            margin-top: 40px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        .diagram-container {
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
            overflow: auto;
        }
        .error-info {
            color: red;
            font-family: monospace;
            white-space: pre-wrap;
            margin-top: 10px;
            padding: 10px;
            background-color: #fff0f0;
            border: 1px solid #ffdddd;
            border-radius: 4px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Source Flow Analysis</h1>
        
        <h2>Code Structure</h2>
        <div class="diagram-container">
            <div class="mermaid">
STRUCTURE_CONTENT_PLACEHOLDER
            </div>
            <div id="structure-error" class="error-info"></div>
        </div>
        
        <h2>Dependencies</h2>
        <div class="diagram-container">
            <div class="mermaid">
DEPENDENCIES_CONTENT_PLACEHOLDER
            </div>
            <div id="dependencies-error" class="error-info"></div>
        </div>
        
        <h2>Execution Paths</h2>
        <div class="diagram-container">
            <div class="mermaid">
EXECUTION_CONTENT_PLACEHOLDER
            </div>
            <div id="execution-error" class="error-info"></div>
        </div>
    </div>
    
    <script>
        // Configure Mermaid with more detailed settings
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: false,
                htmlLabels: true
            },
            logLevel: 'debug'
        });
        
        // Add event listener to catch rendering errors
        document.addEventListener('DOMContentLoaded', function() {
            console.log("Document loaded, checking diagrams...");
            
            // Listen for mermaid errors and display them
            window.addEventListener('error', function(e) {
                if (e.error && e.error.toString().includes('mermaid')) {
                    console.error('Mermaid error:', e.error);
                    
                    // Show errors in the appropriate container
                    const errorElements = document.querySelectorAll('.error-info');
                    errorElements.forEach(el => {
                        el.textContent = 'Diagram rendering error: ' + e.error.toString();
                        el.style.display = 'block';
                    });
                }
            });
        });
    </script>
</body>
</html>"""

        # Replace the placeholders with the actual content
        html_template = html_template.replace("STRUCTURE_CONTENT_PLACEHOLDER", structure_content)
        html_template = html_template.replace("DEPENDENCIES_CONTENT_PLACEHOLDER", dependencies_content)
        html_template = html_template.replace("EXECUTION_CONTENT_PLACEHOLDER", execution_content)
        
        return html_template
    
    def save_html_visualization(self, html_content, output_path):
        """
        Save the HTML visualization to a file.
        
        Args:
            html_content: The HTML content to save
            output_path: The path to save the HTML file to
        """
        try:
            with open(output_path, 'w') as f:
                f.write(html_content)
            print(f"Visualization saved to {output_path}")
            return True
        except Exception as e:
            print(f"Error saving visualization: {e}")
            return False
    
    def visualize_codebase(self, output_name="codebase_visualization", open_browser=True):
        """
        Generate a visualization of the codebase and save it as an HTML file.
        
        Args:
            output_name: The base name for the output file (without extension)
            open_browser: Whether to open the visualization in a browser
            
        Returns:
            str: The path to the generated visualization file
        """
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate the structure diagram
        structure_content = self._generate_structure_diagram()
        
        # Generate the dependencies diagram
        dependencies_content = self._generate_dependencies_diagram()
        
        # Generate the execution paths diagram
        execution_content = self._generate_execution_paths_diagram()
        
        # Ensure all diagrams have the proper syntax
        structure_content = self._ensure_valid_mermaid_syntax(structure_content, "graph TD")
        dependencies_content = self._ensure_valid_mermaid_syntax(dependencies_content, "graph LR")
        execution_content = self._ensure_valid_mermaid_syntax(execution_content, "flowchart TD")
        
        # Generate the HTML visualization
        html_content = self.generate_html_visualization(
            structure_content,
            dependencies_content,
            execution_content
        )
        
        # Save the HTML content to a file
        output_path = os.path.join(self.output_dir, f"{output_name}.html")
        self.save_html_visualization(html_content, output_path)
        
        # Open the visualization in a browser if requested
        if open_browser:
            try:
                webbrowser.open(f"file://{os.path.abspath(output_path)}")
                print(f"Opened visualization in browser: {output_path}")
            except Exception as e:
                print(f"Error opening visualization in browser: {e}")
        
        return output_path
    
    def _generate_structure_diagram(self):
        """
        Generate a Mermaid diagram representing the structure of the codebase.
        
        Returns:
            str: The Mermaid diagram content as a string
        """
        if not self.codebase or not hasattr(self.codebase, 'modules') or not self.codebase.modules:
            return "graph TD\n    A[No module data available]"
        
        diagram = "graph TD\n"
        
        # Create nodes for each module
        for module in self.codebase.modules:
            module_id = self._sanitize_id(module.name)
            diagram += f"    {module_id}[{module.name}]\n"
        
        # Add connections between modules
        for module in self.codebase.modules:
            if hasattr(module, 'imports') and module.imports:
                module_id = self._sanitize_id(module.name)
                for imported_module in module.imports:
                    imported_id = self._sanitize_id(imported_module)
                    diagram += f"    {module_id} --> {imported_id}\n"
        
        return diagram
    
    def _generate_dependencies_diagram(self):
        """
        Generate a Mermaid diagram representing the dependencies between modules.
        
        Returns:
            str: The Mermaid diagram content as a string
        """
        if not self.codebase or not hasattr(self.codebase, 'modules') or not self.codebase.modules:
            return "graph LR\n    A[No dependency data available]"
        
        diagram = "graph LR\n"
        
        # Group modules by package/directory
        packages = {}
        for module in self.codebase.modules:
            parts = module.name.split('.')
            if len(parts) > 1:
                package = parts[0]
                if package not in packages:
                    packages[package] = []
                packages[package].append(module)
            else:
                if "root" not in packages:
                    packages["root"] = []
                packages["root"].append(module)
        
        # Create subgraphs for each package
        for package, modules in packages.items():
            package_id = self._sanitize_id(package)
            diagram += f"    subgraph {package_id}[{package}]\n"
            
            for module in modules:
                module_id = self._sanitize_id(module.name)
                diagram += f"        {module_id}[{module.name.split('.')[-1]}]\n"
            
            diagram += "    end\n"
        
        # Add connections between modules
        for module in self.codebase.modules:
            if hasattr(module, 'imports') and module.imports:
                module_id = self._sanitize_id(module.name)
                for imported_module in module.imports:
                    imported_id = self._sanitize_id(imported_module)
                    diagram += f"    {module_id} --> {imported_id}\n"
        
        return diagram
    
    def _generate_execution_paths_diagram(self):
        """
        Generate a Mermaid diagram representing the execution paths in the codebase.
        
        Returns:
            str: The Mermaid diagram content as a string
        """
        if not self.codebase or not hasattr(self.codebase, 'entry_points') or not self.codebase.entry_points:
            return "flowchart TD\n    A[No execution path data available]"
        
        diagram = "flowchart TD\n"
        
        # Create nodes for each entry point
        for i, entry_point in enumerate(self.codebase.entry_points):
            entry_id = f"entry{i}"
            diagram += f"    {entry_id}[{entry_point}]\n"
        
            # If we have function calls for this entry point, add them
            if hasattr(self.codebase, 'function_calls') and entry_point in self.codebase.function_calls:
                calls = self.codebase.function_calls[entry_point]
                for j, call in enumerate(calls):
                    call_id = f"{entry_id}_call{j}"
                    call_name = call if isinstance(call, str) else call.get('name', f"Call {j}")
                    diagram += f"    {entry_id} --> {call_id}[{call_name}]\n"
        
        return diagram
    
    def _sanitize_id(self, id_str):
        """
        Sanitize a string to be used as a Mermaid node ID.
        
        Args:
            id_str: The string to sanitize
            
        Returns:
            str: The sanitized string
        """
        # Replace dots and other invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', str(id_str))
        
        # If the ID starts with a number, prepend an underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        return sanitized
        
    def _ensure_valid_mermaid_syntax(self, diagram_content, default_type):
        """
        Ensure the diagram content has valid Mermaid syntax.
        
        Args:
            diagram_content: The diagram content to validate
            default_type: The default diagram type to use if none is specified
            
        Returns:
            str: The validated diagram content
        """
        # Trim whitespace
        diagram_content = diagram_content.strip()
        
        # If empty, return a simple valid diagram
        if not diagram_content:
            return f"{default_type}\n    A[No data available]"
        
        # Check if the content starts with a valid diagram type
        valid_starts = ["graph ", "flowchart ", "sequenceDiagram", "classDiagram", "stateDiagram", "gantt", "pie", "erDiagram"]
        has_valid_start = any(diagram_content.startswith(start) for start in valid_starts)
        
        # If not, add the default type
        if not has_valid_start:
            diagram_content = f"{default_type}\n{diagram_content}"
        
        # Fix common syntax errors
        # 1. Ensure nodes have valid names (alphanumeric or enclosed in quotes)
        # 2. Add missing edge types (-- or -->)
        # This is a basic implementation and may need enhancement for more complex issues
        
        return diagram_content 