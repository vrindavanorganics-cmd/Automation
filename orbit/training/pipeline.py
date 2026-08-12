"""Optional ASR improvement pipeline: DOWNLOAD -> CLEAN -> NORMALIZE ->
SPLIT -> TRAIN/FINE-TUNE -> EVALUATE -> VERSION.

Production models are never auto-trained. `download` and `train` require
network access / a GPU and explicit local execution — they return a
PipelineStageResult explaining that, rather than pretending to succeed.
`clean`, `normalize`, `split`, `evaluate`, and `version` are real,
deterministic, and fully testable here since they only need local text/CSV
data.
"""
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from orbit.training.metrics import character_error_rate, word_error_rate


@dataclass
class PipelineStageResult:
    stage: str
    success: bool
    message: str
    data: dict = field(default_factory=dict)


class ASRTrainingPipeline:
    def __init__(self, workspace_dir: Path | str):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.versions_file = self.workspace_dir / "versions.json"

    # ---- DOWNLOAD ----
    def download(self, dataset_name: str) -> PipelineStageResult:
        return PipelineStageResult(
            stage="download",
            success=False,
            message=(
                f"Downloading '{dataset_name}' requires network access and local disk space, "
                "and must be explicitly run on your Windows PC (or a machine with internet + "
                "storage). Not performed automatically. See README 'ASR training pipeline'."
            ),
        )

    # ---- CLEAN ----
    def clean(self, records: list[str]) -> PipelineStageResult:
        cleaned = []
        for text in records:
            text = re.sub(r"[^\w\s.,!?'-]", "", text, flags=re.UNICODE)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                cleaned.append(text)
        return PipelineStageResult("clean", True, f"Cleaned {len(cleaned)}/{len(records)} record(s)", {"records": cleaned})

    # ---- NORMALIZE ----
    def normalize(self, records: list[str]) -> PipelineStageResult:
        normalized = [r.lower().strip() for r in records]
        return PipelineStageResult("normalize", True, f"Normalized {len(normalized)} record(s)", {"records": normalized})

    # ---- SPLIT ----
    def split(self, records: list[str], train_ratio: float = 0.8, val_ratio: float = 0.1, seed: int = 42) -> PipelineStageResult:
        shuffled = list(records)
        random.Random(seed).shuffle(shuffled)
        n = len(shuffled)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        splits = {
            "train": shuffled[:n_train],
            "val": shuffled[n_train : n_train + n_val],
            "test": shuffled[n_train + n_val :],
        }
        return PipelineStageResult(
            "split",
            True,
            f"Split {n} record(s) into train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])}",
            splits,
        )

    # ---- TRAIN / FINE-TUNE ----
    def train(self, model_base: str, train_records: list[str]) -> PipelineStageResult:
        return PipelineStageResult(
            stage="train",
            success=False,
            message=(
                f"Fine-tuning '{model_base}' on {len(train_records)} record(s) requires a GPU "
                "and must be run explicitly as a local/cloud training job — not performed "
                "automatically inside ORBIT."
            ),
        )

    # ---- EVALUATE ----
    def evaluate(self, pairs: list[tuple[str, str]]) -> PipelineStageResult:
        """pairs: list of (reference_text, hypothesis_text)."""
        if not pairs:
            return PipelineStageResult("evaluate", False, "No evaluation pairs provided")
        wers = [word_error_rate(ref, hyp) for ref, hyp in pairs]
        cers = [character_error_rate(ref, hyp) for ref, hyp in pairs]
        avg_wer = sum(wers) / len(wers)
        avg_cer = sum(cers) / len(cers)
        return PipelineStageResult(
            "evaluate",
            True,
            f"Evaluated {len(pairs)} pair(s): WER={avg_wer:.3f}, CER={avg_cer:.3f}",
            {"wer": avg_wer, "cer": avg_cer, "n": len(pairs)},
        )

    # ---- VERSION ----
    def version(self, model_name: str, metrics: dict, notes: str = "") -> PipelineStageResult:
        versions = self._load_versions()
        record = {"model_name": model_name, "metrics": metrics, "notes": notes, "created_at": time.time()}
        versions.append(record)
        self.versions_file.write_text(json.dumps(versions, indent=2))
        return PipelineStageResult("version", True, f"Recorded version '{model_name}'", record)

    def list_versions(self) -> list[dict]:
        return self._load_versions()

    def _load_versions(self) -> list[dict]:
        if not self.versions_file.exists():
            return []
        return json.loads(self.versions_file.read_text())
