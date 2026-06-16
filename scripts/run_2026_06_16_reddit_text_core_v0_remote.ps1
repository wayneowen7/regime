$ErrorActionPreference = "Stop"

$Remote = "lenovo@10.147.18.151"
$RemoteDir = "/home/lenovo/code/regime_reddit_text_core_v0"
$Python = "/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python"
$EnvPython = "env PYTHONPATH=pilot/src $Python"
$Stamp = "20260616_reddit_text_core_v0"

function Invoke-Remote($Command, $TimeoutSeconds = 1800) {
    ssh $Remote "cd $RemoteDir && timeout ${TimeoutSeconds}s $Command"
}

$ArchiveName = "regime_reddit_text_core_v0_$(Get-Date -Format yyyyMMdd_HHmmss).tgz"
$ArchivePath = Join-Path $env:TEMP $ArchiveName

tar -czf $ArchivePath docs pilot tests scripts data/raw/reddit_text_core_v0.jsonl
scp $ArchivePath "${Remote}:/tmp/$ArchiveName"
ssh $Remote "mkdir -p $RemoteDir && tar -xzf /tmp/$ArchiveName -C $RemoteDir"

Invoke-Remote "$EnvPython -m unittest discover -s tests -p 'test_reddit_text_core.py' -v" 300

$Runs = @(
    @("qwen2.5:7b", "qwen25_7b", 30),
    @("llama3.2:latest", "llama32", 30)
)

foreach ($Run in $Runs) {
    $Model = $Run[0]
    $ModelSlug = $Run[1]
    $Limit = $Run[2]
    $FullOutput = "data/raw/remote_${Stamp}_${ModelSlug}_${Limit}case_full.json"
    $SummaryOutput = "pilot/results/remote_${Stamp}_${ModelSlug}_${Limit}case_summary.json"
    Write-Output "Running Reddit-Text-Core v0 $ModelSlug limit=$Limit"
    Invoke-Remote "$EnvPython -m regime_pilot.run_reddit_text_benchmark --cases data/raw/reddit_text_core_v0.jsonl --policy-cards pilot/data/reddit_bao/reddit_bao_policy_cards.json --model '$Model' --conditions comment_only,public_policy --limit-cases $Limit --output-full $FullOutput --summary $SummaryOutput" 2400
}

scp "${Remote}:$RemoteDir/pilot/results/remote_${Stamp}_*summary.json" "pilot/results/"
scp "${Remote}:$RemoteDir/data/raw/remote_${Stamp}_*full.json" "data/raw/"
