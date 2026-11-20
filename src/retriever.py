import re
import sys

import chromadb

from ingest import CHROMA_PATH, COLLECTION, embed_batch

TOP_K = 5
# Chọn từ eval_retrieval.py: Top-1 câu trong phạm vi 0.192–0.294, ngoài phạm vi 0.346–0.425.
# shortcut: mới đo trên 16 câu, cần đo lại với bộ 20–30 câu ở tuần 13–14.
MAX_DISTANCE = 0.32

RE_DIEU = re.compile(r"\bđiều\s+(\d+)", re.IGNORECASE)
RE_KHOAN = re.compile(r"\bkhoản\s+(\d+[a-z]?)\b", re.IGNORECASE)

collection = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(COLLECTION)


def metadata_filter(question: str) -> dict | None:
    dieu = RE_DIEU.search(question)
    if not dieu:
        return None
    cond = [{"dieu": int(dieu.group(1))}]
    if khoan := RE_KHOAN.search(question):
        cond.append({"khoan": khoan.group(1).lower()})
    return cond[0] if len(cond) == 1 else {"$and": cond}


def retrieve(question: str, top_k: int = TOP_K, max_distance: float | None = MAX_DISTANCE,
             vector: list[float] | None = None) -> list[dict]:
    """Trả về tối đa top_k đoạn: {"text", "metadata", "distance"}, gần nhất trước."""
    if vector is None:
        vector = embed_batch([question], task_type="RETRIEVAL_QUERY")[0]
    where = metadata_filter(question)
    res = collection.query(query_embeddings=[vector], n_results=top_k, where=where)
    hits = [{"text": t, "metadata": m, "distance": d}
            for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]
    # Người dùng đã chỉ đích danh Điều/Khoản thì không áp ngưỡng
    if where is None and max_distance is not None:
        hits = [h for h in hits if h["distance"] <= max_distance]
    return hits


if __name__ == "__main__":
    assert metadata_filter("Khoản 2 Điều 9 quy định gì?") == {"$and": [{"dieu": 9}, {"khoan": "2"}]}
    assert metadata_filter("điều 33 nói gì") == {"dieu": 33}
    assert metadata_filter("Đội mũ bảo hiểm thế nào?") is None

    question = " ".join(sys.argv[1:]) or "Người lái xe máy phải đội mũ bảo hiểm không?"
    hits = retrieve(question)
    print(f"Câu hỏi: {question}\nBộ lọc metadata: {metadata_filter(question)}")
    if not hits:
        print("Không tìm thấy đoạn luật đủ liên quan.")
    for i, h in enumerate(hits, 1):
        m = h["metadata"]
        print(f"{i}. [{h['distance']:.3f}] {m['citation']} - {m['dieu_title']} (trang {m['page_start']}-{m['page_end']})")
