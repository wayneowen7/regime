$ErrorActionPreference = "Stop"

$Remote = "lenovo@10.147.18.151"
$RemoteDir = "/home/lenovo/code/regime_boundary_sufficiency"
$Python = "/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python"
$EnvPython = "env PYTHONPATH=pilot/src $Python"
$Stamp = "20260609_action_granularity"

function Invoke-Remote($Command, $TimeoutSeconds = 1800) {
    ssh $Remote "cd $RemoteDir && timeout ${TimeoutSeconds}s $Command"
}

$ArchiveName = "regime_action_granularity_$(Get-Date -Format yyyyMMdd_HHmmss).tgz"
$ArchivePath = Join-Path $env:TEMP $ArchiveName

tar -czf $ArchivePath docs pilot tests scripts
scp $ArchivePath "${Remote}:/tmp/$ArchiveName"
ssh $Remote "mkdir -p $RemoteDir && tar -xzf /tmp/$ArchiveName -C $RemoteDir"

Invoke-Remote "$EnvPython -m unittest discover -s tests -v" 300

$Runs = @(
    @("qwen2.5:7b", "qwen25_7b", "abstract", "pilot/data/action_granularity_policies_abstract.json", "pilot/data/action_granularity_guidance_boundary.jsonl"),
    @("qwen2.5:7b", "qwen25_7b", "boundary", "pilot/data/action_granularity_policies_boundary_clarified.json", "pilot/data/action_granularity_guidance_boundary.jsonl"),
    @("qwen2.5:7b", "qwen25_7b", "action_rubric", "pilot/data/action_granularity_policies_action_rubric.json", "pilot/data/action_granularity_guidance_action.jsonl"),
    @("llama3.2:latest", "llama32", "abstract", "pilot/data/action_granularity_policies_abstract.json", "pilot/data/action_granularity_guidance_boundary.jsonl"),
    @("llama3.2:latest", "llama32", "boundary", "pilot/data/action_granularity_policies_boundary_clarified.json", "pilot/data/action_granularity_guidance_boundary.jsonl"),
    @("llama3.2:latest", "llama32", "action_rubric", "pilot/data/action_granularity_policies_action_rubric.json", "pilot/data/action_granularity_guidance_action.jsonl")
)

foreach ($Run in $Runs) {
    $Model = $Run[0]
    $ModelSlug = $Run[1]
    $PolicySlug = $Run[2]
    $PolicyPath = $Run[3]
    $PrecedentsPath = $Run[4]
    $Output = "pilot/results/remote_${Stamp}_${ModelSlug}_action_granularity_${PolicySlug}_12case_full_on.json"
    Write-Output "Running $ModelSlug $PolicySlug"
    Invoke-Remote "$EnvPython -m regime_pilot.run_llm_pilot --policies $PolicyPath --precedents $PrecedentsPath --test-cases pilot/data/action_granularity_cases.jsonl --model '$Model' --conditions policy_only,naive_memory,regime_aware --top-k 3 --limit-cases 12 --memory-view operational --policy-view full --stale-warning on --output $Output" 1800
}

Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_action_granularity_abstract_12case_full_on.json pilot/results/remote_${Stamp}_llama32_action_granularity_abstract_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_action_granularity_abstract_2model_analysis.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_action_granularity_boundary_12case_full_on.json pilot/results/remote_${Stamp}_llama32_action_granularity_boundary_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_action_granularity_boundary_2model_analysis.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_action_granularity_action_rubric_12case_full_on.json pilot/results/remote_${Stamp}_llama32_action_granularity_action_rubric_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_action_granularity_action_rubric_2model_analysis.json" 300

Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${Stamp}_action_granularity_abstract_2model_analysis.json --candidate pilot/results/remote_${Stamp}_action_granularity_boundary_2model_analysis.json --baseline-name abstract --candidate-name boundary --output pilot/results/remote_${Stamp}_action_granularity_abstract_vs_boundary_comparison.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${Stamp}_action_granularity_boundary_2model_analysis.json --candidate pilot/results/remote_${Stamp}_action_granularity_action_rubric_2model_analysis.json --baseline-name boundary --candidate-name action_rubric --output pilot/results/remote_${Stamp}_action_granularity_boundary_vs_action_rubric_comparison.json" 300

scp "${Remote}:$RemoteDir/pilot/results/remote_${Stamp}_*action_granularity*.json" "pilot/results/"
