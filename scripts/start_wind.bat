@echo off
title WIND — Assistente REPROTECH
cd /d "%~dp0.."
echo.
echo  ====================================
echo   WIND — Iniciando...
echo  ====================================
echo.

REM Verifica Python
python --version 2>nul || (
    echo ERRO: Python nao encontrado no PATH.
    pause
    exit /b 1
)

python src\wind.py
pause
