@echo off
chcp 65001 > nul
title AkunTuntas - Perbaiki Overlay
cd /d "%~dp0"

echo ======================================================================
echo   PERBAIKI TAMPILAN OVERLAY
echo ======================================================================
echo.
echo   Menyetel ukuran overlay supaya tidak ada pita kosong di kanan kiri
echo   dan gambar tidak pecah.
echo.

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

"%PY%" tools\perbaiki_overlay.py

echo.
echo ======================================================================
echo   Selesai. Tekan tombol apa saja untuk menutup.
echo ======================================================================
pause > nul
