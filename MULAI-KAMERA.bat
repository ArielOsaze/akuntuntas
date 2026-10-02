@echo off
chcp 65001 > nul
title AkunTuntas - Kamera Siaran
cd /d "%~dp0"

echo ======================================================================
echo   KAMERA SIARAN AKUNTUNTAS
echo ======================================================================
echo.
echo   Jendela ini menampilkan kamera Anda dengan latar AkunTuntas.
echo.
echo   Di TikTok LIVE Studio:
echo     1. Add source, pilih Window capture
echo     2. Pilih jendela "AkunTuntas - Kamera"
echo     3. Letakkan tepat di kotak kanan atas:
echo        X=646  Y=40  lebar=400  tinggi=300
echo.
echo   Tekan tombol apa saja untuk mulai. Tutup jendela kamera atau
echo   tekan Q untuk berhenti.
echo.
pause > nul

set PY=
if exist "C:\Users\ariel\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" (
    set PY=C:\Users\ariel\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
) else (
    where python >nul 2>&1 && set PY=python
)

if "%PY%"=="" (
    echo   Python tidak ditemukan.
    pause
    exit /b 1
)

"%PY%" tools\jendela_kamera.py

echo.
echo ======================================================================
echo   Jendela kamera ditutup.
echo ======================================================================
pause > nul
