@echo off
REM Builds dist\SmartHealthcareSPMS.exe (Windows). Run from this folder.
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name SmartHealthcareSPMS main.py
echo.
echo Done: dist\SmartHealthcareSPMS.exe  (spms.db is created next to the exe on first run)
pause
