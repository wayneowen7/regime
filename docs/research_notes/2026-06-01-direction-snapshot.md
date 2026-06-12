# 研究方向快照

日期：2026-06-01

## 当前最佳方向

目前推荐方向是：

> 面向长期内容审核 agent 的 regime-aware precedent memory。

这个方向比通用 agent memory 更窄，但这个窄度是优势，前提是我们充分利用内容审核特有结构：policy、precedent、exception、appeal、policy version 和 stale rationale。

## 为什么选这个方向

原始 `iclr2025_conference.tex` 有一个强 insight：

> Semantic relevance does not imply regime validity.

但是当前 draft 的方法容易被看成 metadata filtering，因为 active regime 是显式的，而且 comparator 已经很强。新 pilot 应把工作从通用 regime-aware memory 重新定位到 moderation precedent memory，让 memory 的操作价值和失败模式更清楚。

## 核心主张

长期内容审核 agent 不应该把所有历史案例都存进一个无差别 precedent pool 中检索。

历史 precedent 有用，因为它能稳定模糊政策边界；但历史 precedent 也危险，因为 policy regime 会改变。正确的 memory system 应该管理 precedent validity across regimes。

## 为什么 DynaGuard 没有完全覆盖

DynaGuard 问的是：

> 给定当前用户定义 policy 和当前内容，guardian model 能否判断这条内容？

我们的问题是：

> 给定一个长期运行、积累了历史 precedent 的审核 agent，哪些过去案例在当前 policy regime 下仍然有效？

这两个问题互补。DynaGuard 是 runtime policy-conditioned judging；本项目是 long-term regime-conditioned memory management。

## 主要风险

最大风险是 simple regime filtering 和 proposed method 表现一样好。

如果发生这种情况，有三个选择：

1. 把论文转为 precedent validity 的 evaluation/phenomenon paper。
2. 加入更难设定：explicit regime label 缺失、不完整或互相冲突。
3. 强化方法：加入 policy-diff reasoning、invariant precedent promotion 或 compatibility judgment。

## 最好的初始论文 framing

较弱 framing 不是：

> 我们做了一个更好的内容审核模型。

更强 framing 是：

> 我们识别并评估了长期内容审核 agent 中的 memory-layer failure mode：stale 但语义相关的 precedent，在产生它的 policy regime 失效后仍可能影响 agent。

## 备选方向

如果 pilot 没有产生需要的 tradeoff，fallback directions 是：

1. **Operationalization sensitivity in moderation evaluation。** 研究同一高层 policy 的不同合理操作化如何改变模型排序。
2. **Policy ambiguity and precedent dependence。** 研究什么时候当前 policy text 不足，需要历史 precedent 来稳定决策。
3. **Moderation memory benchmark。** 构建围绕 policy versioning、precedent validity 和 stale rationale detection 的可控 benchmark。

这些方向作为 method paper 较弱，但作为 evaluation 或 empirical paper 仍有机会。

## 立即下一步

根据以下规格创建并运行 v2 pilot：

`docs/superpowers/specs/2026-06-01-regime-aware-moderation-memory-pilot-design.md`

下一项工作应是 implementation plan，而不是继续高层头脑风暴。
