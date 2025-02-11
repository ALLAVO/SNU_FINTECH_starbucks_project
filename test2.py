import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import random

def get_store_chart_data():
    # 차트별 제목
    chart_titles = ["외향형", "내향형", "수다형", "카공형"]

    # 각 차트별 다른 레이블
    labels_list = [
        ["유동인구", "상권 크기", "상점 수", "소비자 수", "브랜드 인지도", "경제력"],
        ["대중교통", "도보 접근성", "차량 접근성", "주차 가능성", "혼잡도", "거리"],
        ["경쟁 매장 수", "가격 경쟁력", "서비스 품질", "고객 충성도", "리뷰 점수", "광고 효과"],
        ["직원 친절도", "청결도", "메뉴 다양성", "매장 분위기", "좌석 수", "WiFi 속도"]
    ]

    # 4개의 차트 데이터 생성 및 점수 랜덤 부여
    all_scores = [np.array([random.randint(1, 10) for _ in range(6)]) for _ in range(4)]

    return all_scores, chart_titles, labels_list

# 한글 폰트 설정 (Mac: AppleGothic, Windows: Malgun Gothic, Linux: NanumGothic)
plt.rc('font', family='AppleGothic')  # Mac 사용자의 경우
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 깨짐 방지

st.set_page_config(
    page_title="매장 상세 분석",
    page_icon="📊",
)

st.title("📊 스타벅스 매장 상세 분석")

# 선택된 매장 정보 가져오기
if "selected_store" not in st.session_state:
    st.warning("⚠️ 분석할 매장을 먼저 선택해주세요!")
    st.stop()

store_name = st.session_state.selected_store
st.subheader(f"🏪 {store_name}")

# 데이터 불러오기
all_scores, chart_titles, labels_list = get_store_chart_data()
angles = np.linspace(0, 2 * np.pi, 7)

# 2x2 차트 레이아웃 생성
cols = st.columns(2)

for i in range(4):
    with cols[i % 2]:  # 2열로 배치
        st.markdown(f"<h3 style='text-align: center;'>{chart_titles[i]}</h3>", unsafe_allow_html=True)

        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
        scores = np.append(all_scores[i], all_scores[i][0])  # 닫힌 육각형
        ax.plot(angles, scores, 'o-', linewidth=2, label=chart_titles[i])
        ax.fill(angles, scores, alpha=0.3)

        # 차트별 다른 레이블 적용
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels_list[i])

        st.pyplot(fig)

# 뒤로 가기 버튼
if st.button("⬅️ 돌아가기"):
    st.switch_page("app.py")
