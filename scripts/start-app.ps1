param(
    [ValidateSet('start', 'stop')][string]$Action = 'start',
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [string]$Database
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$pythonPath = Join-Path $backendRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Backend Python is missing. Run uv sync --extra dev from backend first.'
}
if (-not $Database) {
    if ($env:GAME_REVIEW_ANALYZER_DATABASE) {
        $Database = $env:GAME_REVIEW_ANALYZER_DATABASE
        if (-not [IO.Path]::IsPathRooted($Database)) {
            $Database = Join-Path $backendRoot $Database
        }
    } else {
        $Database = Join-Path $backendRoot 'data/game-review-analyzer.sqlite3'
    }
}
$databasePath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Database)
if ($databasePath.Contains('"')) { throw 'Database path must not contain a double quote.' }
if ($Action -eq 'stop') {
    & $pythonPath -m game_review_analyzer.infrastructure.server --stop --database $databasePath
    if ($LASTEXITCODE -ne 0) { throw 'Could not confirm stop. Check whether this database has a supervised server.' }
    exit 0
}
$arguments = @('-m', 'game_review_analyzer.infrastructure.server', '--supervise',
    '--port', $Port, '--database', ('"' + $databasePath + '"'))
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments `
    -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2
$process.Refresh()
if ($process.HasExited) {
    throw "Server did not start (exit $($process.ExitCode)). Check port/database ownership and $databasePath.server.log."
}
Write-Output "Server supervisor started. URL: http://127.0.0.1:$Port/"
Write-Output "Lifecycle diagnostics: $databasePath.server.log"
