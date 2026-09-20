from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()  # tự đọc GEMINI_API_KEY từ .env

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Trả lời ngắn gọn trong 1 câu: RAG là gì?"
)
print(response.text)