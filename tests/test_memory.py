import pytest

from orbit.memory.store import MemoryStore, SecretRejected


@pytest.fixture
def store(tmp_path):
    s = MemoryStore(tmp_path / "orbit.db")
    yield s
    s.close()


def test_preference_roundtrip(store):
    store.set_preference("theme", "dark")
    assert store.get_preference("theme") == "dark"
    assert store.get_preference("missing", "default") == "default"


def test_preference_rejects_secrets(store):
    with pytest.raises(SecretRejected):
        store.set_preference("gmail_password", "hunter2")
    with pytest.raises(SecretRejected):
        store.set_preference("API_KEY", "sk-xxx")


def test_vocabulary_crud(store):
    store.add_vocabulary("Ekagya Exports", aliases=["ekagya export", "ekagya"])
    terms = store.list_vocabulary()
    assert len(terms) == 1
    assert terms[0]["term"] == "Ekagya Exports"
    store.delete_vocabulary("Ekagya Exports")
    assert store.list_vocabulary() == []


def test_corrections_are_optional_learning_data(store):
    cid = store.add_correction("ekagya export", "Ekagya Exports", approved_for_training=False)
    assert store.list_corrections(approved_only=True) == []
    all_corrections = store.list_corrections()
    assert len(all_corrections) == 1
    assert all_corrections[0]["id"] == cid


def test_activity_log(store):
    store.log_activity("open chrome", ["Launched Google Chrome"], "Launched Google Chrome", "success")
    records = store.list_activity()
    assert len(records) == 1
    assert records[0].command == "open chrome"
    assert records[0].status == "success"


def test_workflow_storage(store):
    store.upsert_workflow("buyer_outreach", {"name": "buyer_outreach", "steps": []})
    assert store.get_workflow("buyer_outreach") is not None
    store.delete_workflow("buyer_outreach")
    assert store.get_workflow("buyer_outreach") is None
