@echo off
echo Installing Drone Swarm 3D Simulator dependencies...
echo.

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies...

REM Try standard requirements first
pip install -r requirements.txt

REM Check if installation succeeded
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Standard installation failed. Trying Windows-specific requirements...
    pip install -r requirements-windows.txt
)

echo.
echo Testing installation...
python -c "import pygame, numpy, yaml; from OpenGL.GL import *; print('All modules imported successfully!')"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Installation complete!
    echo Run the simulator with: python main.py
) else (
    echo.
    echo Some modules failed to import. Please check the error messages above.
    echo You may need to install Visual C++ Build Tools for some packages.
)

pause