import streamlit as st
from pathlib import Path
from typing import List
import requests, os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND_API: str = os.getenv("BACKEND_API", "http://ragbe:6000")

st.set_page_config(page_title="PDK 챗봇", page_icon="📄", layout="wide")
st.title("📄 PDK 챗봇")

# ---------------------------------------------------------------------------
# Sidebar – Upload & remote ingest (ragbe)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 문서 업로드")
    uploaded_files = st.file_uploader(
        "DOCX/PDF/PPTX 파일을 선택하세요(여러 개 가능)",
        type=["docx", "pdf", "pptx"],
        accept_multiple_files=True,
    )
    if st.button("업로드/추가") and uploaded_files:
        # Build multipart‑form payload
        multipart: List[tuple] = []
        for f in uploaded_files:
            # f is a BytesIO-like object; reset cursor just in case
            f.seek(0)
            multipart.append((
                "files",  # field name expected by ragbe
                (f.name, f.read(), "application/octet-stream"),
            ))

        with st.spinner("백엔드로 전송 중 …"):
            try:
                resp = requests.post(f"{BACKEND_API}/ingest", files=multipart, timeout=300)
                resp.raise_for_status()
                data = resp.json()
                st.success(f"✅ {data.get('count', 0)} 개 청크 추가 완료!")
            except Exception as exc:
                st.error(f"🚫 업로드 실패: {exc}")

# ---------------------------------------------------------------------------
# Session‑state chat history
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 궁금한 점을 물어봐 주세요."}
    ]

# ---------------------------------------------------------------------------
# Render existing conversation
# ---------------------------------------------------------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------------------------------------------------------------------------
# Input → /ask on ragbe
# ---------------------------------------------------------------------------
if user_query := st.chat_input("질문을 입력해주세요 …"):
    # 1) echo user message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # 2) backend call
    with st.chat_message("assistant"):
        with st.spinner("Thinking …"):
            try:
                resp = requests.post(f"{BACKEND_API}/ask", json={"text": user_query}, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                answer: str = data.get("response", "응답 실패")
                sources = data.get("sources", [])
            except Exception as exc:
                answer, sources = f"⚠️ 오류: {exc}", []

        st.markdown(answer)
        if sources:
            with st.expander("참고 문서"):
                for s in sources:
                    st.markdown(f"- {s}")

    st.session_state.messages.append({"role": "assistant", "content": answer})
