import sys
import time

from google.genai import types

from ingest import MAX_RETRIES, client
from retriever import retrieve

GEN_MODEL = "gemini-3.5-flash-lite"  # bản flash mất ~33s/câu trên gói miễn phí, lite ~1-2s
NO_ANSWER = "Tài liệu hiện có không đủ thông tin để trả lời câu hỏi này."

SYSTEM_PROMPT = f"""Bạn là trợ lý tra cứu Luật Trật tự, an toàn giao thông đường bộ số 36/2024/QH15.

Quy tắc trả lời:
1. Chỉ sử dụng thông tin trong phần NGỮ CẢNH được cung cấp. Không dùng kiến thức bên ngoài.
2. Sau mỗi ý, ghi nguồn theo dạng (Khoản x Điều y) hoặc (Điều y), lấy đúng như trong ngữ cảnh.
3. Người hỏi thường dùng từ ngữ đời thường khác với văn bản luật (ví dụ "uống rượu bia" tương ứng với
   "có nồng độ cồn", "đèn pha" tương ứng với "đèn chiếu xa"). Nếu ngữ cảnh có quy định về đúng nội dung đó
   thì phải trả lời dựa trên quy định ấy: nêu rõ được hay không được, rồi dẫn quy định làm căn cứ.
4. Chỉ khi ngữ cảnh không có quy định nào về nội dung được hỏi (ví dụ hỏi mức phạt tiền nhưng ngữ cảnh
   không nêu số tiền), mới trả lời đúng một câu: "{NO_ANSWER}"
5. Không tự bổ sung mức phạt, con số hay quy định không có trong ngữ cảnh.
6. Trả lời bằng tiếng Việt, ngắn gọn, rõ ràng."""


def build_prompt(question: str, hits: list[dict]) -> str:
    # Giữ tên Điều: thiếu nó, "Khoản 2 Điều 9" không cho biết đây là hành vi bị nghiêm cấm
    context = "\n\n".join(
        f"[{i}] {m['citation']} – Điều {m['dieu']}. {m['dieu_title']} (trang {m['page_start']}): "
        f"{h['text'].split(chr(10), 1)[-1]}"
        for i, h in enumerate(hits, 1) if (m := h["metadata"])
    )
    return f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI: {question}"


def answer(question: str) -> dict:
    """Trả về {"answer": câu trả lời, "hits": các đoạn luật đã dùng làm ngữ cảnh}."""
    hits = retrieve(question)
    if not hits:  # không đoạn nào vượt ngưỡng -> không gọi Gemini, tránh bịa
        return {"answer": NO_ANSWER, "hits": []}
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT, temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # không dùng tool, tắt cảnh báo AFC
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),  # mặc định suy luận lâu (~50s/câu)
    )
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEN_MODEL, contents=build_prompt(question, hits), config=config
            )
            return {"answer": response.text.strip(), "hits": hits}
        except Exception as e:  # quá hạn mức (429) hoặc lỗi tạm thời: chờ rồi thử lại
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt * 5
            print(f"  lỗi: {str(e)[:120]} -> thử lại sau {wait}s")
            time.sleep(wait)


if __name__ == "__main__":
    sample = [{"text": "ctx\nNội dung khoản", "metadata": {"citation": "Khoản 2 Điều 33", "dieu": 33,
                                                         "dieu_title": "Người lái xe", "page_start": 24}}]
    p = build_prompt("Câu hỏi thử?", sample)
    assert "[1] Khoản 2 Điều 33 – Điều 33. Người lái xe (trang 24): Nội dung khoản" in p and "CÂU HỎI: Câu hỏi thử?" in p

    question = " ".join(sys.argv[1:]) or "Người lái xe máy có bắt buộc đội mũ bảo hiểm không?"
    result = answer(question)
    print(f"Câu hỏi: {question}\n\n{result['answer']}\n\nNguồn:")
    for h in result["hits"]:
        m = h["metadata"]
        print(f"  - {m['citation']} ({m['source']}, trang {m['page_start']}-{m['page_end']}, khoảng cách {h['distance']:.3f})")
