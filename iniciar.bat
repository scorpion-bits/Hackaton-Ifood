@echo off
rem Duplo clique no Windows: chama o iniciar.ps1 sem exigir mudar a política de execução.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" %*
pause
