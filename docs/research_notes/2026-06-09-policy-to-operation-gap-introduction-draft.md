# Policy-to-Operation Gap 论文初稿片段

日期：2026-06-09

## 推荐标题

**From Policy to Operation: Probing Specification Gaps in LLM Content Moderation**

## 一句话 thesis

LLM 内容审核失败并不只来自模型能力不足，还可能来自高层自然语言 policy 到可部署 moderation decision 之间的 specification gap；我们提出 boundary/action probing，系统测试这些 gap，并用 action instability 与 minimal clarification rescue 验证其是否源于 policy 未充分规定。

## Abstract 草稿

Large language models are increasingly used as content moderation systems, where high-level natural-language policies must be translated into operational decisions such as allow, contextualize, restrict, remove, or escalate. However, moderation policies are often written as broad normative instructions rather than complete operational specifications. This creates a policy-to-operation specification gap: a policy may fail to fully define the boundary variables needed to classify borderline cases, or the action granularity needed to choose an appropriate enforcement response.

We propose boundary/action probing, a policy specification testing methodology for LLM-based moderation. The method constructs matched probes that minimally vary candidate boundary variables while holding other factors constant, and uses action-space analysis to test whether similar cases receive stable and policy-grounded operational decisions. We measure boundary and action instability to expose regions where the policy permits inconsistent or unanchored decisions, and introduce minimal clarification rescue to test whether small policy clarifications improve executability. Across pilot moderation scenarios, this framing shifts evaluation from asking only whether a model follows a given policy to asking whether the policy itself contains enough operational information for reliable deployment. Our work provides a diagnostic layer for auditing moderation policies before policy-conditioned judging, memory retrieval, or synthetic data generation.

## Introduction 草稿

Large language models are increasingly used to support content moderation. Instead of training a separate classifier for every policy change, modern moderation systems can directly condition an LLM on a natural-language policy and ask it to judge user content. This makes LLM moderation flexible and attractive for dynamic policies, custom safety requirements, and rapidly evolving trust-and-safety domains.

Yet real moderation deployment requires more than a high-level judgment that content is “safe” or “unsafe.” A deployed system must produce operational decisions: allow the content, add context, restrict distribution, remove it, or escalate it to human review. These actions often depend on subtle boundary variables such as whether a claim is quoted for critique or endorsed, whether a satirical notice is obviously fictional or deceptively official-looking, whether a political statement discusses future reform or gives misleading current voting instructions, and whether an educational explanation becomes mobilization.

Existing LLM moderation work often assumes that once a policy is given, the main question is whether the model follows it. Runtime policy-conditioned systems ask the model to judge content under a user-defined policy. Synthetic guardrail pipelines generate boundary examples from a policy and use them for training or verification. These approaches are useful, but they rely on a shared premise: the policy text is sufficiently specified to support the boundary being judged, generated, or trained.

We argue that this premise deserves direct testing. Natural-language moderation policies are often written as broad normative instructions rather than complete operational specifications. They may be sufficient to describe a risk category while insufficient to define the precise boundary variables and enforcement actions needed for deployment. We call this the **policy-to-operation specification gap**.

This gap has two distinct layers. The first is **boundary sufficiency**: whether the policy sufficiently specifies which variables determine whether a case crosses a moderation boundary. The second is **action-granularity sufficiency**: whether the policy sufficiently specifies which operational action should be taken once the boundary is reached. A policy may correctly distinguish intervention from non-intervention while still failing to distinguish allow from contextualize, or remove from escalate.

To study this problem, we propose **boundary/action probing**, a policy specification testing methodology for LLM moderation. Instead of building a large benchmark of naturally occurring cases, we construct matched probes that minimally vary candidate boundary variables. These probes localize underspecified regions of the policy: when a model shifts decisions across irrelevant changes, fails to shift across relevant changes, or oscillates among action labels, the probe identifies where the policy-to-operation mapping is unstable.

We further introduce **minimal clarification rescue** as a diagnostic test. If adding a small policy clarification reduces boundary error or action instability, this provides evidence that the original failure was not merely a model capability issue, but a policy specification gap. Conversely, if clarification does not help, the failure may reflect instruction following limitations, ambiguous action taxonomy, poor prompt format, or genuinely unresolved policy-owner judgment.

