import pytest

from orbit.asr.vocabulary import VocabularyStore
from orbit.memory.store import MemoryStore


@pytest.fixture
def vocab(tmp_path):
    memory = MemoryStore(tmp_path / "orbit.db")
    v = VocabularyStore(memory)
    yield v
    memory.close()


def test_correct_transcript_fixes_known_company(vocab):
    vocab.add_term("Ekagya Exports", aliases=["ekagya export", "ekagya exports"])
    result = vocab.correct_transcript("email ekagya export about the order")
    assert "Ekagya Exports" in result.interpreted_text
    assert result.raw_text == "email ekagya export about the order"


def test_no_vocabulary_is_noop(vocab):
    result = vocab.correct_transcript("open chrome")
    assert result.interpreted_text == "open chrome"
    assert result.replacements == []


def test_record_correction_does_not_auto_train(vocab):
    correction_id = vocab.record_correction("wapix", "WAPiX", approve_for_training=False)
    corrections = vocab.list_corrections(approved_only=True)
    assert corrections == []
    all_corrections = vocab.list_corrections()
    assert any(c["id"] == correction_id for c in all_corrections)
