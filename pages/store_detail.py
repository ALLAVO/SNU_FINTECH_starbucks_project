import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
from store_data import chart_info

# 📌 CSV 파일 폴더 경로
CSV_FOLDER_PATH = './hexa_point_data/'

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

# 📌 모든 CSV 파일 불러오기
@st.cache_data
def load_all_scores():
    """hexa_point_data 폴더의 모든 CSV 파일을 불러와 하나의 데이터프레임으로 반환"""
    csv_files = glob.glob(os.path.join(CSV_FOLDER_PATH, "*_매장별_Theme_score.csv"))
    if not csv_files:
        st.error("❌ CSV 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    all_dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        df['FileName'] = os.path.basename(file)  # 파일명 컬럼 추가
        all_dfs.append(df)

    return pd.concat(all_dfs, ignore_index=True)

# 📌 Theme별 점수 가져오기 함수
def get_scores_from_all_csv(store_name, labels, file_name_keyword):
    """
    주어진 매장명(store_name)과 유형(file_name_keyword),
    그리고 chart_info의 labels(Theme 목록)에 맞는 점수를 가져옴.
    - file_name_keyword(유형 키워드: '수다형', '카공형' 등) 기반으로 필터링
    - labels(Theme 순서)에 맞게 final_theme_score 리스트 반환
    - Theme이 없으면 0점 반환
    """
    df = load_all_scores()

    # 📌 CSV 파일명 기반으로 유형 필터링 (ex. '수다형'만 포함)
    type_df = df[df['FileName'].str.contains(file_name_keyword)]

    # 📌 매장명 필터링
    store_df = type_df[type_df['Store'] == store_name]

    # 📌 Theme 점수를 labels 순서에 맞게 가져오기
    scores = []
    for theme in labels:
        theme_score = store_df.loc[store_df['Theme'] == theme, 'final_theme_score']
        scores.append(theme_score.values[0] if not theme_score.empty else 0)

    return np.array(scores)

# 📌 레이더 차트 그리기 함수 (각 꼭짓점에 점수 표시)
def plot_radar_chart(title, labels, scores, store_name, color):
    """
    레이더 차트를 그리는 함수 (각 꼭짓점에 점수 포함)
    - title: 차트 제목
    - labels: Theme 레이블 목록
    - scores: 각 Theme에 대한 점수
    """
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)
    scores = np.append(scores, scores[0])  # 닫힌 육각형 형성

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
    ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color=color)
    ax.fill(angles, scores, alpha=0.3, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)

    # 📌 각 꼭짓점에 점수 표시
    for angle, score, label in zip(angles[:-1], scores[:-1], labels):
        x = angle
        y = score
        ax.text(x, y, f'{score:.2f}', ha='center', fontsize=8, fontweight='bold', color='black')

    ax.grid(True)
    ax.set_yticklabels([])

    return fig

# 📌 2x2 차트 레이아웃 설정 (4개 유형)
cols = st.columns(2)

# 📌 CSV 기반 점수 가져오기 및 차트 표시
for i, (title, labels) in enumerate(chart_info):
    with cols[i % 2]:
        st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

        # 📌 유형별 키워드 추출 (예: '내향형', '수다형', '외향형', '카공형')
        file_name_keyword = title

        scores = get_scores_from_all_csv(store_name, labels, file_name_keyword)  # 유형별 점수 가져오기
        fig = plot_radar_chart(title, labels, scores, store_name, "blue")
        st.pyplot(fig)

# 📌 뒤로 가기 버튼
if st.button("⬅️ 돌아가기"):
    st.switch_page("app.py")