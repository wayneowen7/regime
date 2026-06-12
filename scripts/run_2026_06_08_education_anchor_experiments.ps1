param(
    [string]$Remote = "lenovo@10.147.18.151",
    [string]$RemoteDir = "/home/lenovo/code/regime_boundary_sufficiency"
)

$ErrorActionPreference = "Stop"

$Python = "/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python"
$EnvPython = "env PYTHONPATH=pilot/src $Python"
$Cases = "pilot/data/boundary_sufficiency_cases_education_extended.jsonl"
$CurrentGuidance = "pilot/data/boundary_sufficiency_guidance_current_education_extended.jsonl"
$StaleGuidance = "pilot/data/boundary_sufficiency_guidance_stale_education_extended.jsonl"

function Invoke-RemoteCommand {
    param([string]$Command)
    ssh $Remote "cd $RemoteDir && $Command"
}

function Run-BoundaryLlm {
    param(
        [string]$ModelSlug,
        [string]$Model,
        [string]$PolicySlug,
        [string]$PoliciesPath,
        [string]$PoolName,
        [string]$PrecedentsPath
    )

    $Output = "pilot/results/remote_20260608_${ModelSlug}_education_ext_${PolicySlug}_${PoolName}_full_on.json"
    $Command = "timeout 2400s $EnvPython -m regime_pilot.run_llm_pilot --policies $PoliciesPath --precedents $PrecedentsPath --test-cases $Cases --model '$Model' --conditions policy_only,naive_memory,regime_aware --top-k 3 --limit-cases 16 --memory-view operational --policy-view full --stale-warning on --output $Output"
    Invoke-RemoteCommand $Command
}

Write-Host "Checking remote SSH..."
ssh $Remote "mkdir -p $RemoteDir"

Write-Host "Packing workspace subset..."
$ArchiveName = "regime_boundary_education_anchor_$(Get-Date -Format yyyyMMdd_HHmmss).tgz"
$ArchivePath = Join-Path $env:TEMP $ArchiveName
tar -czf $ArchivePath docs pilot tests scripts

Write-Host "Uploading $ArchivePath..."
scp $ArchivePath "${Remote}:/tmp/$ArchiveName"
ssh $Remote "tar -xzf /tmp/$ArchiveName -C $RemoteDir"

Write-Host "Running remote unit tests..."
Invoke-RemoteCommand "timeout 300s $EnvPython -m unittest discover -s tests -v"

Write-Host "Running education extended LLM matrix..."
Run-BoundaryLlm "qwen25_7b" "qwen2.5:7b" "abstract" "pilot/data/policies.json" "current" $CurrentGuidance
Run-BoundaryLlm "qwen25_7b" "qwen2.5:7b" "abstract" "pilot/data/policies.json" "stale" $StaleGuidance
Run-BoundaryLlm "llama32" "llama3.2:latest" "abstract" "pilot/data/policies.json" "current" $CurrentGuidance
Run-BoundaryLlm "llama32" "llama3.2:latest" "abstract" "pilot/data/policies.json" "stale" $StaleGuidance

Run-BoundaryLlm "qwen25_7b" "qwen2.5:7b" "clarified" "pilot/data/boundary_sufficiency_policies_clarified.json" "current" $CurrentGuidance
Run-BoundaryLlm "qwen25_7b" "qwen2.5:7b" "clarified" "pilot/data/boundary_sufficiency_policies_clarified.json" "stale" $StaleGuidance
Run-BoundaryLlm "llama32" "llama3.2:latest" "clarified" "pilot/data/boundary_sufficiency_policies_clarified.json" "current" $CurrentGuidance
Run-BoundaryLlm "llama32" "llama3.2:latest" "clarified" "pilot/data/boundary_sufficiency_policies_clarified.json" "stale" $StaleGuidance

$AbstractInputs = @(
    "pilot/results/remote_20260608_qwen25_7b_education_ext_abstract_current_full_on.json",
    "pilot/results/remote_20260608_qwen25_7b_education_ext_abstract_stale_full_on.json",
    "pilot/results/remote_20260608_llama32_education_ext_abstract_current_full_on.json",
    "pilot/results/remote_20260608_llama32_education_ext_abstract_stale_full_on.json"
) -join " "

$ClarifiedInputs = @(
    "pilot/results/remote_20260608_qwen25_7b_education_ext_clarified_current_full_on.json",
    "pilot/results/remote_20260608_qwen25_7b_education_ext_clarified_stale_full_on.json",
    "pilot/results/remote_20260608_llama32_education_ext_clarified_current_full_on.json",
    "pilot/results/remote_20260608_llama32_education_ext_clarified_stale_full_on.json"
) -join " "

Write-Host "Analyzing education extended runs..."
Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs $AbstractInputs --cases $Cases --output pilot/results/remote_20260608_education_ext_abstract_full_on_analysis.json"
Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs $ClarifiedInputs --cases $Cases --output pilot/results/remote_20260608_education_ext_clarified_full_on_analysis.json"
Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_20260608_education_ext_abstract_full_on_analysis.json --candidate pilot/results/remote_20260608_education_ext_clarified_full_on_analysis.json --baseline-name education_ext_abstract_full_on --candidate-name education_ext_clarified_full_on --output pilot/results/remote_20260608_education_ext_abstract_vs_clarified_full_on_comparison.json"

Write-Host "Analyzing BARRED-like anchor overlay..."
Invoke-RemoteCommand "timeout 300s $EnvPython -m regime_pilot.analyze_barred_like_anchor_review --result pilot/results/remote_20260608_barred_like_qwen25_7b_4families_2candidates.json --review pilot/data/barred_like_anchor_review_qwen25_7b_20260608.jsonl --output pilot/results/remote_20260608_barred_like_anchor_review_qwen25_7b_analysis.json"

Write-Host "Downloading result files..."
scp "${Remote}:$RemoteDir/pilot/results/remote_20260608_*education_ext*.json" "pilot/results/"
scp "${Remote}:$RemoteDir/pilot/results/remote_20260608_barred_like_anchor_review_qwen25_7b_analysis.json" "pilot/results/"

Write-Host "Done."
