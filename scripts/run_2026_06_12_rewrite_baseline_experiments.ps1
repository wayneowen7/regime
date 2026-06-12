$ErrorActionPreference = "Stop"

$Remote = "lenovo@10.147.18.151"
$RemoteDir = "/home/lenovo/code/regime_boundary_sufficiency"
$Python = "/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python"
$EnvPython = "env PYTHONPATH=pilot/src $Python"
$Stamp = "20260612_rewrite_baseline"
$PolarStamp = "20260612_polar_compact"

function Invoke-Remote($Command, $TimeoutSeconds = 1800) {
    ssh $Remote "cd $RemoteDir && timeout ${TimeoutSeconds}s $Command"
}

$ArchiveName = "regime_rewrite_baseline_$(Get-Date -Format yyyyMMdd_HHmmss).tgz"
$ArchivePath = Join-Path $env:TEMP $ArchiveName

tar -czf $ArchivePath docs pilot tests scripts
scp $ArchivePath "${Remote}:/tmp/$ArchiveName"
ssh $Remote "mkdir -p $RemoteDir && tar -xzf /tmp/$ArchiveName -C $RemoteDir"

Invoke-Remote "$EnvPython -m unittest discover -s tests -v" 300

Invoke-Remote "$EnvPython -m regime_pilot.rewrite_baselines --source-policies pilot/data/action_granularity_policies_abstract.json --target-policies pilot/data/action_granularity_policies_action_rubric.json --output-policies pilot/data/rewrite_template_policies_action_granularity.json --output-sidecar pilot/data/rewrite_template_sidecar_action_granularity.json --mode template" 300
Invoke-Remote "$EnvPython -m regime_pilot.rewrite_baselines --source-policies pilot/data/action_granularity_policies_abstract.json --target-policies pilot/data/action_granularity_policies_action_rubric.json --output-policies pilot/data/rewrite_length_matched_policies_action_granularity.json --output-sidecar pilot/data/rewrite_length_matched_sidecar_action_granularity.json --mode length_matched" 300

$Runs = @(
    @("qwen2.5:7b", "qwen25_7b", "rewrite_template", "pilot/data/rewrite_template_policies_action_granularity.json"),
    @("qwen2.5:7b", "qwen25_7b", "rewrite_length_matched", "pilot/data/rewrite_length_matched_policies_action_granularity.json"),
    @("llama3.2:latest", "llama32", "rewrite_template", "pilot/data/rewrite_template_policies_action_granularity.json"),
    @("llama3.2:latest", "llama32", "rewrite_length_matched", "pilot/data/rewrite_length_matched_policies_action_granularity.json")
)

foreach ($Run in $Runs) {
    $Model = $Run[0]
    $ModelSlug = $Run[1]
    $PolicySlug = $Run[2]
    $PolicyPath = $Run[3]
    $Output = "pilot/results/remote_${Stamp}_${ModelSlug}_${PolicySlug}_12case_full_on.json"
    Write-Output "Running $ModelSlug $PolicySlug"
    Invoke-Remote "$EnvPython -m regime_pilot.run_llm_pilot --policies $PolicyPath --precedents pilot/data/action_granularity_guidance_action.jsonl --test-cases pilot/data/action_granularity_cases.jsonl --model '$Model' --conditions policy_only,naive_memory,regime_aware --top-k 3 --limit-cases 12 --memory-view operational --policy-view full --stale-warning on --output $Output" 1800
}

Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_rewrite_template_12case_full_on.json pilot/results/remote_${Stamp}_llama32_rewrite_template_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_rewrite_template_2model_analysis.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.analyze_boundary_sufficiency --inputs pilot/results/remote_${Stamp}_qwen25_7b_rewrite_length_matched_12case_full_on.json pilot/results/remote_${Stamp}_llama32_rewrite_length_matched_12case_full_on.json --cases pilot/data/action_granularity_cases.jsonl --output pilot/results/remote_${Stamp}_rewrite_length_matched_2model_analysis.json" 300

Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${PolarStamp}_abstract_2model_analysis.json --candidate pilot/results/remote_${Stamp}_rewrite_template_2model_analysis.json --baseline-name abstract --candidate-name rewrite_template --output pilot/results/remote_${Stamp}_abstract_vs_rewrite_template_comparison.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${PolarStamp}_abstract_2model_analysis.json --candidate pilot/results/remote_${Stamp}_rewrite_length_matched_2model_analysis.json --baseline-name abstract --candidate-name rewrite_length_matched --output pilot/results/remote_${Stamp}_abstract_vs_rewrite_length_matched_comparison.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${Stamp}_rewrite_template_2model_analysis.json --candidate pilot/results/remote_${PolarStamp}_polar_compact_2model_analysis.json --baseline-name rewrite_template --candidate-name polar_compact --output pilot/results/remote_${Stamp}_rewrite_template_vs_polar_compact_comparison.json" 300
Invoke-Remote "$EnvPython -m regime_pilot.compare_boundary_sufficiency --baseline pilot/results/remote_${Stamp}_rewrite_length_matched_2model_analysis.json --candidate pilot/results/remote_${PolarStamp}_polar_compact_2model_analysis.json --baseline-name rewrite_length_matched --candidate-name polar_compact --output pilot/results/remote_${Stamp}_rewrite_length_matched_vs_polar_compact_comparison.json" 300

scp "${Remote}:$RemoteDir/pilot/results/remote_${Stamp}_*.json" "pilot/results/"
scp "${Remote}:$RemoteDir/pilot/data/rewrite_*action_granularity.json" "pilot/data/"
