import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from store_data import chart_info
from modules.score_utils import get_scores_from_all_csv  # 모듈 불러오기

# 📌 CSV 데이터 로드
csv_file_path = "data/starbucks_seoul_data.csv"
df = pd.read_csv(csv_file_path)

# 추가 CSV 파일 로드 및 매장 유형 매칭
csv_files = {
    "대학가": "data/스타벅스_대학가.csv",
    "병원": "data/스타벅스_병원.csv",
    "지하철 인접": "data/스타벅스_지하철인접.csv",
    "터미널/기차역": "data/스타벅스_터미널_기차역.csv",
}

# 매장 유형 딕셔너리 생성
store_types = {}
for store_type, file_path in csv_files.items():
    if os.path.exists(file_path):
        df_type = pd.read_csv(file_path)
        if "매장명" in df_type.columns:
            for name in df_type["매장명"].dropna().unique():
                store_types[name] = store_types.get(name, []) + [store_type]

# 📌 기본 매장 데이터 (CSV 데이터 기반 변환)
initial_starbucks = [
    {
        "name": row["이름"],
        "types": store_types.get(row["이름"], ["기타"]),
    }
    for _, row in df.iterrows()
]

# 📌 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

# 📌 웹페이지 기본 설정
st.set_page_config(
    page_title='⭐SIREN VALUE⭐',
    page_icon="☕",
)

