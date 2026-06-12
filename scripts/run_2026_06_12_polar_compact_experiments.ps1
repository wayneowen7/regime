$ErrorActionPreference = "Stop"

$Remote = "lenovo@10.147.18.151"
$RemoteDir = "/home/lenovo/code/regime_boundary_sufficiency"
$Python = "/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python"
$EnvPython = "env PYTHONPATH=pilot/src $Python"
$Stamp = "20260612_polar_compact"

function Invoke-Remote($Command, $TimeoutSeconds = 1800) {
    ssh $Remote "cd $RemoteDir && timeout ${TimeoutSeconds}s $Command"
}

$ArchiveName = "regime_polar_compact_$(Get-Date -Format yyyyMMdd_HHmmss).tgz"
$ArchivePath = Join-Path $env:TEMP $ArchiveName

tar -czf $ArchivePath docs pilot tests scripts
scp $ArchivePath "${Remote}:/tmp/$ArchiveName"
ssh $Remote "mkdir -p $RemoteDir && tar -xzf /tmp/$ArchiveName -C $RemoteDir"

Invoke-Remote "$EnvPython -m unittest discover -s tests -v" 300

Invoke-Remote "$EnvPython -m regime_pilot.polar_compact --policies pilot/data/action_granularity_policies_action_rubric.json --output-policies pilot/data/polar_compact_policies_action_granularity.json --output-sidecar pilot/data/polar_compact_sidecar_action_granularity.json --cases pilot/data/action_granularity_cases.jsonl --output-contrast-sets pilot/data/polar_compact_contrast_sets_action_granularity.json" 300

$Runs = @(
    @("qwen2.5:7b", "qwen25_7b", "abstract", "pilot/data/action_granularity_policies_abstract.json", "pilot/data/action_granularity_guidance_boundary.jsonl"),
    @("qwen2.5:7b", "qwen25_7b", "action_rubric", "pilot/data/action_granularity_policies_action_rubric.json", "pilot/data/action_granularity_guidance_action.jsonl"),
    @("qwen2.5:7b", "qwen25_7b", "polar_compact", "pilot/data/polar_compact_policies_action_granularity.json", "pilot/data/action_granularity_guidance_action.jsonl"),
    @("llama3.2:latest", "llama32", "abstract", "pilot/data/action_granularity_policies_abstract.json", "pilot/data/action_granularity_guidance_boundary.jsonl"),
    @("llama3.2:latest", "llama32", "action_rubric", "pilot/data/action_granularity_policies_action_rubric.json", "pilot/data/action_granularity_guidance_action.jsonl"),
    @("llama3.2:latest", "llama32", "polar_compact", "pilot/data/polar_compact_policies_action_granularity.json", "pilot/data/action_granularity_guidance_action.jsonl")
)

foreach ($Run in $Runs) {
    $Model = $Run[0]
    $ModelSlug = $Run[1]
    $PolicySlug = $Run[2]
    $PolicyPath = $Run[3]
    $PrecedentsPath = $Run[4]
    $Output = "pilot/results/remote_${Stamp}_${ModelSlug}_${PolicySlug}_12case_full_on.json"
    Write-Output "Running $ModelSlug $PolicySlug"
    Invoke-Remote "$EnvPython -m regime_pilot.run_llm_pilot --policies $PolicyPath --precedents $PrecedentsPath --test-cases pilot/data/action_granularity_cases.jsonl --model '$Model' --conditions policy_only,naive_memory,regime_aware --top-k 3 --limit-cases 12 --memory-view operational --policy-view full --stale-warning on --output $Output" 1800
}

Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_abstract_12case_full_on.json pilot/results/remote_${Stamp}_llama32_abstract_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_abstract_2model_analysis.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_action_rubric_12case_full_on.json pilot/results/remote_${Stamp}_llama32_action_rubric_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_action_rubric_2model_analysis.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_polar_compact_12case_full_on.json pilot/results/remote_${Stamp}_llama32_polar_compact_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_polar_compact_2model_analysis.json" 300

Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${Stamp}_abstract_2model_analysis.json --candidate pilot/results/remote_${Stamp}_polar_compact_2model_analysis.json --baseline-name abstract --candidate-name polar_compact --output pilot/results/remote_${Stamp}_abstract_vs_polar_compact_comparison.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${Stamp}_action_rubric_2model_analysis.json --candidate pilot/results/remote_${Stamp}_polar_compact_2model_analysis.json --baseline-name action_rubric --candidate-name polar_compact --output pilot/results/remote_${Stamp}_action_rubric_vs_polar_compact_comparison.json" 300

scp "${Remote}:$RemoteDir/pilot/results/remote_${Stamp}_*.json" "pilot/results/"
scp "${Remote}:$RemoteDir/pilot/data/polar_compact_*action_granularity.json" "pilot/data/"
