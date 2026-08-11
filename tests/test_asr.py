from orbit.asr.mock_engine import MockASREngine


def test_mock_engine_default_text():
    engine = MockASREngine(default_text="open chrome", default_language="en")
    result = engine.transcribe(b"")
    assert result.raw_text == "open chrome"
    assert result.language == "en"
    assert result.engine == "mock"


def test_mock_engine_queue():
    engine = MockASREngine()
    engine.enqueue("Chrome kholo", language="hi")
    engine.enqueue("create a folder", language="en")
    r1 = engine.transcribe(b"")
    r2 = engine.transcribe(b"")
    assert r1.raw_text == "Chrome kholo"
    assert r1.language == "hi"
    assert r2.raw_text == "create a folder"


def test_transcribe_stream_default_fallback():
    engine = MockASREngine(default_text="hello")
    results = list(engine.transcribe_stream([b"a", b"b"]))
    assert len(results) == 1
    assert results[0].raw_text == "hello"
