# Registra una tarea programada en Windows que ejecuta el scraper
# diariamente a las 03:00. Ejecutar este script como Administrador.
#
# Uso: .\register_task_windows.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
# Usar el Python del venv para aislar dependencias
$Python = "$ProjectRoot\.venv\Scripts\python.exe"
$Script = "$ProjectRoot\scheduler\run_update.py"
$LogFile = "$ProjectRoot\data\scheduler.log"
$RotateScript = {
    # Rotación simple: si el log supera 5 MB, lo renombramos y empezamos uno nuevo
    if ((Get-Item $LogFile -ErrorAction SilentlyContinue).Length -gt 5MB) {
        $archive = $LogFile -replace '\.log$', "_$(Get-Date -Format 'yyyyMMdd').log"
        Rename-Item -Path $LogFile -NewName $archive -Force
    }
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -Command `"& { $RotateScript }; & '$Python' '$Script' >> '$LogFile' 2>&1`"" `
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
