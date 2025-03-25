# Code Project Analyzer

An AI-powered application that analyzes code projects, generates visual representations of their structure, and provides insights into dependencies and execution paths.

## Features

- **Language Agnostic Analysis**: Works with Python, JavaScript, Java, C/C++, and more
- **Multiple Visualization Types**:
  - Function call diagrams
  - File dependency diagrams
  - Execution path diagrams
- **Visualization Formats**:
  - Graphviz (PNG, SVG, PDF)
  - Mermaid (Markdown)
  - Interactive HTML Viewer with tabbed interface
- **Analysis Caching**: Save and reuse analysis results
- **Application Description**: AI-generated overview of the codebase
- **Customizable**: Configure via environment variables

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sourceflow.git
   cd sourceflow
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   ```bash
   cp .env.template .env
   ```
   
4. Edit the `.env` file with your OpenAI API key and preferred model:
   ```
   OPENAI_API_KEY=your_api_key_here
   OPENAI_MODEL=gpt-4o-mini  # or another compatible model
   ```

## Usage

### Most Common Use Case: Generate Interactive HTML Viewer

Analyze a project directory and generate an interactive HTML viewer (the simplest way to visualize your code):

```bash
python run_analyzer.py /path/to/your/project --output-dir /path/to/output --html-only
```

This will:
1. Analyze the codebase (or use cached analysis if available)
2. Generate an interactive HTML viewer with tabbed interface containing:
   - Code structure diagram (function calls)
   - Dependency diagram
   - Execution path diagram
   - AI-generated application description

### Basic Usage

Analyze a project directory and generate all visualization formats:

```bash
python run_analyzer.py /path/to/your/project
```

### Options

- `--output-dir`, `-o`: Specify custom output directory
- `--formats`, `-f`: Choose output formats (png, svg, pdf, mermaid, html)
- `--skip-analysis`, `-s`: Skip analysis if results exist
- `--html-only`: Generate only the interactive HTML viewer (implies --skip-analysis if analysis data exists)
- `--no-description`: Skip generating the application description

### Examples

Analyze a project and save results to a specific directory:
```bash
python run_analyzer.py /path/to/your/project -o ./my_analysis_results
```

Generate only Mermaid diagrams:
```bash
python run_analyzer.py /path/to/your/project -f mermaid
```

Reuse existing analysis to generate new visualizations:
```bash
python run_analyzer.py /path/to/your/project -s
```

Generate only HTML output:
```bash
python run_analyzer.py /path/to/your/project --html-only
```

### Regenerating Diagrams

You can regenerate diagrams from existing analysis data without rerunning the analysis using the `regenerate_diagrams.py` script:

```bash
python regenerate_diagrams.py /path/to/analysis_data.json --output-dir ./new_diagrams
```

Options:
- `--output-dir`, `-o`: Directory to save generated diagrams
- `--max-nodes`, `-m`: Maximum number of nodes to include in dependency diagrams
- `--generate-description`, `-g`: Generate an application description

## Implementation Status

The Code Project Analyzer has now reached a fully functional end-to-end state:

✅ **Directory Traversal**: Successfully identifies and filters code files  
✅ **AI-Powered Analysis**: Analyzes functions, dependencies, and relationships  
✅ **Relationship Building**: Builds cross-file dependency and call graphs  
✅ **Visualization Generation**: Creates multiple diagram types with Mermaid support  
✅ **Interactive Viewer**: HTML-based viewer with tabbed interface for all diagram types  
✅ **Application Description**: AI-generated overview of the codebase  
✅ **Error Handling**: Robust error recovery and fallback options  
✅ **API Integration**: Uses environment variables for custom API key and model  

Current performance: Analysis of 8 Python files completed in approximately 50 seconds with GPT-4o-mini.

## Next Planned Enhancements

Our priority enhancements for the next iteration:

⭐ **Parallel Processing**: Speed up analysis with concurrent processing  
⭐ **Caching Improvements**: Better caching of analysis results  
⭐ **VCS Integration**: Integration with version control systems  
⭐ **Differential Analysis**: Analyze changes between code versions  
⭐ **IDE Plugins**: Integration with popular IDEs  

## How It Works

1. **Directory Exploration**: Recursively traverses the project directory to identify code files
2. **Code Analysis**: Uses AI (via OpenAI API) to analyze each file's functions, classes, dependencies
3. **Relationship Building**: Aggregates analysis across files to build a comprehensive model
4. **Visualization**: Generates visual diagrams showing code structure and relationships
5. **Description Generation**: Creates a comprehensive overview of the codebase

## Project Structure

- `sourceflow/core/`: Core modules
  - `explorer.py`: Directory traversal and file identification
  - `analyzer.py`: Code analysis with AI
  - `builder.py`: Relationship building between code components
  - `visualizer.py`: Diagram generation
- `sourceflow/main.py`: Orchestrator module
- `run_analyzer.py`: Entry point script
- `regenerate_diagrams.py`: Utility for regenerating diagrams from existing analysis

## Requirements

- Python 3.8+
- OpenAI API key
- Graphviz (optional, for PNG/SVG diagram generation)
  - If Graphviz is not installed, only Mermaid diagrams will be generated
  - To install Graphviz:
    - macOS: `brew install graphviz`
    - Ubuntu/Debian: `apt-get install graphviz`
    - Windows: Download from [Graphviz website](https://graphviz.org/download/)

## License

[MIT License](LICENSE) 