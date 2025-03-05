# SourceFlow - Product Requirements Document (PRD)

## 1. Introduction

### 1.1 Purpose
The Code Project Analyzer is an AI-powered application designed to analyze codebases of varying size and complexity, generate visual representations of their structure, and provide insights into their dependencies and execution paths. This tool aims to help developers quickly understand complex codebases and navigate directly to areas requiring fixes or enhancements.

### 1.2 Scope
This document outlines the requirements, architecture, and implementation plan for developing the Code Project Analyzer as a proof of concept. The initial implementation will focus on creating a functional local tool that can process codebases of various languages and generate useful diagrams.

### 1.3 Objectives
- Create an AI-powered tool that can analyze any codebase regardless of programming language
- Generate visual representations of code structure, dependencies, and execution flows
- Help developers quickly understand complex codebases
- Provide a foundation for future enhancements and integrations

## 2. Requirements

### 2.1 Functional Requirements

#### 2.1.1 Core Functionality
- **FR1:** ✅ Recursively traverse directory structures to identify code files
- **FR2:** ✅ Analyze code files to understand functions, classes, inputs, outputs, and dependencies
- **FR3:** ✅ Build relationship maps between code components across files
- **FR4:** ✅ Generate visual diagrams of code structure and relationships
- **FR5:** ✅ Handle large codebases through chunking and hierarchical analysis
- **FR6:** ✅ Support multiple diagram output formats (Graphviz, Mermaid)
- **FR7:** ✅ Generate comprehensive application descriptions to aid new developers

#### 2.1.2 User Interface
- **FR8:** ✅ Accept input for the root directory of a code project
- **FR9:** ✅ Display progress updates during analysis
- **FR10:** ✅ Generate and display or save resulting diagrams
- **FR11:** ✅ Provide error logs and diagnostics for failed analyses
- **FR12:** ✅ Present organized information through an interactive HTML viewer with tabbed interface

### 2.2 Non-Functional Requirements

#### 2.2.1 Performance
- **NFR1:** ✅ Handle codebases of varying sizes through appropriate chunking strategies
- **NFR2:** ✅ Generate results in a reasonable time for proof-of-concept demonstrations

#### 2.2.2 Reliability
- **NFR3:** ✅ Implement retry logic for failed AI analyses
- **NFR4:** ✅ Handle errors gracefully with meaningful error messages
- **NFR5:** ✅ Implement recovery points to allow resuming from failures

#### 2.2.3 Extensibility
- **NFR6:** ⏳ Design for future integration with CI/CD pipelines
- **NFR7:** ✅ Use modular architecture to allow for different visualization outputs
- **NFR8:** ✅ Support extension to additional programming languages

## 3. System Architecture

### 3.1 High-Level Architecture
The Code Project Analyzer follows a pipeline architecture with the following key components:

1. **Directory Explorer** ✅
   - Traverses the directory structure
   - Identifies relevant code files
   - Filters out non-code files and irrelevant directories

2. **Code Analyzer** ✅
   - Reads code files
   - Chunks large files if necessary
   - Sends code to AI agent for analysis
   - Parses and validates AI responses

3. **Relationship Builder** ✅
   - Aggregates analysis results across files
   - Builds cross-file dependency and call graphs
   - Identifies entry points and major execution paths

4. **Visualization Generator** ✅
   - Constructs graph representations
   - Generates multiple output formats (Graphviz, Mermaid)
   - Organizes visual elements for clarity
   - Generates comprehensive application descriptions
   - Creates interactive HTML viewer with tabbed interface

5. **Orchestrator** ✅
   - Manages the overall analysis workflow
   - Handles errors and retries
   - Tracks progress and reports status

### 3.2 Component Details

#### 3.2.1 Directory Explorer ✅
- Uses Python's `os.walk` to recursively traverse directories
- Configurable file extensions and directory exclusion patterns
- Extensible to support additional filtering criteria

#### 3.2.2 Code Analyzer ✅
- Uses OpenAI's API for code analysis
- Implements token counting and chunking strategies
- Uses standardized JSON schema for AI responses
- Multiple fallback prompts for robust analysis

