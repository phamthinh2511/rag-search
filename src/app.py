import streamlit as st

from rag import answer

st.set_page_config(page_title="Hỏi đáp Luật Giao thông", page_icon="⚖️")
st.title("Hỏi đáp Luật Trật tự, an toàn giao thông đường bộ")
st.caption("Phạm vi: Luật số 36/2024/QH15 (văn bản hợp nhất). Câu trả lời chỉ mang tính tham khảo, "
           "hãy kiểm tra lại với điều luật được trích dẫn.")

with st.form("ask"):
    question = st.text_input("Câu hỏi của bạn", placeholder="Ví dụ: Người lái xe máy có bắt buộc đội mũ bảo hiểm không?")
    submitted = st.form_submit_button("Hỏi")

if submitted and question.strip():
    try:
        with st.spinner("Đang tra cứu và tạo câu trả lời..."):
            result = answer(question.strip())
    except Exception as e:
        st.error(f"Không gọi được Gemini API: {e}")
        st.stop()

    st.subheader("Trả lời")
    st.markdown(result["answer"])

    if result["hits"]:
        with st.expander(f"Nguồn tham khảo ({len(result['hits'])} đoạn luật)", expanded=True):
            for i, h in enumerate(result["hits"], 1):
                m = h["metadata"]
                st.markdown(f"**[{i}] {m['citation']}** – {m['dieu_title']}  \n"
                            f"Tệp `{m['source']}`, trang {m['page_start']}"
                            f"{'' if m['page_start'] == m['page_end'] else '-' + str(m['page_end'])}"
                            f" · khoảng cách {h['distance']:.3f}")
                st.text(h["text"].split("\n", 1)[-1])
