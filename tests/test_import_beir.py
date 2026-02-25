from pathlib import Path

from scripts.import_beir import build_golden_eval, sanitize_filename, write_docs


def test_sanitize_filename() -> None:
    assert sanitize_filename("doc/with spaces?") == "doc_with_spaces"
    assert sanitize_filename("a:b*c") == "a_b_c"


def test_write_docs_and_build_golden(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    corpus = {
        "doc-1": {"title": "Title One", "text": "Body One"},
        "doc-2": {"title": "", "text": "Body Two"},
    }
    id_map = write_docs(corpus, docs_root, dataset="scifact")
    assert "doc-1" in id_map
    assert (docs_root / "beir" / "scifact" / "doc-1.txt").exists()

    queries = {"q1": "What is doc one?", "q2": "What is doc two?"}
    qrels = {"q1": ["doc-1"], "q2": ["doc-2"]}
    rows = build_golden_eval(queries=queries, qrels=qrels, id_to_doc_id=id_map, max_queries=10)
    assert len(rows) == 2
    assert rows[0]["expected_doc_ids"]
    assert rows[0]["expected_substrings"] == []