#### 3.2.3 Relationship Builder ✅
- Builds in-memory graph representations of code relationships
- Resolves cross-file references and dependencies
- Implements heuristics for identifying entry points
- Supports hierarchical aggregation of relationships

#### 3.2.4 Visualization Generator ✅
- Primary support for Graphviz and Mermaid
- Extensible interface for additional visualization formats
- Configurable visual styling and layout options
- Generates comprehensive application descriptions using OpenAI
- Creates interactive HTML viewer with tabs for different visualization aspects

#### 3.2.5 Orchestrator ✅
- Implements workflow control and sequencing
- Error handling and retry logic
- Progress tracking and reporting
- Configurable analysis parameters

## 4. Implementation Status

### 4.1 Completed Items ✅
- Basic framework setup (project structure, dependencies)
- Directory traversal and file identification
- AI agent integration with OpenAI API
- JSON parsing and robust error handling
- Cross-file relationship building
- Graphviz and Mermaid visualization support
- Command-line interface
- Environment variable configuration (.env support)
- Basic performance optimizations
- Error handling and retry logic
- Enhanced visualization styling for improved readability
- Better diagram annotations and relationship type labeling
- Color-coded visual hierarchy for different node types
- Legends explaining diagram elements
- Optimized Mermaid diagram rendering with simplified styling
- Interactive HTML viewers for diagrams
- Deterministic node name sanitization for reliable testing
- Robust visualization output testing against gold standards
- Application description generation for codebase overview
- Description tab in HTML viewer with markdown rendering
- Improved markdown formatting for better readability
- Node limiting for dependency diagrams to prevent rendering errors
- Regeneration of diagrams from existing analysis data without rerunning analysis
- Integration of application description generation into main analysis flow

### 4.2 In Progress Items ⏳
- Additional visualization customization options

### 4.3 Future Enhancements 🔮
- Parallel processing for faster analysis
- Caching mechanism improvements
- Integration with version control systems
- Differential analysis between versions
- IDE plugins for real-time analysis
- Enhanced module descriptions and auto-documentation

## 5. Technical Specifications

### 5.1 Development Environment
- Language: Python 3.8+
- Dependencies:
  - openai
  - graphviz
  - pyyaml (for configuration)
  - tiktoken (for token counting)
  - pytest (for testing)
  - python-dotenv (for environment variables)
  - markdown (for rendering application descriptions)

### 5.2 AI Integration
- API: OpenAI API (GPT-4 or custom model specified in .env)
- Authentication: API key via environment variable or .env file
- Default model: Set in .env file (defaults to gpt-4o-mini)
- Fallback models: Configurable via environment variables
- Application description generation using OpenAI model specified in environment

### 5.3 File Handling
- Supported file extensions: .py, .js, .java, .cpp, .c, .go, .rs, .rb
- Excluded directories: .git, node_modules, venv, .env, __pycache__
- Maximum file size for single analysis: Based on token limits of the model
- Chunking threshold: 6000 tokens (configurable)

### 5.4 Visualization
- Primary formats: PNG (Graphviz), SVG (Graphviz), Markdown (Mermaid)
- Optional format: HTML (interactive)
- Diagram styling:
  - Functions/methods: Boxes
  - Classes: Rounded rectangles
  - Entry points: Double circles / green background
  - Private helper functions: Dashed borders
  - Module headers: Bold styling with descriptions
  - Dependencies: Dashed arrows with "imports" labels
  - Call relationships: Solid arrows with "calls" labels
  - Layout: Left-to-right for better space utilization
  - Text: HTML formatting with proper wrapping for readability
- Mermaid diagrams:
  - Simplified CSS styling to prevent conflicts with Mermaid's internal rendering
  - Minimal style overrides for better natural rendering
  - Responsive diagram sizing
  - Interactive pan and zoom capabilities
  - Automatic complexity detection and adjustment
  - Node limiting for large codebases to prevent rendering errors
- Interactive HTML viewer:
  - Tabbed interface for Code Structure, Dependencies, Execution Paths, and Description
  - Search functionality to filter components
  - Expandable/collapsible modules for better navigation
  - Responsive design for different screen sizes
  - Markdown rendering for application descriptions with syntax highlighting

