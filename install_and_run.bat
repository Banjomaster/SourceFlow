@echo off
setlocal enabledelayedexpansion

:: Colors for Windows console
set "BLUE=[94m"
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "NC=[0m"

:: Print functions
:print_status
echo %BLUE%[SourceFlow]%NC% %~1
exit /b

:print_success
echo %GREEN%[Success]%NC% %~1
exit /b

:print_error
echo %RED%[Error]%NC% %~1
exit /b

:print_warning
echo %YELLOW%[Warning]%NC% %~1
exit /b

echo ======================================
echo    SourceFlow Installation Script
echo ======================================
echo.

:: Check for Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Python not found. Installing..."
    
    :: Download Python installer
    curl -o python_installer.exe https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
    
    :: Install Python
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    
    :: Clean up
    del python_installer.exe
) else (
    for /f "tokens=*" %%i in ('python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"') do (
        call :print_success "Found Python version %%i"
    )
)

:: Check for pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "pip not found. Please reinstall Python with pip."
    exit /b 1
)

:: Check for Graphviz
dot -V >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Graphviz not found. Installing..."
    
    :: Download Graphviz installer
    curl -L -o graphviz_installer.exe https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/8.0.5/windows_10_cmake_Release_graphviz-install-8.0.5-win64.exe
    
    :: Install Graphviz
    graphviz_installer.exe /S
    
    :: Clean up
    del graphviz_installer.exe
    
    :: Add Graphviz to PATH
    setx PATH "%PATH%;C:\Program Files\Graphviz\bin" /M
)

:: Create virtual environment
call :print_status "Setting up virtual environment..."
python -m venv .venv
call .venv\Scripts\activate.bat

:: Upgrade pip
call :print_status "Upgrading pip..."
python -m pip install --upgrade pip

:: Install requirements
call :print_status "Installing Python dependencies..."
pip install -r requirements.txt

:: Check for OpenAI API key
if "%OPENAI_API_KEY%"=="" (
    call :print_warning "OpenAI API key not found in environment variables."
    set /p "api_key=Please enter your OpenAI API key: "
    setx OPENAI_API_KEY "!api_key!"
    echo OPENAI_API_KEY=!api_key!> .env
)

:: Run analyzer if directory is provided
if "%~1"=="" (
    call :print_error "Please provide the directory to analyze."
    echo Usage: %0 ^<input_directory^> [output_directory]
    exit /b 1
)

set "input_dir=%~1"
set "output_dir=%~2"

if "%output_dir%"=="" (
    :: Create output directory with timestamp
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
        set "date=%%c%%a%%b"
    )
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
        set "time=%%a%%b"
    )
    set "output_dir=result\analysis_%date%_%time%"
)

call :print_status "Running SourceFlow analyzer..."
call :print_status "Input directory: %input_dir%"
call :print_status "Output directory: %output_dir%"

python run_analyzer.py "%input_dir%" --output-dir "%output_dir%" --html-only

if %errorlevel% equ 0 (
    call :print_success "Analysis completed successfully!"
    call :print_success "Results saved to: %output_dir%"
    call :print_success "Open %output_dir%\interactive_viewer.html in your browser to view the results."
) else (
    call :print_error "Analysis failed. Please check the error messages above."
)

endlocal 