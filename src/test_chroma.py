import chromadb

client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection("test")

collection.add(ids=["1"], embeddings=[[0.1, 0.2, 0.3]], documents=["đoạn test"])
print("Số lượng vector:", collection.count())