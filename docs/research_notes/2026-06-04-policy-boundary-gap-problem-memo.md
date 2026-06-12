# 当政策文本不是判断边界：动态内容审核中的 Policy Boundary Gap

日期：2026-06-04

## 当前判断

我们目前最值得推进的研究问题，不再是「给内容审核 Agent 加长期记忆」，也不只是「为当前政策生成案例」。

更准确的主问题是：

> 动态、垂域、客制化内容审核系统必须把自然语言政策转化为可执行判断边界；但文本政策、真实政策意图、模型实际形成的判断边界之间经常存在缺口。

我们暂时把这个问题称为：

> **Policy Boundary Gap in Dynamic Moderation**

中文可以写作：

> **动态内容审核中的政策边界缺口**

这个问题的关键不是「缺少样本」本身，而是：

> 样本、prompt、历史案例、合成数据、微调、debate 等机制都在试图把抽象政策压成可执行边界；但这个压实过程本身可能不可靠。

因此，我们要研究的不是某一种特定方法，而是 LLM 审核系统从 policy text 到 executable boundary 的 operationalization 过程。

## 一句话问题

英文版：

> Dynamic moderation systems must operationalize abstract, changing, and customized natural-language policies into executable decision boundaries. However, the same policy text may admit multiple plausible boundaries, and LLM-based systems can silently instantiate one through prompting, retrieval, synthetic data, or fine-tuning.

中文版：

> 动态内容审核系统需要把抽象、变化、客制化的自然语言政策转化为可执行判断边界；但同一段政策文本可能对应多个合理边界，而大模型系统会通过 prompt、检索、合成数据或微调，悄悄选择其中一个边界。

## 三个边界

为了把问题说清楚，需要区分三种边界。

| 边界 | 含义 | 风险 |
|---|---|---|
| True Policy Boundary | 平台、客户、监管、业务真正想执行的审核边界 | 通常没有完全显式化，只存在于政策制定者意图、历史执行经验、申诉反馈和业务风险判断中 |
| Textual Policy Boundary | 写在政策文档、prompt 或 rule set 里的自然语言边界 | 往往抽象、压缩、缺少边界例子和优先级细节 |
| Model-Operationalized Boundary | 模型根据文本政策、prompt、示例、检索结果、合成数据或微调实际形成的判断边界 | 可能稳定但错误，也可能在模型、prompt、样本分布变化时漂移 |

我们关心的 gap 不是单一误差，而是这些边界之间的不一致：

```text
True Policy Boundary
        !=
Textual Policy Boundary
        !=
Model-Operationalized Boundary
```

这比「政策模糊」更具体。政策模糊只是现象；Policy Boundary Gap 关注的是：当模糊政策被 LLM 系统强制转化成分类边界时，系统会如何补全缺失信息，以及这个补全是否可靠。

## 为什么这是内容审核里的核心问题

内容审核不是普通分类任务。普通分类任务通常假设类别定义相对稳定，标注数据能够代表目标边界。但内容审核政策有几个特殊性质：

1. **政策会变**

   选举、公共安全事件、监管变化、平台策略调整、地区法律差异，都会改变同类内容的处置边界。

2. **政策是垂域和客制化的**

   不同平台、产品、社区、客户和地区，对同一内容可能有不同阈值。例如医疗建议、政治讨论、成人内容、金融建议、青少年安全等场景，边界高度依赖业务目标。

3. **政策文本天然压缩**

   政策文档不可能枚举所有 case。它通常写成「禁止误导性投票信息」「允许新闻、教育或批评语境」「限制危险操作性指导」这样的高层表达。

4. **模型必须输出具体动作**

   审核系统不能回答「这个边界不清楚」。它通常必须输出 `allow`、`contextualize`、`restrict`、`remove`、`escalate` 等动作。

5. **边界错误具有系统性风险**

   如果模型把抽象政策补全成错误边界，错误会通过批量审核、合成训练、微调或在线部署被放大。

所以真正的问题不是「模型能不能读政策」，而是：