# =========================================
# 1. CSS 스타일 & 3D 카드 디자인 추가
# =========================================
st.markdown(
    """
    <style>
    /* 페이지 배경 그라디언트 및 기본 애니메이션 유지 */
    body {
        background: linear-gradient(135deg, #E3F2FD, #FFE8E8, #E5FFF5);
        background-size: 400% 400%;
        animation: gradientBG 10s ease infinite;
        margin: 0; padding: 0;
    }
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }

    /* 메인 컨테이너 (유리효과) */
    .main {
        background-color: rgba(255, 255, 255, 0.7) !important; 
        backdrop-filter: blur(6px);
        padding: 1rem;
        border-radius: 8px;
    }

    /* 일반 제목 스타일 */
    .title {
        color: #1A1A1A;
        text-align: center;
        font-weight: 900;
        margin-bottom: 0.6em;
        font-size: 2.0rem;
        letter-spacing: -1px;
    }

    /* 3D 카드 효과 */
    .store-card {
        background: linear-gradient(45deg, #FFFFFF, #F9F9F9);
        border-radius: 12px;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
        padding: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        transform-style: preserve-3d;
        margin-bottom: 1.2rem;
    }
    .store-card:hover {
        transform: translateY(-5px) rotateX(5deg) rotateY(3deg);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
    }

    /* 매장 아이콘 */
    .store-icon {
        width: 50px;
        display: block;
        margin: 0 auto 0.5rem auto; /* 중앙 정렬 & 아래쪽 여백 */
    }

    /* 매장명 */
    .store-name {
        text-align: center;
        font-weight: 700;
        color: #2C2C2C;
        margin-bottom: 0.3rem;
        font-size: 1.1rem;
    }

    /* 매장 유형 정보 */
    .store-type {
        text-align: center;
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
    }

    /* 다른 스타일들 */
    .slide-up {
        animation: slideUp 0.4s ease-out;
    }
    @keyframes slideUp {
        0% { transform: translateY(10px); opacity: 0; }
        100% { transform: translateY(0); opacity: 1; }
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =========================================
# 2. 탭 레이아웃 (Pills 스타일)
# =========================================
tab1, tab2 = st.tabs(["📋 매장 목록 보기", "🏪 매장 별 비교하기"])

# =========================================
# 3. "매장 목록 보기" 탭
# =========================================
with tab1:
    st.title("⭐SIREN VALUE⭐")

    # 스타벅스 위치 유형 이모지 매핑
    type_emoji_dict = {
        "대학가": "🎓",
        "터미널/기차역": "🚉",
        "병원": "🏥",
        "지하철 인접": "🚈",
        "기타": "☑️"
    }

    # 매장 아이콘(원하는 이미지 링크로 변경 가능)
    store_icon_url = "https://img.icons8.com/ios-filled/100/shop.png"

    # 매장 유형 필터
    selected_types = st.multiselect(
        "📌 조회할 매장 유형 선택",
        options=list(type_emoji_dict.keys()),
        default=list(type_emoji_dict.keys())
    )

    if "stores" not in st.session_state:
        st.session_state.stores = initial_starbucks

    # 선택된 유형만 포함된 매장
    filtered_stores = [
        store for store in st.session_state.stores
        if set(store['types']).issubset(set(selected_types))
    ]

    st.markdown('서울 지역 분석 결과 바로보기')

    # 🔍 검색 기능 추가
    search_query = st.text_input("🔍 매장 검색", value="")
    if search_query:
        filtered_stores = [
            store for store in filtered_stores
            if search_query.lower() in store['name'].lower()
        ]

    # 검색 결과 없을 때
    if not filtered_stores:
        st.warning("🚫 해당 검색어에 맞는 매장이 없습니다.")

    # 매장 목록을 3개씩 나누어 표시
    for i in range(0, len(filtered_stores), 3):
        row_stores = filtered_stores[i:i+3]
        cols = st.columns(3)

        for j in range(len(row_stores)):
            with cols[j]:
                store = row_stores[j]
                store_name = store["name"]
                emoji_types = [f"{type_emoji_dict.get(x, '❓')} {x}" for x in store.get('types', [])]

                # 📌 입체적 카드 HTML (expander 내부에 넣어도 되고, 그대로 사용 가능)
                with st.expander(label=f"**{i+j+1}. {store_name}**", expanded=True):
                    store_card_html = f"""
                    <div class='store-card slide-up'>
                        <img src='{store_icon_url}' alt='Store Icon' class='store-icon'/>
                        <div class='store-name'>{store_name}</div>
                        <div class='store-type'>{' / '.join(emoji_types)}</div>
                    </div>
                    """
                    st.markdown(store_card_html, unsafe_allow_html=True)

                    # 매장 상세 분석 버튼
                    if st.button(f"📊 {store_name} 분석", key=f"analyze_{i+j}"):
                        st.session_state.selected_store = store_name
                        st.switch_page("pages/store_detail.py")

                    # 매장 삭제 버튼
                    if st.button("삭제", key=f"delete_{i+j}"):
                        del st.session_state.stores[i+j]
                        st.experimental_rerun()

# =========================================
# 4. "매장 별 비교하기" 탭
# =========================================
with tab2:
    st.title("🏪 매장 비교하기")

    # 2개의 매장 선택
    col1, col2 = st.columns(2)
    with col1:
        selected_store_1 = st.selectbox("첫 번째 매장 선택", [""] + [store['name'] for store in st.session_state.stores], index=0)
    with col2:
        selected_store_2 = st.selectbox("두 번째 매장 선택", [""] + [store['name'] for store in st.session_state.stores], index=0)

    # 두 매장이 선택된 경우만 차트 비교
    if selected_store_1 and selected_store_2:
        st.subheader(f"📊 {selected_store_1} vs {selected_store_2}")

        # 2x2 차트 레이아웃
        cols = st.columns(2)

        for i, (title, labels) in enumerate(chart_info):  # chart_info에서 테마명과 평가 기준 가져오기
            with cols[i % 2]:  # 2열 배치
                # 차트 제목 중앙 정렬
                st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

                file_name_keyword = title
                all_scores_1 = get_scores_from_all_csv(selected_store_1, labels, file_name_keyword)
                all_scores_2 = get_scores_from_all_csv(selected_store_2, labels, file_name_keyword)

                angles = np.linspace(0, 2 * np.pi, len(all_scores_1)+1)

                fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})

                scores_1 = np.append(all_scores_1, all_scores_1[0])
                ax.plot(angles, scores_1, 'o-', linewidth=2, label=selected_store_1, color="blue")
                ax.fill(angles, scores_1, alpha=0.3, color="blue")

                scores_2 = np.append(all_scores_2, all_scores_2[0])
                ax.plot(angles, scores_2, 'o-', linewidth=2, label=selected_store_2, color="red")
                ax.fill(angles, scores_2, alpha=0.3, color="red")

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(labels)
                ax.legend(loc="upper right")

                st.pyplot(fig)
    else:
        st.warning("📢️ 두 개의 매장을 선택해주세요!")