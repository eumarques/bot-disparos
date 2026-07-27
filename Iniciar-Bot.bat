@echo off
chcp 65001 >nul
title Bot de Disparos - Telegram
cd /d "%~dp0"

echo ==================================================
echo    BOT DE DISPAROS - TELEGRAM
echo ==================================================
echo.

REM --- 1. Procurar o Python instalado no computador -------------------------
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [ERRO] O Python nao foi encontrado neste computador.
  echo.
  echo   1^) Baixe o Python em: https://www.python.org/downloads/
  echo   2^) Durante a instalacao, MARQUE a opcao "Add Python to PATH".
  echo   3^) Depois de instalar, rode este arquivo novamente.
  echo.
  pause
  exit /b 1
)

REM --- 2. Na primeira vez: criar o ambiente e instalar tudo -----------------
if not exist ".venv\Scripts\python.exe" (
  echo Primeira execucao detectada.
  echo Preparando o ambiente e baixando as dependencias...
  echo Isso pode demorar alguns minutos ^(so acontece uma vez^).
  echo.
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar o ambiente virtual.
    pause
    exit /b 1
  )
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul 2>nul
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERRO] Falha ao instalar as dependencias. Verifique a internet e tente de novo.
    pause
    exit /b 1
  )
  echo.
  echo Ambiente pronto!
) else (
  call ".venv\Scripts\activate.bat"
)

REM --- 3. Garantir que o arquivo .env exista --------------------------------
if not exist ".env" (
  if exist ".env.example" copy ".env.example" ".env" >nul
  echo.
  echo [ATENCAO] O arquivo de configuracao ".env" foi criado.
  echo Abra ele e cole o TOKEN do seu bot em TELEGRAM_BOT_TOKEN antes de agendar disparos.
  echo.
)

REM --- 4. Criar o atalho na Area de Trabalho (se ainda nao existir) ----------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $p=Join-Path $d 'Bot de Disparos.lnk'; if(-not (Test-Path $p)){$w=New-Object -ComObject WScript.Shell; $l=$w.CreateShortcut($p); $l.TargetPath='%~f0'; $l.WorkingDirectory='%~dp0'; $ico='%~dp0bot-icon.ico'; if(Test-Path $ico){$l.IconLocation=$ico}; $l.Description='Ligar o Bot de Disparos do Telegram'; $l.Save(); Write-Host 'Atalho \"Bot de Disparos\" criado na Area de Trabalho.'}" 2>nul

REM --- 5. Abrir o navegador sozinho assim que o bot subir -------------------
start "" /min powershell -NoProfile -Command "Start-Sleep 4; Start-Process 'http://127.0.0.1:5000'"

REM --- 6. Ligar o bot ------------------------------------------------------
echo.
echo --------------------------------------------------
echo   BOT LIGADO! O painel vai abrir no navegador.
echo.
echo   Endereco do painel:  http://127.0.0.1:5000
echo.
echo   ^>^>^>  Para DESLIGAR o bot, feche esta janela.  ^<^<^<
echo --------------------------------------------------
echo.
python app.py

echo.
echo O bot foi encerrado. Pode fechar esta janela.
pause
