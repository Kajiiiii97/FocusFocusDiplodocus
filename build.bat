@echo off
rem Builds dist\FocusCat.exe (needs Python 3.10+ from python.org, with tkinter ticked).
python -m pip install --upgrade pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --onefile --windowed --name FocusCat FocusCat.pyw || exit /b 1
echo.
echo Done: dist\FocusCat.exe
