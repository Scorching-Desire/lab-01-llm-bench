"""Create adaptation records using dev queries and source documents only."""

import json
from pathlib import Path

from bench import data


def main():
    core = Path("prompts/lab3-core-v1.md").read_text(encoding="utf-8")
    rows = []
    examples = []
    chunks = data.read_rows("data/lab3/chunks.jsonl")
    for query in data.read_rows("data/lab3/queries.jsonl"):
        if query["split"] != "dev":
            continue
        citations = []
        for span in query["gold_spans"]:
            chunk = next(c for c in chunks if c["doc_id"] == span["doc_id"] and span["text"] in c["text"])
            citations.append(dict(doc_id=span["doc_id"], chunk_id=chunk["chunk_id"], quote=span["text"]))
        response = json.dumps(dict(answer=query["expected"], citations=citations), ensure_ascii=False)
        rows.append(dict(messages=[dict(role="system", content=core), dict(role="user", content=query["input"]),
                                   dict(role="assistant", content=response)], src_split="dev", src_query_id=query["id"],
                         src_doc_ids=[c["doc_id"] for c in citations]))
        examples.append(f"Приклад {query['id']} (dev)\nЗапит: {query['input']}\nВідповідь: {response}")
    for document in data.read_rows("data/lab3/manifest.jsonl"):
        source = Path(document["path"]).read_text(encoding="utf-8")
        # The training target uses a source paragraph that contains no test-answer sectors.
        paragraph = source.split("\n\n")[3]
        response = json.dumps(dict(answer=paragraph, citations=[]), ensure_ascii=False)
        rows.append(dict(messages=[dict(role="system", content=core),
                                   dict(role="user", content=f"Опиши процедуру приймання {document['doc_id']} за регламентом."),
                                   dict(role="assistant", content=response)], src_split="corpus", src_query_id=None,
                         src_doc_ids=[document["doc_id"]]))
    out = Path("data/lab3/train.jsonl")
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
    Path("prompts/lab3-line-prompting.md").write_text(
        "Використовуй лише ці приклади. Пошукових фрагментів у цій лінії немає.\n\n" + "\n\n".join(examples) + "\n",
        encoding="utf-8", newline="\n")
    print(f"{len(rows)} training pairs; 8 dev examples")


if __name__ == "__main__":
    main()
