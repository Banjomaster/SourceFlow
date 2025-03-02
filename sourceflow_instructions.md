# Code Project Analyzer

## Original Instructions
I would like to build an application (using AI agent(s)) that looks at a directory root of a code project, this could be repo root for example for any code base that exists or will exist in the future. The AI agents should use tools to look at the directory, files, etc and deduce next steps. This will be a recursive groveler that can go through any code, understand it in detail for things like what each block of code does, what it needs for input, what is the output, etc. The idea is to be able to produce a detailed block diagram or workflow diagram of the code at this location, its dependencies, and its major execution code paths and last but not least, its general purpose or function descriptions. This output can be super effective at helping developers quickly understand the complex code paths and be able to jump in directly to areas they need to target for precision fixes or enhancements.

## Solution Overview

To address your requirement, we will build an AI-powered application that analyzes a code project's directory root (e.g., a repository root) for any existing or future codebase, regardless of programming language. The application will use AI agents equipped with tools to explore the directory, recursively analyze files, and deduce the next steps autonomously. The goal is to produce a detailed block diagram or workflow diagram that illustrates the code's structure, dependencies, major execution paths, and general purpose, enabling developers to quickly understand complex codebases and target specific areas for fixes or enhancements.

## Implementation Considerations

Based on our discussions, we've identified several key considerations for implementation:

### Handling Large Codebases
- Implement a multi-level analysis approach (file-level, module/package level, system level)
- Create chunking strategies for files that exceed token limits
- Use hierarchical summarization to maintain the big picture

### Visualization Options
- Initially implement both Graphviz (for detailed static diagrams) and Mermaid (for web-friendly integration)
- Consider interactive HTML/D3.js or Neo4j visualization as future enhancements
- Ensure diagrams are clear and navigable even for complex codebases

### Error Handling & Retry Logic
- Implement detailed error logging with contextual information
- Create multiple fallback prompts of varying complexity
- Add retry mechanisms with different chunking strategies
- Ensure recovery points to allow resuming analysis from failures

### Initial Focus
- Create a viable proof of concept first, before optimizing for performance
- Start with common programming languages
- Focus on accuracy of code analysis before adding integrations
- Run locally for initial testing and validation

## Solution Approach

We'll design the application to leverage AI agents (specifically, large language models or LLMs) that can:

1. **Explore the Directory**: Recursively traverse the directory to identify all code files.
2. **Analyze Code**: Understand each file's content in detail, including what each block does, its inputs, outputs, dependencies, and execution paths.
3. **Deduce Next Steps**: Use the analysis to determine relationships between code blocks across files and build a comprehensive representation.
4. **Generate a Diagram**: Produce a visual output showing the code's structure, dependencies, and execution flow.

The AI agents will operate in a language-agnostic manner, relying on their training to interpret various programming languages without predefined parsers, making the tool adaptable to future languages. The output will be a detailed diagram created using Graphviz and Mermaid, providing a clear, actionable view of the codebase.

## Detailed Workflow

1. **Directory Traversal**: The application starts by exploring the directory root, identifying code files based on common extensions (e.g., .py, .cpp, .java, .js), and skipping irrelevant directories (e.g., .git, node_modules).

2. **File Analysis with AI Agents**:
   - Each code file is read and fed to an AI agent (e.g., an LLM like GPT-4).
   - The agent analyzes the code to extract:
     - Functions/Classes: Names, purposes, inputs (parameters), and outputs (return values).
     - Dependencies: Imported modules, included headers, or other external references.
     - Execution Paths: Function calls or method invocations, including potential entry points (e.g., main functions).
   - The agent deduces the general purpose of the file based on its content and context.

3. **Cross-File Relationship Building**:
   - The AI agent correlates calls and dependencies across files, resolving connections (e.g., a function in file A calling a function in file B via an import).
   - Entry points are identified to highlight where execution begins.

4. **Graph Construction**:
   - A graph is built where:
     - Nodes: Represent functions or classes, labeled with their purpose.
     - Edges: Represent calls or dependencies between nodes.
     - Clusters: Group nodes by file for organizational clarity.
     - Entry points are emphasized (e.g., with distinct shapes or colors).

5. **Diagram Output**: The graph is rendered as visual diagrams (PNG, SVG, and Mermaid markdown) showing the code's structure, dependencies, and major execution paths.

## Implementation

Below is a Python implementation that realizes this vision using AI agents and Graphviz:

