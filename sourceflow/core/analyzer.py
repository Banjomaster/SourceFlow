"""
Code Analyzer Module

This module is responsible for analyzing code files, chunking large files if necessary,
sending code to the AI agent for analysis, and parsing/validating AI responses.
"""

import os
import json
import tiktoken
from typing import Dict, List, Tuple, Any, Optional
from openai import OpenAI
import time
from dotenv import load_dotenv
import ast
import re

# Load environment variables from .env file
load_dotenv()

# Default model to use for analysis (now loaded from environment variable if available)
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Default token limit for a single analysis (conservative estimate)
DEFAULT_TOKEN_LIMIT = 6000

class CodeAnalyzer:
    """
    A class for analyzing code files using AI.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        token_limit: int = DEFAULT_TOKEN_LIMIT,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize the CodeAnalyzer with the specified settings.
        
        Args:
            api_key: OpenAI API key. If None, will look for OPENAI_API_KEY environment variable.
            model: The model to use for code analysis. If None, will look for OPENAI_MODEL environment variable.
            token_limit: The maximum number of tokens to send in a single analysis request.
            max_retries: Maximum number of retry attempts for failed analyses.
            retry_delay: Delay between retry attempts in seconds.
        """
        # Get API key from parameter, environment variable or .env file
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as OPENAI_API_KEY environment variable in .env file")
            
        # Get model from parameter, environment variable or .env file
        self.model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        
        self.client = OpenAI(api_key=self.api_key)
        self.token_limit = token_limit
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.encoding = tiktoken.encoding_for_model(self.model)
        
        print(f"Analyzer initialized with model: {self.model}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for.
            
        Returns:
            The number of tokens in the text.
        """
        return len(self.encoding.encode(text))
    
    def _create_prompt(self, code: str) -> str:
        """
        Create the prompt for the AI agent.
        
        Args:
            code: The code to analyze.
            
        Returns:
            The prompt for the AI agent.
        """
        return f"""
You are an AI agent specializing in code analysis. Your task is to examine the following code and extract clear and accurate structured information about it.

CODE TO ANALYZE:
```
{code}
```

INSTRUCTIONS:
Analyze this code and extract the following information:
1. Functions or classes defined in this code with their detailed descriptions
2. Look for and extract inputs (parameters) and outputs (return values) for each function/class
3. Function calls made within each function/class
4. External dependencies (imported modules, libraries, etc.)
5. Potential entry points (main functions, public APIs)
6. A concise summary of the file's purpose

IMPORTANT FOR FILE SUMMARY:
- Be direct and concise when writing the file summary
- Do NOT start with phrases like "This module...", "This script...", "This file..."
- Focus only on the core functionality or purpose
- Examples:
  * Instead of "This script regenerates diagrams from existing analysis data", write "Regenerates diagrams from existing analysis data"
  * Instead of "This module handles directory traversal", write "Directory traversal and file identification"
  * Instead of "This file contains the CLI entry point", write "CLI entry point for running SourceFlow app"

Your response must be ONLY a valid JSON object with the following structure:
{{
  "functions": [
    {{
      "name": "function_name",
      "description": "what this function does",
      "inputs": "description of parameters",
      "outputs": "description of return values",
      "calls": ["function_call1", "function_call2"]
    }}
  ],
  "dependencies": ["dependency1", "dependency2"],
  "entry_points": ["entry_point1", "entry_point2"],
  "summary": "concise file purpose without 'This module/script/file...' phrasing"
}}

IMPORTANT: Your entire response must be valid JSON that can be parsed with Python's json.loads(). Do not include any explanations, markdown formatting, or additional text outside the JSON structure.
"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the AI agent's JSON response.
        
        Args:
            response: The AI agent's response as a string.
            
        Returns:
            The parsed response as a dictionary.
            
        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        # Clean the response to extract just the JSON part
        cleaned_response = response.strip()
        
        # Handle cases where the response might be wrapped in backticks or markdown code blocks
        if cleaned_response.startswith("```json"):
            # Extract content from markdown code block
            cleaned_response = cleaned_response.replace("```json", "", 1)
            if "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[0]
        elif cleaned_response.startswith("```"):
            # Extract content from generic markdown code block
            cleaned_response = cleaned_response.replace("```", "", 1)
            if "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[0]
                
        # Remove any other non-JSON content that might appear before or after JSON
        # Try to find the first { and last }
        try:
            start = cleaned_response.index("{")
            end = cleaned_response.rindex("}") + 1
            cleaned_response = cleaned_response[start:end]
        except ValueError:
            # If we can't find proper JSON delimiters, continue with the cleaned string
            pass
            
        cleaned_response = cleaned_response.strip()
            
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            # Try a fallback analysis with a simpler structure
            print(f"Failed to parse AI response as JSON. Response: {cleaned_response[:100]}...")
            print(f"Error: {e}")
            
            # Return a minimal valid structure rather than failing completely
            return {
                "functions": [],
                "dependencies": [],
                "entry_points": [],
                "summary": f"Analysis failed: {str(e)}"
            }
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a single code file.
        
        Args:
            file_path: Path to the code file to analyze.
            
        Returns:
            The analysis result as a dictionary.
            
        Raises:
            ValueError: If the file cannot be read or the AI response cannot be parsed.
        """
        if not os.path.isfile(file_path):
            raise ValueError(f"'{file_path}' is not a valid file")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                code = file.read()
                
            # Check if file needs chunking (token count > token_limit)
            token_count = self.count_tokens(code)
            if token_count > self.token_limit:
                print(f"File {file_path} exceeds token limit ({token_count} > {self.token_limit}). Chunking needed.")
                return self._analyze_large_file(file_path, code)
            
            return self._analyze_code(code, file_path)
        except Exception as e:
            raise ValueError(f"Failed to analyze file '{file_path}': {e}")
    
    def _analyze_code(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Send the code to the AI agent for analysis.
        
        Args:
            code: The code to analyze.
            file_path: Path to the code file (for error reporting).
            
        Returns:
            The analysis result as a dictionary.
        """
        prompt = self._create_prompt(code)
        
        for attempt in range(self.max_retries):
            try:
                print(f"Analyzing {file_path} (attempt {attempt + 1}/{self.max_retries})...")
                
                # Generate a system message to enforce JSON response
                messages = [
                    {"role": "system", "content": "You are a code analysis assistant that only responds with valid JSON."},
                    {"role": "user", "content": prompt}
                ]
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.1,  # Lower temperature for more deterministic responses
                    response_format={"type": "json_object"}  # Ensure JSON response format
                )
                
                result = response.choices[0].message.content
                
                # Print first 100 chars of response for debugging
                print(f"Response preview: {result[:100]}...")
                
                try:
                    return self._parse_response(result)
                except ValueError as e:
                    print(f"Parse error: {e}")
                    if attempt == self.max_retries - 1:
                        # On last attempt, use the fallback parser which returns empty structure
                        return self._parse_response(result)
                    # Otherwise retry
                    raise
                    
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"All {self.max_retries} attempts failed for {file_path}")
                    # Instead of raising, return a minimal valid structure
                    return {
                        "functions": [],
                        "dependencies": [],
                        "entry_points": [],
                        "summary": f"Analysis failed after {self.max_retries} attempts: {str(e)}"
                    }
    
    def _analyze_large_file(self, file_path: str, code: str) -> Dict[str, Any]:
        """
        Analyze a large file by chunking it into smaller pieces at function and class boundaries.
        
        Args:
            file_path: Path to the code file.
            code: The full code content.
            
        Returns:
            The combined analysis result as a dictionary.
        """
        print(f"Analyzing large file {file_path} at function boundaries...")
        
        # Get file extension to determine language for proper chunking
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # For Python files, use AST to identify function and class boundaries
        if file_ext == '.py':
            try:
                # Parse the code with ast module
                tree = ast.parse(code)
                
                # Find all function and class definitions with their line numbers
                chunks = self._extract_ast_chunks(code, tree)
                
                # If AST parsing failed or no chunks were found, fall back to simplified analysis
                if not chunks:
                    return self._simplified_large_file_analysis(file_path, code)
                
                # Analyze each chunk and combine results
                return self._analyze_chunks(file_path, chunks)
                
            except SyntaxError as e:
                print(f"Syntax error parsing {file_path} with AST: {e}")
                # Fall back to simplified analysis
                return self._simplified_large_file_analysis(file_path, code)
        else:
            # For non-Python files, use regex-based chunking or simplified analysis
            # This is a placeholder - in a production system, you'd want language-specific parsers
            return self._simplified_large_file_analysis(file_path, code)

    def _extract_ast_chunks(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """
        Extract code chunks from an AST tree, preserving function and class boundaries.
        
        Args:
            code: Original source code.
            tree: AST parse tree.
            
        Returns:
            List of chunks with name, type, content, and line number information.
        """
        chunks = []
        
        # Get the lines of code for line number reference
        lines = code.splitlines()
        
        # Keep track of where functions/classes start and end
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Function definition
                name = node.name
                lineno = node.lineno - 1  # AST line numbers are 1-indexed
                
                # Try to get the end line number if available (Python 3.8+)
                end_lineno = getattr(node, 'end_lineno', None)
                if end_lineno is not None:
                    end_lineno -= 1  # Convert to 0-indexed
                else:
                    # Estimate end by finding the last line in the function body
                    end_lineno = max(getattr(child, 'lineno', lineno) for child in ast.walk(node))
                    
                # Extract function source
                func_source = '\n'.join(lines[lineno:end_lineno + 1])
                
                chunks.append({
                    'name': name,
                    'type': 'function',
                    'content': func_source,
                    'lineno': lineno,
                    'end_lineno': end_lineno
                })
                
            elif isinstance(node, ast.ClassDef):
                # Class definition
                name = node.name
                lineno = node.lineno - 1  # AST line numbers are 1-indexed
                
                # Try to get the end line number if available (Python 3.8+)
                end_lineno = getattr(node, 'end_lineno', None)
                if end_lineno is not None:
                    end_lineno -= 1  # Convert to 0-indexed
                else:
                    # Estimate end by finding the last line in the class body
                    end_lineno = max(getattr(child, 'lineno', lineno) for child in ast.walk(node))
                    
                # Extract class source
                class_source = '\n'.join(lines[lineno:end_lineno + 1])
                
                chunks.append({
                    'name': name,
                    'type': 'class',
                    'content': class_source,
                    'lineno': lineno,
                    'end_lineno': end_lineno
                })
        
        # Sort chunks by line number
        chunks.sort(key=lambda x: x['lineno'])
        
        # Add imports and module-level code as a separate chunk
        if chunks:
            first_chunk_start = chunks[0]['lineno']
            if first_chunk_start > 0:
                module_code = '\n'.join(lines[:first_chunk_start])
                chunks.insert(0, {
                    'name': 'module_imports',
                    'type': 'module',
                    'content': module_code,
                    'lineno': 0,
                    'end_lineno': first_chunk_start - 1
                })
            
            # Add any code between chunks
            for i in range(1, len(chunks)):
                prev_end = chunks[i-1]['end_lineno']
                curr_start = chunks[i]['lineno']
                
                if curr_start - prev_end > 1:  # There's code between chunks
                    between_code = '\n'.join(lines[prev_end + 1:curr_start])
                    chunks.insert(i, {
                        'name': f'module_code_{prev_end + 1}_{curr_start}',
                        'type': 'module',
                        'content': between_code,
                        'lineno': prev_end + 1,
                        'end_lineno': curr_start - 1
                    })
                    
            # Add any code after the last chunk
            last_end = chunks[-1]['end_lineno']
            if last_end < len(lines) - 1:
                end_code = '\n'.join(lines[last_end + 1:])
                chunks.append({
                    'name': 'module_end',
                    'type': 'module',
                    'content': end_code,
                    'lineno': last_end + 1,
                    'end_lineno': len(lines) - 1
                })
        else:
            # If no functions/classes found, just return the whole file
            chunks.append({
                'name': 'whole_module',
                'type': 'module',
                'content': code,
                'lineno': 0,
                'end_lineno': len(lines) - 1
            })
        
        return chunks

    def _analyze_chunks(self, file_path: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze code chunks and combine results.
        
        Args:
            file_path: Path to the code file.
            chunks: List of code chunks to analyze.
            
        Returns:
            Combined analysis result.
        """
        combined_result = {
            "functions": [],
            "dependencies": set(),
            "entry_points": set(),
            "summary": ""
        }
        
        # Create context information for each chunk
        context = f"This is a partial analysis of file {os.path.basename(file_path)}."
        context += " The file has been split into logical sections."
        
        # Analyze each chunk
        for i, chunk in enumerate(chunks):
            print(f"Analyzing chunk {i+1}/{len(chunks)}: {chunk['name']} ({chunk['type']})")
            
            # For very small chunks, skip detailed analysis
            if len(chunk['content'].strip()) < 10:
                continue
            
            chunk_prompt = f"""
You are an AI agent specializing in code analysis. Analyze this code CHUNK from a larger file.
This is chunk {i+1} of {len(chunks)} from file {os.path.basename(file_path)}.
Chunk type: {chunk['type']}
Chunk name: {chunk['name']}

{context}

CODE CHUNK TO ANALYZE:
```
{chunk['content']}
```

Provide a focused analysis of this chunk only. Extract:
1. Functions/classes defined (if any)
2. Dependencies imported or used
3. Potential entry points
4. Brief description of the chunk's purpose

Format as valid JSON with this structure:
{{
  "functions": [
    {{
      "name": "function_name",
      "description": "what this function does",
      "inputs": "description of parameters",
      "outputs": "description of return values",
      "calls": ["function_call1", "function_call2"]
    }}
  ],
  "dependencies": ["dependency1", "dependency2"],
  "entry_points": ["entry_point1", "entry_point2"],
  "summary": "chunk purpose"
}}
"""
            
            for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a code analysis assistant that only responds with valid JSON."},
                            {"role": "user", "content": chunk_prompt}
                        ],
                        max_tokens=1000,
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                    
                    result = response.choices[0].message.content
                    parsed_result = self._parse_response(result)
                    
                    # Add results to combined result
                    combined_result["functions"].extend(parsed_result.get("functions", []))
                    combined_result["dependencies"].update(parsed_result.get("dependencies", []))
                    combined_result["entry_points"].update(parsed_result.get("entry_points", []))
                    
                    # For the first meaningful chunk with a summary, use it as the basis for the file summary
                    if not combined_result["summary"] and parsed_result.get("summary"):
                        combined_result["summary"] = parsed_result["summary"]
                        
                    # Success, move to next chunk
                    break
                    
                except Exception as e:
                    print(f"Failed to analyze chunk {i+1} (attempt {attempt+1}): {e}")
                    if attempt == self.max_retries - 1:
                        print(f"All attempts failed for chunk {i+1}")
        
        # If we have no summary from chunks, try to generate one
        if not combined_result["summary"]:
            # Create a high-level summary prompt with just the function names
            func_names = [f["name"] for f in combined_result["functions"]]
            summary_prompt = f"""
This file contains the following functions/classes: {', '.join(func_names)}.
Provide a one-sentence summary of what this file's purpose is likely to be.
Response should be plain text, not JSON.
"""
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=100
                )
                combined_result["summary"] = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Failed to generate summary: {e}")
                combined_result["summary"] = f"Analysis of {os.path.basename(file_path)}"
        
        # Convert sets back to lists for JSON serialization
        combined_result["dependencies"] = list(combined_result["dependencies"])
        combined_result["entry_points"] = list(combined_result["entry_points"])
        
        # Add a note about chunked analysis
        combined_result["note"] = f"This file was analyzed in {len(chunks)} logical chunks."
        
        return combined_result

    def _simplified_large_file_analysis(self, file_path: str, code: str) -> Dict[str, Any]:
        """
        Provide a smart analysis for large files using language-aware prompting.
        
        Args:
            file_path: Path to the code file.
            code: The full code content.
            
        Returns:
            Enhanced analysis result with structural information.
        """
        # Determine the language from file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Map file extensions to language names
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React JSX',
            '.tsx': 'React TSX',
            '.java': 'Java',
            '.cpp': 'C++',
            '.hpp': 'C++',
            '.c': 'C',
            '.h': 'C',
            '.go': 'Go',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.rs': 'Rust',
            '.scala': 'Scala',
            '.cs': 'C#',
            '.fs': 'F#',
            '.r': 'R',
            '.m': 'Objective-C',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.ps1': 'PowerShell'
        }
        
        language = language_map.get(file_ext, 'Unknown')
        print(f"Analyzing {language} file: {file_path}")
        
        simplified_prompt = f"""
You are an expert code analyzer specializing in {language} and other programming languages. Your task is to perform a STRUCTURAL analysis of the following code, similar to what an AST (Abstract Syntax Tree) parser would provide, but using your understanding of {language} syntax and patterns.

CODE TO ANALYZE ({language}):
```{file_ext}
{code}
```

ANALYSIS INSTRUCTIONS:
1. STRUCTURAL BREAKDOWN:
   - Identify all code blocks (functions, classes, methods, etc.) with their exact line spans
   - Note any nested structures (e.g., inner classes, nested functions)
   - Identify scope boundaries and code organization patterns

2. COMPONENT IDENTIFICATION:
   - Find all major code components (functions, classes, interfaces, etc.)
   - Identify their relationships and dependencies
   - Note any design patterns or architectural structures

3. DETAILED ANALYSIS:
   - For each identified component:
     * Exact location (start and end lines)
     * Scope and visibility (public, private, etc.)
     * Parameters and return types
     * Dependencies and relationships
     * Internal function calls
     * External dependencies

4. LANGUAGE-SPECIFIC FEATURES:
   - Identify {language}-specific patterns and idioms
   - Note any framework-specific code structures
   - Highlight language-specific optimizations or concerns

Format your response as a valid JSON object with this enhanced structure:
{{
  "file_type": "{language}",
  "components": [
    {{
      "type": "function|class|method|interface|etc",
      "name": "component_name",
      "start_line": line_number,
      "end_line": line_number,
      "scope": "public|private|protected|etc",
      "description": "what this component does",
      "inputs": "parameter descriptions",
      "outputs": "return value descriptions",
      "calls": ["function_calls"],
      "dependencies": ["external_dependencies"],
      "parent": "parent_component_if_nested",
      "language_specific": {{
        "patterns": ["relevant_language_patterns"],
        "features": ["language_specific_features_used"]
      }}
    }}
  ],
  "structure": {{
    "imports": ["list_of_imports"],
    "global_scope": ["global_variables_or_constants"],
    "namespaces": ["identified_namespaces"],
    "exports": ["exported_components"]
  }},
  "dependencies": {
    "external": ["external_dependencies"],
    "internal": ["internal_module_dependencies"]
  },
  "entry_points": ["potential_entry_points"],
  "summary": "concise_file_purpose",
  "language_features": ["language_specific_features_used"],
  "complexity_analysis": {{
    "cyclomatic_complexity": "estimated_complexity",
    "nesting_depth": "max_nesting_depth",
    "component_count": "number_of_components"
  }}
}}

IMPORTANT: 
- Focus on STRUCTURAL analysis similar to AST parsing
- Maintain precise line number tracking
- Identify nested relationships accurately
- Pay special attention to {language}-specific patterns
- Ensure all JSON is properly formatted and can be parsed by Python's json.loads()
"""
        
        for attempt in range(self.max_retries):
            try:
                print(f"Analyzing file {file_path} (attempt {attempt + 1}/{self.max_retries})...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a code analysis expert that specializes in providing detailed structural analysis of source code. You focus on accuracy and precision, similar to an AST parser."},
                        {"role": "user", "content": simplified_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                result = response.choices[0].message.content
                parsed_result = self._parse_response(result)
                
                # Convert the enhanced format to our standard format
                standardized_result = self._standardize_analysis_result(parsed_result, language)
                
                # Add analysis metadata
                standardized_result["analysis_type"] = "language_aware_structural"
                standardized_result["language"] = language
                
                return standardized_result
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"All {self.max_retries} attempts failed for file {file_path}")
                    raise

    def _standardize_analysis_result(self, enhanced_result: Dict[str, Any], language: str) -> Dict[str, Any]:
        """
        Convert the enhanced analysis format to our standard format.
        
        Args:
            enhanced_result: The enhanced analysis result.
            language: The programming language.
            
        Returns:
            Standardized analysis result.
        """
        standard_result = {
            "functions": [],
            "dependencies": [],
            "entry_points": enhanced_result.get("entry_points", []),
            "summary": enhanced_result.get("summary", ""),
            "language_info": {
                "name": language,
                "features": enhanced_result.get("language_features", []),
                "complexity": enhanced_result.get("complexity_analysis", {})
            }
        }
        
        # Convert components to our standard function format
        for component in enhanced_result.get("components", []):
            standard_result["functions"].append({
                "name": component["name"],
                "description": component["description"],
                "inputs": component["inputs"],
                "outputs": component["outputs"],
                "calls": component["calls"],
                "location": {
                    "start_line": component["start_line"],
                    "end_line": component["end_line"]
                },
                "metadata": {
                    "type": component["type"],
                    "scope": component["scope"],
                    "language_specific": component.get("language_specific", {})
                }
            })
        
        # Combine all dependencies
        if "dependencies" in enhanced_result:
            standard_result["dependencies"].extend(enhanced_result["dependencies"].get("external", []))
            standard_result["dependencies"].extend(enhanced_result["dependencies"].get("internal", []))
        
        # Add structure information
        standard_result["structure"] = enhanced_result.get("structure", {})
        
        return standard_result 