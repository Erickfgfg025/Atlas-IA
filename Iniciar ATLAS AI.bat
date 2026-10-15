@echo off
setlocal EnableExtensions
title ATLAS AI - Inicializador
cd /d "%~dp0"

set "ATLAS_ROOT=%~dp0"
set "PYTHON=%ATLAS_ROOT%.venv\Scripts\python.exe"
set "PYTHONW=%ATLAS_ROOT%.venv\Scripts\pythonw.exe"
set "HEALTH_URL=http://127.0.0.1:8000/health"

rem Create or refresh a normal Windows desktop shortcut.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $shortcut = $shell.CreateShortcut((Join-Path $desktop 'ATLAS AI.lnk')); $shortcut.TargetPath = '%~f0'; $shortcut.WorkingDirectory = '%~dp0'; $shortcut.WindowStyle = 7; $shortcut.Description = 'Iniciar ATLAS AI'; $shortcut.Save()" >nul 2>&1

if not exist "%PYTHON%" (
    echo.
    echo  ATLAS AI - Ambiente Python nao encontrado
    echo  -----------------------------------------
    echo  Nao encontrei: .venv\Scripts\python.exe
    echo.
    echo  Abra o PowerShell nesta pasta e execute:
    echo  py -3.13 -m venv .venv
    echo  .\.venv\Scripts\Activate.ps1
    echo  pip install -e ".[dev]"
    echo.
    pause
    exit /b 1
)

if not exist "%PYTHONW%" (
    echo ERRO: pythonw.exe nao foi encontrado dentro de .venv.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo              ATLAS AI
echo       Inicializando seu assistente
echo  ==========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%HEALTH_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if errorlevel 1 (
    echo [1/2] Iniciando o servidor local...
    start "ATLAS AI - API" /min "%PYTHON%" -m uvicorn atlas.backend.main:app --host 127.0.0.1 --port 8000
) else (
    echo [1/2] Servidor local ja esta ativo.
)

echo [2/2] Aguardando a API ficar pronta...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ready = $false; for ($i = 0; $i -lt 30; $i++) { try { $r = Invoke-WebRequest -UseBasicParsing '%HEALTH_URL%' -TimeoutSec 1; if ($r.StatusCode -eq 200) { $ready = $true; break } } catch {}; Start-Sleep -Seconds 1 }; if ($ready) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Nao foi possivel iniciar a API do ATLAS AI.
    echo  Confira a janela "ATLAS AI - API" para ver o erro.
    echo  Verifique tambem se a porta 8000 esta livre.
    echo.
    pause
    exit /b 1
)

echo Abrindo a interface...
start "" "%PYTHONW%" -m atlas.desktop.app

echo.
echo ATLAS AI iniciado. O atalho "ATLAS AI" foi criado na area de trabalho.
timeout /t 2 /nobreak >nul
exit /b 0
