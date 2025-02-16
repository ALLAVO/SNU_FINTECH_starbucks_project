import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import math
from store_data import chart_info
from modules.score_utils import load_all_scores, get_scores_from_all_csv  # 모듈 불러오기

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

# 📌 CSV 파일 폴더 경로
CSV_FOLDER_PATH = './hexa_point_data/'

# =========================================
# 레이더 차트 그리기 (log_score 사용)
# =========================================
def plot_radar_chart(title, labels, scores, store_name, color):
    """
    레이더 차트를 그리는 함수
    - title: 차트 제목
    - labels: Theme 목록
    - scores: 각 Theme에 대한 점수
    """
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)
    scores = np.append(scores, scores[0])  # 닫힌 다각형 형성

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
    ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color=color)
    ax.fill(angles, scores, alpha=0.3, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)

    for angle, score, label in zip(angles[:-1], scores[:-1], labels):
        ax.text(angle, score, f'{score:.2f}', ha='center', fontsize=8, fontweight='bold', color='black')

    ax.grid(True)
    ax.set_yticklabels([])
    return fig


# =========================================
# 4. 레이더 차트 출력 (파일별 b값 반영된 로그 점수)
# =========================================
merged_df, b_values_dict = load_all_scores()

cols = st.columns(2)

for i, (title, labels) in enumerate(chart_info):
    with cols[i % 2]:
        st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

        # 유형별 키워드를 파일명에서 찾음
        file_name_keyword = title

        # 해당 유형의 점수 가져오기 -> /modules/score_utils.py
        scores = get_scores_from_all_csv(store_name, labels, file_name_keyword)

        # 레이더 차트 표시
        fig = plot_radar_chart(title, labels, scores, store_name, "blue")
        st.pyplot(fig)

# =========================================
# 5. 유형별 b값 출력
# =========================================
st.subheader("📊 유형별 b 값 목록")
for file_name, theme_b_values in b_values_dict.items():
    st.write(f"**📂 파일명: {file_name}**")
    for theme, b in theme_b_values.items():
        st.write(f"- {theme}: b = {b}")

# 뒤로 가기 버튼
if st.button("⬅️ 돌아가기"):
    st.switch_page("app.py")