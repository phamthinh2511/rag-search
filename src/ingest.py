import json
import os
import time

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
CHROMA_PATH = os.path.join(ROOT, "data", "chroma_db")

COLLECTION = "luat_giao_thong"
EMBED_MODEL = "gemini-embedding-001"
BATCH_SIZE = 50
MAX_RETRIES = 6

load_dotenv()
client = genai.Client()


def embed_batch(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    for attempt in range(MAX_RETRIES):
        try:
            result = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            wait = 2 ** attempt * 5
            print(f"  lỗi: {str(e)[:120]} -> thử lại sau {wait}s")
            time.sleep(wait)
    raise RuntimeError("Embedding thất bại sau nhiều lần thử")


def main():
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    # Cosine phù hợp với embedding văn bản; embedding_function=None vì ta tự tạo vector
    collection = chroma.get_or_create_collection(
        COLLECTION, configuration={"hnsw": {"space": "cosine"}}, embedding_function=None
    )

    for name in sorted(os.listdir(PROCESSED_DIR)):
        if not name.endswith(".chunks.json"):
            continue
        with open(os.path.join(PROCESSED_DIR, name), encoding="utf-8") as f:
            chunks = json.load(f)

        existing = set(collection.get(ids=[c["id"] for c in chunks], include=[])["ids"])
        todo = [c for c in chunks if c["id"] not in existing]
        print(f"{name}: {len(chunks)} chunk, {len(existing)} đã có, cần nạp {len(todo)}")

        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i:i + BATCH_SIZE]
            vectors = embed_batch([c["text"] for c in batch])
            collection.upsert(
                ids=[c["id"] for c in batch],
                embeddings=vectors,
                documents=[c["text"] for c in batch],
                metadatas=[c["metadata"] for c in batch],
            )
            print(f"  đã nạp {min(i + BATCH_SIZE, len(todo))}/{len(todo)}")

    print("Tổng số vector trong collection:", collection.count())


if __name__ == "__main__":
    main()
