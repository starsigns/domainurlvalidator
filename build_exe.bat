@echo off
echo Building Domain Validator Pro executable...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo Cleaning completed.
echo.

REM Build the executable
echo Starting PyInstaller build...
pyinstaller --clean DomainValidator.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =====================================
    echo BUILD SUCCESSFUL!
    echo =====================================
    echo.
    echo Executable created at: dist\DomainValidatorPro.exe
    echo.
    echo You can now copy DomainValidatorPro.exe to any Windows system
    echo and run it without installing Python or dependencies.
    echo.
    pause
) else (
    echo.
    echo =====================================
    echo BUILD FAILED!
    echo =====================================
    echo Please check the error messages above.
    echo.
    pause
)
