import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import random
from store_data import chart_info


# 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 폰트 깨짐 방지

st.set_page_config(page_title="매장 상세 분석", page_icon="📊")
st.title("📊 스타벅스 매장 상세 분석")

# 선택된 매장 정보 가져오기
if "selected_store" not in st.session_state:
    st.warning("⚠️ 분석할 매장을 먼저 선택해주세요!")
    st.stop()

store_name = st.session_state.selected_store
st.subheader(f"🏪 {store_name}")

# 랜덤 점수 생성
def generate_random_scores():
    return np.array([random.randint(1, 10) for _ in range(6)])

# 레이더 차트 그리기 함수
def plot_radar_chart(title, labels, scores, store_name, color):
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)
    scores = np.append(scores, scores[0])  # 닫힌 육각형 형성

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
    ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color=color)
    ax.fill(angles, scores, alpha=0.3, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    # ax.legend(loc="upper right")

    return fig

# 2x2 차트 레이아웃 설정
cols = st.columns(2)
all_scores = [generate_random_scores() for _ in chart_info]

for i, (title, labels) in enumerate(chart_info):
    with cols[i % 2]:
        st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)
        fig = plot_radar_chart(title, labels, all_scores[i], store_name, "blue")
        st.pyplot(fig)

# 뒤로 가기 버튼
if st.button("⬅️ 돌아가기"):
    st.switch_page("app.py")
