@echo off
setlocal
cd /d "%~dp0"
title SARWatch
if /i "%~1"=="--server" goto server_mode
if not "%~1"=="" goto server_mode
if not exist "app\standalone\index.html" goto missing_web
echo Opening SARWatch...
start "" "%~dp0app\standalone\index.html"
exit /b %ERRORLEVEL%

:missing_web
echo The website file is missing: app\standalone\index.html
echo Run python run.py build to rebuild it.
pause
exit /b 1

:server_mode
set "SARWATCH_ARGS=%*"
if /i "%~1"=="--server" set "SARWATCH_ARGS=%SARWATCH_ARGS:~9%"
if not exist "dev\.venv\Scripts\python.exe" goto find_python
"dev\.venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 goto local_python
:find_python
where py >nul 2>&1
if errorlevel 1 goto find_system_python
py -3 -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 goto python_launcher
:find_system_python
where python >nul 2>&1
if errorlevel 1 goto missing_python
python -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 goto system_python
:missing_python
echo Python 3.11 or newer is required. Install Python and run this file again.
pause
exit /b 1

:local_python
"dev\.venv\Scripts\python.exe" run.py --open %SARWATCH_ARGS%
goto finished

:python_launcher
py -3 run.py --open %SARWATCH_ARGS%
goto finished

:system_python
python run.py --open %SARWATCH_ARGS%

:finished
set "SARWATCH_EXIT=%ERRORLEVEL%"
if "%SARWATCH_EXIT%"=="0" exit /b 0
echo.
echo SARWatch could not start. The error is shown above.
pause
exit /b %SARWATCH_EXIT%
