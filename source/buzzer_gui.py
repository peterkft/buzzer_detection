"""
Buzzer Detector - GUI entry point.

The implementation lives in the ``buzzer`` package alongside this file. This shim is what ``build_windows.bat`` feeds
to PyInstaller; it imports from the package so PyInstaller pulls every module in transitively.

Run from source:
    pip install numpy scipy matplotlib soundfile
    python buzzer_gui.py

Build into a Windows .exe (run on Windows, with this script's environment):
    pip install pyinstaller
    pyinstaller --onefile --windowed --name BuzzerDetector buzzer_gui.py

The resulting BuzzerDetector.exe will be in the dist/ folder.
"""

from buzzer.gui import main

if __name__ == "__main__":
    main()
