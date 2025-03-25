#!/bin/bash

# Text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

# Print with color
print_status() {
    echo -e "${BLUE}[SourceFlow]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[Success]${NC} $1"
}

print_error() {
    echo -e "${RED}[Error]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python using the appropriate package manager
install_python() {
    print_status "Installing Python..."
    
    if command_exists brew; then
        brew install python
    elif command_exists apt-get; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif command_exists dnf; then
        sudo dnf install -y python3 python3-pip
    elif command_exists yum; then
        sudo yum install -y python3 python3-pip
    elif command_exists pacman; then
        sudo pacman -S python python-pip
    else
        print_error "Could not install Python. Please install Python 3.8 or later manually."
        exit 1
    fi
}

# Function to install Graphviz
install_graphviz() {
    print_status "Installing Graphviz..."
    
    if command_exists brew; then
        brew install graphviz
    elif command_exists apt-get; then
        sudo apt-get update
        sudo apt-get install -y graphviz
    elif command_exists dnf; then
        sudo dnf install -y graphviz
    elif command_exists yum; then
        sudo yum install -y graphviz
    elif command_exists pacman; then
        sudo pacman -S graphviz
    else
        print_error "Could not install Graphviz. Please install Graphviz manually."
        exit 1
    fi
}

# Print welcome message
echo "======================================"
echo "   SourceFlow Installation Script"
echo "======================================"
echo ""

# Check for Python installation
if ! command_exists python3; then
    print_warning "Python 3 not found. Installing..."
    install_python
else
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Found Python version $PYTHON_VERSION"
fi

# Check for pip
if ! command_exists pip3; then
    print_warning "pip3 not found. Installing..."
    if command_exists apt-get; then
        sudo apt-get install -y python3-pip
    elif command_exists dnf; then
        sudo dnf install -y python3-pip
    else
        print_error "Could not install pip. Please install pip manually."
        exit 1
    fi
fi

# Check for Graphviz
if ! command_exists dot; then
    print_warning "Graphviz not found. Installing..."
    install_graphviz
fi

# Create virtual environment
print_status "Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install requirements
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    print_warning "OpenAI API key not found in environment variables."
    echo "Please enter your OpenAI API key:"
    read -r api_key
    export OPENAI_API_KEY="$api_key"
    # Also save it to .env file
    echo "OPENAI_API_KEY=$api_key" > .env
fi

# Function to run the analyzer
run_analyzer() {
    local input_dir="$1"
    local output_dir="$2"
    
    if [ -z "$input_dir" ]; then
        print_error "Please provide the directory to analyze."
        echo "Usage: $0 <input_directory> [output_directory]"
        exit 1
    fi
    
    if [ -z "$output_dir" ]; then
        # Create output directory with timestamp
        output_dir="result/analysis_$(date +%Y%m%d_%H%M%S)"
    fi
    
    print_status "Running SourceFlow analyzer..."
    print_status "Input directory: $input_dir"
    print_status "Output directory: $output_dir"
    
    python run_analyzer.py "$input_dir" --output-dir "$output_dir" --html-only
    
    if [ $? -eq 0 ]; then
        print_success "Analysis completed successfully!"
        print_success "Results saved to: $output_dir"
        print_success "Open ${output_dir}/interactive_viewer.html in your browser to view the results."
    else
        print_error "Analysis failed. Please check the error messages above."
    fi
}

# Check if this script is being sourced or run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [ $# -eq 0 ]; then
        print_error "Please provide the directory to analyze."
        echo "Usage: $0 <input_directory> [output_directory]"
        exit 1
    fi
    
    run_analyzer "$1" "$2"
fi 