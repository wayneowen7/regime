param(
    [string]$Queue = "pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl",
    [string]$Output = "data/raw/reddit_bao_pullpush_full_stream.jsonl",
    [string]$Summary = "data/raw/reddit_bao_pullpush_full_stream_summary.json",
    [string]$SeedFrom = "data/raw/reddit_bao_pullpush_balanced_600.jsonl",
    [string]$Python = "python",
    [double]$SleepSeconds = 1.0,
    [int]$MaxRetries = 5,
    [double]$RetrySleepSeconds = 15.0,
    [double]$Timeout = 20.0,
    [int]$CheckpointEvery = 25,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $RepoRoot "data\raw\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$OutputPath = Join-Path $RepoRoot $Output
$SummaryPath = Join-Path $RepoRoot $Summary
$SeedPath = Join-Path $RepoRoot $SeedFrom
$LogPath = Join-Path $LogDir ("reddit_pullpush_background_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SummaryPath) | Out-Null

$WouldSeed = (-not (Test-Path -LiteralPath $OutputPath)) -and (Test-Path -LiteralPath $SeedPath)
if ((-not $DryRun) -and $WouldSeed) {
    Copy-Item -LiteralPath $SeedPath -Destination $OutputPath
}

$Command = @"
`$ErrorActionPreference = 'Continue'
Set-Location '$RepoRoot'
`$env:PYTHONPATH = 'pilot/src'
& '$Python' -m regime_pilot.reddit_pullpush_resolver --queue '$Queue' --output '$Output' --summary '$Summary' --resume --stream --checkpoint-every $CheckpointEvery --sleep-seconds $SleepSeconds --max-retries $MaxRetries --retry-sleep-seconds $RetrySleepSeconds --timeout $Timeout *> '$LogPath'
"@

$Result = [ordered]@{
    repo_root = $RepoRoot
    queue = $Queue
    output = $OutputPath
    summary = $SummaryPath
    log = $LogPath
    seeded_from = $(if ($WouldSeed -or ((Test-Path -LiteralPath $SeedPath) -and (Test-Path -LiteralPath $OutputPath))) { $SeedPath } else { $null })
    command = "$Python -m regime_pilot.reddit_pullpush_resolver --queue $Queue --output $Output --summary $Summary --resume --stream --checkpoint-every $CheckpointEvery --sleep-seconds $SleepSeconds --max-retries $MaxRetries --retry-sleep-seconds $RetrySleepSeconds --timeout $Timeout"
}

if ($DryRun) {
    $Result["dry_run"] = $true
    $Result | ConvertTo-Json -Depth 4
    exit 0
}

$Process = Start-Process `
    -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command) `
    -WindowStyle Hidden `
    -PassThru

$Result["pid"] = $Process.Id
$Result["dry_run"] = $false
$Result | ConvertTo-Json -Depth 4
