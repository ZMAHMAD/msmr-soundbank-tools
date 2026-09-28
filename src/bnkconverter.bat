@echo off
setlocal enabledelayedexpansion

set "BASE=%~dp0"
set "BNKEXTR=%BASE%..\External Libraries\bnkextr.exe"
set "BANKS=%BASE%..\Banks"
set "OUT=%BASE%..\WEMs"

if not exist "%BNKEXTR%" (
    echo Could not find bnkextr.exe at: %BNKEXTR%
    pause
    exit /b 1
)

if not exist "%BANKS%" (
    echo Could not find Banks folder at: %BANKS%
    pause
    exit /b 1
)

if not exist "%OUT%" mkdir "%OUT%"

for %%f in ("%BANKS%\*.bnk") do (
    echo === Extracting %%~nxf ===
    "%BNKEXTR%" "%%f"

    if exist "%BANKS%\%%~nf\" (
        robocopy "%BANKS%\%%~nf" "%OUT%\%%~nf" /E /MOVE /NFL /NDL /NJH /NJS /NP >nul
        echo     moved to WEMs\%%~nf
    ) else (
        echo     [WARNING] no output folder found for %%~nxf
    )
)

echo Done.
pause