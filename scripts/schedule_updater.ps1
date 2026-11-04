<#
.SYNOPSIS
    Registers a Windows Scheduled Task to run update_data.py weekly.
.DESCRIPTION
    Creates a scheduled task "FootballValueWeeklySync" that triggers every Monday at 04:00 AM,
    invoking the project virtualenv Python to run update_data.py --rebuild.
#>

$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python.exe).Source
}

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "update_data.py --rebuild" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 4am
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Write-Host "Registering Scheduled Task 'FootballValueWeeklySync'..." -ForegroundColor Cyan
Register-ScheduledTask -TaskName "FootballValueWeeklySync" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Weekly sync and model rebuild for Football Value Predictor" -Force

Write-Host "Successfully registered scheduled task! It will run every Monday at 4:00 AM." -ForegroundColor Green
