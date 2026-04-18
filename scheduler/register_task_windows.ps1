# Registra una tarea programada en Windows que ejecuta el scraper
# diariamente a las 03:00. Ejecutar este script como Administrador.
#
# Uso: .\register_task_windows.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "python"  # Ajustar si usas venv: "$ProjectRoot\.venv\Scripts\python.exe"
$Script = "$ProjectRoot\scheduler\run_update.py"
$LogFile = "$ProjectRoot\data\scheduler.log"

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Script`" >> `"$LogFile`" 2>&1" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At 3:00am

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName "LicitacionesSAP-Update" `
    -Description "Actualización diaria de licitaciones SAP del PLACSP" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Force

Write-Host "Tarea programada 'LicitacionesSAP-Update' registrada." -ForegroundColor Green
Write-Host "Verificar: Get-ScheduledTask -TaskName LicitacionesSAP-Update"
