@echo off
rem GENESIS AutoDev: abre la interfaz sin dejar una consola abierta.
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 -m autodev.ui
) else (
    echo No se encuentra el iniciador grafico de Python (pyw).
    echo Instala Python 3.10 o posterior desde python.org.
    pause
)
