@echo off
setlocal

set "BASE=%~dp0"
set "VGMSTREAM=%BASE%..\External Libraries\vgmstream-win64\vgmstream-cli.exe"
set "WEMS=%BASE%..\WEMs"
set "WAVS=%BASE%..\WAVs"

if not exist "%VGMSTREAM%" (
    echo Could not find vgmstream-cli.exe at: %VGMSTREAM%
    pause
    exit /b 1
)

if not exist "%WEMS%" (
    echo Could not find WEMs folder at: %WEMS%
    pause
    exit /b 1
)

if not exist "%WAVS%" mkdir "%WAVS%"

for /d %%d in ("%WEMS%\*") do (
    echo === Processing folder: %%~nxd ===
    mkdir "%WAVS%\%%~nxd" 2>nul

    for %%f in ("%%d\*.wem") do (
        "%VGMSTREAM%" -o "%WAVS%\%%~nxd\%%~nf.wav" "%%f" >nul
        if errorlevel 1 echo     [FAILED] %%~nxf
    )
)

echo All folders processed.
pause