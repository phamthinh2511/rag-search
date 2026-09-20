import streamlit as st

st.title("Test giao diện")
q = st.text_input("Nhập câu hỏi:")
if q:
    st.write(f"Bạn vừa hỏi: {q}")