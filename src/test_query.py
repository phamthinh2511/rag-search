import os

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHROMA_PATH = os.path.join(ROOT, "data", "chroma_db")
QUESTIONS = [
    "Người lái xe máy phải đội mũ bảo hiểm không?",
    "Tuổi tối thiểu để được cấp giấy phép lái xe hạng A1 là bao nhiêu?",
]
TOP_K = 3
load_dotenv()
client = genai.Client()
collection = chromadb.PersistentClient(path=CHROMA_PATH).get_collection("luat_giao_thong")
print("Số vector trong collection:", collection.count())
for q in QUESTIONS:
    vector = client.models.embed_content(
        model="gemini-embedding-001",
        contents=[q],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    ).embeddings[0].values
    result = collection.query(query_embeddings=[vector], n_results=TOP_K)
    print(f"\nCâu hỏi: {q}")
    for meta, dist in zip(result["metadatas"][0], result["distances"][0]):
        print(f"  {dist:.3f}  {meta['citation']} - {meta['dieu_title'][:50]} (trang {meta['page_start']}-{meta['page_end']})")
result = collection.get(where={"$and": [{"dieu": 9}, {"khoan": "3"}]})
print("\nLọc metadata Điều 9, khoản 3:", result["ids"])
print(result["documents"][0][:300])
