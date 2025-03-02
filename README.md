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
- **Analysis Caching**: Save and reuse analysis results
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
   OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo
   ```

## Usage

### Basic Usage

Analyze a project directory and generate visualizations:

```bash
python run_analyzer.py /path/to/your/project
```

### Options

- `--output-dir`, `-o`: Specify custom output directory
- `--formats`, `-f`: Choose output formats (png, svg, pdf, mermaid)
- `--skip-analysis`, `-s`: Skip analysis if results exist

### Examples

Analyze a project and save results to a specific directory:
```bash
python run_analyzer.py /path/to/your/project -o ./my_analysis_results
```

Generate only PNG and Mermaid diagrams:
```bash
python run_analyzer.py /path/to/your/project -f png mermaid
```

Reuse existing analysis to generate new visualizations:
```bash
python run_analyzer.py /path/to/your/project -s
```

## How It Works

1. **Directory Exploration**: Recursively traverses the project directory to identify code files
2. **Code Analysis**: Uses AI (via OpenAI API) to analyze each file's functions, classes, dependencies
3. **Relationship Building**: Aggregates analysis across files to build a comprehensive model
4. **Visualization**: Generates visual diagrams showing code structure and relationships

## Project Structure

- `sourceflow/core/`: Core modules
  - `explorer.py`: Directory traversal and file identification
  - `analyzer.py`: Code analysis with AI
  - `builder.py`: Relationship building between code components
  - `visualizer.py`: Diagram generation
- `sourceflow/main.py`: Orchestrator module
- `run_analyzer.py`: Entry point script

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