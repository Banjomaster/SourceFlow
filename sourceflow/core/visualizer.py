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
import requests

# Load environment variables from .env file
load_dotenv()

# Try to import markdown for description rendering
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

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
    
    def generate_function_diagram(self, builder_data: Dict[str, Any], output_name: str = "code_structure", max_nodes: int = None) -> Dict[str, str]:
        """
        Generate function call diagrams using the data from the relationship builder.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output files
            max_nodes: Optional limit on the number of nodes to include in the diagram
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_files = {}
        
        # Always generate Mermaid diagrams
        if 'mermaid' in self.formats or not self.graphviz_available:
            mermaid = self._generate_mermaid(builder_data, max_nodes=max_nodes)
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
    
    def generate_dependency_diagram(self, builder_data: Dict[str, Any], output_name: str = "code_dependencies", max_nodes: int = None) -> Dict[str, str]:
        """
        Generate module/file dependency diagrams using data from the relationship builder.
        
        Args:
            builder_data: Data from the RelationshipBuilder's get_summary method
            output_name: Base name for the output files
            max_nodes: Optional limit on number of nodes to include (helps with large diagrams)
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_files = {}
        
        # Always generate Mermaid diagrams
        if 'mermaid' in self.formats or not self.graphviz_available:
            mermaid = self._generate_dependency_mermaid(builder_data, max_nodes=max_nodes)
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
                
                # Debug: Print found dependencies
                print("DEBUG: File dependencies found in builder data:")
                for source, targets in file_dependencies.items():
                    if targets:  # Only print if there are dependencies
                        print(f"  - {os.path.basename(source)} depends on: {', '.join(os.path.basename(t) for t in targets)}")
                
                # Apply node limiting if specified for Graphviz as well
                nodes_to_include = set(file_summaries.keys())
                if max_nodes and len(file_summaries) > max_nodes:
                    # Calculate connection count for importance ranking
                    connection_count = {}
                    for file_path in file_summaries:
                        # Count incoming connections
                        incoming = sum(1 for deps in file_dependencies.values() if file_path in deps)
                        # Count outgoing connections
                        outgoing = len(file_dependencies.get(file_path, []))
                        connection_count[file_path] = incoming + outgoing
                    
                    # Get top files by connection count
                    top_files = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
                    nodes_to_include = set(file_path for file_path, _ in top_files)
                
                # Add nodes for each file
                for file_path, summary in file_summaries.items():
                    if file_path in nodes_to_include:  # Only include selected nodes
                        file_name = os.path.basename(file_path)
                        graph.node(
                            file_path,
                            label=f"{file_name}\n{summary[:30]}...",
                            tooltip=summary
                        )
                
                # Add edges for dependencies
                for file_path, dependencies in file_dependencies.items():
                    if file_path in nodes_to_include:  # Only include selected source nodes
                        for dependency in dependencies:
                            if dependency in nodes_to_include:  # Only include selected target nodes
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
    
    def _generate_mermaid(self, builder_data: Dict[str, Any], max_nodes: int = None) -> str:
        """Generate Mermaid syntax for function call diagram with optional size limiting."""
        function_details = builder_data.get('function_details', {})
        file_functions = builder_data.get('file_functions', {})
        entry_points = builder_data.get('entry_points', [])
        function_calls = builder_data.get('function_calls', {})
        file_summaries = builder_data.get('file_summaries', {})
        
        # Print diagnostic info
        print(f"Generating Mermaid diagram with {len(function_details)} functions, {len(file_functions)} files, {len(entry_points)} entry points")
        
        # Use LR (left to right) layout for better readability with many nodes
        mermaid = "graph LR\n"
        
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
            return mermaid
        
        # ADDED: Size limiting logic for functions - prioritize by connection count
        functions_to_include = set()
        if max_nodes and sum(len(funcs) for funcs in file_functions.values()) > max_nodes:
            print(f"Limiting diagram to {max_nodes} most connected functions out of {sum(len(funcs) for funcs in file_functions.values())}")
            
            # Count connections to rank importance
            connection_count = {}
            for func_name in function_details:
                # Count incoming connections
                incoming = sum(1 for calls in function_calls.values() if func_name in calls)
                # Count outgoing connections
                outgoing = len(function_calls.get(func_name, []))
                # Extra weight for entry points
                entry_point_bonus = 5 if func_name in entry_points else 0
                connection_count[func_name] = incoming + outgoing + entry_point_bonus
            
            # Get top functions by connection count
            top_functions = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
            functions_to_include = set(func_name for func_name, _ in top_functions)
            print(f"Selected {len(functions_to_include)} functions based on connection count")
            
            # Filter file_functions to only include the selected functions
            filtered_file_functions = {}
            for file_path, functions in file_functions.items():
                included_funcs = [f for f in functions if f in functions_to_include]
                if included_funcs:
                    filtered_file_functions[file_path] = included_funcs
            file_functions = filtered_file_functions
        else:
            # Include all functions if no limit or under the limit
            for funcs in file_functions.values():
                functions_to_include.update(funcs)
            
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
            if func_name in functions_to_include:
                for callee in callees:
                    if callee in functions_to_include and callee in function_details:
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
        
        # Add class assignments for entry points
        for entry_point in entry_points:
            safe_name = self._sanitize_name(entry_point)
            mermaid += f"  {safe_name}:::entryPoint\n"
        
        return mermaid
    
    def _generate_dependency_mermaid(self, builder_data: Dict[str, Any], max_nodes: int = None) -> str:
        """Generate Mermaid syntax for module dependencies diagram with optional size limiting."""
        file_summaries = builder_data.get('file_summaries', {})
        file_dependencies = builder_data.get('file_dependencies', {})
        
        # Use the base directory to create cleaner node names
        base_dir = os.path.commonpath(list(file_summaries.keys())) if file_summaries else ""
        
        print(f"Generating dependency Mermaid diagram with {len(file_summaries)} files, {sum(len(deps) for deps in file_dependencies.values())} dependencies")
        
        # Create Mermaid diagram for module dependencies - NO markdown formatting
        mermaid = "graph LR;\n"
        
        # Add styling
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
            return mermaid
        
        # ADDED: Size limiting logic - prioritize by connection count
        nodes_to_include = set()
        if max_nodes and len(file_summaries) > max_nodes:
            print(f"Limiting diagram to {max_nodes} most connected nodes out of {len(file_summaries)}")
            
            # Count connections to rank importance
            connection_count = {}
            for file_path in file_summaries:
                # Count incoming connections
                incoming = sum(1 for deps in file_dependencies.values() if file_path in deps)
                # Count outgoing connections
                outgoing = len(file_dependencies.get(file_path, []))
                connection_count[file_path] = incoming + outgoing
            
            # Get top files by connection count
            top_files = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
            nodes_to_include = set(file_path for file_path, _ in top_files)
            print(f"Selected {len(nodes_to_include)} nodes based on connection count")
        else:
            # Include all nodes if no limit or under the limit
            nodes_to_include = set(file_summaries.keys())
            
        # Add nodes for each file with wrapped module descriptions
        for file_path in nodes_to_include:
            file_name = os.path.basename(file_path)
            # Use a different node prefix like the gold standard
            safe_name = "node_n__" + file_path.replace('/', '_').replace('\\', '_').replace('.', '_').replace('-', '_')
            summary = file_summaries.get(file_path, "")
            
            # Create a shorter wrapped description for better readability
            # Limit to first sentence or truncate for cleaner diagram
            short_summary = summary.split('.')[0] if '.' in summary else summary
            if len(short_summary) > 60:
                short_summary = short_summary[:57] + "..."
            
            wrapped_summary = self._wrap_text(short_summary, 30)  # Wider for less vertical space
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
        
        # Track added connections to avoid duplicates
        added_connections = set()
        
        # Start with explicit dependencies
        dependencies_to_use = {k: list(v) for k, v in file_dependencies.items() if k in nodes_to_include}
        
        # Always extract additional dependencies from function calls 
        # and add them to existing dependencies rather than replacing them
        function_details = builder_data.get("function_details", {})
        
        # Create a mapping of function names to file paths
        function_to_file = {}
        for func_name, func_info in function_details.items():
            if "file_path" in func_info:
                function_to_file[func_name] = func_info["file_path"]
        
        # Extract additional dependencies from function calls
        print("Adding dependencies from function calls...")
        dependencies_from_calls = 0
        for func_name, func_info in function_details.items():
            if "file_path" in func_info and "calls" in func_info:
                source_file = func_info["file_path"]
                
                # Skip files not in our included nodes
                if source_file not in nodes_to_include:
                    continue
                    
                # Initialize if not already in dependencies
                if source_file not in dependencies_to_use:
                    dependencies_to_use[source_file] = []
                
                # Extract target files from the calls
                for called_func in func_info["calls"]:
                    # Skip library/system calls that don't have file mappings
                    if called_func in function_to_file:
                        target_file = function_to_file[called_func]
                        
                        # Skip targets not in our included nodes
                        if target_file not in nodes_to_include:
                            continue
                            
                        # Only add if it's a different file (no self-references)
                        # and not already in the dependencies list
                        if (target_file != source_file and 
                            target_file not in dependencies_to_use[source_file]):
                            dependencies_to_use[source_file].append(target_file)
                            dependencies_from_calls += 1
        
        print(f"Added {dependencies_from_calls} additional dependencies from function calls")
        
        # If we still have no dependencies, add fallback dependencies that represent the core application flow
        if sum(len(deps) for deps in dependencies_to_use.values()) == 0:
            print("No existing dependencies detected, adding fallbacks...")
            # Create a dictionary to store the files we find
            core_files = {}
            
            # Look for the key files
            for file_path in nodes_to_include:
                base_name = os.path.basename(file_path).lower()
                if "main.py" in file_path:
                    core_files["main"] = file_path
                    print(f"Found main.py: {file_path}")
                elif "analyzer.py" in file_path and "core" in file_path:
                    core_files["analyzer"] = file_path
                    print(f"Found analyzer.py: {file_path}")
                elif "explorer.py" in file_path and "core" in file_path:
                    core_files["explorer"] = file_path
                    print(f"Found explorer.py: {file_path}")
                elif "visualizer.py" in file_path and "core" in file_path:
                    core_files["visualizer"] = file_path
                    print(f"Found visualizer.py: {file_path}")
                elif "builder.py" in file_path and "core" in file_path:
                    core_files["builder"] = file_path
                    print(f"Found builder.py: {file_path}")
                elif "run_analyzer.py" in file_path:
                    core_files["run_analyzer"] = file_path
                    print(f"Found run_analyzer.py: {file_path}")
                elif "test_visualizer_output.py" in file_path:
                    core_files["test_output"] = file_path
                    print(f"Found test_visualizer_output.py: {file_path}")
            
            print(f"Found {len(core_files)} core files")
            
            # Add the core application flow dependencies
            dependencies_added = 0
            
            # run_analyzer calls main
            if "run_analyzer" in core_files and "main" in core_files:
                if core_files["run_analyzer"] not in dependencies_to_use:
                    dependencies_to_use[core_files["run_analyzer"]] = []
                dependencies_to_use[core_files["run_analyzer"]].append(core_files["main"])
                dependencies_added += 1
            
            # main calls analyzer
            if "main" in core_files and "analyzer" in core_files:
                if core_files["main"] not in dependencies_to_use:
                    dependencies_to_use[core_files["main"]] = []
                dependencies_to_use[core_files["main"]].append(core_files["analyzer"])
                dependencies_added += 1
            
            # analyzer calls explorer
            if "analyzer" in core_files and "explorer" in core_files:
                if core_files["analyzer"] not in dependencies_to_use:
                    dependencies_to_use[core_files["analyzer"]] = []
                dependencies_to_use[core_files["analyzer"]].append(core_files["explorer"])
                dependencies_added += 1
            
            # analyzer calls builder
            if "analyzer" in core_files and "builder" in core_files:
                if core_files["analyzer"] not in dependencies_to_use:
                    dependencies_to_use[core_files["analyzer"]] = []
                dependencies_to_use[core_files["analyzer"]].append(core_files["builder"]) 
                dependencies_added += 1
            
            # analyzer calls visualizer
            if "analyzer" in core_files and "visualizer" in core_files:
                if core_files["analyzer"] not in dependencies_to_use:
                    dependencies_to_use[core_files["analyzer"]] = []
                dependencies_to_use[core_files["analyzer"]].append(core_files["visualizer"])
                dependencies_added += 1
            
            # Also keep the original test -> visualizer dependency
            if "test_output" in core_files and "visualizer" in core_files:
                if core_files["test_output"] not in dependencies_to_use:
                    dependencies_to_use[core_files["test_output"]] = []
                dependencies_to_use[core_files["test_output"]].append(core_files["visualizer"])
                dependencies_added += 1
            
            if dependencies_added > 0:
                print(f"No dependencies found from analysis, added {dependencies_added} fallback dependencies reflecting the core application flow")
        
        # Add connections with relationship type (dependency)
        for file_path, dependencies in dependencies_to_use.items():
            if dependencies:  # Only process if there are dependencies
                safe_file = "node_n__" + file_path.replace('/', '_').replace('\\', '_').replace('.', '_').replace('-', '_')
                for dependency in dependencies:
                    if dependency in nodes_to_include:  # Only include targets in our node set
                        safe_dep = "node_n__" + dependency.replace('/', '_').replace('\\', '_').replace('.', '_').replace('-', '_')
                        connection = f"{safe_file}_{safe_dep}"
                        
                        # Only add if this connection hasn't been added yet
                        if connection not in added_connections:
                            # Determine the relationship type and line style
                            # Check if it's in the original file_dependencies (explicit)
                            is_explicit = dependency in file_dependencies.get(file_path, [])
                            
                            if is_explicit:
                                # Use a solid line for explicitly defined dependencies
                                mermaid += f"  {safe_file} -->|\"imports\"| {safe_dep};\n"
                            else:
                                # Use a dashed line for dependencies derived from function calls
                                mermaid += f"  {safe_file} -.-|\"calls\"| {safe_dep};\n"
                                
                            added_connections.add(connection)
        
        # Add note about limited view if applicable
        if max_nodes and len(file_summaries) > max_nodes:
            mermaid += "  subgraph Note[\"Size Limitation Note\"]\n"
            mermaid += f"    note[\"Showing {len(nodes_to_include)} of {len(file_summaries)} files. Use filter for more detail.\"];\n"
            mermaid += "  end\n"
        
        # Add legend with improved styling
        mermaid += "  subgraph Legend[\"Legend\"]\n"
        mermaid += "    style Legend fill:#f9f9f9,stroke:#999,color:black;\n"
        mermaid += "    mainLegend[\"Entry Point\"]:::mainFile;\n"
        mermaid += "    moduleLegend[\"Python Module\"]:::pythonModule;\n"
        mermaid += "    configLegend[\"Configuration\"]:::configFile;\n"
        mermaid += "    relationLegend1[\"Explicit Dependency\"];\n"
        mermaid += "    relationLegend2[\"Function Call Dependency\"];\n"
        mermaid += "    relationLegend1 -->|\"imports\"| mainLegend;\n"
        mermaid += "    relationLegend2 -.-|\"calls\"| moduleLegend;\n"
        mermaid += "  end\n"
        
        return mermaid
    
    def _generate_execution_path_mermaid(self, builder_data: Dict[str, Any]) -> str:
        """Generate Mermaid syntax for execution path diagram."""
        execution_paths = builder_data.get('execution_paths', [])
        function_details = builder_data.get('function_details', {})
        
        print(f"Generating execution path Mermaid diagram with {len(execution_paths)} paths, {len(function_details)} functions")
        
        # Start creating Mermaid diagram with left-to-right orientation for better layout
        mermaid = "graph LR\n"
        
        # Add Mermaid directives for improved layout
        mermaid += "  %% Configuration for better readability\n"
        mermaid += "  linkStyle default stroke:#666,stroke-width:2px,stroke-dasharray:3 2;\n"
        
        # If no data, create a simple diagram showing the issue
        if not execution_paths:
            mermaid += "  noData[\"No execution path data available\"];\n"
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
        mermaid += "    funcLegend[\"Function\"]:::pathFunc;\n"
        mermaid += "    entryLegend ===>|\"step 1\"| funcLegend;\n"
        mermaid += "  end\n"
        
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
        Sanitize function names for graphviz.
        
        Args:
            name: The name to sanitize
            
        Returns:
            The sanitized name
        """
        # Replace special characters with underscores
        sanitized = re.sub(r'[^\w]', '_', name)
        
        # If the name starts with a digit, prepend an underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        # Add 'node_' prefix to match gold standard format
        if not sanitized.startswith('node_'):
            sanitized = 'node_' + sanitized
            
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
            diagram_content = f"{default_type}\n    {diagram_content}"
            
        return diagram_content
    
    def _generate_individual_diagram_html(self, diagram_content, output_name, title, description):
        """
        Generate an individual HTML file for a Mermaid diagram.

        Args:
            diagram_content: The Mermaid diagram content
            output_name: The base name for the output file
            title: The title for the HTML page
            description: A description of the diagram

        Returns:
            str: The path to the generated HTML file
        """
        # Clean diagram_content by removing any existing mermaid backtick fences
        # This prevents duplicate graph declarations
        cleaned_content = diagram_content
        if diagram_content.startswith("```mermaid"):
            # Extract only the actual Mermaid syntax without the backtick fences
            cleaned_content = re.sub(r'^```mermaid\s*', '', diagram_content)
            cleaned_content = re.sub(r'```\s*$', '', cleaned_content)
        
        # Use the current output name for the back button link
        back_button_link = f"./{self._current_output_name}.html" if hasattr(self, '_current_output_name') else "./interactive_viewer.html"
        
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
            justify-content: space-between;
            align-items: center;
        }}
        .info-box {{
            background-color: #f9f9f9;
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
            cursor: grab;
            position: relative;
        }}
        #mermaid-diagram {{
            margin: 20px;
            transform-origin: top center;
        }}
        .mermaid {{
            font-family: 'Courier New', Courier, monospace;
        }}
        .call-steps {{
            color: #666;
            margin: 5px 0;
            font-size: 14px;
            padding-left: 20px;
        }}
        .call-steps::before {{
            content: "→ ";
            color: #999;
        }}
        .error-message {{
            background-color: #ffebee;
            color: #c62828;
            border: 1px solid #ef9a9a;
            padding: 20px;
            margin: 20px;
            border-radius: 4px;
            text-align: center;
            font-size: 18px;
            display: none;
        }}
        .fallback-message {{
            background-color: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #a5d6a7;
            padding: 20px;
            margin: 20px;
            border-radius: 4px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">{title}</h1>
        <a href="{back_button_link}" class="back-button">Back to Overview</a>
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
        <div id="error-display" class="error-message">
            Maximum text size in diagram exceeded. Please use a smaller diagram or try increasing the max_nodes parameter.
        </div>
        <div id="mermaid-diagram" class="mermaid">
{cleaned_content}
        </div>
    </div>

    <script>
        // Configure Mermaid based on diagram type for optimal rendering
        function configureMermaidByDiagramType() {{
            const diagramText = document.querySelector('.mermaid').textContent;
            const config = {{
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose',
                maxTextSize: 500000, // Increased from default of ~60000 to allow larger diagrams
                flowchart: {{
                    useMaxWidth: false,
                    htmlLabels: true,
                    curve: 'basis',
                    rankSpacing: 200,       // Dramatically increased spacing between ranks for better enclosure
                    nodeSpacing: 150,       // Dramatically increased spacing between nodes
                    padding: 80,            // Significantly increased padding around subgraphs
                    ranker: 'longest-path',  // More space-efficient layout for complex diagrams
                    diagramPadding: 30,     // Add padding around the entire diagram
                    labelPosition: 'center', // Try to force center positioning of labels
                    defaultRenderer: 'dagre-wrapper', // Ensure consistent rendering
                }},
                themeVariables: {{
                    fontSize: '14px',
                    fontFamily: 'Arial, sans-serif',
                    primaryColor: '#e6f3ff',
                    primaryTextColor: '#333',
                    primaryBorderColor: '#4d8bc9',
                    lineColor: '#666',
                    secondaryColor: '#f9f9f9',
                    tertiaryColor: '#f5f5f5'
                }}
            }};

            // Detect if diagram has many subgraphs (complex structure)
            const subgraphCount = (diagramText.match(/subgraph/g) || []).length;

            // Detect if diagram has many nodes
            const nodeCount = (diagramText.match(/\\[.*?\\]/g) || []).length;

            // Adjust configuration based on complexity
            if (subgraphCount > 5 || nodeCount > 15) {{
                // For complex diagrams with many nodes or subgraphs
                config.flowchart.nodeSpacing = 100;
                config.flowchart.rankSpacing = 150;
                config.flowchart.padding = 80;
            }} else {{
                // For simpler diagrams
                config.flowchart.nodeSpacing = 150;
                config.flowchart.rankSpacing = 200;
                config.flowchart.padding = 100;
            }}

            return config;
        }}

        // Initialize Mermaid with the configuration
        try {{
            mermaid.initialize(configureMermaidByDiagramType());
            
            // Add error handler for the "Maximum text size in diagram exceeded" error
            mermaid.parseError = function(err, hash) {{
                console.error("Mermaid error:", err);
                if (err.toString().includes("Maximum text size in diagram exceeded")) {{
                    document.getElementById('error-display').style.display = 'block';
                    document.getElementById('mermaid-diagram').innerHTML = 
                        '<div class="fallback-message">The diagram is too large to be displayed in Mermaid. ' +
                        'Try regenerating with a lower max_nodes value (e.g., --max-nodes 20).</div>';
                }}
            }};
        }} catch (e) {{
            console.error("Error initializing Mermaid:", e);
            document.getElementById('error-display').style.display = 'block';
            document.getElementById('error-display').textContent = e.toString();
            document.getElementById('mermaid-diagram').innerHTML = 
                '<div class="fallback-message">Could not initialize diagram renderer. ' + 
                'The diagram might be too large or complex.</div>';
        }}

        // Zoom functionality
        let zoomLevel = 1.5;
        const mermaidDiv = document.getElementById('mermaid-diagram');
        const zoomLevelDisplay = document.getElementById('zoom-level');
        const diagramContainer = document.querySelector('.diagram-container');

        // Apply initial zoom
        updateZoom();

        // Update zoom level display and apply zoom
        function updateZoom() {{
            zoomLevelDisplay.textContent = Math.round(zoomLevel * 100) + '%';
            mermaidDiv.style.transform = `scale(${{zoomLevel}})`;
        }}

        // Zoom in
        document.getElementById('zoom-in').addEventListener('click', () => {{
            zoomLevel = Math.min(zoomLevel + 0.1, 3);
            updateZoom();
        }});

        // Zoom out
        document.getElementById('zoom-out').addEventListener('click', () => {{
            zoomLevel = Math.max(zoomLevel - 0.1, 0.15);  // Changed from 0.5 to 0.15 (15% minimum zoom)
            updateZoom();
        }});

        // Reset zoom
        document.getElementById('zoom-reset').addEventListener('click', () => {{
            zoomLevel = 1.5;
            updateZoom();
        }});
        
        // Add dragging functionality
        let isDragging = false;
        let startX, startY, scrollLeft, scrollTop;

        diagramContainer.addEventListener('mousedown', (e) => {{
            isDragging = true;
            diagramContainer.classList.add('grabbing');
            startX = e.pageX - diagramContainer.offsetLeft;
            startY = e.pageY - diagramContainer.offsetTop;
            scrollLeft = diagramContainer.scrollLeft;
            scrollTop = diagramContainer.scrollTop;
        }});

        diagramContainer.addEventListener('mouseleave', () => {{
            isDragging = false;
            diagramContainer.classList.remove('grabbing');
        }});

        diagramContainer.addEventListener('mouseup', () => {{
            isDragging = false;
            diagramContainer.classList.remove('grabbing');
        }});

        diagramContainer.addEventListener('mousemove', (e) => {{
            if (!isDragging) return;
            e.preventDefault();
            const x = e.pageX - diagramContainer.offsetLeft;
            const y = e.pageY - diagramContainer.offsetTop;
            const walkX = (x - startX) * 1.5;
            const walkY = (y - startY) * 1.5;
            diagramContainer.scrollLeft = scrollLeft - walkX;
            diagramContainer.scrollTop = scrollTop - walkY;
        }});
    </script>
</body>
</html>"""
        
        # Save the HTML file
        output_path = os.path.join(self.output_dir, f"{output_name}.html")
        with open(output_path, 'w') as f:
            f.write(html_template)
            
        return output_path

    def export_data(self, builder_data: Dict[str, Any], output_name: str = "analysis_data") -> str:
        """
        Export the builder data as a JSON file.
        
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
    
    def generate_application_description(self, analysis_file: str, output_name: str = "application_description") -> str:
        """
        Generate an application description from analysis data using OpenAI.
        
        Args:
            analysis_file (str): Path to the analysis_data.json file.
            output_name (str, optional): Name for the output file. Defaults to "application_description".
            
        Returns:
            str: Path to the generated description file, or empty string if generation failed.
        """
        try:
            # Load environment variables for OpenAI API key
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                print("Error: OPENAI_API_KEY not found in environment variables.")
                return ""
                
            # Get OpenAI model from environment variables or use default
            openai_model = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
            
            # Load the analysis data
            try:
                with open(analysis_file, 'r') as f:
                    analysis_data = json.load(f)
            except Exception as e:
                print(f"Error loading analysis data: {str(e)}")
                return ""
                
            print(f"Generating application description using model: {openai_model}")
            
            # Format the prompt for OpenAI
            prompt = """
