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
# 마이너스 폰트 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False

# 📌 웹페이지 기본 설정
st.set_page_config(
    page_title='⭐SIREN VALUE⭐',
    page_icon="☕",
)

# 📌 기본 매장 데이터 (CSV 데이터 기반 변환)
initial_starbucks = [
    {
        "name": row["이름"],
        "types": store_types.get(row["이름"], ["기타"]),
    }
    for _, row in df.iterrows()
]

# 📌 페이지 선택 (Pills 스타일 탭)
tab1, tab2 = st.tabs(["📋 매장 목록 보기", "🏪 매장 별 비교하기"])

# 📌 "매장 목록 보기" 기능
with tab1:
    st.title("⭐SIREN VALUE⭐")

    # 스타벅스 위치 유형 이모지 매핑
    type_emoji_dict = {
        "대학가": "🎓", "터미널/기차역": "🚉", "병원": "🏥", "지하철 인접": "🚈", "기타": "☑️"
    }

    # 📌 매장 유형 필터 추가
    selected_types = st.multiselect(
        "📌 조회할 매장 유형 선택",
        options=list(type_emoji_dict.keys()),
        default=list(type_emoji_dict.keys())
    )
    # 📌 세션 상태 초기화
    if "stores" not in st.session_state:
        st.session_state.stores = initial_starbucks

    # 선택된 유형만 포함된 매장 필터링
    filtered_stores = [
        store for store in st.session_state.stores
        if set(store['types']).issubset(set(selected_types))
    ]

    st.markdown('서울 지역 분석 결과 바로보기')

    # 📌 🔍 검색 기능 추가
    search_query = st.text_input("🔍 매장 검색", value="")

    # 검색어가 입력된 경우, 검색어를 포함하는 매장만 필터링
    if search_query:
        filtered_stores = [store for store in filtered_stores if search_query.lower() in store['name'].lower()]

    # 검색 결과 없을 때 메시지 표시
    if not filtered_stores:
        st.warning("🚫 해당 검색어에 맞는 매장이 없습니다.")

    # 매장 목록을 3개씩 나누어 출력`
    for i in range(0, len(filtered_stores), 3):
        row_stores = filtered_stores[i:i+3]
        cols = st.columns(3)

        for j in range(len(row_stores)):
            with cols[j]:
                store = row_stores[j]
                with st.expander(label=f"**{i+j+1}. {store['name']}**", expanded=True):

                    emoji_types = [f"{type_emoji_dict.get(x, '❓')} {x}" for x in store.get('types', [])]
                    st.text(" / ".join(emoji_types))

                    # 매장 상세 분석 페이지로 이동 버튼
                    if st.button(f"📊 {store['name']} 분석", key=f"button_{i+j}"):
                        st.session_state.selected_store = store['name']
                        st.switch_page("pages/store_detail.py")  # 상세 페이지로 이동

                    # 매장 삭제 버튼
                    delete_button = st.button(label="삭제", key=f"delete_{i+j}")

                    if delete_button:
                        del st.session_state.stores[i+j]
                        st.rerun()

# 📌 "매장 별 비교하기" 기능
with tab2:
    st.title("🏪 매장 비교하기")

    # 📌 2개의 매장을 선택하도록 드롭다운 추가
    col1, col2 = st.columns(2)
    with col1:
        selected_store_1 = st.selectbox("첫 번째 매장 선택", [""] + [store['name'] for store in st.session_state.stores], index=0)
    with col2:
        selected_store_2 = st.selectbox("두 번째 매장 선택", [""] + [store['name'] for store in st.session_state.stores], index=0)

    # 📌 두 개의 매장이 선택된 경우 비교 차트 생성
    if selected_store_1 and selected_store_2:
        st.subheader(f"📊 {selected_store_1} vs {selected_store_2}")

        # 📌 2x2 차트 레이아웃 생성
        cols = st.columns(2)

        for i, (title, labels) in enumerate(chart_info):  # chart_info에서 테마명과 평가 기준 가져오기
            with cols[i % 2]:  # 2열로 배치
                # 📌 차트 제목 중앙 정렬
                st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

                # 유형별 키워드를 파일명에서 찾음
                file_name_keyword = title

                all_scores_1 = get_scores_from_all_csv(selected_store_1, labels, file_name_keyword)
                all_scores_2 = get_scores_from_all_csv(selected_store_2, labels, file_name_keyword)
                angles = np.linspace(0, 2 * np.pi, 7)

                fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})

                scores_1 = np.append(all_scores_1, all_scores_1[0])  # 닫힌 육각형
                ax.plot(angles, scores_1, 'o-', linewidth=2, label=selected_store_1, color="blue")
                ax.fill(angles, scores_1, alpha=0.3, color="blue")

                # 📌 두 번째 매장 차트 (빨간색)
                scores_2 = np.append(all_scores_2, all_scores_2[0])  # 닫힌 육각형
                ax.plot(angles, scores_2, 'o-', linewidth=2, label=selected_store_2, color="red")
                ax.fill(angles, scores_2, alpha=0.3, color="red")

                # 📌 축 설정
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(labels)  # 📌 chart_info에서 가져온 labels 적용

                # 📌 범례 추가
                ax.legend(loc="upper right")

                st.pyplot(fig)

    else:
        st.warning("📢️ 두 개의 매장을 선택해주세요!")