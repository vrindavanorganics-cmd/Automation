"""Intent parsing: turns an (already vocabulary-corrected) transcript into a
structured Intent the planner can act on.

Rule-based on purpose: fast, fully offline, debuggable, and works across
English / Hindi / Hinglish / mixed-language commands without needing a
cloud call for simple actions. Complex/ambiguous commands fall back to
`action="unknown"` so the planner (or an LLM-backed planner later) can
decide what to do.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Each action maps to trigger phrases in English, Hindi (devanagari + roman),
# and common Hinglish variants. Matching is substring/regex based on the
# lowercased, whitespace-normalized transcript.
ACTION_PATTERNS: dict[str, list[str]] = {
    "open_app": [r"\bopen\b", r"\bkholo\b", r"\bkhol do\b", r"\bkhol\b", r"\bstart\b", r"\blaunch\b"],
    "close_app": [r"\bclose\b", r"\bband karo\b", r"\bband kar do\b", r"\bexit\b", r"\bquit\b"],
    "search": [r"\bsearch\b", r"\bkhojo\b", r"\bkhoj\b", r"\bfind\b", r"\bdhundo\b"],
    "create_folder": [r"\bcreate (a )?folder\b", r"\bfolder banao\b", r"\bnew folder\b", r"\bfolder bana do\b"],
    "create_file": [r"\bcreate (a )?file\b", r"\bfile banao\b", r"\bnew file\b"],
    "read_pdf": [r"\bread (this |the )?pdf\b", r"\bpdf padho\b", r"\bopen (this |the )?pdf\b"],
    "summarize": [r"\bsummariz", r"\bsummary banao\b", r"\bsankshep\b", r"\bsummary do\b"],
    "create_excel": [r"\bcreate (an |a )?excel\b", r"\bexcel sheet banao\b", r"\bmake (a |an )?spreadsheet\b"],
    "draft_email": [r"\bdraft (an |a )?email\b", r"\bemail draft\b", r"\bemail likho\b", r"\bcompose (an |a )?email\b"],
    "send": [r"\bsend it\b", r"\bsend (the )?email\b", r"\bbhej do\b", r"\bbhejo\b", r"^send$"],
    "cancel_send": [
        r"\bdon'?t send\b",
        r"\bdo not send\b",
        r"\bmat bhejo\b",
        r"\bmat bhejna\b",
        r"\bcancel\b",
    ],
    "organize_files": [r"\borganiz", r"\bfiles ko organize\b", r"\barrange (the )?files\b"],
    "research": [r"\bresearch\b", r"\bresearch karo\b"],
    "run_skill": [r"\brepeat\b", r"\brun (the )?(.+ )?(skill|workflow)\b", r"\bwaisa hi karo\b"],
    "stop": [r"\bstop\b", r"\bruko\b", r"\bruk jao\b", r"\bband karo\b"],
    "read_email": [r"\bcheck (my )?(gmail|email|inbox)\b", r"\bemail check karo\b", r"\bread (my )?email\b"],
}

# Order matters: more specific intents should be checked before generic ones.
ACTION_PRIORITY = [
    "stop",
    "cancel_send",
    "send",
    "draft_email",
    "read_email",
    "create_folder",
    "create_excel",
    "create_file",
    "summarize",
    "read_pdf",
    "organize_files",
    "search",
    "research",
    "run_skill",
    "close_app",
    "open_app",
]

# Common app names/aliases used to extract an `app` entity from open/close commands.
KNOWN_APPS = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "msedge": "Microsoft Edge",
    "excel": "Microsoft Excel",
    "word": "Microsoft Word",
    "notion": "Notion",
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "whatsapp": "WhatsApp",
    "file explorer": "File Explorer",
    "explorer": "File Explorer",
    "gmail": "Gmail",
    "outlook": "Outlook",
}

LANGUAGE_HINDI_HINTS = [
    "kholo", "karo", "banao", "bhejo", "bhej do", "ruko", "dhundo", "khojo", "mat", "hai", "kar do",
]

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
EMAIL_BODY_RE = re.compile(r"\b(?:as|saying)\s+(.+?)\s+to\s+\S+@\S+", re.IGNORECASE)
EMAIL_SUBJECT_RE = re.compile(r"\babout\s+(.+?)(?:\s+to\s+\S+@\S+|$)", re.IGNORECASE)
PDF_FILE_HINT_RE = re.compile(r"\b(?:this|the)\s+([\w\s]+?)\s+pdf\b", re.IGNORECASE)
PDF_FOLDER_HINT_RE = re.compile(
    r"\bin\s+(downloads|desktop|documents)(?:\s+folder)?\b", re.IGNORECASE
)


@dataclass
class Intent:
    raw_text: str
    interpreted_text: str
    action: str
    entities: dict = field(default_factory=dict)
    language_guess: str = "en"
    confidence: float = 0.5


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def guess_language(text: str) -> str:
    if DEVANAGARI_RE.search(text):
        return "hi"
    lowered = text.lower()
    hindi_hits = sum(1 for w in LANGUAGE_HINDI_HINTS if w in lowered)
    if hindi_hits >= 2:
        return "hi"
    if hindi_hits == 1:
        return "hinglish"
    return "en"


def _extract_app(text: str) -> Optional[str]:
    for alias, canonical in sorted(KNOWN_APPS.items(), key=lambda kv: -len(kv[0])):
        if alias in text:
            return canonical
    return None


def _extract_folder_name(text: str) -> Optional[str]:
    match = re.search(r"folder (?:called|named)\s+([\w \-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_email_fields(text: str) -> dict:
    entities: dict = {}
    email_match = EMAIL_RE.search(text)
    if email_match:
        entities["to"] = email_match.group(0)

    body_match = EMAIL_BODY_RE.search(text)
    if body_match:
        entities["body"] = body_match.group(1).strip()

    subject_match = EMAIL_SUBJECT_RE.search(text)
    if subject_match:
        entities["subject"] = subject_match.group(1).strip()
    elif "body" in entities:
        entities["subject"] = entities["body"][:60]

    return entities


def _extract_pdf_hints(text: str) -> dict:
    entities: dict = {}
    hint_match = PDF_FILE_HINT_RE.search(text)
    if hint_match:
        hint = hint_match.group(1).strip()
        if hint:
            entities["file_hint"] = hint
    folder_match = PDF_FOLDER_HINT_RE.search(text)
    if folder_match:
        entities["folder_hint"] = folder_match.group(1).strip().lower()
    return entities


def parse_intent(raw_text: str, interpreted_text: Optional[str] = None) -> Intent:
    interpreted_text = interpreted_text if interpreted_text is not None else raw_text
    normalized = _normalize(interpreted_text)
    cased = re.sub(r"\s+", " ", interpreted_text.strip())
    language = guess_language(raw_text)

    action = "unknown"
    for candidate in ACTION_PRIORITY:
        patterns = ACTION_PATTERNS[candidate]
        if any(re.search(p, normalized) for p in patterns):
            action = candidate
            break

    entities: dict = {}
    if action in ("open_app", "close_app"):
        app = _extract_app(normalized)
        if app:
            entities["app"] = app
    if action == "create_folder":
        name = _extract_folder_name(cased)
        if name:
            entities["folder_name"] = name
    if action in ("search", "research"):
        # everything after the trigger verb, best-effort (case preserved)
        m = re.search(r"(?:search|find|research|khojo|dhundo)\s+(?:for\s+)?(.+)", cased, re.IGNORECASE)
        if m:
            entities["query"] = m.group(1).strip()
    if action == "draft_email":
        entities.update(_extract_email_fields(cased))
    if action in ("read_pdf", "summarize"):
        entities.update(_extract_pdf_hints(cased))

    confidence = 0.85 if action != "unknown" else 0.2

    return Intent(
        raw_text=raw_text,
        interpreted_text=interpreted_text,
        action=action,
        entities=entities,
        language_guess=language,
        confidence=confidence,
    )
