from app.core.config import Settings
from app.rag.ingestion import chunk_text, source_to_doc_id


def test_source_to_doc_id_normalizes() -> None:
    source = "https://example.com/docs/Guide 101?.md"
    doc_id = source_to_doc_id(source)
    assert "__" in doc_id
    assert " " not in doc_id


def test_chunk_text_produces_overlap() -> None:
    settings = Settings(CHUNK_SIZE=20, CHUNK_OVERLAP=5)
    chunks = chunk_text("abcdefghijklmnopqrstuvwxyz", settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    assert len(chunks) >= 2
    assert chunks[0][-5:] == chunks[1][:5]
