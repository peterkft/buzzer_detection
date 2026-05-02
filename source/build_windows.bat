@echo off
REM ==========================================================================
REM  Build BuzzerDetector.exe from buzzer_gui.py
REM
REM  Run this from a Windows command prompt in the source\ folder (the folder
REM  that contains this .bat and buzzer_gui.py). Requirements files live one
REM  level up at the project root. Requires Python 3.9+ on the PATH.
REM ==========================================================================

echo.
echo [1/3] Creating virtual environment...
python -m venv build_env || goto :error

echo.
echo [2/3] Installing dependencies (this can take a few minutes)...
call build_env\Scripts\activate.bat
python -m pip install --upgrade pip || goto :error
python -m pip install -r ..\requirements.txt -r ..\coding_standard\requirements.txt || goto :error

echo.
echo [3/3] Building BuzzerDetector.exe...
pyinstaller --onefile --windowed --name BuzzerDetector buzzer_gui.py || goto :error

echo.
echo ==========================================================================
echo  Done! Your .exe is at:  dist\BuzzerDetector.exe
echo  You can copy it anywhere and run it - no Python needed on the target PC.
echo ==========================================================================
goto :end

:error
echo.
echo *** Build failed. Scroll up for details. ***
exit /b 1

:end
pause
