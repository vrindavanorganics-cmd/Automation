"""Registry of legally-usable open datasets for optional ASR fine-tuning.

Every entry tracks source, license, language, and usage rights so ORBIT
never trains on data without a clear legal basis. Nothing here is
downloaded automatically — `downloaded`/`local_path` are only set after an
explicit, user-initiated download step (see orbit.training.pipeline).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DatasetEntry:
    name: str
    source_url: str
    license: str
    language: str
    usage_rights: str
    downloaded: bool = False
    local_path: Optional[str] = None


DATASET_REGISTRY: list[DatasetEntry] = [
    DatasetEntry(
        name="Mozilla Common Voice (English)",
        source_url="https://commonvoice.mozilla.org/en/datasets",
        license="CC0-1.0",
        language="en",
        usage_rights="Public domain; free for training/commercial use",
    ),
    DatasetEntry(
        name="Mozilla Common Voice (Hindi)",
        source_url="https://commonvoice.mozilla.org/hi/datasets",
        license="CC0-1.0",
        language="hi",
        usage_rights="Public domain; free for training/commercial use",
    ),
    DatasetEntry(
        name="OpenSLR SLR103 (Hindi ASR corpus)",
        source_url="https://www.openslr.org/103/",
        license="CC-BY-SA 4.0",
        language="hi",
        usage_rights="Attribution + share-alike required for derivatives",
    ),
    DatasetEntry(
        name="OpenSLR SLR118 (Hindi/Indian-language speech)",
        source_url="https://www.openslr.org/118/",
        license="CC-BY 4.0",
        language="hi",
        usage_rights="Attribution required",
    ),
    DatasetEntry(
        name="ORBIT approved corrections",
        source_url="local:orbit-memory-corrections",
        license="Proprietary (user-owned)",
        language="mixed",
        usage_rights="User's own correction data — usable only with explicit approval per correction",
    ),
]


def list_datasets(language: Optional[str] = None) -> list[DatasetEntry]:
    if language is None:
        return list(DATASET_REGISTRY)
    return [d for d in DATASET_REGISTRY if d.language == language or d.language == "mixed"]
