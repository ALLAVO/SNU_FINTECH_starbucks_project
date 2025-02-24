import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from store_data import chart_info
from modules.score_utils import load_all_scores, get_scores_from_all_csv  # 모듈 불러오기

# 📌 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 폰트 깨짐 방지

st.set_page_config(page_title="스타벅스 매장 비교", page_icon="🏪", layout="wide", initial_sidebar_state="collapsed")  # 전체 너비 사용

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
""", unsafe_allow_html=True)

# 📌 매장별 색상 매핑
store_color_mapping = {
    "store_1": "#fb9783",  # 핑크 (외향형)
    "store_2": "#73FFD0"   # 민트 (내향형)
}

# 📌 선택된 매장 정보 가져오기
if "selected_store_1" not in st.session_state or "selected_store_2" not in st.session_state:
    st.warning("⚠️ 비교할 두 개의 매장을 먼저 선택해주세요!")
    st.stop()

selected_store_1 = st.session_state.selected_store_1
selected_store_2 = st.session_state.selected_store_2

# 📌 매장별 색상 매핑
store_color_mapping = {
    "store_1": "#fb9783",  # 핑크 (외향형)
    "store_2": "#96ddfd"   # 민트 (내향형)
}

# 📌 매장별 배경색 적용된 제목 생성
store_1_color = store_color_mapping["store_1"]
store_2_color = store_color_mapping["store_2"]

st.markdown(f"""
    <div style="
        background: linear-gradient(to right, {store_color_mapping["store_1"]} calc(50% - 12px), {store_color_mapping["store_2"]} calc(50% + 12px));
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 30px;
        color: white;
    ">
        {selected_store_1}   
        <span style="display: inline-block; transform: scaleX(-1);">🥊</span>🔥   
        <span style="color: black; padding: 0 5px; border-radius: 5px;">vs</span> 
        💥🥊 {selected_store_2}
    </div>
""", unsafe_allow_html=True)

# 📌 데이터 로드
merged_df, _ = load_all_scores()


# 📌 레이더 차트 그리기 (방사형 격자선 추가 + 배경 꾸미기)
def plot_radar_chart(labels, scores_1, scores_2, store_1, store_2):
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
    ax.spines['polar'].set_visible(False)
    ax.grid(False)

    scores_1 = np.append(scores_1, scores_1[0])
    scores_2 = np.append(scores_2, scores_2[0])

    # 매장별 색상 적용
    store_1_color = store_color_mapping["store_1"]
    store_2_color = store_color_mapping["store_2"]

    # 🔹 외곽 배경 채우기
    outer_radius = max(max(scores_1), max(scores_2)) * 1.1  # 격자선의 최대 반경 설정
    ax.fill(angles, [outer_radius] * len(angles), color='#f0f0f0', alpha=1)

    # # 🔹 유형 제목 표시 (도형 상단)
    # ax.set_title(title, loc='center', fontsize=30, fontweight='bold', pad=20)

    # 🔹 레이더 차트 그리기 (매장별 색상 유지)
    ax.plot(angles, scores_1, 'o-', linewidth=2, label=store_1, color=store_1_color)
    ax.fill(angles, scores_1, alpha=0.3, color=store_1_color)

    ax.plot(angles, scores_2, 'o-', linewidth=2, label=store_2, color=store_2_color)
    ax.fill(angles, scores_2, alpha=0.3, color=store_2_color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)

    # 🔹 여러 개의 방사형 격자선 추가
    num_grid_lines = 5  # 격자선 개수 설정
    grid_step = outer_radius / num_grid_lines  # 격자선 간격 계산

    for i in range(1, num_grid_lines + 1):
        r = grid_step * i  # 현재 격자선의 반경
        ax.plot(angles, [r] * len(angles), color='grey', linestyle='-', linewidth=0.5)

    # 🔹 방사형 축 (중심에서 바깥으로 뻗는 선) 추가
    for angle in angles[:-1]:  # 마지막 닫힌 각도는 제외
        ax.plot([angle, angle], [0, outer_radius], color='grey', linestyle='-', linewidth=0.5)

    # 🔹 값 표시 (각 점수 라벨 추가)
    for angle, score, label in zip(angles[:-1], scores_1[:-1], labels):
        ax.text(angle, score, f'{score:.2f}', ha='center', fontsize=10, fontweight='bold', color=store_1_color)

    for angle, score, label in zip(angles[:-1], scores_2[:-1], labels):
        ax.text(angle, score, f'{score:.2f}', ha='center', fontsize=10, fontweight='bold', color=store_2_color)

    # 🔹 y축 눈금 제거
    ax.set_yticklabels([])

    return fig


# 📌 유형별 우세 매장 분석 결과 + 그래프 한 행에 출력
st.markdown("---")
st.subheader("유형별 매장 비교")

# 🔹 한 행에 모든 유형을 배치
cols = st.columns(len(chart_info))

for i, (title, labels) in enumerate(chart_info):
    file_name_keyword = title

    try:
        scores_1 = get_scores_from_all_csv(selected_store_1, labels, file_name_keyword)
        scores_2 = get_scores_from_all_csv(selected_store_2, labels, file_name_keyword)

        # 두 매장의 총점 비교
        total_1 = sum(scores_1)
        total_2 = sum(scores_2)

        # 우세한 매장 결정
        winner = selected_store_1 if total_1 > total_2 else selected_store_2
        winner_color = store_color_mapping["store_1"] if winner == selected_store_1 else store_color_mapping["store_2"]

        with cols[i]:
            # 📌 유형 제목을 중앙 정렬하여 표시
            st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

            # 📌 `plot_radar_chart()` 함수를 사용하여 그래프 생성 (매장별 색상 적용)
            fig = plot_radar_chart(labels, scores_1, scores_2, selected_store_1, selected_store_2)
            st.pyplot(fig)  # 🔹 그래프 출력 (먼저 표시)

            # 📌 점수표 표시 (그래프 아래에 배치)
            st.markdown(f"""
                <div style="
                    background-color: {winner_color};  
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    font-weight: bold;
                    font-size: 18px;
                    color: white;
                    line-height: 1.6;
                ">
                    <h4>{winner} WIN!!</h4>
                    <p>{selected_store_1}: {total_1:.2f} 점</p>
                    <p>{selected_store_2}: {total_2:.2f} 점</p>
                </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ 데이터 로드 중 오류 발생: {str(e)}")

    # 구분선 추가
st.markdown("---")

# 돌아가기 버튼
if st.button("⬅️ 돌아가기"):
    # 선택된 매장 정보 초기화
    if 'selected_store_1' in st.session_state:
        del st.session_state.selected_store_1
    if 'selected_store_2' in st.session_state:
        del st.session_state.selected_store_2
    if 'selected_stores' in st.session_state:
        st.session_state.selected_stores = []
    # 메인 페이지로 이동
    st.switch_page("app.py")