> 模型读完政策后形成了什么边界？这个边界是谁决定的？它和真实政策意图是否一致？

## 什么是 boundary case

这里的 boundary 不是抽象机器学习里的任意分类边界，而是政策中最容易发生可执行解释分歧的区域。

典型例子：

| 场景 | 边界问题 |
|---|---|
| 选举信息 | 未来制度改革讨论 vs 当前投票误导 |
| 政治讽刺 | 明显 satire vs 可误导事实声明 |
| 仇恨内容 | 新闻、教育、批评性引用 vs 宣扬、认同、动员 |
| 自伤内容 | 支持性表达 vs 操作性指导 |
| 医疗建议 | 个人经历分享 vs 高风险具体建议 |
| 金融内容 | 一般财经评论 vs 个性化投资建议 |
| 暴力内容 | 新闻报道、历史讨论 vs 煽动或协助现实暴力 |

这些 boundary case 的共同点是：

> 只有高层政策文本时，多个判断都可能看起来有道理；但实际系统必须选择一个。

因此，boundary case 是观察 policy operationalization gap 的显微镜。

## 为什么不是简单的「政策写清楚就好了」

评审可能会质疑：这是不是只是政策文档写得不好？

我们的回答应该是：不是。

首先，真实内容审核政策不可能完全形式化。开放世界内容不断变化，政策总会存在未枚举边界。即使政策写得很长，也只能把一部分边界提前显式化。

其次，动态政策和客制化政策会持续引入新边界。每次新平台需求、新地区规则、新事件风险、新业务策略出现，都会出现新的 operationalization gap。

第三，LLM 系统会放大这个问题。传统人审流程中，模糊政策可能通过人工讨论、升级、申诉、质检逐步澄清；但 LLM 审核系统会在推理时立即把模糊政策转成一个确定输出。这个自动补全过程就是新的研究对象。

所以我们不是在研究「人类政策写作缺陷」，而是在研究：

> 当不完全政策被 LLM 系统自动执行时，系统如何隐式选择边界，以及这种选择如何被发现、度量和控制。

## 现有工作如何处理这个 gap

### DynaGuard

DynaGuard 的重要贡献是把审核从固定安全类别推进到用户自定义自然语言政策。它证明了 dynamic guardian model 可以根据当前 policy 判断内容。

它处理 gap 的方式是：

```text
current policy text + current content -> guardian decision
```

也就是说，它更强调 runtime policy-conditioned judging。

但 DynaGuard 没有把「policy text 是否足以确定目标边界」作为主问题。它默认用户定义的 policy 能够充分表达想执行的审核边界。我们的空间在于研究这个默认前提什么时候不成立。

