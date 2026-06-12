from __future__ import annotations

from dataclasses import dataclass
import re

from regime_pilot.schema import Precedent


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RetrievalResult:
    precedent: Precedent
    score: float


def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def score_precedent(post: str, policy_rule: str, precedent: Precedent) -> float:
    query_tokens = tokenize(post)
    precedent_tokens = tokenize(precedent.post)
    if not query_tokens or not precedent_tokens:
        text_score = 0.0
    else:
        text_score = len(query_tokens & precedent_tokens) / len(query_tokens | precedent_tokens)
    rule_bonus = 1.0 if precedent.policy_rule == policy_rule else 0.0
    return rule_bonus + text_score


def rank_precedents(
    post: str,
    policy_rule: str,
    precedents: list[Precedent],
    top_k: int,
) -> list[RetrievalResult]:
    ranked = [
        RetrievalResult(precedent=precedent, score=score_precedent(post, policy_rule, precedent))
        for precedent in precedents
    ]
    ranked.sort(key=lambda item: (-item.score, item.precedent.case_id))
    return ranked[:top_k]
