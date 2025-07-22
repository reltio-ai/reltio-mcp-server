@echo off
:: Check if Python exists
echo Checking Python version...
where python >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install it: https://www.python.org/downloads/
    exit /b 1
)

:: Get major and minor version
for /f "tokens=2 delims=[] " %%i in ('ver') do set OS_VER=%%i
for /f "tokens=2 delims= " %%i in ('python --version 2^>nul') do set PY_VER=%%i
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set /a PY_MAJOR=%%a
    set /a PY_MINOR=%%b
)

:: Compare versions
if %PY_MAJOR% LSS 3 (
    echo Python version must be 3.10 or higher.
    exit /b 1
)
if %PY_MAJOR%==3 if %PY_MINOR% LSS 10 (
    echo Python version must be 3.10 or higher.
    exit /b 1
)

echo Python version %PY_VER% is OK.
:: Step 2: Create virtual environment
:: Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    
    :: Check if python is available
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python is not installed. Please install Python 3.x first.
        exit /b 1
    )

    :: Create virtual environment
    python -m venv .venv
) else (
    echo Virtual environment .venv already exists.
)


:: Step 3: Activate virtual environment
call .venv\Scripts\activate.bat

: Step 4: Check if dependencies are already installed
echo Checking for uv installation...
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo uv not found. Installing dependencies...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
) else (
    echo uv is already installed.
)

pip install mcp
uv add "mcp[cli]" httpx requests

:: Step 6: Start MCP server
echo Starting MCP server...
mcp install --with requests --with pyyaml main.py -f .env 

echo MCP server started. Restart the Claude app now.
