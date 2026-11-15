@echo off
rem Abre el visor de GENESIS. Uso:
rem   iniciar.bat                 abre la partida mas reciente (o crea "semilla-1")
rem   iniciar.bat --semilla 42    abre o crea la partida "semilla-42"
rem   iniciar.bat mi-partida      abre una partida por su nombre
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PYTHON=py -3") else (set "PYTHON=python")
%PYTHON% ejecutar.py visor %*
if errorlevel 1 (
  echo.
  echo GENESIS no ha podido arrancar. Comprueba que Python 3.10 o posterior esta instalado.
  pause
)
