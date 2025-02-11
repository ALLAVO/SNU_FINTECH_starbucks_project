import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import random

st.set_page_config(
    page_title="매장 비교하기",
    page_icon="📊",
)

st.title("🏪 매장 비교하기")

# 세션 상태에서 매장 목록 가져오기
if "stores" not in st.session_state or len(st.session_state.stores) < 2:
    st.warning("⚠️ 비교할 매장이 최소 2개 이상 필요합니다.")
    st.stop()

# 2개의 매장을 선택하도록 드롭다운 추가
col1, col2 = st.columns(2)
with col1:
    selected_store_1 = st.selectbox("첫 번째 매장 선택", ["선택 안함"] + [store['name'] for store in st.session_state.stores])
with col2:
    selected_store_2 = st.selectbox("두 번째 매장 선택", ["선택 안함"] + [store['name'] for store in st.session_state.stores])

# 비교할 두 매장이 선택된 경우 분석
if selected_store_1 != "선택 안함" and selected_store_2 != "선택 안함":
    st.subheader(f"📊 {selected_store_1} vs {selected_store_2}")

    categories = ["유동인구", "접근성", "경쟁력", "시설", "주차", "서비스"]
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()

    scores_1 = [random.randint(1, 10) for _ in range(len(categories))]
    scores_2 = [random.randint(1, 10) for _ in range(len(categories))]

    scores_1 += scores_1[:1]
    scores_2 += scores_2[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)

    ax.plot(angles, scores_1, 'o-', linewidth=2, label=selected_store_1, color="blue")
    ax.fill(angles, scores_1, alpha=0.3, color="blue")

    ax.plot(angles, scores_2, 'o-', linewidth=2, label=selected_store_2, color="red")
    ax.fill(angles, scores_2, alpha=0.3, color="red")

    ax.legend(loc="upper right")
    st.pyplot(fig)