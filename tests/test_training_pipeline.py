from orbit.training.datasets import list_datasets
from orbit.training.metrics import character_error_rate, command_accuracy, word_error_rate
from orbit.training.pipeline import ASRTrainingPipeline


def test_dataset_registry_tracks_license_and_language():
    datasets = list_datasets(language="hi")
    assert len(datasets) > 0
    for d in datasets:
        assert d.license
        assert d.source_url


def test_word_error_rate_perfect_match():
    assert word_error_rate("open chrome now", "open chrome now") == 0.0


def test_word_error_rate_one_substitution():
    wer = word_error_rate("open chrome now", "open chrone now")
    assert wer == 1 / 3


def test_character_error_rate_basic():
    cer = character_error_rate("orbit", "orbi")
    assert cer == 1 / 5


def test_command_accuracy():
    pairs = [("open_app", "open_app"), ("send", "cancel_send"), ("stop", "stop")]
    assert command_accuracy(pairs) == 2 / 3


def test_pipeline_clean_normalize_split(tmp_path):
    pipeline = ASRTrainingPipeline(tmp_path)
    raw = ["  Open   Chrome!! ", "Ekagya *** Exports", ""]
    cleaned = pipeline.clean(raw)
    assert cleaned.success
    normalized = pipeline.normalize(cleaned.data["records"])
    assert all(r == r.lower() for r in normalized.data["records"])

    split = pipeline.split([f"sample {i}" for i in range(20)], train_ratio=0.8, val_ratio=0.1)
    assert split.success
    assert len(split.data["train"]) + len(split.data["val"]) + len(split.data["test"]) == 20


def test_pipeline_download_and_train_require_local_execution(tmp_path):
    pipeline = ASRTrainingPipeline(tmp_path)
    dl = pipeline.download("Mozilla Common Voice (Hindi)")
    assert dl.success is False
    train = pipeline.train("orbit-asr-v1", ["a", "b"])
    assert train.success is False


def test_pipeline_evaluate_and_version(tmp_path):
    pipeline = ASRTrainingPipeline(tmp_path)
    result = pipeline.evaluate([("open chrome", "open chrome"), ("stop now", "stop know")])
    assert result.success
    assert 0 <= result.data["wer"] <= 1

    version_result = pipeline.version("orbit-asr-v1", result.data)
    assert version_result.success
    versions = pipeline.list_versions()
    assert len(versions) == 1
    assert versions[0]["model_name"] == "orbit-asr-v1"
