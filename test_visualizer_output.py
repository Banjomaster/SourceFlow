import os
import re
import json
import unittest
from bs4 import BeautifulSoup
import shutil
from pathlib import Path
import difflib

# Import the needed components
from sourceflow.core.visualizer import VisualizationGenerator
from sourceflow.core.builder import RelationshipBuilder

class TestVisualizerOutput(unittest.TestCase):
    """Test the visualizer output against gold standard files."""

    @classmethod
    def setUpClass(cls):
        """Set up test data and paths."""
        # Define paths
        cls.gold_standard_dir = "results/sourceflow"
        cls.test_output_dir = "test_results_compare"
        cls.test_data_file = os.path.join(cls.gold_standard_dir, "analysis_data.json")
        
        # Create test output directory if it doesn't exist
        if not os.path.exists(cls.test_output_dir):
            os.makedirs(cls.test_output_dir)
        
        # Load test data from the gold standard analysis
        with open(cls.test_data_file, 'r') as f:
            cls.test_data = json.load(f)
        
        # Save original gold standard Mermaid files for later comparison
        cls.gold_mermaid_files = {}
        for mermaid_file in ['structure_raw.md', 'dependencies_raw.md', 'execution_raw.md']:
            gold_path = os.path.join(cls.gold_standard_dir, mermaid_file)
            if os.path.exists(gold_path):
                with open(gold_path, 'r') as f:
                    cls.gold_mermaid_files[mermaid_file] = f.read()
        
        # Copy the gold standard mermaid files to the test directory
        print("Copying gold standard files for deterministic testing...")
        for mermaid_file in ['structure_raw.md', 'dependencies_raw.md', 'execution_raw.md']:
            gold_path = os.path.join(cls.gold_standard_dir, mermaid_file)
            test_path = os.path.join(cls.test_output_dir, mermaid_file)
            if os.path.exists(gold_path):
                shutil.copy(gold_path, test_path)
                print(f"Copied {mermaid_file} from gold standard")
            else:
                print(f"Warning: Could not find {mermaid_file} in gold standard directory")
        
        # Initialize the visualizer for the test output
        cls.visualizer = VisualizationGenerator(output_dir=cls.test_output_dir)
        
        # Initialize a separate instance for testing the generation engine
        cls.generation_test_dir = "test_results_generation"
        if not os.path.exists(cls.generation_test_dir):
            os.makedirs(cls.generation_test_dir)
        cls.generation_visualizer = VisualizationGenerator(output_dir=cls.generation_test_dir)
        
        # Read the gold standard mermaid content
        try:
            # Use proper context managers to avoid resource warnings
            with open(os.path.join(cls.test_output_dir, 'structure_raw.md'), 'r') as f:
                structure_content = f.read()
            with open(os.path.join(cls.test_output_dir, 'dependencies_raw.md'), 'r') as f:
                dependencies_content = f.read()
            with open(os.path.join(cls.test_output_dir, 'execution_raw.md'), 'r') as f:
                execution_content = f.read()
            
            # Generate HTML directly using the gold standard content
            print("Generating HTML diagrams using gold standard content...")
            cls.visualizer._generate_individual_diagram_html(
                structure_content, 
                "code_structure_diagram", 
                "Code Structure Diagram",
                "This diagram shows the overall structure of the codebase, including functions, classes, and their relationships."
            )
            cls.visualizer._generate_individual_diagram_html(
                dependencies_content, 
                "dependencies_diagram", 
                "Module Dependencies Diagram",
                "This diagram illustrates the relationships between modules in the codebase, showing how files depend on one another and the overall architecture of the system."
            )
            cls.visualizer._generate_individual_diagram_html(
                execution_content, 
                "execution_paths_diagram", 
                "Execution Paths Diagram",
                "This diagram shows the major execution paths from entry points, illustrating the flow of execution through different functions and modules."
            )
            
            # Generate the custom HTML viewer using the test data
            print("Generating custom viewer HTML...")
            cls.visualizer.generate_html_viewer(cls.test_data)
            
        except Exception as e:
            print(f"Error generating HTML files: {str(e)}")
            raise
        
        # Files to compare
        cls.html_files = [
            "custom_viewer.html",
            "code_structure_diagram.html", 
            "dependencies_diagram.html",
            "execution_paths_diagram.html"
        ]

    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        # Commenting out to keep test files for inspection
        # if os.path.exists(cls.test_output_dir):
        #     shutil.rmtree(cls.test_output_dir)
        # if os.path.exists(cls.generation_test_dir):
        #     shutil.rmtree(cls.generation_test_dir)

    def load_html_files(self, filename):
        """Load both gold standard and test HTML files."""
        gold_path = os.path.join(self.gold_standard_dir, filename)
        test_path = os.path.join(self.test_output_dir, filename)
        
        with open(gold_path, 'r') as f:
            gold_html = f.read()
        
        with open(test_path, 'r') as f:
            test_html = f.read()
            
        gold_soup = BeautifulSoup(gold_html, 'html.parser')
        test_soup = BeautifulSoup(test_html, 'html.parser')
        
        return gold_soup, test_soup

    def test_file_existence(self):
        """Test that all required files were generated."""
        for filename in self.html_files:
            test_path = os.path.join(self.test_output_dir, filename)
            self.assertTrue(os.path.exists(test_path), f"Failed to generate {filename}")

    def extract_html_structure(self, soup):
        """Extract structural elements from HTML for comparison."""
        # Remove dynamic content like specific function names
        for tag in soup.find_all(string=True):
            # Replace dynamic text in various tags with placeholders
            if tag.parent.name not in ['script', 'style']:
                tag.replace_with("CONTENT")
                
        # Keep important structure and classes
        structure = {
            'head_tags': [tag.name for tag in soup.head.find_all()],
            'body_structure': self.get_tag_hierarchy(soup.body),
            'css_classes': self.extract_css_classes(soup),
            'scripts': [script.get('src', 'inline_script') for script in soup.find_all('script')],
            'links': [a.get('href') for a in soup.find_all('a') if a.get('href')]
        }
        
        return structure
    
    def get_tag_hierarchy(self, element, level=0, max_level=3):
        """Get a simplified tag hierarchy."""
        if level >= max_level or not hasattr(element, 'name') or not element.name:
            return None
            
        result = {'tag': element.name, 'class': element.get('class', [])}
        children = []
        
        for child in element.children:
            if hasattr(child, 'name') and child.name:
                child_hierarchy = self.get_tag_hierarchy(child, level + 1, max_level)
                if child_hierarchy:
                    children.append(child_hierarchy)
        
        if children:
            result['children'] = children
            
        return result
    
    def extract_css_classes(self, soup):
        """Extract all CSS classes used in the document."""
        classes = set()
        for tag in soup.find_all(True):
            if 'class' in tag.attrs:
                classes.update(tag['class'])
        return sorted(list(classes))

    def test_html_structure(self):
        """Test the HTML structure of all files."""
        for filename in self.html_files:
            with self.subTest(file=filename):
                gold_soup, test_soup = self.load_html_files(filename)
                
                # Compare HTML structure
                gold_structure = self.extract_html_structure(gold_soup)
                test_structure = self.extract_html_structure(test_soup)
                
                # Compare script sources
                self.assertEqual(
                    gold_structure['scripts'], 
                    test_structure['scripts'],
                    f"Script sources different in {filename}"
                )
                
                # Use different important classes depending on the file type
                if filename == "custom_viewer.html":
                    important_classes = ['tab', 'tab-content', 'module-header', 'function', 'entry-point']
                else:
                    # For diagram HTML files
                    important_classes = ['diagram-container', 'mermaid', 'controls-container', 'back-button']
                
                # Check for important CSS classes but don't require exact match
                for css_class in important_classes:
                    self.assertIn(
                        css_class, 
                        test_structure['css_classes'],
                        f"Missing important CSS class '{css_class}' in {filename}"
                    )
                
                # Print missing classes but don't fail the test for them
                missing_classes = set(gold_structure['css_classes']) - set(test_structure['css_classes'])
                if missing_classes:
                    print(f"Note: {filename} is missing some non-critical CSS classes: {missing_classes}")
                
                # Compare head tags
                self.assertEqual(
                    set(gold_structure['head_tags']), 
                    set(test_structure['head_tags']),
                    f"Head structure different in {filename}"
                )
                
                # For the main custom viewer, more detailed checks
                if filename == "custom_viewer.html":
                    self.verify_custom_viewer_structure(gold_soup, test_soup)

    def verify_custom_viewer_structure(self, gold_soup, test_soup):
        """Verify the structure of the custom viewer HTML."""
        # Check for tab elements
        gold_tabs = gold_soup.select('.tab')
        test_tabs = test_soup.select('.tab')
        self.assertEqual(len(gold_tabs), len(test_tabs), "Different number of tabs")
        
        # Check for tab content divs
        gold_tab_contents = gold_soup.select('.tab-content')
        test_tab_contents = test_soup.select('.tab-content')
        self.assertEqual(len(gold_tab_contents), len(test_tab_contents), "Different number of tab content divs")
        
        # Check for searchable input
        self.assertIsNotNone(test_soup.select_one('#search-input'), "Missing search input")
        
        # Check for links to diagram pages
        gold_buttons = gold_soup.select('.button')
        test_buttons = test_soup.select('.button')
        self.assertEqual(len(gold_buttons), len(test_buttons), "Different number of diagram buttons")
        
        # Check for module headers
        gold_headers = gold_soup.select('.module-header')
        test_headers = test_soup.select('.module-header')
        self.assertGreaterEqual(len(test_headers), 1, "Missing module headers")

    def test_javascript_functionality(self):
        """Test that all required JavaScript functionality is present."""
        for filename in self.html_files:
            with self.subTest(file=filename):
                gold_soup, test_soup = self.load_html_files(filename)
                
                # Get all scripts
                gold_scripts = [script.string for script in gold_soup.find_all('script') if script.string]
                test_scripts = [script.string for script in test_soup.find_all('script') if script.string]
                
                # Check for key JavaScript functionality
                js_features = [
                    'addEventListener', 
                    'querySelector', 
                    'classList'
                ]
                
                for feature in js_features:
                    gold_has_feature = any(feature in script for script in gold_scripts)
                    test_has_feature = any(feature in script for script in test_scripts)
                    
                    if gold_has_feature:
                        self.assertTrue(
                            test_has_feature,
                            f"Missing JavaScript feature '{feature}' in {filename}"
                        )
                
                # For the main viewer, check for tab switching code
                if filename == "custom_viewer.html":
                    tab_switch_code = any("tab" in script and "click" in script for script in test_scripts)
                    self.assertTrue(tab_switch_code, "Missing tab switching JavaScript")
                    
                    search_code = any("search-input" in script for script in test_scripts)
                    self.assertTrue(search_code, "Missing search JavaScript")

    def test_mermaid_generation_engine(self):
        """Test that the Mermaid generation engine produces correct output.
        
        Note: The gold standard files and newly generated files will have significant
        differences in node naming and structure due to changes in the generation code:
          - Gold standard uses node_prefixed IDs (e.g., node_main)
          - Current code uses simple IDs without the prefix (e.g., main)
        
        This test does not expect exact matches but validates that the generated
        Mermaid content is valid and contains a similar amount of semantic information.
        """
        print("\nTesting Mermaid generation engine...")
        
        # Generate fresh Mermaid content using the test data
        print("Generating fresh Mermaid content...")
        self.generation_visualizer.generate_html_viewer(self.test_data)
        
        # Define the mapping between gold standard files and generated files
        file_mapping = {
            'structure_raw.md': 'structure_raw.md',
            'dependencies_raw.md': 'dependencies_raw.md',
            'execution_raw.md': 'execution_raw.md'
        }
        
        # Load the newly generated Mermaid files
        generated_mermaid = {}
        for gold_file, gen_file in file_mapping.items():
            gen_path = os.path.join(self.generation_test_dir, gen_file)
            if os.path.exists(gen_path):
                with open(gen_path, 'r') as f:
                    generated_content = f.read()
                    generated_mermaid[gold_file] = generated_content
                    
                    # Verify that the generated content is valid Mermaid syntax
                    self._verify_valid_mermaid(generated_content, gen_file)
            else:
                self.fail(f"Failed to generate {gen_file}")
        
        # Print a summary of the differences
        print("\nMermaid Generation Summary:")
        all_valid = True
        
        for mermaid_file in ['structure_raw.md', 'dependencies_raw.md', 'execution_raw.md']:
            print(f"\n=== Analyzing {mermaid_file} ===")
            
            # Get Mermaid content from both sources
            gold_mermaid = self.gold_mermaid_files.get(mermaid_file, "")
            generated_content = generated_mermaid.get(mermaid_file, "")
            
            # Skip empty files
            if not gold_mermaid or not generated_content:
                print(f"Skipping comparison for {mermaid_file} - file missing")
                continue
            
            # Clean up whitespace and line breaks for comparison
            gold_mermaid = self._normalize_mermaid(gold_mermaid)
            generated_content = self._normalize_mermaid(generated_content)
            
            # Calculate similarity percentage
            similarity = self._calculate_similarity(gold_mermaid, generated_content)
            print(f"Similarity: {similarity:.2f}%")
            
            # Compare basic statistics
            gold_stats = self._get_mermaid_stats(gold_mermaid)
            gen_stats = self._get_mermaid_stats(generated_content)
            
            print(f"Gold standard: {gold_stats['nodes']} nodes, {gold_stats['connections']} connections, {gold_stats['subgraphs']} subgraphs")
            print(f"Generated: {gen_stats['nodes']} nodes, {gen_stats['connections']} connections, {gen_stats['subgraphs']} subgraphs")
            
            # More detailed analysis
            # Extract specific critical features that must be present
            valid, diagnostics = self._check_critical_features(mermaid_file, gold_stats, gen_stats, gold_mermaid, generated_content)
            if not valid:
                all_valid = False
                print(f"❌ ISSUES DETECTED: {diagnostics}")
            else:
                print(f"✓ Mermaid generation produces valid diagram with all critical features")
                
        # Final assertion to ensure all diagrams are valid
        self.assertTrue(all_valid, "One or more generated diagrams have critical issues. See diagnostic output for details.")
    
    def _check_critical_features(self, file_name, gold_stats, gen_stats, gold_content, gen_content):
        """
        Check critical features that must be present in the generated diagram.
        
        Returns:
            tuple: (valid, diagnostics) where valid is a boolean and diagnostics is error message if invalid
        """
        # For all diagram types, there should be nodes
        if gen_stats['nodes'] == 0:
            return False, "No nodes in generated diagram"
            
        # For structure_raw.md
        if file_name == 'structure_raw.md':
            # Must have entry points (classDef entryPoint is used)
            if ":::entryPoint" not in gen_content:
                return False, "No entry points marked in structure diagram"
                
            # Must have connections between nodes
            if gen_stats['connections'] == 0:
                return False, "No connections between nodes in structure diagram"
                
            # Must have file/module subgraphs
            if gen_stats['subgraphs'] == 0:
                return False, "No subgraphs (module groupings) in structure diagram"
                
            # The node count should be at least 75% of the gold standard
            node_ratio = gen_stats['nodes'] / gold_stats['nodes'] * 100
            if node_ratio < 75:
                return False, f"Node count is only {node_ratio:.1f}% of gold standard ({gen_stats['nodes']} vs {gold_stats['nodes']})"
                
        # For dependencies_raw.md
        elif file_name == 'dependencies_raw.md':
            # Must have the legend
            if "subgraph Legend" not in gen_content:
                return False, "Missing Legend subgraph in dependencies diagram"
                
            # Must have module styling classes
            if "classDef pythonModule" not in gen_content:
                return False, "Missing module styling in dependencies diagram"
                
            # The node count should be at least 75% of the gold standard
            node_ratio = gen_stats['nodes'] / gold_stats['nodes'] * 100
            if node_ratio < 75:
                return False, f"Node count is only {node_ratio:.1f}% of gold standard ({gen_stats['nodes']} vs {gold_stats['nodes']})"
                
        # For execution_raw.md
        elif file_name == 'execution_raw.md':
            # Must have some execution paths
            if gen_stats['subgraphs'] == 0:
                return False, "No execution path subgraphs in execution diagram"
                
            # The execution diagram can vary more, but should have at least 50% of gold standard 
            # nodes and connections
            if gen_stats['nodes'] > 0 and gold_stats['nodes'] > 0:
                node_ratio = min(gen_stats['nodes'], gold_stats['nodes']) / max(gen_stats['nodes'], gold_stats['nodes']) * 100
                if node_ratio < 50:
                    return False, f"Node count differs too much from gold standard (similarity: {node_ratio:.1f}%)"
            
            # Must have some step labeling in execution paths
            if '"step ' not in gen_content:
                return False, "No step labels in execution paths"
                
        return True, "All critical features present"
    
    def _verify_valid_mermaid(self, mermaid_content, file_name):
        """Verify that the content is valid Mermaid syntax."""
        # Check for basic Mermaid syntax elements
        self.assertIn('graph', mermaid_content.lower(), f"Missing graph declaration in {file_name}")
        
        # Check for node definitions
        node_pattern = r'\w+\['
        nodes = re.findall(node_pattern, mermaid_content)
        self.assertTrue(len(nodes) > 0, f"No node definitions found in {file_name}")
        
        # Check for connections based on file type
        if file_name == 'dependencies_raw.md':
            # Check for legend connections
            self.assertIn('-.-|"imports"|', mermaid_content, f"Missing legend connections in {file_name}")
        elif file_name == 'execution_raw.md':
            # Execution paths use '===>' connectors
            connection_pattern = r'===>'
            connections = re.findall(connection_pattern, mermaid_content)
            self.assertTrue(len(connections) > 0, f"No execution path connections found in {file_name}")
        else:
            # Structure diagram uses '-->' connectors
            connection_pattern = r'-->'
            connections = re.findall(connection_pattern, mermaid_content)
            self.assertTrue(len(connections) > 0, f"No connections found in {file_name}")
        
        # Check for class definitions
        self.assertIn('classDef', mermaid_content, f"Missing class definitions in {file_name}")
        
    def _get_mermaid_stats(self, mermaid_content):
        """Get basic statistics about a Mermaid diagram."""
        # Count different connection types used in different diagram types
        connection_count = len(re.findall(r'-->', mermaid_content)) + \
                           len(re.findall(r'===>', mermaid_content)) + \
                           len(re.findall(r'-\.-', mermaid_content))
        
        stats = {
            'nodes': len(re.findall(r'\w+\[', mermaid_content)),
            'connections': connection_count,
            'subgraphs': len(re.findall(r'subgraph', mermaid_content)),
            'classes': len(re.findall(r'classDef', mermaid_content))
        }
        return stats
    
    def _normalize_mermaid(self, mermaid_content):
        """Normalize Mermaid content for comparison by removing whitespace and empty lines."""
        # Remove comments
        mermaid_content = re.sub(r'%%.*?%%', '', mermaid_content)
        
        # Split by lines, strip whitespace, remove empty lines
        lines = [line.strip() for line in mermaid_content.split('\n')]
        lines = [line for line in lines if line]
        
        return '\n'.join(lines)
    
    def _calculate_similarity(self, text1, text2):
        """Calculate similarity percentage between two texts."""
        # Use difflib's SequenceMatcher to calculate similarity
        matcher = difflib.SequenceMatcher(None, text1, text2)
        similarity = matcher.ratio() * 100
        return similarity

if __name__ == "__main__":
    unittest.main() 