from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=["Người điều khiển xe máy phải đội mũ bảo hiểm khi tham gia giao thông."],
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
)
vector = result.embeddings[0].values
print("Số chiều vector:", len(vector))
print("5 giá trị đầu:", vector[:5])