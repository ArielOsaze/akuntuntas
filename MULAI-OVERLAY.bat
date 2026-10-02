@echo off
chcp 65001 > nul
title AkunTuntas - Overlay Live TikTok
cd /d "%~dp0"

echo ======================================================================
echo   OVERLAY LIVE TIKTOK - AkunTuntas
echo ======================================================================
echo.
echo   Menyiapkan overlay untuk siaran...
echo.

rem Pakai Python yang tersedia, utamakan yang punya semua keperluan.
set PY=
if exist "C:\Users\ariel\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" (
    set PY=C:\Users\ariel\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
) else (
    where python >nul 2>&1 && set PY=python
)

if "%PY%"=="" (
    echo   Python tidak ditemukan.
    echo   Pasang Python lebih dahulu dari python.org
    echo.
    pause
    exit /b 1
)

echo   Membuka jendela overlay...
echo.
"%PY%" tools\jalankan_overlay.py --chrome

if errorlevel 1 (
    echo.
    echo   Ada masalah saat membuka overlay.
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   OVERLAY SUDAH TERBUKA
echo ======================================================================
echo.
echo   Jendela overlay berjalan di latar belakang.
echo   Jangan tutup jendela itu selama siaran berlangsung.
echo.
echo   Langkah berikutnya di TikTok LIVE Studio:
echo     1. Tambahkan Window capture, pilih "AkunTuntas - Overlay Live"
echo     2. Tambahkan Camera, pilih "USB Camera"
echo     3. Letakkan kamera tepat di kotak kanan atas
echo     4. Untuk ganti latar kamera, pakai efek
echo        "Virtual Background (Static/Dynamic)"
echo.
echo   Panduan lengkap:
echo     live_overlay\PANDUAN-TIKTOK-STUDIO.md
echo.
echo   Tekan tombol apa saja untuk menutup jendela ini.
pause > nul
