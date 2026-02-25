from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

BEIR_BASE_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets"


def sanitize_filename(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_")
    return safe or "doc"


def download_dataset(dataset: str, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / f"{dataset}.zip"
    if zip_path.exists():
        return zip_path
    url = f"{BEIR_BASE_URL}/{dataset}.zip"
    with httpx.Client(timeout=120) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with zip_path.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    return zip_path


def extract_dataset(zip_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    dataset_dir = out_dir / zip_path.stem
    if dataset_dir.exists():
        return dataset_dir
    # Fallback for archives with direct root files.
    return out_dir


def load_corpus(corpus_path: Path, max_docs: int) -> dict[str, dict[str, str]]:
    corpus: dict[str, dict[str, str]] = {}
    with corpus_path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if max_docs > 0 and idx >= max_docs:
                break
            row = json.loads(line)
            corpus_id = str(row["_id"])
            corpus[corpus_id] = {
                "title": str(row.get("title") or "").strip(),
                "text": str(row.get("text") or "").strip(),
            }
    return corpus


def load_queries(queries_path: Path) -> dict[str, str]:
    queries: dict[str, str] = {}
    with queries_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            queries[str(row["_id"])] = str(row.get("text") or "").strip()
    return queries


def load_qrels(qrels_path: Path) -> dict[str, list[str]]:
    qrels: dict[str, list[str]] = defaultdict(list)
    with qrels_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            qid = str(row["query-id"])
            did = str(row["corpus-id"])
            score = int(row["score"])
            if score > 0:
                qrels[qid].append(did)
    return qrels


def write_docs(corpus: dict[str, dict[str, str]], docs_root: Path, dataset: str) -> dict[str, str]:
    target_dir = docs_root / "beir" / dataset
    target_dir.mkdir(parents=True, exist_ok=True)
    id_to_doc_id: dict[str, str] = {}
    for corpus_id, row in corpus.items():
        filename = f"{sanitize_filename(corpus_id)}.txt"
        rel_source = Path("beir") / dataset / filename
        out_path = docs_root / rel_source
        text = (f"{row['title']}\n\n{row['text']}" if row["title"] else row["text"]).strip()
        out_path.write_text(text, encoding="utf-8")
        id_to_doc_id[corpus_id] = rel_source.as_posix().replace("/", "__")
    return id_to_doc_id


def build_golden_eval(
    *,
    queries: dict[str, str],
    qrels: dict[str, list[str]],
    id_to_doc_id: dict[str, str],
    max_queries: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    count = 0
    for qid, relevant_ids in qrels.items():
        if max_queries > 0 and count >= max_queries:
            break
        question = queries.get(qid, "").strip()
        if not question:
            continue
        mapped = [id_to_doc_id[doc_id] for doc_id in relevant_ids if doc_id in id_to_doc_id]
        if not mapped:
            continue
        rows.append(
            {
                "id": f"beir_{qid}",
                "question": question,
                "expected_doc_ids": mapped[:5],
                "expected_substrings": [],
            }
        )
        count += 1
    return rows


def write_golden_eval(rows: list[dict[str, Any]], benchmark_path: Path) -> None:
    benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=True) for row in rows]
    benchmark_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def run_import(dataset: str, split: str, max_docs: int, max_queries: int) -> dict[str, Any]:
    settings = get_settings()
    data_root = settings.docs_dir.parent
    raw_dir = data_root / "beir_raw"
    extract_dir = data_root / "beir_extracted"

    zip_path = download_dataset(dataset, raw_dir)
    dataset_dir = extract_dataset(zip_path, extract_dir)

    corpus_path = dataset_dir / "corpus.jsonl"
    queries_path = dataset_dir / "queries.jsonl"
    qrels_path = dataset_dir / "qrels" / f"{split}.tsv"
    if not corpus_path.exists():
        raise FileNotFoundError(f"Missing corpus file: {corpus_path}")
    if not queries_path.exists():
        raise FileNotFoundError(f"Missing queries file: {queries_path}")
    if not qrels_path.exists():
        raise FileNotFoundError(f"Missing qrels split file: {qrels_path}")

    corpus = load_corpus(corpus_path, max_docs=max_docs)
    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)

    id_to_doc_id = write_docs(corpus, settings.docs_dir, dataset)
    rows = build_golden_eval(
        queries=queries,
        qrels=qrels,
        id_to_doc_id=id_to_doc_id,
        max_queries=max_queries,
    )
    write_golden_eval(rows, settings.benchmark_path)
    return {
        "dataset": dataset,
        "split": split,
        "docs_written": len(id_to_doc_id),
        "eval_cases_written": len(rows),
        "docs_dir": str(settings.docs_dir),
        "benchmark_path": str(settings.benchmark_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import BEIR dataset into local docs + golden eval.")
    parser.add_argument("--dataset", default="scifact", help="BEIR dataset name (example: scifact, fiqa, nfcorpus)")
    parser.add_argument("--split", default="test", help="Qrels split: test/dev/train (dataset dependent)")
    parser.add_argument("--max-docs", type=int, default=2000, help="Max corpus docs to write (0 = all)")
    parser.add_argument("--max-queries", type=int, default=200, help="Max eval queries to generate (0 = all)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_import(
        dataset=args.dataset,
        split=args.split,
        max_docs=args.max_docs,
        max_queries=args.max_queries,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
