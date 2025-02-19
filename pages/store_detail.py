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

st.set_page_config(page_title="매장 상세 분석", page_icon="📊", layout="wide")  # 전체 너비 사용
st.markdown("""
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        .card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            text-align: center;
            font-family: 'AppleGothic', sans-serif;
            margin-bottom: 20px;
        }
        .card h4 {
            margin-top: 0;
            font-size: 22px;
            color: #333333;
        }
        .card p {
            font-size: 20px;
            color: #666666;
        }
        .card .score {
            font-size: 26px;
            font-weight: bold;
            color: #000000;
        }
    </style>
""", unsafe_allow_html=True)  # 기본 패딩 제거 및 카드 스타일 추가

st.title("📊 스타벅스 매장 상세 분석")

# 선택된 매장 정보 가져오기
if "selected_store" not in st.session_state:
    st.warning("⚠️ 분석할 매장을 먼저 선택해주세요!")
    st.stop()

store_name = st.session_state.selected_store
st.subheader(f"🏪 {store_name}")

# 📌 레이더 차트 색상 매핑
color_mapping = {
    "외향형": "#fb9783",
    "내향형": "#73FFD0",
    "수다형": "#fdde8d",
    "카공형": "#96ddfd"
}

# =========================================
# 레이더 차트 그리기 (log_score 사용)
# =========================================
def plot_radar_chart(title, labels, scores, store_name, color):
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)
    scores = np.append(scores, scores[0])  # 닫힌 다각형 형성

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})  # 크기 조정
    ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color=color)
    ax.fill(angles, scores, alpha=0.3, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)

    for angle, score, label in zip(angles[:-1], scores[:-1], labels):
        ax.text(angle, score, f'{score:.2f}', ha='center', fontsize=12, fontweight='bold', color='black')

    ax.grid(True)
    ax.set_yticklabels([])
    return fig


# =========================================
# 가장 총점이 높은 유형 선택 + 나머지 유형 한 줄에 표시
# =========================================
merged_df, b_values_dict = load_all_scores()

# ✅ 모든 유형별 점수 계산
scores_dict = {}

for title, labels in chart_info:
    file_name_keyword = title
    scores = get_scores_from_all_csv(store_name, labels, file_name_keyword)
    total_score = np.sum(scores)  # 총점 계산
    scores_dict[title] = {"labels": labels, "scores": scores, "total": total_score}

# ✅ 가장 총점이 높은 유형 선택
max_score_title = max(scores_dict, key=lambda x: scores_dict[x]["total"])
max_score_labels = scores_dict[max_score_title]["labels"]
max_score_values = scores_dict[max_score_title]["scores"]
max_score = scores_dict[max_score_title]["total"]

# ✅ 나머지 3개의 유형 리스트 생성
remaining_types = [t for t in scores_dict if t != max_score_title]

# 📌 가장 높은 점수 유형 강조 (좌우 여백 제거, 성적표 크기 키움)
cols = st.columns([1, 1.2])

with cols[0]:  # 🔹 왼쪽: 레이더 차트
    st.markdown(f"<h3 style='text-align: center;'>{max_score_title} 레이더 차트</h3>", unsafe_allow_html=True)
    chart_color = color_mapping.get(max_score_title, "blue")
    fig = plot_radar_chart(max_score_title, max_score_labels, max_score_values, store_name, chart_color)
    st.pyplot(fig)

with cols[1]:  # 🔹 오른쪽: 성적표 출력 (2열 배치)
    st.markdown(f"<h3 style='text-align: center;'>{max_score_title} 성적표</h3>", unsafe_allow_html=True)

    # 📋 성적표 카드 형태로 출력 (2열 배치)
    card_cols = st.columns(2)
    for i, (label, score) in enumerate(zip(max_score_labels, max_score_values)):
        with card_cols[i % 2]:
            st.markdown(f"""
                <div class="card">
                    <h4>{label}</h4>
                    <p class="score">{score:.2f} 점</p>
                </div>
            """, unsafe_allow_html=True)

    # 🔥 총합 부분은 한 줄로 단독 출력
    st.markdown(f"""
        <div class="card" style="background-color: #f0f0f0; width: 100%;">
            <h4>총합</h4>
            <p class="score">{max_score:.2f} 점</p>
        </div>
    """, unsafe_allow_html=True)

# 📌 나머지 3개의 유형을 한 행에 나란히 표시 (좌우 여백 제거)
st.markdown("---")
st.markdown("### 📊 나머지 유형 비교")

cols = st.columns(3)  # 3개 컬럼 생성

for i, title in enumerate(remaining_types):
    with cols[i]:
        st.markdown(f"<h4 style='text-align: center;'>{title}</h4>", unsafe_allow_html=True)

        labels = scores_dict[title]["labels"]
        values = scores_dict[title]["scores"]
        total = scores_dict[title]["total"]
        chart_color = color_mapping.get(title, "blue")

        fig = plot_radar_chart(title, labels, values, store_name, chart_color)
        st.pyplot(fig)

        st.markdown(f"<p style='text-align: center; font-weight: bold;'>총점: {total:.2f}</p>", unsafe_allow_html=True)

# 뒤로 가기 버튼
if st.button("⬅️ 돌아가기"):
    st.switch_page("app.py")