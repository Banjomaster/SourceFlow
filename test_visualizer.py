#!/usr/bin/env python3

import os
import sys

# Add the parent directory to the path so we can import the sourceflow package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sourceflow.core.visualizer import Visualizer

class DummyModule:
    def __init__(self, name, imports=None):
        self.name = name
        self.imports = imports or []

class DummyCodebase:
    def __init__(self):
        # Create some dummy modules
        self.modules = [
            DummyModule("main", ["utils", "database"]),
            DummyModule("utils", ["database"]),
            DummyModule("database"),
            DummyModule("api.routes", ["api.controllers", "database"]),
            DummyModule("api.controllers", ["database", "utils"])
        ]
        
        # Add some dummy entry points
        self.entry_points = ["main.py", "api/server.py"]
        
        # Add some dummy function calls
        self.function_calls = {
            "main.py": ["initialize_app", "connect_to_database", "start_server"],
            "api/server.py": ["setup_routes", "start_listening"]
        }

def main():
    # Create a dummy codebase
    codebase = DummyCodebase()
    
    # Create a visualizer
    visualizer = Visualizer(codebase, output_dir="./test_output")
    
    # Generate the visualization
    output_path = visualizer.visualize_codebase(output_name="test_visualization")
    
    print(f"Visualization generated at: {output_path}")

if __name__ == "__main__":
    main() 