### 5.5 Application Description Generation
- Comprehensive overview of analyzed application
- Generated using OpenAI model specified in environment
- Markdown formatting for better readability
- Sections include:
  - Purpose and overview of application
  - Core functionality
  - Main components
  - Architecture
  - Key execution flows
  - Implementation focus areas for new developers
- Displayed in a dedicated tab within the HTML viewer
- Properly formatted with code highlighting
- Automatically generated as part of the main analysis flow (can be disabled with `--no-description` flag)

### 5.6 Error Handling
- Retry attempts: 3 per file (configurable)
- Fallback strategies:
  - Alternative prompting
  - Increased chunking
  - Simplified request (functions only, then relationships)
- Error logging: Detailed logs with file context and error specifics

## 6. Testing Strategy

### 6.1 Unit Testing
- Test individual components (directory traversal, JSON parsing, etc.)
- Mock AI responses for deterministic testing
- Test error handling and retry logic

### 6.2 Integration Testing
- Test end-to-end workflow with small codebases
- Verify correct relationship mapping
- Validate diagram generation

### 6.3 Visualization Testing
- Compare generated visualizations against gold standard files
- Test deterministic node naming and sanitization
- Ensure visualization output is consistent and reliable
- Use direct Mermaid file comparisons for robust testing
- Allow for reasonable whitespace and formatting differences

### 6.4 Test Datasets
- Small Python project (< 10 files)
- Medium mixed-language project (20-50 files)
- Open-source project samples for realistic testing

## 7. Future Enhancements

### 7.1 Short-term Enhancements (Next Sprint)
- ✅ Enhanced diagram readability with better module/function descriptions
- ✅ Visual differentiation between different types of functions/methods
- ✅ Relationship type labeling on connectors
- ✅ Flow direction annotation showing typical data flow
- ✅ Legend to explain diagram elements
- ✅ Improved Mermaid diagrams with simplified styling for better rendering
- ✅ Application description generation for codebase overview
- ✅ Interactive HTML viewer with tabbed interface including Description tab
- ✅ Node limiting for dependency diagrams to prevent rendering errors
- ✅ Regeneration of diagrams from existing analysis data
- ✅ Integration of application description generation into main analysis flow
- Parallel processing for faster analysis
- Caching of analysis results

### 7.2 Medium-term Enhancements
- Interactive web-based viewer
- Integration with version control systems
- Differential analysis (changes between versions)
- Export to additional formats (UML, etc.)
- Configurable visualization styles

### 7.3 Long-term Vision
- CI/CD pipeline integration
- IDE plugins for real-time analysis
- Collaborative sharing and annotation
- Analysis recommendation engine
- Fine-tuned models for code analysis

## 8. Appendix

### 8.1 Glossary
- **AI Agent**: An LLM-based component that analyzes code files
- **Chunking**: Breaking large files into smaller pieces for analysis
- **Entry Point**: A function or method where execution begins
- **Graphviz**: A graph visualization software
- **Mermaid**: A JavaScript-based diagramming and charting tool
- **Application Description**: A comprehensive overview of the codebase generated by AI

### 8.2 References
- OpenAI API Documentation
- Graphviz Documentation
- Mermaid Documentation
- Markdown Documentation

### 8.3 Implementation Notes
- The system falls back to generating only Mermaid diagrams when Graphviz is not installed
- Configuration through environment variables allows for easy customization
- API response parsing includes robust error handling to manage various potential failure modes
- Environment variable configuration via .env file simplifies setup and customization
- Visualization improvements include color-coding, legends, relationship labels, and HTML formatting for readability
- Application descriptions are generated using the OPENAI_MODEL specified in the .env file
- Markdown rendering includes extensions for improved code formatting
- Application description generation is automatically included in the main analysis flow, with an option to disable it using the `--no-description` flag
- Application description generation is also available through the regenerate_diagrams.py script with the `--generate-description` flag
- Node limiting is implemented to prevent rendering errors in large diagrams 