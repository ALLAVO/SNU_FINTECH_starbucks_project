import numpy as np
import matplotlib.pyplot as plt
from store_data import chart_info
from modules.score_utils import load_all_scores, get_scores_from_all_csv  # 모듈 불러오기

# 📌 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 폰트 깨짐 방지

st.set_page_config(page_title="매장 유형 분석", page_icon="📊", layout="wide")  # 전체 너비 사용
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


# 📌 레이더 차트 색상 매핑
color_mapping = {
    "외향형": "#fb9783",
    "내향형": "#73FFD0",
    "수다형": "#fdde8d",
    "카공형": "#96ddfd"
}

# 📌 레이더 차트 그리기 (log_score 사용) - 여러 개의 방사형 격자선 추가
def plot_radar_chart(title, labels, scores, store_name, color):
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)
    scores = np.append(scores, scores[0])  # 닫힌 다각형 형성

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})  # 크기 조정

    # 🔹 바깥 테두리 제거 (필요 시)
    ax.spines['polar'].set_visible(False)

    # 🔹 격자선 제거
    ax.grid(False)

    # 🔹 도형 뒤에 있는 격자선 끝을 직선으로 연결
    outer_radius = max(scores) * 1.1  # 격자선의 최대 반경 설정
    outer_points = [(outer_radius * np.cos(angle), outer_radius * np.sin(angle)) for angle in angles[:-1]]
    outer_points.append(outer_points[0])  # 닫힌 다각형 형성

    # 🔹 특정 영역만 회색 배경 칠하기
    ax.fill(angles, [outer_radius] * len(angles), color='#f0f0f0', alpha=1)

    # 🔹 레이더 차트 그리기
    ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color=color)
    ax.fill(angles, scores, alpha=0.3, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)

    # 🔹 여러 개의 방사형 격자선 추가
    num_grid_lines = 5  # 격자선 개수 설정
    grid_step = outer_radius / num_grid_lines  # 격자선 간격 계산

    for i in range(1, num_grid_lines + 1):
        r = grid_step * i  # 현재 격자선의 반경

        # 🔹 각 반경에 대해 다각형 모양으로 격자선 그리기
        grid_points = [(r * np.cos(angle), r * np.sin(angle)) for angle in angles[:-1]]
        grid_points.append(grid_points[0])  # 닫힌 다각형 형성

        # 🔹 방사형 격자선 그리기
        ax.plot(angles, [r] * len(angles), color='grey', linestyle='-', linewidth=0.5)

    # 🔹 방사형 축 (중심에서 바깥으로 뻗는 선) 추가
    for angle in angles[:-1]:  # 마지막 닫힌 각도는 제외
        ax.plot([angle, angle], [0, outer_radius], color='grey', linestyle='-', linewidth=0.5)

    # 🔹 외곽 테두리 연결
    for i in range(len(outer_points) - 1):
        ax.plot([angles[i], angles[i+1]],
                [outer_radius, outer_radius],
                color='grey', linestyle='-', linewidth=1)

    for angle, score, label in zip(angles[:-1], scores[:-1], labels):
        ax.text(angle, score, f'{score:.2f}', ha='center', fontsize=12, fontweight='bold', color='black')

    # 🔹 y축 눈금 제거
    ax.set_yticklabels([])

    return fig