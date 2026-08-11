"""WER/CER computation for evaluating ASR model versions. Real, deterministic,
fully testable — no network or GPU required.
"""
from __future__ import annotations


def _edit_distance(ref: list, hyp: list) -> int:
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return _edit_distance(ref_words, hyp_words) / len(ref_words)


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref_chars = list(reference.strip())
    hyp_chars = list(hypothesis.strip())
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    return _edit_distance(ref_chars, hyp_chars) / len(ref_chars)


def command_accuracy(pairs: list[tuple[str, str]]) -> float:
    """pairs: list of (expected_intent_action, actual_intent_action)."""
    if not pairs:
        return 0.0
    correct = sum(1 for expected, actual in pairs if expected == actual)
    return correct / len(pairs)
