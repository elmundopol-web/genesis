@echo off
rem Ejecuta todas las pruebas automaticas de GENESIS.
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PYTHON=py -3") else (set "PYTHON=python")
%PYTHON% -m unittest discover -s pruebas -t . %*
set "GENESIS_TEST_RESULT=%errorlevel%"
where node >nul 2>nul
if %errorlevel%==0 (
  node --test pruebas/test_interfaz.mjs
  if errorlevel 1 set "GENESIS_TEST_RESULT=1"
) else (
  echo Pruebas de interfaz omitidas: Node.js no esta instalado. No es necesario para jugar.
)
echo.
if not "%GENESIS_TEST_RESULT%"=="0" (echo HAY PRUEBAS QUE FALLAN.) else (echo Todas las pruebas disponibles pasan.)
pause
exit /b %GENESIS_TEST_RESULT%
