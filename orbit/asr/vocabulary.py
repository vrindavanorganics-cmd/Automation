"""Personal vocabulary system.

Keeps RAW TRANSCRIPT (what the ASR model heard) separate from the
INTERPRETED TRANSCRIPT (after correcting known company/product/people names
against the user's personal vocabulary). User corrections are stored as
optional learning data — never auto-applied to retrain a production model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from orbit.memory.store import MemoryStore

DEFAULT_FUZZY_THRESHOLD = 85


@dataclass
class CorrectionResult:
    raw_text: str
    interpreted_text: str
    replacements: list[dict] = field(default_factory=list)


class VocabularyStore:
    """Wraps MemoryStore's vocabulary table with fuzzy correction logic."""

    def __init__(self, memory: MemoryStore, fuzzy_threshold: int = DEFAULT_FUZZY_THRESHOLD):
        self.memory = memory
        self.fuzzy_threshold = fuzzy_threshold

    def add_term(self, term: str, aliases: list[str] | None = None, category: str = "") -> None:
        self.memory.add_vocabulary(term, aliases or [], category)

    def remove_term(self, term: str) -> None:
        self.memory.delete_vocabulary(term)

    def list_terms(self) -> list[dict]:
        return self.memory.list_vocabulary()

    def _all_surface_forms(self) -> dict[str, str]:
        """Maps every alias/term surface form (lowercased) -> canonical term."""
        forms: dict[str, str] = {}
        for entry in self.list_terms():
            forms[entry["term"].lower()] = entry["term"]
            for alias in entry["aliases"]:
                forms[alias.lower()] = entry["term"]
        return forms

    def correct_transcript(self, raw_text: str) -> CorrectionResult:
        """Applies fuzzy word/phrase-level correction against known vocabulary.

        Simple sliding-window approach: for each 1-3 word span in the
        transcript, fuzzy-match against known vocabulary surface forms and
        replace if confidently close enough. Good enough for short command
        transcripts; not a general-purpose NLP correction system.
        """
        forms = self._all_surface_forms()
        if not forms:
            return CorrectionResult(raw_text=raw_text, interpreted_text=raw_text, replacements=[])

        words = raw_text.split()
        choices = list(forms.keys())
        replacements: list[dict] = []
        result_words = list(words)

        for window in (3, 2, 1):
            i = 0
            while i <= len(words) - window:
                span = " ".join(words[i : i + window])
                match = process.extractOne(span.lower(), choices, scorer=fuzz.ratio)
                if match and match[1] >= self.fuzzy_threshold:
                    canonical = forms[match[0]]
                    if canonical.lower() != span.lower():
                        for k in range(window):
                            result_words[i + k] = canonical if k == 0 else ""
                        replacements.append({"span": span, "corrected": canonical, "score": match[1]})
                i += 1

        interpreted = " ".join(w for w in result_words if w != "").strip()
        interpreted = " ".join(interpreted.split())
        return CorrectionResult(raw_text=raw_text, interpreted_text=interpreted, replacements=replacements)

    def record_correction(self, raw_text: str, corrected_text: str, approve_for_training: bool = False) -> int:
        """Stores a user-supplied correction as optional learning data.

        This does NOT retrain or modify the production ASR model. It only
        accumulates candidate data for the offline training pipeline
        (orbit.training.pipeline), which requires an explicit run.
        """
        return self.memory.add_correction(raw_text, corrected_text, approved_for_training=approve_for_training)

    def list_corrections(self, approved_only: bool = False) -> list[dict]:
        return self.memory.list_corrections(approved_only=approved_only)