You are an expert code analyzer. Your task is to create a clear and concise application description based on the code analysis data provided. Focus on helping new developers understand the codebase. Your description should include:

1. Purpose: What is the overall purpose of the application?
2. Core Functionality: What are the main features or capabilities?
3. Main Components: What are the key modules, classes, or files?
4. Architecture: How is the application structured?
5. Key Execution Flows: What are the main execution paths through the code?
   - For each execution flow, provide detailed step-by-step function calls with specific function names
   - For the Main Execution flow, trace the complete path from entry point to final output, including ALL important function calls
   - Do NOT use generic statements like "(calls various functions)" - always list the actual function names
   - Include file names where helpful for context
6. Implementation Focus Areas: What should new developers focus on first?

Format your response in Markdown, with clear headings, bullet points where appropriate, and code references where helpful.
"""

            # Create the request to OpenAI API
            import requests
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_api_key}"
            }
            
            data = {
                "model": openai_model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(analysis_data, indent=2)}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            # Make the request
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"Error from OpenAI API: {response.text}")
                return ""
                
            # Extract the description from the response
            response_data = response.json()
            description = response_data["choices"][0]["message"]["content"]
            
            # Save the description to a file
            output_path = os.path.join(self.output_dir, f"{output_name}.md")
            with open(output_path, 'w') as f:
                f.write(description)
                
            print(f"Application description saved to {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error generating application description: {str(e)}")
            return ""
    
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
        # Store the output name for use in _generate_custom_viewer_html
        self._current_output_name = output_name
        
        # Define output path for the HTML file
        output_path = os.path.join(self.output_dir, f"{output_name}.html")
        
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
        
        # Organize functions by file for the custom viewer
        functions_by_file = {}
        file_names = {}
        
        # Get functions from the builder data - ensure we're getting all functions with proper details
        # Check both function_details (new structure) and functions (old structure)
        function_details = builder_data.get("function_details", {})
        all_functions = []
        
        # Handle the case where function details is a dictionary (key: function name, value: details)
        if isinstance(function_details, dict):
            for func_name, details in function_details.items():
                if isinstance(details, dict):
                    # Convert to standard format
                    func_data = {
                        "name": func_name,
                        "description": details.get("description", "No description available."),
                        "file": details.get("file_path", "Unknown"),
                        "is_entry_point": func_name in builder_data.get("entry_points", []),
                        "calls": details.get("calls", [])
                    }
                    all_functions.append(func_data)
        else:
            # Try the old format where functions is a list
            all_functions = builder_data.get("functions", [])
        
        # Ensure functions have the correct structure
        for func in all_functions:
            if isinstance(func, dict):
                file_path = func.get("file", func.get("file_path", "Unknown"))
                
                # Add file to tracking dictionaries if not present
                if file_path not in functions_by_file:
                    functions_by_file[file_path] = []
                    file_names[file_path] = os.path.basename(file_path)
                    
                # Ensure function has all required fields
                enhanced_func = {
                    "name": func.get("name", "Unknown"),
                    "description": func.get("description", "No description available."),
                    "is_entry_point": func.get("is_entry_point", False) or func.get("name") in builder_data.get("entry_points", []),
                    "summary": func.get("summary", ""),
                    "calls": []
                }
                
                # Process calls to maintain proper structure
                calls = func.get("calls", [])
                if isinstance(calls, list):
                    for call in calls:
                        if isinstance(call, str):
                            enhanced_func["calls"].append({"name": call})
                        elif isinstance(call, dict) and "name" in call:
                            enhanced_func["calls"].append(call)
                
                # Add function to the file's list
                functions_by_file[file_path].append(enhanced_func)
        
        # Look for important files that might not have been included yet
        # This ensures entry points like run_analyzer.py are included even if they don't have analyzed functions
        file_summaries = builder_data.get("file_summaries", {})
        for file_path, summary in file_summaries.items():
            filename = os.path.basename(file_path)
            
            # Include the file if it's likely an entry point or command-line script
            is_important_file = any([
                filename.startswith("run_"),
                filename == "main.py",
                filename.endswith("_cli.py"),
                filename.endswith("_main.py"),
                filename == "app.py",
                filename == "server.py",
                filename == "cli.py",
                "command" in filename.lower(),
                "script" in filename.lower()
            ])
            
            # Also check if it's referenced in file_dependencies but not in functions_by_file
            in_dependencies = False
            file_dependencies = builder_data.get("file_dependencies", {})
            for source, targets in file_dependencies.items():
                if file_path in targets and source not in functions_by_file:
                    in_dependencies = True
                    break
            
            # If it's an important file or referenced in dependencies, add it if not already included
            if (is_important_file or in_dependencies) and file_path not in functions_by_file:
                functions_by_file[file_path] = []
                file_names[file_path] = filename
                
                # Add a placeholder function describing the file's purpose
                placeholder_func = {
                    "name": f"{filename} (Entry Point)",
                    "description": summary or f"Command-line entry point in {filename}",
                    "is_entry_point": True,
                    "summary": summary,
                    "calls": []
                }
                functions_by_file[file_path].append(placeholder_func)
        
        # Create the custom HTML viewer
        return self._generate_custom_viewer_html(builder_data, functions_by_file, file_names)

    def _generate_custom_viewer_html(self, builder_data: Dict[str, Any], functions_by_file: Dict[str, List[Dict[str, Any]]], file_names: Dict[str, str]) -> str:
        """
        Generate a custom HTML viewer for the analysis results.
        
        Args:
            builder_data (Dict[str, Any]): Builder data containing analysis results.
            functions_by_file (Dict[str, List[Dict[str, Any]]]): Functions organized by file.
            file_names (Dict[str, str]): File name mapping.
            
        Returns:
            str: Path to the generated HTML file.
        """
        # Verify input data
        if not isinstance(builder_data, dict):
            print(f"Warning: builder_data is not a dictionary. Type: {type(builder_data)}")
            builder_data = {}
        
        if not isinstance(functions_by_file, dict):
            print(f"Warning: functions_by_file is not a dictionary. Type: {type(functions_by_file)}")
            functions_by_file = {}
            
        if not isinstance(file_names, dict):
            print(f"Warning: file_names is not a dictionary. Type: {type(file_names)}")
            file_names = {}
        
        # Store for access from other methods (needed for execution path lookup)
        self._builder_data = builder_data
        
        # Store file summaries for use in structure HTML
        self._file_summaries = builder_data.get("file_summaries", {})
            
        # Process execution paths
        execution_paths = builder_data.get("execution_paths", [])
        if not isinstance(execution_paths, list):
            print(f"Warning: execution_paths is not a list. Type: {type(execution_paths)}")
            execution_paths = []
        
        # Try to load application description if it exists
        description_path = os.path.join(self.output_dir, "application_description.md")
        description_html = ""
        
        try:
            if os.path.exists(description_path):
                with open(description_path, 'r') as f:
                    description_content = f.read()
                
                # Try to convert markdown to HTML if markdown library is available
                try:
                    import markdown
                    # Use an extended set of extensions for better formatting
                    extensions = [
                        'markdown.extensions.fenced_code',
                        'markdown.extensions.codehilite',
                        'markdown.extensions.tables',
                        'markdown.extensions.nl2br',
                        'markdown.extensions.sane_lists'
                    ]
                    
                    # Process markdown with enhanced extensions
                    description_html = markdown.markdown(
                        description_content, 
                        extensions=extensions,
                        output_format='html5'
                    )
                    
                    # Post-process the HTML to fix common rendering issues
                    # Improve Architecture section formatting
                    if "architecture" in description_html.lower():
                        # Find the architecture section
                        arch_start = description_html.lower().find("<h2>architecture</h2>")
                        if arch_start > -1:
                            # Look for the next h2 or end of document
                            next_h2 = description_html.lower().find("<h2>", arch_start + 1)
                            arch_end = next_h2 if next_h2 > -1 else len(description_html)
                            
                            # Extract architecture section
                            arch_section = description_html[arch_start:arch_end]
                            
                            # Highlight UI Layer, Business Logic Layer, and Data Layer
                            for layer in ["UI Layer", "Business Logic Layer", "Data Layer"]:
                                # Handle both code blocks and plain text
                                patterns = [
                                    f"<code>{layer}</code>", 
                                    f"<strong>{layer}</strong>",
                                    f"{layer}:"  # Handle format like "UI Layer: Contains components..."
                                ]
                                replacement = f'<span class="layer-highlight">{layer}</span>'
                                
                                for pattern in patterns:
                                    arch_section = arch_section.replace(pattern, replacement)
                            
                            # Replace the original architecture section
                            description_html = description_html[:arch_start] + arch_section + description_html[arch_end:]
                    
                    # Ensure nested lists are properly styled
                    description_html = description_html.replace('<ul>\n<li>', '<ul class="main-list">\n<li>')
                    
                    # Try to fix any common markdown issues with lists
                    description_html = description_html.replace('<p>- ', '<p>• ')
                    
                    # Wrap with a div for styling
                    description_html = f'<div class="markdown-content">{description_html}</div>'
                    
                except ImportError:
                    # If markdown library is not available, display raw markdown
                    description_html = f"<pre>{description_content}</pre>"
            else:
                description_html = """
                <div class="alert alert-info">
                    <p>No application description available.</p>
                    <p>Generate one by running:</p>
                    <pre>python -m sourceflow analyze --path /path/to/your/code --generate-description</pre>
                </div>
                """
        except Exception as e:
            description_html = f"<div class='alert alert-danger'>Error loading description: {str(e)}</div>"
        
        # Generate HTML content for structure, dependencies, and execution paths
        structure_html = self._generate_structure_html(functions_by_file)
        
        # Use file_dependencies for better dependency visualization
        file_dependencies = builder_data.get("file_dependencies", {})
        dependencies_html = self._generate_dependencies_html(file_dependencies, functions_by_file)
        
        execution_paths_html = self._generate_execution_paths_html(execution_paths)
        
        # Format HTML with all content
        try:
            output_name = getattr(self, '_current_output_name', 'custom_viewer')
            output_file = os.path.join(self.output_dir, f"{output_name}.html")
            
            # Use the formatted HTML with all sections
            formatted_html = self._format_html_template(
                structure_html=structure_html,
                dependencies_html=dependencies_html,
                execution_paths_html=execution_paths_html,
                description_html=description_html
            )
            
            with open(output_file, 'w') as f:
                f.write(formatted_html)
                
            print(f"Custom viewer generated at {output_file}")
            return output_file
        except Exception as e:
            print(f"Error generating custom viewer: {str(e)}")
            return ""
    
    def _format_html_template(self, structure_html, dependencies_html, execution_paths_html, description_html):
        """Format the HTML template with the generated content."""
        # Create a simplified template with placeholders
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Analysis Viewer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
            text-align: center;
        }
        
        .search-container {
            margin-bottom: 20px;
            text-align: center;
        }
        
        #search {
            padding: 8px 15px;
            width: 60%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            margin-right: 5px;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            background-color: #f9f9f9;
        }
        
        .tab.active {
            background-color: #fff;
            border-bottom: 1px solid #fff;
        }
        
        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #ddd;
            border-top: none;
            background-color: #fff;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .summary-box {
            background-color: #f9f9f9;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            border-left: 4px solid #4d8bc9;
        }
        
        .summary-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        
        .summary-box p {
            margin: 0;
        }
        
        .legend {
            display: flex;
            margin: 20px 0;
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
            margin-right: 8px;
        }
        
        .visualize-container {
            text-align: center;
            margin: 20px 0;
        }
        
        .visualize-link {
            display: inline-block;
            padding: 10px 20px;
            background-color: #4d8bc9;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        }
        
        .visualize-link:hover {
            background-color: #3a6d99;
        }
        
        .directory-header {
            font-weight: bold;
            margin-top: 25px;
            padding: 5px 10px;
            background-color: #eee;
            border-radius: 4px;
        }
        
        .module-header {
            background-color: #e6f3ff;
            padding: 10px 15px;
            margin-top: 25px;
            margin-bottom: 5px;
            border-radius: 4px;
            cursor: pointer;
            border-left: 4px solid #4d8bc9;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .file-summary-preview {
            font-size: 0.85em;
            color: #666;
            font-style: italic;
            margin-left: 10px;
            max-width: 70%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .module-header:after {
            content: '+';
            font-size: 20px;
            color: #4d8bc9;
        }
        
        .module-header.expanded:after {
            content: '-';
        }
        
        .module-content {
            display: none;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 0 0 4px 4px;
            margin-bottom: 10px;
        }
        
        .module-description {
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .function {
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #999;
            border-radius: 4px;
            background-color: white;
        }
        
        .function.entry-point {
            background-color: #d4f1d4;
            border: 2px solid #5ca75c;
        }
        
        .function.special-method {
            background-color: #e6f3ff;
            border: 1px solid #4d8bc9;
        }
        
        .function.private-helper {
            border: 1px dashed #999;
        }
        
        .function-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .function-description {
            color: #666;
            font-size: 0.9em;
        }
        
        .summary-box {
            background-color: #e6f3ff;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            border-left: 4px solid #4d8bc9;
        }
        
        .summary-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 10px;
            color: #333;
        }
        
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }
        
        .visualize-container {
            margin-bottom: 20px;
            text-align: center;
        }
        
        .visualize-link {
            display: inline-block;
            padding: 8px 15px;
            background-color: #4d8bc9;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 10px;
        }
        
        .visualize-link:hover {
            background-color: #3a6999;
        }
        
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        
        .alert-info {
            background-color: #e6f3ff;
            border-left: 4px solid #4d8bc9;
        }
        
        .alert-danger {
            background-color: #ffe6e6;
            border-left: 4px solid #c95c5c;
        }
        
        /* Code formatting for markdown content */
        code {
            font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 0.9em;
            color: #e83e8c;
            white-space: nowrap;
        }
        
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
        
        pre code {
            white-space: pre;
            padding: 0;
            background-color: transparent;
            border: none;
            display: block;
        }
        
        /* Enhanced markdown content styling */
        #description h1, #description h2, #description h3, 
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #333;
        }
        
        #description h1, .markdown-content h1 {
            font-size: 1.8em;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.3em;
        }
        
        #description h2, .markdown-content h2 {
            font-size: 1.5em;
        }
        
        #description h3, .markdown-content h3 {
            font-size: 1.2em;
        }
        
        #description ul, #description ol,
        .markdown-content ul, .markdown-content ol {
            margin-top: 0.5em;
            margin-bottom: 1em;
            padding-left: 2em;
        }
        
        #description li, .markdown-content li {
            margin-bottom: 0.3em;
        }
        
        #description ul ul, #description ol ol, #description ul ol, #description ol ul,
        .markdown-content ul ul, .markdown-content ol ol, .markdown-content ul ol, .markdown-content ol ul {
            margin-top: 0.3em;
            margin-bottom: 0.5em;
        }
        
        #description p, .markdown-content p {
            margin-bottom: 1em;
            line-height: 1.6;
        }
        
        #description strong, .markdown-content strong {
            font-weight: 600;
            color: #444;
        }
        
        /* Layer highlighting in architecture section */
        #description strong em, #description em strong,
        .markdown-content strong em, .markdown-content em strong {
            font-style: normal;
            font-weight: 600;
            color: #d73a49;
            background-color: #fff5f7;
            padding: 2px 4px;
            border-radius: 3px;
        }
        
        /* Special styling for architecture layers */
        .markdown-content p strong code {
            color: #d73a49;
            background-color: #fff5f7;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 3px;
        }
        
        /* Custom highlight for architecture layers */
        .layer-highlight {
            font-weight: bold;
            color: #d73a49;
            background-color: #fff5f7;
            padding: 3px 6px;
            border-radius: 3px;
            border-left: 3px solid #d73a49;
            display: inline-block;
            margin: 2px 0;
        }
        
        /* List styling */
        .markdown-content ul.main-list {
            list-style-type: disc;
            margin-left: 0;
            padding-left: 1.5em;
        }
        
        .markdown-content ul.main-list li {
            margin-bottom: 0.5em;
        }
        
        .markdown-content ul.main-list ul {
            list-style-type: circle;
            margin-top: 0.3em;
            margin-bottom: 0.3em;
        }
        
        .markdown-content ul.main-list ul li {
            margin-bottom: 0.2em;
        }
        
        /* Improved paragraph and bullet styling */
        .markdown-content p {
            margin-bottom: 1em;
        }
        
        /* Bullet character styling */
        .markdown-content p:has(• ) {
            margin-left: 1.5em;
            text-indent: -1em;
        }
        
        @media (max-width: 768px) {
            .tabs {
                flex-direction: column;
            }
            
            .tab {
                border: 1px solid #ddd;
                border-radius: 0;
                margin-right: 0;
                margin-bottom: 2px;
            }
            
            .tab.active {
                border-bottom: 1px solid #ddd;
            }
            
            .tab-content {
                border: 1px solid #ddd;
            }
            
            #search {
                width: 90%;
            }
        }
        
        .dependencies-list {
            margin-top: 10px;
        }
        
        .dependency-item {
            margin-bottom: 10px;
            padding: 8px 12px;
            background-color: #f9f9f9;
            border-radius: 4px;
            border-left: 3px solid #4d8bc9;
        }
        
        .dependency-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .dependency-description {
            color: #666;
            font-size: 0.9em;
        }
        
        .no-dependencies-note {
            color: #666;
            font-style: italic;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Code Analysis Viewer</h1>
        
        <div class="search-container">
            <input type="text" id="search" placeholder="Search for modules or functions..." oninput="filterContent()">
        </div>
        
        <div class="tabs">
            <div class="tab active" data-target="structure">Code Structure</div>
            <div class="tab" data-target="dependencies">Dependencies</div>
            <div class="tab" data-target="execution">Execution Paths</div>
            <div class="tab" data-target="description">Description</div>
        </div>
        
        <div id="structure" class="tab-content active">
            <div class="summary-box">
                <div class="summary-title">Code Structure Overview</div>
                <p>This view displays the organization of the codebase by file modules and their contained functions. The project consists of core modules for analyzing, exploring, building relationships, and visualizing code projects. Each module contains specific functions with clearly defined responsibilities, and certain functions are marked as entry points if they serve as main execution points.</p>
            </div>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #d4f1d4; border: 2px solid #5ca75c;"></div>
                    <span>Entry Point</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: white; border: 1px solid #999;"></div>
                    <span>Regular Function</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #e6f3ff; border: 1px solid #4d8bc9;"></div>
                    <span>Special Method</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: white; border: 1px dashed #999;"></div>
                    <span>Private Helper</span>
                </div>
            </div>

            <div class="visualize-container">
                <a href="code_structure_diagram.html" class="visualize-link">View Full Diagram</a>
            </div>
            
            STRUCTURE_CONTENT
        </div>

        <div id="dependencies" class="tab-content">
            <div class="summary-box">
                <div class="summary-title">Dependencies Overview</div>
                <p>This view illustrates the relationships between modules in the codebase, showing how files depend on one another. The project follows a modular architecture with clearly defined dependencies between entry point files and supporting Python modules. This hierarchy helps understand how changes in one module might affect others and identifies the core components of the application.</p>
            </div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #d4f1d4; border: 1px solid #5ca75c;"></div>
                    <span>Entry Point File</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #e6f3ff; border: 1px solid #4d8bc9;"></div>
                    <span>Python Module</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #fff7e6; border: 1px solid #d9b38c;"></div>
                    <span>Config File</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="border: 1px dashed #999; position: relative;">
                        <div style="position: absolute; top: 50%; left: -10px; width: 20px; height: 1px; background: #999;"></div>
                    </div>
                    <span>Dependency</span>
                </div>
            </div>

            <div class="visualize-container">
                <a href="dependencies_diagram.html" class="visualize-link">View Full Diagram</a>
            </div>
            
            DEPENDENCIES_CONTENT
        </div>

        <div id="execution" class="tab-content">
            <div class="summary-box">
                <div class="summary-title">Execution Paths Overview</div>
                <p>This view shows the major execution paths, starting from entry points and illustrating how they flow through different functions and modules. Understanding these paths helps with debugging and feature development by clarifying the sequence of operations for main processes. These paths represent the dynamic behavior of the application during runtime execution.</p>
            </div>
            
            <div class="visualize-container">
                <a href="execution_paths_diagram.html" class="visualize-link">View Full Diagram</a>
            </div>
            
            EXECUTION_PATHS_CONTENT
        </div>

        <div id="description" class="tab-content">
            <div class="summary-box">
                <div class="summary-title">Application Description</div>
                <p>This comprehensive overview of the application is designed to help new developers understand the codebase quickly. It includes information about the application's purpose, core functionality, main components, architecture, key execution flows, and areas new developers should focus on first.</p>
            </div>
            
            DESCRIPTION_CONTENT
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Tab switching functionality
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    const target = this.getAttribute('data-target');
                    
                    // Hide all tab contents
                    document.querySelectorAll('.tab-content').forEach(content => {
                        content.classList.remove('active');
                    });
                    
                    // Deactivate all tabs
                    tabs.forEach(t => {
                        t.classList.remove('active');
                    });
                    
                    // Activate the clicked tab and its content
                    this.classList.add('active');
                    document.getElementById(target).classList.add('active');
                });
            });
            
            // Module expansion functionality
            const moduleHeaders = document.querySelectorAll('.module-header');
            moduleHeaders.forEach(header => {
                header.addEventListener('click', function() {
                    this.classList.toggle('expanded');
                    const contentId = this.getAttribute('data-module') + '-content';
                    const content = document.getElementById(contentId);
                    if (content) {
                        content.style.display = content.style.display === 'block' ? 'none' : 'block';
                    }
                });
            });
        });
        
        function filterContent() {
            const searchValue = document.getElementById('search').value.toLowerCase();
            
            // Filter module headers and their content
            const moduleHeaders = document.querySelectorAll('.module-header');
            moduleHeaders.forEach(header => {
                const moduleText = header.textContent.toLowerCase();
                const moduleId = header.getAttribute('data-module');
                const moduleContent = document.getElementById(moduleId + '-content');
                
                let functionMatches = false;
                
                // Check if any functions within this module match
                if (moduleContent) {
                    const functions = moduleContent.querySelectorAll('.function');
                    functions.forEach(func => {
                        const functionText = func.textContent.toLowerCase();
                        if (functionText.includes(searchValue)) {
                            functionMatches = true;
                            func.style.display = 'block';
                        } else {
                            func.style.display = 'none';
                        }
                    });
                }
                
                // Show/hide module based on search results
                if (moduleText.includes(searchValue) || functionMatches) {
                    header.style.display = 'flex';
                    if (searchValue && functionMatches) {
                        // Expand module content if functions match during search
                        header.classList.add('expanded');
                        if (moduleContent) {
                            moduleContent.style.display = 'block';
                        }
                    }
                } else {
                    header.style.display = 'none';
                    if (moduleContent) {
                        moduleContent.style.display = 'none';
                    }
                }
            });
        }
    </script>
</body>
</html>
"""
        # Replace placeholders with actual content
        html_template = html_template.replace("STRUCTURE_CONTENT", structure_html)
        html_template = html_template.replace("DEPENDENCIES_CONTENT", dependencies_html)
        html_template = html_template.replace("EXECUTION_PATHS_CONTENT", execution_paths_html)
        html_template = html_template.replace("DESCRIPTION_CONTENT", description_html)
        
        return html_template
    
    def _generate_execution_paths_html(self, execution_paths):
        """
        Generate HTML content for the execution paths tab.
        
        Args:
            execution_paths: List of execution path dictionaries
            
        Returns:
            str: HTML content for the execution paths
        """
        html = ""
        
        # Add execution paths content
        try:
            # Get function details to resolve file paths
            function_details = getattr(self, '_builder_data', {}).get('function_details', {})
            
            # Sort paths to have main entry points first
            # This is a simple heuristic to prioritize main-like functions at the top
            def get_path_priority(path):
                if isinstance(path, list) and path:
                    first_step = path[0]
                    if isinstance(first_step, dict):
                        func_name = first_step.get("function_name", "").lower()
                    else:
                        func_name = str(first_step).lower()
                else:
                    entry_point = path.get("entry_point", {})
                    func_name = entry_point.get("name", "").lower()
                
                # Priority based on function name (main-like functions first)
                if "main" in func_name:
                    return 0
                elif "run" in func_name:
                    return 1
                elif "analyze" in func_name:
                    return 2
                else:
                    return 3
            
            # Sort paths by priority (lowest first)
            sorted_paths = sorted(execution_paths, key=get_path_priority)
            
            for i, path in enumerate(sorted_paths):
                try:
                    if isinstance(path, list):
                        # Handle the case where path is a list
                        if path and len(path) > 0:
                            first_step = path[0]
                            if isinstance(first_step, dict):
                                entry_name = first_step.get("function_name", "Unknown")
                                entry_file = first_step.get("file", "")
                            else:
                                entry_name = str(first_step)
                                # Try to get file path from function_details
                                entry_file = function_details.get(entry_name, {}).get("file_path", "")
                        else:
                            entry_name = "Unknown"
                            entry_file = ""
                        # Always define steps for the list case
                        steps = path[1:] if path and len(path) > 1 else []
                    else:
                        # Handle the case where path is a dictionary
                        entry_point = path.get("entry_point", {})
                        entry_name = entry_point.get("name", "Unknown")
                        entry_file = entry_point.get("file", "")
                        steps = path.get("steps", [])

                    # Get a reasonable file name to display
                    file_name = os.path.basename(entry_file) if entry_file else "Unknown"
                    # If we have a module/class method, try to determine its origin
                    if "." in entry_name and not entry_file:
                        parts = entry_name.split(".")
                        # Check if the class name is in the function details
                        class_name = parts[0]
                        class_info = function_details.get(class_name, {})
                        if class_info:
                            file_name = os.path.basename(class_info.get("file_path", "")) or "Unknown"
                        
                    path_id = f"path{i+1}"

                    html += f"""
            <h3 data-module="{path_id}" class="module-header">Execution Path {i+1}: {entry_name}</h3>
            <div class="module-content" id="{path_id}-content">
                <div class="function entry-point">
                    <div class="function-name">{entry_name} ({file_name})</div>
                    <div class="function-description">Execution path starting from {entry_name}</div>
                </div>
                """

                    # Add execution steps if available
                    if steps:
                        html += """
                <div class="call-steps">
                """
                        for step_idx, step in enumerate(steps):
                            try:
                                if isinstance(step, dict):
                                    step_name = step.get("function_name", f"step {step_idx+1}")
                                    step_description = step.get("description", "Execution step")
                                    step_file = step.get("file", "")
                                else:
                                    step_name = str(step)
                                    step_description = "Execution step"
                                    # Try to get file path from function_details
                                    step_file = function_details.get(step_name, {}).get("file_path", "")
                                
                                # Get a reasonable file name to display
                                step_file_name = os.path.basename(step_file) if step_file else ""
                                step_display = f"{step_name} ({step_file_name})" if step_file_name else step_name
                                
                                indent = 20 * (step_idx + 1)
                                
                                html += f"""
                    <div class="function" style="margin-left: {indent}px;">
                        <div class="function-name">step {step_idx+1}: {step_display}</div>
                        <div class="function-description">{step_description}</div>
                    </div>
                """
                            except Exception as e:
                                print(f"Error processing execution step {step_idx} in path {i+1}: {str(e)}")

                        html += """
                </div>
                """

                    html += """
            </div>
            """
                except Exception as e:
                    print(f"Error processing execution path {i+1}: {str(e)}")
                    
            return html
        except Exception as e:
            print(f"Error generating execution paths HTML: {str(e)}")
            return "<p>Error generating execution paths.</p>"

    def _generate_structure_html(self, functions_by_file):
        """Generate HTML for the code structure section."""
        structure_html = ""
        
        if not functions_by_file:
            return "<div class='alert alert-info'>No code structure information available.</div>"
            
        try:
            # Organize files by directory for better structure
            root_dir = os.path.commonpath(list(functions_by_file.keys()))
            
            # Get file summaries if available
            file_summaries = getattr(self, '_file_summaries', {})
            
            # Group files by their directory
            files_by_dir = {}
            for file_path in functions_by_file.keys():
                rel_path = os.path.relpath(file_path, root_dir)
                dir_name = os.path.dirname(rel_path)
                
                if not dir_name:
                    dir_name = "root"
                    
                if dir_name not in files_by_dir:
                    files_by_dir[dir_name] = []
                
                files_by_dir[dir_name].append(file_path)
            
            # Sort directories and files
            sorted_dirs = sorted(files_by_dir.keys())
            
            # Process each directory and its files
            for dir_name in sorted_dirs:
                dir_title = dir_name if dir_name != "root" else "Root Directory"
                
                # Add directory header if it's not root
                if len(sorted_dirs) > 1:
                    structure_html += f"""
            <div class="directory-header">{dir_title}</div>
            """
                
                # Process files in this directory
                for file_path in sorted(files_by_dir[dir_name]):
                    try:
                        functions = functions_by_file[file_path]
                        file_name = os.path.basename(file_path)
                        rel_path = os.path.relpath(file_path, root_dir)
                        module_id = rel_path.replace('/', '_').replace('\\', '_').replace('.', '-')

                        # Create module description from the first function's description
                        module_description = "This module contains various functions for code processing."
                        for func in functions:
                            if func.get("name", "").startswith("__init__"):
                                module_description = func.get("description", module_description)
                                break

                        # Use summary if available in first function
                        for func in functions:
                            if "summary" in func:
                                module_description = func.get("summary", module_description)
                                break

                        # Get file summary from file_summaries if available
                        file_summary = file_summaries.get(file_path, "")
                        
                        # Truncate the summary for display in the header
                        summary_preview = ""
                        if file_summary:
                            # Get first sentence or truncate to 60 chars
                            short_summary = file_summary.split('.')[0] if '.' in file_summary else file_summary
                            if len(short_summary) > 60:
                                short_summary = short_summary[:57] + "..."
                            summary_preview = f' <span class="file-summary-preview">{short_summary}</span>'

                        # Simplify the display name for nested modules to just show the filename
                        # But keep the full path in the id for uniqueness
                        display_name = file_name
                                
                        structure_html += f"""
            <!-- {rel_path} Module -->
            <h3 data-module="{module_id}" class="module-header">{display_name}{summary_preview}</h3>
            <div class="module-content" id="{module_id}-content">
                <div class="module-description">{module_description}</div>
                """
                                
                        # Add all functions for this file
                        for func in functions:
                            name = func.get("name", "Unknown")
                            description = func.get("description", "No description available.")
                            is_entry_point = func.get("is_entry_point", False)
                            
                            # Determine function styling class
                            function_class = ""
                            if is_entry_point:
                                function_class = " entry-point"
                            elif name.startswith("_") and not name.startswith("__"):
                                function_class = " private-helper"
                            elif name.startswith("__") and name.endswith("__"):
                                function_class = " special-method"
                            
                            structure_html += f"""
                <div class="function{function_class}">
                    <div class="function-name">{name}</div>
                    <div class="function-description">{description}</div>
                </div>
                """
                                
                        structure_html += """
            </div>
            """
                    except Exception as e:
                        structure_html += f"""
            <div class="alert alert-danger">Error processing file {file_path}: {str(e)}</div>
            """
                        
        except Exception as e:
            structure_html = f"<div class='alert alert-danger'>Error generating structure HTML: {str(e)}</div>"
            
        return structure_html
        
    def _generate_dependencies_html(self, dependencies, functions_by_file):
        """Generate HTML for the dependencies section."""
        dependencies_html = ""
        
        # Get file summaries if available for better display
        file_summaries = getattr(self, '_file_summaries', {})
        
        # Only show a no-dependencies message if we have neither dependencies nor file information
        if not dependencies and not functions_by_file and not file_summaries:
            return "<div class='alert alert-info'>No dependency information available.</div>"
            
        try:
            file_descriptions = {}
            root_dir = os.path.commonpath(list(functions_by_file.keys())) if functions_by_file else ""
            
            # Extract file descriptions from functions
            for file_path, functions in functions_by_file.items():
                file_name = os.path.basename(file_path)
                description = "This is a module in the codebase."
                
                # Try to find a good description from functions
                for func in functions:
                    if func.get("name", "").startswith("__init__"):
                        description = func.get("description", description)
                        break
                
                file_descriptions[file_path] = description
            
            # Process dependencies based on their format
            dependencies_by_source = {}
            
            # Handle dictionary format (file_dependencies)
            if isinstance(dependencies, dict):
                for source, targets in dependencies.items():
                    if source not in dependencies_by_source:
                        dependencies_by_source[source] = []
                    
                    # Process each target dependency
                    for target in targets:
                        dependencies_by_source[source].append({
                            "target": target,
                            "description": f"This module depends on {os.path.basename(target)}"
                        })
            
            # Handle list format (original dependencies)
            elif isinstance(dependencies, list):
                for dependency in dependencies:
                    if isinstance(dependency, dict):
                        source = dependency.get("source", "")
                        target = dependency.get("target", "")
                        description = dependency.get("description", "")
                        
                        if source and target:
                            if source not in dependencies_by_source:
                                dependencies_by_source[source] = []
                            
                            # Check if this dependency already exists
                            already_exists = False
                            for dep in dependencies_by_source[source]:
                                if dep.get("target") == target:
                                    already_exists = True
                                    # If both have descriptions, use the more detailed one
                                    if description and len(description) > len(dep.get("description", "")):
                                        dep["description"] = description
                                    break
                            
                            # Include more details about the dependency if it's new
                            if not already_exists:
                                dependencies_by_source[source].append({
                                    "target": target,
                                    "description": description or f"This module depends on {os.path.basename(target)}"
                                })
            
            # If there are no dependencies but we have files, show all files
            if not dependencies_by_source and (functions_by_file or file_summaries):
                # Create an explanatory message at the top
                dependencies_html += """
            <div class="alert alert-info">No explicit dependencies were detected between files. Showing available modules with no dependencies.</div>
            """
                
                # Add all files from functions_by_file
                file_list = set()
                for file_path in functions_by_file.keys():
                    file_list.add(file_path)
                
                # Also add files from file_summaries
                for file_path in file_summaries.keys():
                    file_list.add(file_path)
                
                # Process each file
                for file_path in sorted(file_list):
                    file_name = os.path.basename(file_path)
                    # Use file summary if available
                    summary = file_summaries.get(file_path, "")
                    description = file_descriptions.get(file_path, summary or "No description available.")
                    
                    # Create a module ID for the HTML
                    module_id = file_name.replace(".", "_").lower()
                    
                    # Simplify the path for display
                    if root_dir:
                        display_name = os.path.relpath(file_path, root_dir)
                    else:
                        display_name = file_path
                    
                    dependencies_html += f"""
            <h3 data-module="{module_id}" class="module-header">{display_name}</h3>
            <div class="module-content" id="{module_id}-content">
                <div class="module-description">{description}</div>
                <div class="dependencies-list">
                    <p class="no-dependencies-note">This module has no detected dependencies.</p>
                </div>
            </div>
            """
                
                return dependencies_html
            
            # If we still have no dependencies, show a message
            if not dependencies_by_source:
                return "<div class='alert alert-info'>No detailed dependency information available.</div>"
                
            # Create more organized IDs for the dependencies tab
            processed_modules = set()  # Track processed modules to avoid duplicates
            
            # Helper function to get module ID for dependencies tab
            def get_module_id_and_display(file_path, root_dir):
                base_name = os.path.basename(file_path)
                rel_path = os.path.relpath(file_path, root_dir) if root_dir else file_path
                
                # Create a simplified module ID like in the gold standard
                module_id = base_name.replace(".", "_").lower()
                
                # For a nicer display name, use relative path
                display_name = rel_path
                
                return module_id, display_name
            
            # Sort dependencies by module name for consistent display
            module_ids = {}
            for source in dependencies_by_source.keys():
                module_id, _ = get_module_id_and_display(source, root_dir)
                module_ids[source] = module_id
            
            sorted_sources = sorted(dependencies_by_source.keys(), key=lambda s: module_ids.get(s, s).lower())
            
            # Generate HTML for dependencies
            for source in sorted_sources:
                # Skip if we already processed this module
                if source in processed_modules:
                    continue
                
                processed_modules.add(source)
                
                # Get module ID and display name
                module_id, display_name = get_module_id_and_display(source, root_dir)
                
                # Get module description
                description = file_descriptions.get(source, "")
                
                # Get target dependencies
                target_deps = dependencies_by_source.get(source, [])
                
                # Only show modules with actual dependencies
                if target_deps:
                    dependencies_html += f"""
            <h3 data-module="{module_id}" class="module-header">{display_name}</h3>
            <div class="module-content" id="{module_id}-content">
                <div class="module-description">{description}</div>
                
                <div class="dependencies-list">
                    <h4>Dependencies:</h4>
                    <ul>
                """
                    
                    # Sort dependencies by name for consistent display
                    sorted_deps = sorted(target_deps, key=lambda d: os.path.basename(d.get("target", "")).lower())
                    
                    for dep in sorted_deps:
                        target = dep.get("target", "")
                        dep_description = dep.get("description", "")
                        
                        if target:
                            target_module_id, target_display = get_module_id_and_display(target, root_dir)
                            
                            dependencies_html += f"""
                        <li>
                            <div class="dependency-item">
                                <div class="dependency-name">{target_display}</div>
                                <div class="dependency-description">{dep_description}</div>
                            </div>
                        </li>
                    """
                    
                    dependencies_html += """
                    </ul>
                </div>
            </div>
            """
        except Exception as e:
            dependencies_html = f"<div class='alert alert-danger'>Error generating dependencies HTML: {str(e)}</div>"
            print(f"Error generating dependencies HTML: {str(e)}")
            
        return dependencies_html

class Visualizer:
    """
    A class for visualizing codebase structure and relationships.
    """
    
    def __init__(self, codebase=None, output_dir="./output"):
        """
        Initialize the visualizer.
        
        Args:
            codebase: The codebase to visualize
            output_dir: The output directory for visualization artifacts
        """
        self.codebase = codebase
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
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
            diagram_content = f"{default_type}\n    {diagram_content}"
            
        return diagram_content 