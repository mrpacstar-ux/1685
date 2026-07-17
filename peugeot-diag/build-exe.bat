@echo off
REM Build a standalone psa-diag.exe on Windows.
REM Needs Python 3 installed (tick "Add python.exe to PATH" in the installer).
REM Double-click this file, or run it from a Command Prompt in this folder.

echo Installing build tools...
python -m pip install --upgrade pip pyinstaller pyserial || goto :error

echo Building psa-diag.exe...
pyinstaller --onefile --windowed --name psa-diag ^
  --collect-submodules psadiag --collect-submodules serial ^
  --noconfirm --clean launch.py || goto :error

echo.
echo Done. Your program is:  dist\psa-diag.exe
echo Copy that single file anywhere and double-click it to run.
pause
exit /b 0

:error
echo.
echo Build failed. Make sure Python 3 is installed and on PATH.
pause
exit /b 1
