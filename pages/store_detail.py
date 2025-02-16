import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import math
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

# =========================================
# 1. CSV 파일 불러오고, 유형별 b값 및 로그 변환
# =========================================

@st.cache_data
def load_all_scores():
    """
    hexa_point_data 폴더의 모든 CSV 파일을 불러와
    파일별(b값 다름) 및 Theme별 log_score 컬럼 추가 후 반환
    """
    csv_files = glob.glob(os.path.join(CSV_FOLDER_PATH, "*_매장별_Theme_score.csv"))
    if not csv_files:
        st.error("❌ CSV 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    # 모든 CSV 파일을 하나의 리스트로 읽음
    all_dfs = []
    b_values_dict = {}  # CSV 파일별 b 값 저장

    for file in csv_files:
        df = pd.read_csv(file)
        file_name = os.path.basename(file)
        df['FileName'] = file_name  # CSV 파일명 추가
        all_dfs.append(df)

        # 유형별 b 값 계산
        themes = df['Theme'].unique()
        file_b_values = {}

        for theme in themes:
            theme_data = df[df['Theme'] == theme]['final_theme_score']
            min_value = math.floor(theme_data.min())

            if min_value < 0:
                b = abs(min_value) + 1
            elif min_value == 0:
                b = 1
            else:
                b = 0

            file_b_values[theme] = b

        b_values_dict[file_name] = file_b_values
        print(f"📊 [파일명: {file_name}] 유형별 b 값:", file_b_values)

    # 모든 CSV를 하나로 합침
    merged_df = pd.concat(all_dfs, ignore_index=True)

    # 로그 변환 함수
    def log_transform(x, b):
        return np.log(x + b)

    # merged_df에 log_score 컬럼 추가 (파일별 b값 적용)
    def apply_log_transform(row):
        file_name = row['FileName']
        theme = row['Theme']
        b = b_values_dict[file_name].get(theme, 0)
        return log_transform(row['final_theme_score'], b)

    merged_df['log_score'] = merged_df.apply(apply_log_transform, axis=1)

    print("\n📊 merged_df (로그 점수 포함):")
    print(merged_df.head())

    return merged_df, b_values_dict


# =========================================
# 2. Theme별 점수(로그) 가져오기 함수 (파일별 적용)
# =========================================
def get_scores_from_all_csv(store_name, labels, file_name_keyword):
    """
    주어진 매장명(store_name)과 유형(file_name_keyword),
    chart_info의 labels(Theme 목록)에 맞는 'log_score'를 가져옴.
    """
    df, _ = load_all_scores()

    # 파일명 기반 필터링
    type_df = df[df['FileName'].str.contains(file_name_keyword)]

    # 매장명 필터링
    store_df = type_df[type_df['Store'] == store_name]

    scores = []
    for theme in labels:
        theme_score = store_df.loc[store_df['Theme'] == theme, 'log_score']
        scores.append(theme_score.values[0] if not theme_score.empty else 0)

    return np.array(scores)


# =========================================
# 3. 레이더 차트 그리기 (log_score 사용)
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

        # 해당 유형의 점수 가져오기
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