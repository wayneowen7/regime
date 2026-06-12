param(
    [string]$Remote = "lenovo@10.147.18.151",
    [string]$RemoteDir = "/home/lenovo/code/regime_boundary_sufficiency"
)

$ErrorActionPreference = "Stop"

$Python = "/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python"
$EnvPython = "env PYTHONPATH=pilot/src $Python"
$ArchiveName = "regime_boundary_next_$(Get-Date -Format yyyyMMdd_HHmmss).tgz"
$ArchivePath = Join-Path $env:TEMP $ArchiveName

function Invoke-RemoteCommand {
    param([string]$Command)
    ssh $Remote "cd $RemoteDir && $Command"
}

function Run-ClarifiedLlmPilot {
    param(
        [string]$ModelSlug,
        [string]$Model,
        [string]$PoolName,
        [string]$PrecedentsPath
    )

    $Output = "pilot/results/remote_20260608_${ModelSlug}_boundary_${PoolName}_clarified_full_on.json"
    $Command = "timeout 1800s $EnvPython -m regime_pilot.run_llm_pilot --policies pilot/data/boundary_sufficiency_policies_clarified.json --precedents $PrecedentsPath --test-cases pilot/data/boundary_sufficiency_cases.jsonl --model '$Model' --conditions policy_only,naive_memory,regime_aware --top-k 3 --limit-cases 12 --memory-view operational --policy-view full --stale-warning on --output $Output"
    Invoke-RemoteCommand $Command
}

Write-Host "Checking remote SSH..."
ssh $Remote "mkdir -p $RemoteDir"

Write-Host "Packing workspace subset..."
tar -czf $ArchivePath docs pilot tests scripts

Write-Host "Uploading $ArchivePath..."
scp $ArchivePath "${Remote}:/tmp/$ArchiveName"
ssh $Remote "tar -xzf /tmp/$ArchiveName -C $RemoteDir"

Write-Host "Running remote unit tests..."
Invoke-RemoteCommand "timeout 300s $EnvPython -m unittest discover -s tests -v"

Write-Host "Running clarified policy contrast..."
$AbstractInputs = @(
    "pilot/results/remote_20260608_qwen25_7b_boundary_current_full_on.json",
    "pilot/results/remote_20260608_qwen25_7b_boundary_stale_full_on.json",
    "pilot/results/remote_20260608_llama32_boundary_current_full_on.json",
    "pilot/results/remote_20260608_llama32_boundary_stale_full_on.json"
) -join " "

Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs $AbstractInputs --cases pilot/data/boundary_sufficiency_cases.jsonl --output pilot/results/remote_20260608_boundary_sufficiency_abstract_full_on_analysis_for_compare.json"

Run-ClarifiedLlmPilot "qwen25_7b" "qwen2.5:7b" "current" "pilot/data/boundary_sufficiency_guidance_current.jsonl"
Run-ClarifiedLlmPilot "qwen25_7b" "qwen2.5:7b" "stale" "pilot/data/boundary_sufficiency_guidance_stale.jsonl"
Run-ClarifiedLlmPilot "llama32" "llama3.2:latest" "current" "pilot/data/boundary_sufficiency_guidance_current.jsonl"
Run-ClarifiedLlmPilot "llama32" "llama3.2:latest" "stale" "pilot/data/boundary_sufficiency_guidance_stale.jsonl"

$ClarifiedInputs = @(
    "pilot/results/remote_20260608_qwen25_7b_boundary_current_clarified_full_on.json",
    "pilot/results/remote_20260608_qwen25_7b_boundary_stale_clarified_full_on.json",
    "pilot/results/remote_20260608_llama32_boundary_current_clarified_full_on.json",
    "pilot/results/remote_20260608_llama32_boundary_stale_clarified_full_on.json"
) -join " "

Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs $ClarifiedInputs --cases pilot/data/boundary_sufficiency_cases.jsonl --output pilot/results/remote_20260608_boundary_sufficiency_clarified_full_on_analysis.json"
Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_20260608_boundary_sufficiency_abstract_full_on_analysis_for_compare.json --candidate pilot/results/remote_20260608_boundary_sufficiency_clarified_full_on_analysis.json --baseline-name abstract_full_on --candidate-name clarified_full_on --output pilot/results/remote_20260608_boundary_sufficiency_abstract_vs_clarified_full_on_comparison.json"

Write-Host "Running BARRED-like front-half audit..."
$Families = "future_reform_vs_current_voting_instruction,obvious_satire_vs_deceptive_notice,prediction_opinion_vs_false_certification,education_critique_quote_vs_endorsement_or_mobilization"
Invoke-RemoteCommand "timeout 1800s $EnvPython -m regime_pilot.barred_like --policies pilot/data/policies.json --families $Families --model 'qwen2.5:7b' --num-candidates 2 --regime-id election_integrity_period_v2 --judge-count 2 --judge-variants policy_clause,boundary_variable --output pilot/results/remote_20260608_barred_like_qwen25_7b_4families_2candidates.json"

Write-Host "Downloading result files..."
scp "${Remote}:$RemoteDir/pilot/results/remote_20260608_*clarified*.json" "pilot/results/"
scp "${Remote}:$RemoteDir/pilot/results/remote_20260608_boundary_sufficiency_abstract_full_on_analysis_for_compare.json" "pilot/results/"
scp "${Remote}:$RemoteDir/pilot/results/remote_20260608_boundary_sufficiency_abstract_vs_clarified_full_on_comparison.json" "pilot/results/"
scp "${Remote}:$RemoteDir/pilot/results/remote_20260608_barred_like_*.json" "pilot/results/"

Write-Host "Done."
