"""PDF reading + offline extractive summarization.

Uses pypdf for text extraction (no GUI automation). The summarizer is a
simple deterministic frequency-scored extractive summarizer so ORBIT can
produce a useful summary fully offline; when a cloud LLM is configured, the
agent brain can instead summarize via the LLM for higher quality.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "is", "are", "was", "were",
    "be", "been", "with", "as", "by", "at", "this", "that", "it", "from", "we", "you", "our", "your",
    "will", "shall", "not", "have", "has", "had", "which", "their", "its",
}


@dataclass
class PdfReadResult:
    text: str
    page_count: int
    pages: list[str]


def read_pdf(path: str | Path) -> PdfReadResult:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return PdfReadResult(text="\n".join(pages), page_count=len(reader.pages), pages=pages)


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def summarize_text(text: str, max_sentences: int = 5) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    words = re.findall(r"[a-zA-Z']+", text.lower())
    freq = Counter(w for w in words if w not in _STOPWORDS and len(w) > 2)
    if not freq:
        return " ".join(sentences[:max_sentences])
    max_freq = max(freq.values())
    for w in freq:
        freq[w] /= max_freq

    scored = []
    for idx, sentence in enumerate(sentences):
        sent_words = re.findall(r"[a-zA-Z']+", sentence.lower())
        score = sum(freq.get(w, 0.0) for w in sent_words)
        # small positional bonus for early sentences (often most informative)
        score += max(0.0, (len(sentences) - idx) / len(sentences)) * 0.1
        scored.append((score, idx, sentence))

    top = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    top_in_order = [s for _, _, s in sorted(top, key=lambda x: x[1])]
    return " ".join(top_in_order)


def summarize_pdf(path: str | Path, max_sentences: int = 5) -> str:
    result = read_pdf(path)
    return summarize_text(result.text, max_sentences=max_sentences)
