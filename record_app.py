import streamlit as st
import pandas as pd
import os

# CSV 파일 로드
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

# 기본 매장 데이터 (CSV 데이터 기반 변환)
initial_starbucks = [
    {
        "name": row["이름"],
        "types": store_types.get(row["이름"], ["기타"]),
    }
    for _, row in df.iterrows()
]

# 웹페이지 기본 설정
st.set_page_config(
    page_title='⭐SIREN VALUE⭐',
    page_icon='📊',
)

# 웹페이지 타이틀과 설명
st.title("⭐SIREN VALUE⭐")

# 스타벅스 위치 유형 이모지 매핑
type_emoji_dict = {
    "대학가": "🎓", "터미널/기차역": "🚉", "병원": "🏥", "지하철 인접": "🚈", "기타": "❓"
}

# 매장 유형 필터 추가
selected_types = st.multiselect(
    "조회할 매장 유형을 선택하세요",
    options=list(type_emoji_dict.keys()),
    default=list(type_emoji_dict.keys())
)

st.markdown('새로운 매장을 추가해보세요!')

# 세션 상태에 매장 데이터가 없으면 초기 데이터로 설정
if "stores" not in st.session_state:
    st.session_state.stores = initial_starbucks

# 매장 추가 입력 폼
with st.form(key="store_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(label="매장 이름", value="스타벅스 신촌점")

    with col2:
        types = st.multiselect(label="매장 유형", options=list(type_emoji_dict.keys()), max_selections=2)

    submit = st.form_submit_button(label="매장 추가")

    if submit:
        if not name:
            st.error("매장 이름을 입력해주세요.")
        elif len(types) == 0:
            st.error("매장 유형을 적어도 1개 선택해주세요.")
        else:
            st.success("매장이 추가되었습니다!")
            st.session_state.stores.append({"name": name, "types": types})
            st.rerun()

st.markdown('서울 지역 분석 결과 바로보기')

# 선택된 유형만 포함된 매장 필터링
filtered_stores = [
    store for store in st.session_state.stores
    if set(store['types']).issubset(set(selected_types))
]

## 매장 검색기능 추가

# 매장 검색 기능 추가
search_query = st.text_input("🔍 매장 검색", value="")

# 검색어가 입력된 경우, 검색어를 포함하는 매장만 필터링
if search_query:
    filtered_stores = [store for store in filtered_stores if search_query.lower() in store['name'].lower()]

# 검색 결과 없을 때 메시지 표시
if not filtered_stores:
    st.warning("🚫 해당 검색어에 맞는 매장이 없습니다.")

# 매장 목록을 3개씩 나누어 출력
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