Our work reframes LLM moderation evaluation. Rather than only asking whether a model follows a given policy, we ask whether the policy itself is sufficiently specified for operational use. This diagnostic layer is useful before deploying policy-conditioned judges, retrieving historical cases, or generating synthetic training data: all of these mechanisms can silently fill missing policy branches with unanchored assumptions if the policy is underspecified.

## Contributions 草稿

1. We introduce the **policy-to-operation specification gap** in LLM content moderation, characterizing the mismatch between high-level natural-language policies and operational moderation decisions.

2. We decompose this gap into **boundary sufficiency** and **action-granularity sufficiency**, showing that a policy may support coarse intervention decisions while remaining insufficient for fine-grained actions.

3. We propose **boundary/action probing**, a methodology that uses matched probes and action-space analysis to localize underspecified policy regions.

4. We introduce diagnostic metrics including decision-family error, exact-action error, action instability, current-clarification rescue, and stale-guidance harm.

5. We position policy specification testing as a preflight audit for policy-conditioned judging, memory retrieval, and synthetic guardrail data generation.

## 论文结构建议

### 1. Introduction

目标：建立 policy-to-operation gap，说明它为什么不是普通 instruction following，也不是单纯数据集问题。

关键段落：

- LLM moderation 的灵活性；
- 真实部署需要 operational action；
- policy 不是完整 operational specification；
- gap 的两层：boundary + action；
- 我们的方法：boundary/action probing；
- 实验预览；
- contributions。

### 2. Related Work

建议分四组：

1. Policy-conditioned moderation / Policy-as-Prompt
2. Dynamic/custom guardrails: DynaGuard, BARRED
3. Policy operationalization and evolving policies
4. LLM evaluation, instruction following, and specification testing

核心写法：

```text
These works improve how models execute, adapt to, or learn from policies. In contrast, we test whether the policy itself is sufficiently specified before it is executed, retrieved against, or used to synthesize examples.
```

### 3. Problem Formulation

定义：

```text
Policy P
Content x
Boundary variables z
Action space A = {allow, contextualize, restrict, remove, escalate}
Operational decision y in A
```

问题：

```text
Does P sufficiently constrain f_P(x) -> y?
```

两类 gap：

- boundary gap：P 未规定关键 z；
- action gap：P 规定了风险但未规定 action threshold。

### 4. Method: Boundary/Action Probing

包括：

- matched probe construction；
- boundary variable isolation；
- action-space evaluation；
- minimal clarification test；
- stale/data-first guidance stress test。

### 5. Pilot Study

报告现有结果：

- 12-case boundary sufficiency；
- clarified policy contrast；
- education action-granularity signal；
- BARRED-like anchor overlay。

### 6. Action-Granularity Validation

下一步新增实验：

- abstract policy；
- boundary-clarified policy；
- boundary + action-rubric policy；
- 2 个模型；
- 8-12 个 action probes。

关键表：

| policy condition | decision-family error | exact-action error | action instability |
|---|---:|---:|---:|
| abstract | high | high | high |
| boundary-clarified | low | still high | medium/high |
| boundary + action rubric | low | lower | lower |

### 7. Discussion

重点：

- 这不是自动恢复 true policy；
- 模糊性有时是治理上的刻意选择；
- specification testing 可以帮助 policy owner 找到需要人工判断的位置；
- synthetic data 和 memory 需要先通过 policy sufficiency preflight。

## 需要避免的 overclaim

- 不说我们自动决定正确 policy。
- 不说所有审核失败都来自 policy underspecification。
- 不说 BARRED、DynaGuard 或 synthetic data 错。
- 不说 action instability 一定等于模型随机性。
- 不把 minimal clarification rescue 写成严格因果证明。
- 不把 12/16-case pilot 写成最终大规模结论。

## 给领导看的简洁版

我们研究的是 LLM 内容审核中的一个前置问题：平台给出的自然语言 policy 是否已经足以支撑真实部署中的审核动作。真实审核不只是判断内容是否违规，还要决定 allow、加提示、限制传播、删除或升级人工。很多 policy 能说明大方向，但没有把边界变量和动作阈值写到足够可执行的程度。我们提出 boundary/action probing，用成对案例探索这些缺口，并通过最小政策澄清测试验证这些缺口是否可修复。这个工作不是替平台写规则，而是帮助发现当前规则哪里还没有写到足以被大模型稳定执行。
