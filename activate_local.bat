@echo off
REM Local Windows activation script for testing direct GSAS-II import (Option 2)
REM This mimics the HPC environment setup for local testing

echo ========================================
echo Activating XRD Environment (Local Test)
echo ========================================
echo.

REM Set GSAS-II paths (matches official docs and HPC setup)
set "GSAS2DIR=C:\Users\wgonzalez\Software\G2\GSAS-II"
set "PYTHONPATH=%GSAS2DIR%;%PYTHONPATH%"

echo GSAS-II environment configured:
echo   GSAS2DIR=%GSAS2DIR%
echo   PYTHONPATH=%PYTHONPATH%
echo.
echo Testing direct import (Option 2 method)...
python -c "from GSASII import GSASIIscriptable as G2sc; print('✓ Direct import successful!')" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Option 2 works locally!
) else (
    echo ✗ Direct import failed - checking setup...
    python -c "from GSASII import GSASIIscriptable as G2sc; print('OK')"
)
echo.
echo Environment activated. You can now test your code.
echo To test: python -c "from XRD.core import gsas_processing; print('Import OK')"
echo.