相关链接：[DynaGuard: A Dynamic Guardian Model With User-Defined Policies](https://arxiv.org/abs/2509.02563)

### BARRED

BARRED 的重要贡献是针对 custom guardrails，用 domain dimension decomposition 和 multi-agent debate 生成合成训练数据，再微调小 guardrail model。

它处理 gap 的方式是：

```text
task description / policy
        -> synthetic boundary examples
        -> debate verification
        -> fine-tuned guardrail
```

这条路线很有启发：它承认 prompt-only 在 boundary case 上不稳定，也承认人工标注成本高，所以试图用合成数据和 debate 把政策压实成训练集。

但它的关键假设是：

> 由模型生成、模型辩论、模型验证得到的边界，足够接近真实政策边界。

这正是我们可以追问的地方。模型 debate 可以提升内部一致性，但内部一致性不等于外部政策有效性。合成数据的「良品率」低，也可能不是工程瑕疵，而是 policy boundary gap 的信号：政策文本本身不足以支持稳定生成。

相关链接：[BARRED: Synthetic Training of Custom Policy Guardrails via Asymmetric Debate](https://arxiv.org/abs/2604.25203)

### OpenAI GPT-4 moderation practice

OpenAI 关于 GPT-4 内容审核的实践更接近一个稳健答案：让 GPT-4 根据政策打标，再把模型判断和人类/专家标签之间的 discrepancy 用于澄清政策。

它处理 gap 的方式是：

```text
policy + examples -> model labels
model-human discrepancy -> policy clarification
```

这说明工业实践里并没有完全取消权威来源，而是把模型用于加速发现歧义、解释差异和迭代政策。

相关链接：[Using GPT-4 for content moderation](https://openai.com/blog/using-gpt-4-for-content-moderation)

## 我们与这些工作的关系

我们的目标不是替代 DynaGuard 或 BARRED，而是研究它们共同依赖的一步：

```text
natural-language policy -> executable moderation boundary
```

可以这样定位：

| 工作类型 | 默认问题 | 我们追问的问题 |
|---|---|---|
| DynaGuard 类 policy-conditioned judge | 给定 policy，模型如何执行 | 给定 policy 是否足以确定执行边界 |
| BARRED 类 synthetic guardrail training | 如何低成本生成训练数据 | 生成数据形成的边界是否真的是目标边界 |
| OpenAI 类 policy refinement loop | 如何减少人工审核成本 | 哪些 discrepancy 暴露了 policy boundary gap |
| 历史案例 / memory | 如何利用具体案例提高一致性 | 历史案例是否把旧边界带入新政策 |

这样写有一个好处：我们不需要证明「大家一定会用历史审核数据」。历史案例只是众多 operationalization mechanisms 之一。prompt、合成数据、few-shot examples、retrieval、fine-tuning、debate 都可能把 policy text 转成某个边界。

## 我们当前 pilot 能支持什么

现有 pilot 不能证明一个完整论文结论，但可以作为 motivating evidence。

目前比较稳的观察是：

1. **policy-only 在 boundary case 上可能不够具体**

   在 case-guidance mini-study 中，qwen2.5:7b 面对明显 satire 的 election meme 时，policy-only 曾输出过度严格的 `remove`，而 current-policy-valid guidance 能把它修正为 `contextualize`。

2. **stale guidance 可以把判断推向旧边界**

   在 qwen2.5 stress setting 中，`brief policy + no stale warning + naive memory` 下，模型显式使用旧 normal-regime precedent，把当前 election-integrity period 中应 `remove` 的 case 判断为 `contextualize`。

3. **强模型并不总是脆弱**

   qwen2.5:7b 在完整 policy 或有 stale warning 的条件下比较稳定。这说明我们不能写成「强模型一定被历史案例污染」。

4. **风险是有条件的**

   风险更可能出现在 policy 较抽象、boundary case 本身模糊、示例来源未标注、历史示例语义高度相似但政策已变的条件下。

这些观察支持的问题不是：

> 历史记忆一定有害。

而是：

> LLM moderation 的执行边界会受到 policy wording、case guidance、历史示例和运行上下文影响；在动态政策下，这些机制可能产生与当前真实政策不一致的 operationalized boundary。

## 更强的研究问题

暂时不要先定方法，可以把研究问题写成以下四个层次。

### RQ1: Boundary multiplicity

同一段自然语言审核政策是否会诱导多个合理但不同的执行边界？

可观察信号：

- 不同模型对同一 boundary case 判断不一致。
- 同一模型在不同 prompt wording 下判断不一致。
- 同一模型在有无示例、有无合成数据、有无历史案例时判断边界移动。
- 输出 decision 一样，但 rationale 中引用的边界原则不同。

### RQ2: Boundary instability under policy change

当政策 regime 变化时，模型是否会继续沿用旧 regime 的 operationalized boundary？

可观察信号：

- 对语义相似但政策 regime 不同的 case，模型迁移了旧理由。
- 历史案例或旧合成样本加入上下文后，模型更倾向旧边界。
- policy diff 很小但执行边界变化很大时，模型不能稳定捕捉变化。

### RQ3: Synthetic boundary risk

合成数据和 debate 是否可能把模糊政策压成一个看似一致、但缺少真实权威支撑的伪边界？

可观察信号：

- 生成样本在模型间看似一致，但与少量专家边界决策冲突。
- debate 提高 label agreement，却没有提高与真实 policy owner 意图的一致性。
- 样本良品率随 policy ambiguity 增加而下降。
- 微调后模型更稳定，但稳定在错误边界上。

### RQ4: Gap localization

能否系统性定位哪些政策条款、维度组合或 case family 最容易产生 boundary gap？

可观察信号：

- 某些 policy clauses 反复对应高 disagreement。
- 某些语境变量，例如 satire、教育、新闻、意图、时间敏感性，会显著改变判断。
- boundary probes 能聚类出政策中缺失的例外、优先级或阈值。

## 为什么这个问题有发表空间

这个问题有潜力，是因为它不只是内容审核工程问题，而是 LLM safety 中一个更一般的问题：

> Natural-language policies are not executable specifications.

在任何 guardrail、agent policy、AI governance、platform compliance 场景里，都有类似转换：

```text
policy text -> model behavior
```

但现有工作通常直接优化后半段：

- 让模型更会遵守规则；
- 让 guardrail 更准；
- 让 synthetic data 更便宜；
- 让 fine-tuned classifier 更快。

我们的切入点是前半段：

> policy text 本身能否唯一地、稳定地、可迁移地决定执行边界？

如果不能，那么很多后续方法的高准确率可能只是 benchmark 上的边界对齐，而不是对真实政策意图的对齐。

这使得我们的论文可以不是单纯方法论文，而是：

1. 一个问题定义；
2. 一个系统性现象研究；
3. 一套 boundary-gap 测量框架；
4. 一个或多个轻量修复机制作为 proof-of-concept。

## 我们不应该主张什么

为了避免被评审抓住逻辑漏洞，需要明确不主张：

- 不主张模型可以无权威地自动恢复真实政策边界。
- 不主张合成数据一定没有价值。
- 不主张 BARRED 这类方法错误，只主张它们没有充分研究 synthetic boundary 的可靠性条件。
- 不主张历史案例一定会污染模型。
- 不主张大厂一定会召回历史审核数据。
- 不主张 policy-only 一定失败。
- 不主张我们的当前 pilot 已经能支撑最终论文结论。

更稳的主张是：

> 当 policy text 欠规范时，任何把它转化为 executable boundary 的机制都可能隐式引入额外假设。我们研究这些假设如何出现、何时不稳定、如何被系统性发现。

## 与「case guidance」旧 framing 的关系

旧的 case-guidance gap 可以作为这个问题的一个子问题：

```text
Policy Boundary Gap
        includes
Case-Guidance Gap
```

也就是说：

- case guidance 是帮助模型形成执行边界的一种方式；
- historical cases 是可能带入旧边界的一种信息源；
- current-valid cases 是一种可能的边界澄清材料；
- BARRED 式 synthetic data 是另一种边界澄清材料；
- DynaGuard 式 policy-conditioned judging 是直接由文本政策形成边界。

主问题上移后，我们不再被「历史审核数据是否会被召回」这个行业假设绑住。

## 初步案例表述

### Case 1: 未来改革讨论 vs 当前投票误导

政策文本可能写：

> 禁止误导用户投票时间、地点、方式或资格的信息；允许关于选举制度改革的公共讨论。

边界 case：

```text
Weekday voting is hard. We should support Sunday voting in future elections.
```

这更像未来改革讨论。

另一个 case：

```text
Do not vote today. Wait for Sunday voting instead.
```

这在当前投票日可能是投票误导。

文本政策看似清楚，但真正的边界依赖时间语境、行动指令、当前选举状态和用户可能后果。模型如果看到旧 regime 下「Sunday voting reform」的允许案例，可能把当前误导性指令也解释成普通改革讨论。

这个例子展示：

```text
semantic similarity != boundary validity
```

### Case 2: 明显 satire vs 可误导事实声明

政策文本可能写：

> 限制可能误导选民的候选人资格、投票有效性和选举程序相关虚假信息。

边界 case：

```text
A clearly edited meme says Candidate A was disqualified by a fictional space court and votes for A vanish into orbit.
```

这更像明显 satire，可能需要 contextualize 而不是 remove。

另一个 case：

```text
Candidate A was disqualified this morning. Votes for A will not count today.
```

这更像可误导事实声明，可能需要 restrict 或 remove。

如果 policy 只说「限制误导性候选人资格声明」，模型可能过度执行，把 satire 也 remove。合成数据如果主要生成严肃误导样本，也可能把边界训练得过严。

这个例子展示：

```text
policy text may be current, but still under-operationalized
```

### Case 3: 教育引用 vs 宣扬认同

政策文本可能写：

> 禁止宣扬或支持仇恨组织；允许新闻、教育、批评和反仇恨语境下的引用。

边界 case：

```text
This history class slide shows a hate symbol while explaining how propaganda worked.
```

另一个 case：

```text
This post shows the same symbol with praise and recruitment language.
```

这里的文本符号可能相同，但边界依赖语境、意图、框架和行动号召。仅靠关键词或语义相似度会失败；仅靠抽象 policy 也可能不稳定。

这个例子展示：

```text
same surface content, different policy boundary
```

## 下一步最小验证目标

在暂时不确定最终方法的情况下，下一步可以先做一个问题确认型 study。

目标不是证明我们的系统最好，而是证明 Policy Boundary Gap 是真实、可观测、可度量的问题。

最小 study 可以回答：

1. 同一 policy text 下，不同模型和 prompt 是否形成不同 operationalized boundary？
2. policy wording 轻微变化是否导致 boundary case 判断明显移动？
3. 加入不同来源的 guidance，例如历史案例、当前案例、合成案例，是否会改变边界？
4. BARRED 式生成/debate 是否会在高模糊 policy 下产生低良品率或伪一致性？
5. 少量权威边界决策是否能显著改变模型或生成数据形成的边界？

这里的「少量权威」不是大规模人工流水线，而是研究上必须存在的 anchor。没有 anchor，就无法判断模型形成的边界是否接近真实政策意图。

## 推荐的论文主线

当前最推荐的主线可以写成：

> We identify the Policy Boundary Gap in dynamic moderation: natural-language policies often under-specify executable decision boundaries, while LLM-based operationalization mechanisms such as prompting, retrieval, synthetic data generation, debate, and fine-tuning silently instantiate boundaries that may diverge from policy-owner intent. We characterize this gap through boundary probes and study how it manifests under policy change, custom guardrails, and stale or synthetic case guidance.

中文：

> 我们提出动态内容审核中的 Policy Boundary Gap：自然语言政策常常不足以完整规定可执行判断边界，而基于 LLM 的执行机制，例如 prompt、检索、合成数据、辩论和微调，会隐式补全这些边界，并可能偏离政策制定者的真实意图。我们通过边界探针刻画这一缺口，并研究它在政策变更、客制化 guardrail、历史案例和合成案例中的表现。

这条主线的优势：

- 不依赖历史案例召回一定存在。
- 不和 DynaGuard 正面重复，因为我们研究 policy-conditioned judging 的前提是否稳。
- 不和 BARRED 正面重复，因为我们研究 synthetic boundary 是否可靠，而不是继续优化合成数据。
- 可以从内容审核出发，但抽象到更一般的 natural-language policy operationalization。
- 可以先做 evaluation / phenomenon paper，后续再自然引出方法。

## 当前结论

这个方向值得推进。

但当前最重要的不是立刻设计复杂方法，而是先把问题做实：

1. 明确 boundary gap 的形式化定义。
2. 构造能暴露 gap 的 boundary case families。
3. 对比不同 operationalization mechanisms。
4. 证明 gap 不是单个模型失误，而是政策文本到模型执行之间的系统性现象。
5. 再决定后续方法是 stress testing、minimal policy repair、boundary probe generation，还是 synthetic-data reliability auditing。

一句话：

> 我们要研究的不是「怎样让模型审核更准」这么泛的问题，而是「当政策文本不足以定义边界时，LLM 审核系统会怎样隐式补全边界，以及这种补全何时可靠」。
