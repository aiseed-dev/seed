@echo off
chcp 65001 >nul
rem seed のアプリを開く（Windows）。エクスプローラーで二度押しします。
rem 初めての時は、このフォルダーに .venv を作って部品を入れ（数分）、それからアプリを開きます。
rem Opens the seed app (Windows). The first time, it makes .venv here and installs the parts (a few minutes).
rem SEED_OPEN_DRY=1 で、走らせる命令を出すだけにします（何も作らず、開きません）。
setlocal
cd /d "%~dp0"
set "PYTHON_PAGE=https://www.python.org/downloads/windows/"
set "CHECK=import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"

if exist ".venv\Scripts\seed.exe" goto open

if exist ".venv\Scripts\python.exe" goto parts

set "PY="
py -3 -c "%CHECK%" >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python -c "%CHECK%" >nul 2>&1 && set "PY=python"
)
if defined PY goto venv

echo Python 3.11 以上が要ります。開いた頁から入れて、もう一度開いてください。
echo seed needs Python 3.11 or later. Install it from the page that opened, then open this again.
call :run start "" "%PYTHON_PAGE%"
pause
exit /b 1

:venv
echo 初めてなので、部品を入れます（数分かかります）。
echo First time: installing the parts (a few minutes).
call :run %PY% -m venv .venv || goto failed

:parts
call :run ".venv\Scripts\python.exe" -m pip install -e ".[app,server]" || goto failed

:open
call :run ".venv\Scripts\seed.exe" app
exit /b %errorlevel%

:failed
echo 部品を入れられませんでした。上の文を Discord か GitHub の Issues で見せてください。
echo Could not install the parts. Please share the messages above on Discord or GitHub Issues.
pause
exit /b 1

:run
if "%SEED_OPEN_DRY%"=="1" (
    echo + %*
    exit /b 0
)
%*
exit /b %errorlevel%
