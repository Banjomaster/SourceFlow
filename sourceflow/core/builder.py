"""
Relationship Builder Module

This module is responsible for aggregating analysis results across files, 
building cross-file dependency and call graphs, and identifying entry points 
and major execution paths.
"""

from typing import Dict, List, Set, Any, Tuple

class RelationshipBuilder:
    """
    A class for building relationships between code components across files.
    """
    
    def __init__(self):
        """
        Initialize the RelationshipBuilder.
        """
        self.all_functions = {}  # Maps function name to its details
        self.all_dependencies = set()  # All external dependencies
        self.all_entry_points = set()  # All entry points
        self.file_summaries = {}  # Maps file paths to their summaries
        self.call_graph = {}  # Maps function names to the list of functions they call
        self.reverse_call_graph = {}  # Maps function names to functions that call them
    
    def add_file_analysis(self, file_path: str, analysis: Dict[str, Any]) -> None:
        """
        Add a file's analysis results to the relationship builder.
        
        Args:
            file_path: Path to the analyzed file.
            analysis: The analysis result for the file.
        """
        # Store the file summary
        summary = analysis.get("summary", "No summary available")
        self.file_summaries[file_path] = summary
        
        # Add dependencies
        deps = analysis.get("dependencies", [])
        self.all_dependencies.update(deps)
        
        # Add entry points
        entry_points = analysis.get("entry_points", [])
        self.all_entry_points.update(entry_points)
        
        # Process functions
        functions = analysis.get("functions", [])
        for func_data in functions:
            # If functions is a list of dicts, process accordingly
            if isinstance(func_data, dict):
                func_name = func_data.get("name", "unknown")
                # Store full function details with file path
                self.all_functions[func_name] = {
                    "description": func_data.get("description", ""),
                    "inputs": func_data.get("inputs", ""),
                    "outputs": func_data.get("outputs", ""),
                    "calls": func_data.get("calls", []),
                    "file_path": file_path
                }
                
                # Update call graph
                self.call_graph[func_name] = func_data.get("calls", [])
                
                # Update reverse call graph
                for called_func in func_data.get("calls", []):
                    if called_func not in self.reverse_call_graph:
                        self.reverse_call_graph[called_func] = []
                    self.reverse_call_graph[called_func].append(func_name)
    
    def get_function_details(self, func_name: str) -> Dict[str, Any]:
        """
        Get details for a specific function.
        
        Args:
            func_name: The name of the function to get details for.
            
        Returns:
            A dictionary with the function's details.
        """
        return self.all_functions.get(func_name, {})
    
    def get_functions_by_file(self, file_path: str) -> List[str]:
        """
        Get all functions defined in a specific file.
        
        Args:
            file_path: The path to the file.
            
        Returns:
            A list of function names defined in the file.
        """
        return [
            func_name for func_name, details in self.all_functions.items()
            if details.get("file_path") == file_path
        ]
    
    def get_function_callers(self, func_name: str) -> List[str]:
        """
        Get all functions that call a specific function.
        
        Args:
            func_name: The name of the function to get callers for.
            
        Returns:
            A list of function names that call the specified function.
        """
        return self.reverse_call_graph.get(func_name, [])
    
    def get_function_callees(self, func_name: str) -> List[str]:
        """
        Get all functions called by a specific function.
        
        Args:
            func_name: The name of the function to get callees for.
            
        Returns:
            A list of function names called by the specified function.
        """
        return self.call_graph.get(func_name, [])
    
    def get_entry_point_paths(self) -> List[List[str]]:
        """
        Get the major execution paths starting from entry points.
        
        Returns:
            A list of paths (each being a list of function names) starting from entry points.
        """
        paths = []
        for entry_point in self.all_entry_points:
            if entry_point in self.all_functions:
                path = self._trace_path_from(entry_point, set())
                if path:
                    paths.append(path)
        return paths
    
    def _trace_path_from(self, func_name: str, visited: Set[str]) -> List[str]:
        """
        Trace a path starting from a specific function.
        
        Args:
            func_name: The name of the function to start tracing from.
            visited: A set of already visited function names to avoid cycles.
            
        Returns:
            A list of function names forming a path from the specified function.
        """
        if func_name in visited:
            return []  # Avoid cycles
        
        visited.add(func_name)
        path = [func_name]
        
        # Get callees that exist in our function list (to exclude external calls)
        callees = [
            callee for callee in self.get_function_callees(func_name)
            if callee in self.all_functions
        ]
        
        for callee in callees:
            sub_path = self._trace_path_from(callee, visited.copy())
            if sub_path:
                return path + sub_path
        
        return path
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the analysis results.
        
        Returns:
            A dictionary with summary information.
        """
        # Organize functions by file
        functions_by_file = {}
        for func_name, details in self.all_functions.items():
            file_path = details.get('file_path', '')
            if file_path:
                if file_path not in functions_by_file:
                    functions_by_file[file_path] = []
                functions_by_file[file_path].append(func_name)
        
        # Create file dependencies map (what files each file depends on)
        file_dependencies = {}
        for file_path in self.file_summaries:
            file_dependencies[file_path] = []
            
        for func_name, details in self.all_functions.items():
            file_path = details.get('file_path', '')
            if file_path and func_name in self.call_graph:
                for called_func in self.call_graph[func_name]:
                    if called_func in self.all_functions:
                        called_file = self.all_functions[called_func].get('file_path', '')
                        if called_file and called_file != file_path and called_file not in file_dependencies[file_path]:
                            file_dependencies[file_path].append(called_file)
        
        return {
            "total_files": len(self.file_summaries),
            "total_functions": len(self.all_functions),
            "total_dependencies": len(self.all_dependencies),
            "entry_points": list(self.all_entry_points),
            "execution_paths": self.get_entry_point_paths(),
            # Additional data needed by visualizer
            "function_details": self.all_functions,
            "file_functions": functions_by_file,
            "function_calls": self.call_graph,
            "file_dependencies": file_dependencies,
            "file_summaries": self.file_summaries,
            "entry_point_paths": self.get_entry_point_paths()
        } 