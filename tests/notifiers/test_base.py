from stockbriefing.notifiers.base import chunk_text


def test_chunk_text_respects_limit():
    text = "\n".join(f"line{i}" for i in range(100))
    chunks = chunk_text(text, limit=50)
    assert all(len(c) <= 51 for c in chunks)
    assert "line0" in chunks[0]