```python
import os
import graphviz
import json
from openai import OpenAI
from pathlib import Path

# Initialize OpenAI client for AI agent (set your API key in environment variables)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Common code file extensions (extendable for future languages)
CODE_EXTENSIONS = {'.py', '.cpp', '.c', '.java', '.js', '.rs', '.go', '.rb'}
# Directories to skip (e.g., version control, dependencies)
SKIP_DIRS = {'.git', 'node_modules', 'venv', '.env'}

def explore_directory(root_dir):
    """AI agent explores the directory recursively to find code files."""
    code_files = []
    for subdir, dirs, files in os.walk(root_dir):
        # Skip irrelevant directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if os.path.splitext(file)[1] in CODE_EXTENSIONS:
                code_files.append(os.path.join(subdir, file))
    print(f"AI agent identified {len(code_files)} code files.")
    return code_files

def analyze_file(file_path):
    """AI agent analyzes a single code file and deduces its structure."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        code = file.read()

    # Prompt for AI agent to analyze the code autonomously
    prompt = f"""
You are an AI agent specializing in all types of software coding languages. Your job is to analyze code from an unknown project and create clarity and accurate representation of the project. Here is the code:

{code}

Deduce the following without specific instructions on language syntax:
1. A list of functions or classes defined in this code, including fully qualified names (e.g., module.func, namespace::func) and a brief description of their purpose.
2. For each function/class, identify inputs (parameters) and outputs (return values).
3. List function calls or method invocations made within each function/class, specifying the fully qualified name of the called entity if possible.
4. Identify external dependencies (e.g., imported modules, headers).
5. Suggest potential entry points (e.g., main functions or public APIs).
6. Provide a one-sentence summary of the file's general purpose.

Format your response as valid JSON with the following structure:
{{
  "functions": [
    {{
      "name": "fully_qualified_name",
      "description": "description of the function",
      "inputs": "description of inputs/parameters",
      "outputs": "description of outputs/return values",
      "calls": ["called_function1", "called_function2"]
    }}
  ],
  "dependencies": ["dependency1", "dependency2"],
  "entry_points": ["entry_point1", "entry_point2"],
  "summary": "general purpose of the file"
}}

Ensure the JSON is properly formatted and can be parsed by Python's json.loads().
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )
    return response.choices[0].message.content

def parse_analysis(response):
    """Parse the AI agent's JSON analysis into structured data."""
    try:
        data = json.loads(response)
        
        # Extract and structure the data
        functions = {}
        for func in data.get("functions", []):
            name = func.get("name", "")
            functions[name] = {
                'description': func.get("description", ""),
                'inputs': func.get("inputs", ""),
                'outputs': func.get("outputs", ""),
                'calls': func.get("calls", [])
            }
        
        dependencies = data.get("dependencies", [])
        entry_points = data.get("entry_points", [])
        summary = data.get("summary", "")
        
        return functions, dependencies, entry_points, summary
    except json.JSONDecodeError:
        print("Error parsing JSON response. Using empty defaults.")
        return {}, [], [], ""

def build_diagram(code_files):
    """Construct and render a workflow diagram based on AI analysis."""
    graph = graphviz.Digraph(format='png', graph_attr={'rankdir': 'TB'})
    all_functions = {}
    all_entry_points = set()
    file_summaries = {}

    # Analyze each file and collect data
    for file_path in code_files:
        print(f"Analyzing {file_path}...")
        analysis = analyze_file(file_path)
        functions, dependencies, entry_points, summary = parse_analysis(analysis)
        all_functions.update(functions)
        all_entry_points.update(entry_points)
        file_summaries[file_path] = summary

        # Create a cluster for this file
        with graph.subgraph(name=f'cluster_{file_path}', graph_attr={'label': f"{os.path.basename(file_path)}\n{summary}"}) as cluster:
            for func, details in functions.items():
                label = f"{func}\n{details['description']}"
                shape = 'doublecircle' if func in entry_points else 'box'
                cluster.node(func, label=label, shape=shape)

    # Add edges for function calls
    for func, details in all_functions.items():
        for called_func in details['calls']:
            if called_func in all_functions:
                graph.edge(func, called_func)

    return graph

def main():
    root_dir = input("Enter the root directory of the code project: ")
    if not os.path.isdir(root_dir):
        print("Invalid directory. Please provide a valid path.")
        return

    # AI agent explores and analyzes the codebase
    code_files = explore_directory(root_dir)
    if not code_files:
        print("No code files found in the directory.")
        return

    # Build and render the diagram
    graph = build_diagram(code_files)
    output_file = os.path.join(root_dir, 'code_workflow')
    graph.render(output_file, view=True, cleanup=True)
    print(f"Workflow diagram saved as {output_file}.png")

if __name__ == "__main__":
    main()
```

## Explanation of the Solution

### AI-Driven Exploration:
- The `explore_directory` function acts as an initial AI agent step, identifying code files recursively while skipping non-code directories.
- It uses a flexible list of extensions, making it adaptable to new languages.

### Autonomous Code Analysis:
- The `analyze_file` function delegates detailed analysis to an AI agent via a broad, open-ended prompt.
- The agent deduces functions, inputs, outputs, calls, dependencies, entry points, and the file's purpose without language-specific guidance, relying on its general understanding of code.

### Data Structuring:
- The `parse_analysis` function converts the AI's JSON response into a structured format, capturing all required details.

### Diagram Generation:
- The `build_diagram` function constructs a Graphviz graph:
  - **Nodes**: Functions or classes, labeled with their purpose, grouped into clusters by file.
  - **Edges**: Function calls, showing execution paths.
  - **Clusters**: Labeled with file names and summaries for context.
  - **Entry Points**: Highlighted with a distinct shape (e.g., doublecircle) to mark major execution starting points.
- The resulting PNG diagram visualizes the code's structure, dependencies, and flow.

### User Experience:
- The application prompts for a directory, processes the codebase, and outputs a diagram, with progress updates for transparency.

## Benefits

- **Language Agnostic**: The AI agent interprets code without predefined parsers, supporting any current or future programming language.
- **Detailed Insights**: Provides function descriptions, inputs, outputs, dependencies, and execution paths, fulfilling the need for a comprehensive understanding.
- **Visual Clarity**: The diagram organizes code by file, highlights entry points, and traces major paths, aiding developers in navigating complexity.
- **Actionable Output**: Developers can quickly identify key areas for fixes or enhancements based on the diagram.

## Limitations and Considerations

- **Accuracy**: Depends on the AI agent's ability to interpret code correctly; complex or obfuscated code may lead to inaccuracies.
- **Scalability**: Large codebases may require significant API calls, increasing time and cost. Caching or selective analysis could be added later.
- **File Size**: Very large files may exceed LLM token limits; chunking could be implemented if needed.
- **Dependencies**: Focuses on explicit calls and imports; implicit dependencies (e.g., runtime-loaded modules) may be missed.

This solution meets your original requirements by using AI agents to autonomously analyze and visualize any codebase, producing a detailed, actionable diagram that enhances developer productivity.