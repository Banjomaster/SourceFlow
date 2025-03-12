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
        Analyze a large file by chunking it into smaller pieces.
        
        Args:
            file_path: Path to the code file.
            code: The full code content.
            
        Returns:
            The combined analysis result as a dictionary.
        """
        # This is a simplified chunking strategy - in a real implementation, 
        # we'd want to chunk based on logical boundaries like functions/classes
        print(f"Analyzing large file {file_path} in chunks...")
        
        # For now, just analyze the whole file with a simplified request
        # In a real implementation, we would implement proper chunking
        simplified_prompt = f"""
You are an AI agent specializing in all types of software coding languages. Your job is to analyze code from an unknown project and create clarity and accurate representation of the project. 

This is a large file, so I'm asking for a HIGH-LEVEL analysis only. Here is the code:

{code}

Please identify:
1. The main purpose of this file
2. Major components (classes, functions) defined
3. Key external dependencies
4. Potential entry points

Format your response as valid JSON with the following structure:
{{
  "functions": [
    {{
      "name": "fully_qualified_name",
      "description": "description of the function (high-level only)"
    }}
  ],
  "dependencies": ["dependency1", "dependency2"],
  "entry_points": ["entry_point1", "entry_point2"],
  "summary": "general purpose of the file"
}}

Ensure the JSON is properly formatted and can be parsed by Python's json.loads().
"""
        
        for attempt in range(self.max_retries):
            try:
                print(f"Analyzing large file {file_path} (attempt {attempt + 1}/{self.max_retries})...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": simplified_prompt}],
                    max_tokens=1500
                )
                
                result = response.choices[0].message.content
                parsed_result = self._parse_response(result)
                
                # Add a note that this is a simplified analysis
                parsed_result["note"] = "This is a simplified analysis due to the large file size. Some details may be missing."
                
                return parsed_result
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"All {self.max_retries} attempts failed for large file {file_path}")
                    raise 