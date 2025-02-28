import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import folium
import json
import tempfile
import streamlit.components.v1 as components
from streamlit_folium import st_folium
from modules.score_utils import load_all_scores, get_scores_from_all_csv  # 모듈 불러오기
import base64
import requests
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
from pyvis.network import Network
import numpy as np

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
    layout="wide",
    page_title='SIREN VALUE',
    page_icon="https://img.icons8.com/fluency/48/starbucks.png",
    initial_sidebar_state="collapsed" #처음에 열때 사이드 바 접힌 상태로 나옴
)

# 매장 유형별 색상 정의
store_type_colors = {
    'general': '#00704A',     # Regular Starbucks green
    'reserve': '#A6192E',     # Reserve stores in dark red
    'generalDT': '#FF9900',   # Drive-thru in orange
    'generalWT': '#4B3C8C'    # Walk-thru in purple
}

# ================ 추가 유틸리티 함수 (Tab2) ================
# Tab2의 점수 총합 비교를 위한 함수들 포함
# 서울 매장 데이터 로드 함수
@st.cache_data
def load_store_data():
    df = pd.read_csv('data/starbucks_seoul_all_store_info.csv')
    df['district'] = df['주소'].str.extract(r'서울특별시\s+(\S+구)')
    df['매장명'] = df['매장명'].str.strip()
    # 이름 처리 - 점(点) 제거 및 정규화
    df['매장명_원본'] = df['매장명']  # 원본 이름 보존
    df['매장명'] = df['매장명'].str.replace('점', '').str.strip()  # '점' 제거된 버전 사용
    return df

@st.cache_data
def load_seoul_geojson():
    response = requests.get('https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json')
    return response.json()

@st.cache_data
def load_theme_scores():
    merged_df, b_values = load_all_scores()
    # 매장명 정규화 - '점' 제거
    merged_df['Store_Original'] = merged_df['Store']  # 원본 이름 보존
    merged_df['Store'] = merged_df['Store'].str.strip().str.replace('점', '').str.strip()
    return merged_df, b_values

# ================ 추가 유틸리티 함수 (Tab3,4) ================
# Tab3의 매장, 인구 수 비교를 위한 함수들 포함
# Tab4의 음료 분석 비교를 위한 함수들 포함
@st.cache_data
def load_beverage_data():
    df = pd.read_csv('data/starbucks_nutrition_with_images.csv')
    return df

@st.cache_data
def load_review_counts():
    df = pd.read_csv('data/starbucks_review_num_with_district.csv')
    return df

@st.cache_data
def load_worker_data():
    df = pd.read_csv('data/seoul_district_age_group_workers.csv')
    return df

@st.cache_data
def load_review_data():
    df = pd.read_csv('data/cleaned_starbucks_reviews_with_counts.csv')
    return df

# 키워드 불러오기
@st.cache_data
def load_keywords_data():
    with open('./keyword_data/store_keywords.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def load_theme_keywords():
    df = pd.read_csv('./keyword_data/0_네이버_리뷰_테마_전체.csv')
    return df['Keywords'].tolist()

@st.cache_data
def generate_wordcloud(text_data, width=800, height=400):
    wordcloud = WordCloud(
        font_path='NanumSquareRoundB.ttf',  # 폰트 경로 확인 필요
        width=width,
        height=height,
        background_color='white',
        colormap='Greens',
        max_words=100
    ).generate_from_frequencies(text_data)
    return wordcloud

def get_store_theme_scores(theme_type, selected_district='전체'):
    try:
        merged_df, _ = load_theme_scores()
        theme_pattern = f"{theme_type}_테마_키워드_매장별_Theme_score.csv"
        theme_df = merged_df[merged_df['FileName'].str.contains(theme_pattern, case=False)]

        if theme_df.empty:
            return pd.DataFrame()

        df_stores = load_store_data()

        # 매장명에서 '점'이 제거된 버전으로 매칭
        theme_df = theme_df.merge(
            df_stores[['매장명', 'district', '주소', '매장명_원본']],
            left_on='Store',
            right_on='매장명',
            how='inner'
        )

        if selected_district != '전체':
            theme_df = theme_df[theme_df['district'] == selected_district]

        total_scores = theme_df.groupby('매장명_원본').agg({
            'log_score': 'sum',
            'district': 'first',
            '주소': 'first'
        }).reset_index()

        # 컬럼명 변경 - Store로 통일
        total_scores = total_scores.rename(columns={'매장명_원본': 'Store'})
        total_scores = total_scores.sort_values('log_score', ascending=False)

        return total_scores

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {str(e)}")
        return pd.DataFrame()
# =========================================
# 네트워크 그래프를 위한 함수들 호출
# =========================================
# 키워드 카테고리 매핑 함수
def map_keywords_to_categories(keywords):
    # 카테고리 키워드 맵핑
    category_keywords = {
        "맛/음료": ["맛있", "커피", "디저트", "메뉴", "음료", "차가", "양이"],
        "청결/위생": ["청결", "깨끗", "화장실"],
        "좌석/공간": ["좌석", "편해", "자리", "넓어", "의자", "매장이 넓"],
        "인테리어/분위기": ["인테리어", "분위기", "예쁜", "멋", "뷰", "사진", "음악"],
        "서비스": ["친절", "서비스", "가성비"],
        "사교/대화": ["대화", "수다", "친구"],
        "집중/업무": ["집중", "공부", "카공", "오래 머무"]
    }
    
    keyword_to_category = {}
    
    # 각 키워드를 적절한 카테고리로 매핑
    for keyword in keywords:
        keyword_lower = keyword.lower()
        assigned = False
        
        for category, patterns in category_keywords.items():
            if not assigned:
                for pattern in patterns:
                    if pattern in keyword_lower:
                        keyword_to_category[keyword] = category
                        assigned = True
                        break
        
        if not assigned:
            keyword_to_category[keyword] = "기타"
    
    return keyword_to_category

# 키워드 네트워크 데이터 생성 함수
def create_keyword_network(data, min_edge_weight=0, max_edges=100, theme_keywords=None, min_node_value=0):
    # 키워드 총 빈도수 계산
    keyword_total_freq = {}
    for store, keywords in data.items():
        for keyword, freq in keywords.items():
            keyword_total_freq[keyword] = keyword_total_freq.get(keyword, 0) + freq
    
    # 테마 키워드 필터링
    if theme_keywords:
        filtered_keywords = {k: v for k, v in keyword_total_freq.items() if k in theme_keywords}
    else:
        filtered_keywords = keyword_total_freq
    
    # 최소 빈도수 필터링
    filtered_keywords = {k: v for k, v in filtered_keywords.items() if v >= min_node_value}
    
    # 카테고리 매핑
    keyword_categories = map_keywords_to_categories(filtered_keywords.keys())
    
    # 노드 생성
    nodes = []
    for keyword, freq in filtered_keywords.items():
        category = keyword_categories.get(keyword, "기타")
        
        # 노드 크기 계산 (로그 스케일로 조정)
        size = 15 + np.log1p(freq) * 5
        
        nodes.append({
            "id": keyword,
            "label": keyword,
            "value": freq,
            "title": f"{keyword}<br>총 언급 횟수: {freq}회",
            "category": category,
            "size": size
        })
    
    # 동시 등장 관계 행렬 생성
    co_occurrence = {}
    node_connections = {}
    
    # 키워드 빈도 정규화 (상위 키워드의 영향 감소)
    max_freq = max(filtered_keywords.values())
    normalized_keywords = {k: v/max_freq for k, v in filtered_keywords.items()}
    
    for store, store_keywords in data.items():
        keyword_list = list(store_keywords.keys())
        
        for i, keyword1 in enumerate(keyword_list):
            if keyword1 not in filtered_keywords:
                continue
                
            if keyword1 not in co_occurrence:
                co_occurrence[keyword1] = {}
                node_connections[keyword1] = {}
            
            for j, keyword2 in enumerate(keyword_list):
                if i != j and keyword2 in filtered_keywords:
                    # 연관 강도 계산 (정규화된 빈도 사용)
                    strength = np.sqrt(
                        normalized_keywords[keyword1] * 
                        normalized_keywords[keyword2] * 
                        store_keywords[keyword1] * 
                        store_keywords[keyword2]
                    )
                    
                    co_occurrence[keyword1][keyword2] = co_occurrence[keyword1].get(keyword2, 0) + strength
                    node_connections[keyword1][keyword2] = node_connections[keyword1].get(keyword2, 0) + strength
    
    # 엣지 생성
    edges = []
    for keyword1, relations in co_occurrence.items():
        for keyword2, strength in relations.items():
            # 중복 방지 (A-B와 B-A 중 하나만 추가)
            if keyword1 < keyword2 and strength >= min_edge_weight:
                edges.append({
                    'from': keyword1,
                    'to': keyword2,
                    'value': strength,
                    'title': f"{keyword1} ↔ {keyword2}: {strength:.1f}"
                })
    
    # 강도 기준 내림차순 정렬
    edges.sort(key=lambda x: x['value'], reverse=True)
    
    # 최대 엣지 수 제한
    edges = edges[:max_edges]
    
    # 각 노드에 대한 상위 연관 키워드 데이터
    node_top_connections = {}

    for node_id in node_connections:
        # 상위 6개 키워드로 변경
        top_cons = sorted(node_connections[node_id].items(), key=lambda x: x[1], reverse=True)[:6]
        node_top_connections[node_id] = [conn[0] for conn in top_cons]
        
    # 각 노드의 연관 강도 저장
    node_connection_strengths = {}
    for node_id in node_connections:
        connections = node_connections[node_id]
        sorted_connections = sorted(connections.items(), key=lambda x: x[1], reverse=True)
        node_connection_strengths[node_id] = {conn[0]: conn[1] for conn in sorted_connections[:6]}
    
    return {
        'nodes': nodes,
        'edges': edges,
        'top_connections': node_top_connections,
        'connection_strengths': node_connection_strengths
    }
    
# 카테고리별 색상 매핑
def get_category_colors():
    return {
        "맛/음료": "#006241",  # 스타벅스 그린
        "청결/위생": "#00A862",  # 밝은 초록색
        "좌석/공간": "#D4B59E",  # 베이지색
        "인테리어/분위기": "#FF8C3A",  # 주황색
        "서비스": "#1A75CF",  # 파란색
        "사교/대화": "#E01931",  # 빨간색
        "집중/업무": "#9370DB",  # 보라색
        "기타": "#767676"  # 회색
    }

# 세션 상태의 초기 좌표 가져오기
def get_initial_positions():
    if 'network_positions' not in st.session_state:
        # 초기값 생성 (빈 딕셔너리)
        st.session_state.network_positions = {}
    return st.session_state.network_positions

#지도, 매장, 음료 정보를 불러오기 위한 데이터 미리 호출
df_stores = load_store_data()
seoul_geo = load_seoul_geojson()
df_beverages = load_beverage_data()
df_review_counts = load_review_counts()
df_workers = load_worker_data()
df_reviews = load_review_data()
df_keywords = load_keywords_data()
df_theme_keywords = load_theme_keywords()

# TAB4의 직장인구 분석을 위한 데이터 전처리
# 직장인구 데이터 처리
df_workers['total_workers'] = (
    df_workers['male_10s_20s'] + df_workers['male_30s_40s'] + df_workers['male_50s_60s_above'] +
    df_workers['female_10s_20s'] + df_workers['female_30s_40s'] + df_workers['female_50s_60s_above']
)

# 구별 매장 수 계산
stores_per_district = df_stores.groupby('district').size().reset_index(name='store_count')

# 직장인구와 매장 수 데이터 병합
combined_district_data = pd.merge(
    df_workers,
    stores_per_district,
    left_on='district_name',
    right_on='district',
    how='left'
)
combined_district_data['store_count'] = combined_district_data['store_count'].fillna(0)
combined_district_data['stores_per_10k'] = (combined_district_data['store_count'] / combined_district_data['total_workers']) * 10000


# =========================================
# 추가 CSS & 디자인 요소 (네비게이션 바, 푸터, fade-in 애니메이션, 커스텀 네모칸 체크박스)
# =========================================
st.markdown(
    """
    <style>
    /* ✅ 1. 페이지 전체 배경 및 애니메이션
    페이지 배경 그라디언트 + fade-in 애니메이션 */
    body {
        background: linear-gradient(135deg, #E9F6F2, #FCFCFA, #CFE9E5); /* 배경 그라디언트 */
        background-size: 400% 400%; /* 배경 크기 확장 */
        animation: gradientBG 12s ease infinite, fadeIn 1s ease-in; /* 그라디언트 및 페이드인 애니메이션 */
        margin: 60px 0 0 0;  /* 페이지 외부 여백 (위쪽만 60px) */
        padding: 0; /* 내부 여백 제거 */
        font-family: 'Noto Sans KR', sans-serif; /* 폰트 스타일 */
    }
    
    /* 그라디언트 애니메이션 */
    @keyframes gradientBG { 
        0%   {background-position: 0% 50%;}
        50%  {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    
    /* 페이드인 애니메이션 (화면 로드 시) */
    @keyframes fadeIn {
        from { opacity: 0; } /* 시작: 투명 */
        to { opacity: 1; }   /* 끝: 불투명 */
    }

    /* ✅ 2. 네비게이션 바 (.navbar) */
    .navbar {
        width: 100%; /* 전체 너비 */
        padding: 1rem 2rem; /* 내부 여백 (위/아래 1rem, 좌/우 2rem) */
        background-color: #006241; /* 배경색 (스타벅스 그린) */
        color: #ffffff; /* 글씨색 (흰색) */
        text-align: center; /* 텍스트 가운데 정렬 */
        # font-size: 1.5rem; /* 글씨 크기 */
        font-weight: bold; /* 글씨 두껍게 */
        position: fixed; /* 화면 상단에 고정 */
        top: 0;  /* 화면 위쪽에 고정 */
        left: 0; /* 화면 왼쪽에 고정 */
        z-index: 1000; /* 다른 요소 위에 표시 */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* 하단 그림자 (입체감) */
    }
    
    /* 네비게이션 바 링크 스타일 */
    .navbar a {
        color: #ffffff; /* 링크 글씨색 (흰색) */
        margin: 0 1rem; /* 좌우 여백 */
        text-decoration: none; /* 밑줄 제거 */
        transition: color 0.3s ease; /* 색상 전환 부드럽게 */
    }
    
    /* 네비게이션 바 링크 호버 시 */
    .navbar a:hover {
        color: #C4D600; /* 마우스 오버 시 라임색으로 변경 */
    }

    /* ✅ 3. 푸터 (.footer) */
    .footer {
        text-align: center; /* 텍스트 중앙 정렬 */
        padding: 1rem; /* 내부 여백 */
        font-size: 0.8rem; /* 글씨 크기 (작게) */
        color: #1E3932; /* 글씨색 (스타벅스 그린 톤) */
        margin-top: 2rem; /* 위 여백 */
        border-top: 1px solid #CFE9E5; /* 상단 경계선 (연한 민트색) */
    }

    /* ✅ 4. 메인 컨테이너 투명도 및 블러 효과 (.main) */
    .main {
        background-color: rgba(255, 255, 255, 0.35) !important; /* 배경색*/
        backdrop-filter: blur(3px); /* 블러 효과 */
        padding: 1rem; /* 내부 여백 */
        border-radius: 8px; /* 모서리 둥글게 */
    }

    /* ✅ 5. 페이지 제목 스타일 (.title-center)
    페이지 제목 스타일 */
    .title-center {
        text-align: center; /* 제목 중앙 정렬 */
        font-weight: 900; /* 글씨 두껍게 */
        margin-bottom: 0.6em; /* 아래 여백 */
        font-size: 2.2rem; /* 글씨 크기 */
        letter-spacing: -1px; /* 글자 간격 좁게 */
        color: #006241; /* 글씨색 (스타벅스 그린) */
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.2); /* 그림자 효과 */
    }
    

    /* ✅ 7. 매장 카드 스타일 (.store-card)
    매장 카드 (Expander 내부) */
    .store-card {
        background: #CFE9E5 !important; /* 카드 배경색 (연한 민트) */
        border-radius: 12px; /* 모서리 둥글게 */
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1); /* 입체감 그림자 */
        padding: 1rem; /* 내부 여백 */
        transition: transform 0.3s ease, box-shadow 0.3s ease; /* 부드러운 전환 효과 */
        margin-bottom: 1.2rem; /* 아래 여백 */
        border: 1px solid #0062411A; /* 경계선 (스타벅스 그린의 투명한 버전) */
        color: #1E3932 !important; /* 글씨색 (짙은 스타벅스 그린) */
    }
    
    /* 🟡 카드 호버 시 애니메이션 */
    .store-card:hover {
        transform: translateY(-5px) rotateX(3deg) rotateY(2deg); /* 3D 효과 */
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15); /* 그림자 더 강조 */
    }
    
    /* 카드 내부 아이콘 스타일 */
    .store-icon {
        width: 45px; /* 아이콘 크기 */
        display: block; /* 블록 요소로 표시 */
        margin: 0 auto 0.5rem auto; /* 아이콘 중앙 정렬 */
        filter: drop-shadow(0 0 1px #ffffff88); /* 그림자 효과 */
    }
    
    /* 카드 내부 매장명 스타일 */
    .store-name {
        text-align: center; /* 중앙 정렬 */
        font-weight: 700;   /* 글씨 두껍게 */
        color: #1E3932 !important; /* 색상 (짙은 그린) */
        margin-bottom: 0.3rem; /* 아래 여백 */
        font-size: 1.1rem; /* 글씨 크기 */
    }
    
    /* 카드 내부 매장 유형 스타일 */
    .store-type {
        text-align: center; /* 중앙 정렬 */
        color: #1E3932 !important; /* 글씨색 (짙은 스타벅스 그린) */
        font-size: 0.9rem; /* 글씨 크기 */
        margin-bottom: 0.8rem; /* 아래 여백 */
    }

    .slide-up {
        animation: slideUp 0.4s ease-out;
    }
    @keyframes slideUp {
        0% { transform: translateY(10px); opacity: 0; }
        100% { transform: translateY(0); opacity: 1; }
    }

    /* ✅ 8. 모든 버튼에 대한 커스터마이징 */
    div.stButton > button {
        background-color: #B8FFE7;   /* 배경색 */
        color: #000000;              /* 글씨색 */
        border-radius: 5000px;       /* 구글 스타일 둥근 버튼 */
        border: 2px solid #006241;  /* 테두리 (스타벅스 그린) */
        padding: 0.5rem 1rem;        /* 내부 여백 */
        transition: transform 0.2s ease, box-shadow 0.2s ease; /* 부드러운 전환 */
    }
    
    /* 🟡 버튼 호버 시 효과 */
    div.stButton > button:hover {
        transform: translateY(-3px); /* 위로 살짝 올라감 */
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); /* 그림자 강조 */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================
# 네비게이션 바
# =========================================
st.markdown(
    """
    <div class="navbar">
        <a href="/">SIREN VALUE</a>
        <a href="#매장목록">매장 목록</a>
        <a href="#매장비교">매장 비교</a>
    </div>
    """,
    unsafe_allow_html=True
)

# 📌 배경사진 추가
def get_base64_of_image(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def add_bg_from_local(image_file):
    base64_image = get_base64_of_image(image_file)
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/avif;base64,{base64_image}");
            background-attachment: fixed;
            background-size: cover;
            # 이미지를 중앙 정렬 
            background-position: left left;
        }}
        .main .block-container {{
            # 배경 이미지의 좌우 여백 삭제
            padding-left: 0rem;
            padding-right: 0rem;
        }}
        # .block-container {{
        #     padding: 0;
        #     margin: 0;
        #     width: 100%;
        # }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 로컬 경로에 있는 이미지 불러오기
add_bg_from_local("images/스타벅스2.avif")

# 탭 이름 변경 - 기존 "매장 별 비교하기"에서 "서울 스타벅스 개인 특성 별 매장 추천"으로 변경
tab1, tab2, tab3, tab4 = st.tabs(["SEARCH", "COMPARISION", "ANALYSIS", "ChatBot"])

st.markdown(
    """
    <style>
    /* 🟢 탭 컨테이너 스타일 */
    div.stTabs {
        font-weight: bold;         /* 기본 글씨 두껍게 */
        font-size: 24px;           /* 기본 글씨 크기 */
        padding: 20px;             /* 내부 여백 */
    }
    
    /* 🟡 활성 탭 스타일링 (선택된 탭) */
    div.stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #004b2b; /* 선택된 탭 배경색 (더 진한 스타벅스 그린) */
        color: #FFFFFF !important; /* 선택된 탭 글씨색 (흰색) */
        font-size: 30px;          /* 선택된 탭 글씨 크기 (더 크게) */
        font-family: 'Noto Sans KR', sans-serif; /* 원하는 폰트 적용 */
        font-weight: 900;           /* 글씨 매우 두껍게 */
        # padding: 25px 50px;          /* 탭 크기 확대 */   
        transition: all 0.3s ease-in-out;
        border-radius: 12px;       /* 모서리 둥글게 */
    }
    
    /* 🟠 비활성 탭 스타일링 */
    div.stTabs [data-baseweb="tab"] {
        background-color: #C3D7BA; 
        transition: background-color 0.3s ease, color 0.3s ease;
        padding: 1rem 1.5rem; /* 탭 내부 여백 */
        font-weight: 600;     /* 기본 글씨 두께 */
        font-size: 24px;      /* 기본 글씨 크기 */
        padding: 25px 40px;          /* 탭 크기 확대 */   
        color: #1E3932;       /* 글씨색 (짙은 스타벅스 그린) */
        font-family: 'Noto Sans KR', sans-serif; /* 원하는 폰트 적용 */
        border-radius: 12px;       /* 모서리 둥글게 */
    }
    
    /* 🟢 탭 호버 시 스타일 */
    div.stTabs [data-baseweb="tab"]:hover {
        background-color: #C4D600; /* 라임색 */
        color: #FFFFFF; /* 흰색 글씨 */
        transform: scale(1.05); /* 약간 확대 효과 */
        transition: all 0.2s ease-in-out;
        border-radius: 12px;       /* 모서리 둥글게 */

    }
    </style>
    """,
    unsafe_allow_html=True
)

# 📌 "매장 목록 보기" 탭
with tab1:
    st.markdown("""
        <style>
        /* 🟢 기본 검색창 스타일링 */
        div[data-baseweb="input"] {
            border-radius: 25px; /* 모서리를 둥글게 (구글 검색창 스타일) */
            border: 2px solid #006241; /* 테두리 색상 (스타벅스 그린) */
            padding: 5px; /* 내부 여백 (입력창 안의 여백) */
            font-size: 20px; /* 입력 글자 크기 */
            transition: box-shadow 0.3s ease; /* 호버 시 박스 그림자 부드럽게 전환 */
            box-shadow: 0 2px 5px rgba(0,0,0,0.15); /* 기본 그림자 (은은한 느낌) */
            width: 70%; /* 검색창 너비 (화면의 70% 차지) */
            height: 5.3vh; /* 화면 높이의 5% */
            margin: 0 auto; /* 검색창을 화면 중앙 정렬 */
        }
    
        /* 🟡 검색창 호버 시 스타일링 (마우스 오버 효과) */
        div[data-baseweb="input"]:hover {
            box-shadow: 0 4px 10px rgba(0,0,0,0.2); /* 그림자를 더 진하게 (부드러운 떠 있는 느낌) */
        }
    
        /* 🟠 검색창 포커스 시 스타일링 (클릭 시 효과) */
        div[data-baseweb="input"]:focus-within {
            box-shadow: 0 0 10px rgba(0,128,0,0.5); /* 초록색 하이라이트 테두리 (스타벅스 테마) */
        }
        </style>
        """, unsafe_allow_html=True)

    # 🔍 검색 기능 (구글 스타일)
    search_query = st.text_input(
        "",         # 검색창 위에 문구 추가
        value="",
        placeholder="매장명을 검색해 보세요...",
    )

    # 매장 유형 선택 -> 네모칸 전체가 클릭 가능한 커스텀 체크박스 UI
    type_emoji_dict = {
        "대학가": "🎓",
        "터미널/기차역": "🚉",
        "병원": "🏥",
        "지하철 인접": "🚈",
        "기타": "☑️"
    }
    available_types = list(type_emoji_dict.keys())

    # 매장 유형 디자인을 위한 CSS 추가
    st.markdown("""
        <style>
        /* 🟢 매장 유형 선택 네모칸 (커스텀 체크박스) 스타일 */
        div.stCheckbox > label {
            display: flex;              /* 플렉스박스 사용 */
            flex-direction: column;     /* 세로 정렬 */
            align-items: center;        /* 가로축 중앙 정렬 */
            justify-content: center;    /* 세로축 중앙 정렬 */
            width: 20vw;               /* 네모칸 너비 (뷰포트 너비의 20%) */
            height: 10vh;              /* 네모칸 높이 (뷰포트 높이의 15%) */
            border: 1px solid #006241;  /* 테두리 (스타벅스 그린) */
            border-radius: 16px;        /* 모서리 둥글게 */
            background-color: #F5F5F5;  /* 배경색 (연한 회색) */
            color: #006241;             /* 글씨색 (스타벅스 그린) */
            font-weight: bold;          /* 글씨 두껍게 */
            font-size: 1.2vw;            /* 글씨 크기 (뷰포트 너비 기준) */
            padding: 1vw;               /* 내부 여백 */
            margin: 1vw;                /* 외부 여백 */
            transition: all 0.3s ease;  /* 부드러운 전환 효과 */
            box-shadow: 2px 2px 6px rgba(0, 0, 0, 0.1); /* 은은한 그림자 */
            cursor: pointer;            /* 클릭 시 포인터 모양 */
        }
    
        /* 🟡 체크박스 호버 시 효과 */
        div.stCheckbox > label:hover {
            background-color: #CFE9E5;  /* 호버 시 연한 민트색 */
            transform: scale(1.05);     /* 살짝 확대 */
            box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.15); /* 그림자 강조 */
        }
    
        /* 🟢 체크된 상태 스타일 */
        div.stCheckbox input[type="checkbox"]:checked + label {
            background-color: #CFE9E5;  /* 배경색 (스타벅스 그린) */
            color: #FFFFFF;             /* 글씨색 (흰색) */
            border: 3px solid #004b2b;  /* 테두리 (더 진한 스타벅스 그린) */
            font-size: 1.5vw;           /* 선택 시 글씨 크기 확대 */
            transition: all 0.3s ease;  /* 부드러운 전환 효과 */
        }
    
        /* 🟠 체크박스 애니메이션 효과 */
        div.stCheckbox input[type="checkbox"]:checked + label {
            animation: pulse 0.3s ease-in-out;
        }
    
        /* 💫 체크박스 선택 시 애니메이션 */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.08); }
            100% { transform: scale(1); }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div id='chip-container'>", unsafe_allow_html=True)
    # 한 행에 최대 5개씩 배치
    n_per_row = 5
    selected_types = []
    for i in range(0, len(available_types), n_per_row):
        cols = st.columns(min(n_per_row, len(available_types) - i))
        for j, store_type in enumerate(available_types[i:i+n_per_row]):
            with cols[j]:
                # 전체 네모칸을 클릭하면 체크박스 토글됨
                if st.checkbox(
                        f"{type_emoji_dict.get(store_type, '')}\n{store_type}",
                        value=False,
                        key=f"chip_{store_type}"
                ):
                    selected_types.append(store_type)
    st.markdown("</div>", unsafe_allow_html=True)
    # ----------------------------------

    # 매장 목록 불러오기 (세션 스토리지 사용)
    if "stores" not in st.session_state:
        st.session_state.stores = initial_starbucks

    # 선택된 유형만 포함한 매장 필터링
    filtered_stores = [
        store for store in st.session_state.stores
        if set(store['types']).issubset(set(selected_types))
    ]
    # 검색어 적용
    if search_query:
        filtered_stores = [
            store for store in filtered_stores
            if search_query.lower() in store['name'].lower()
        ]

    if not filtered_stores:
        # 알림 메시지에 대한 CSS 스타일 적용
        st.markdown(
            """
            <style>
            .custom-warning {
                background-color: rgba(120,155,0, 0.8);  /* 빨간색 배경, 투명도 20% */
                color: #151B19;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 필터링 결과가 없을 때 경고 메시지 표시
        filtered_stores = []  # 예시: 검색 결과가 없을 때

        if not filtered_stores:
            st.markdown('<div class="custom-warning">📢 원하는 매장 테마를 선택해주세요.</div>', unsafe_allow_html=True)
        # st.warning("🚫 해당 검색어에 맞는 매장이 없습니다.")

    else:
        # 📌 [css적용] 글씨 밑에 배경책 적용
        st.markdown(
            """
            <style>
            .custom-title {
                color: #ffffff; /* 글자 색상 (흰색) */
                font-weight: bold;
                display: inline-block;
                background-color: rgba(120,155,0, 0.7);  /* 흰색 배경, 투명도 50% */
                padding: 5px 10px;
                border-radius: 5px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown('#### <p class="custom-title">서울 지역 분석 결과 바로보기</p>', unsafe_allow_html=True)

        store_icon_url = "https://img.icons8.com/fluency/48/starbucks.png"

        # 매장 목록을 3개씩 나누어 표시
        for i in range(0, len(filtered_stores), 3):
            row_stores = filtered_stores[i:i+3]
            cols = st.columns(3)
            for j in range(len(row_stores)):
                with cols[j]:
                    store = row_stores[j]
                    store_name = store["name"]
                    # 매장 유형에 해당하는 이모지와 텍스트
                    emoji_types = [f"{type_emoji_dict.get(x, '❓')} {x}" for x in store.get('types', [])]
                    # with st.expander(label=f"**{i+j+1}. {store_name}**", expanded=True):
                    with st.expander(label="", expanded=True):
                        store_card_html = f"""
                        <div class='store-card slide-up'>
                            <img src='{store_icon_url}' alt='Store Icon' class='store-icon'/>
                            <div class='store-name'>{store_name}</div>
                            <div class='store-type'>{' / '.join(emoji_types)}</div>
                        </div>
                        """
                        st.markdown(store_card_html, unsafe_allow_html=True)
                        if st.button(f"📊 {store_name} 분석", key=f"analyze_{i+j}"):
                            st.session_state.selected_store = store_name
                            st.switch_page("pages/store_detail.py")


# 📌 "개인 특성별 매장 추천" 탭 - 새로운 내용으로 대체
with tab2:
    # "자치구 선택", "매장 유형 선택" 등 라벨에 대한 배경색
    st.markdown(
        """
        <style>
            .custom-label {
                display: inline-block;
                background-color: rgba(120, 155, 0, 0.7); /* 연두빛 배경, 투명도 70% */
                color: #ffffff; /* 글자 색상 (흰색) */
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 5px;
                margin-bottom: 0px; /* selectbox와의 간격 조정 */
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 필터 컬럼 생성
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        # 기존 스타일과 유사하게 구 선택 드롭다운
        df_stores = load_store_data()
        districts = ['전체'] + sorted(df_stores['district'].unique().tolist())

        # HTML을 활용한 제목 스타일링 (배경색 적용)
        st.markdown('##### <p class="custom-label">자치구 선택</p>', unsafe_allow_html=True)

        # selectbox의 label을 완전히 숨기기
        selected_district = st.selectbox(
            label="",
            options=districts,
            key="district_filter",
            label_visibility="collapsed"  # 제목 숨기기
        )

    with filter_col2:
        # HTML을 활용한 제목 스타일링
        st.markdown('##### <p class="custom-label">매장 유형 선택</p>', unsafe_allow_html=True)

        # selectbox의 label을 완전히 숨기기
        selected_theme = st.selectbox(
            label="",
            options=["내향형", "수다형", "외향형", "카공형"],
            key="theme_filter",
            label_visibility="collapsed"  # 제목 숨기기
        )


    st.markdown("<br>", unsafe_allow_html=True)


    # Main content columns
    col1, col2 = st.columns([5, 5])

    with col1:
        if selected_district != '전체':
            st.markdown(
                f'##### <p class="custom-label">{selected_district} 지역 매장 분포도</p>',
                unsafe_allow_html=True
            )
        else:
            st.markdown('##### <p class="custom-label">서울 전체 매장 분포도</p>', unsafe_allow_html=True)

        # 선택된 지역구에 따라 지도 중심 설정
        if selected_district != '전체':
            district_data = df_stores[df_stores['district'] == selected_district]
            center_lat = district_data['위도'].mean()
            center_lng = district_data['경도'].mean()
            zoom_level = 13
        else:
            center_lat, center_lng = 37.5665, 126.9780
            zoom_level = 11

        # 지도 생성
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=zoom_level,
            tiles="CartoDB positron"  # 💡 밝은 테마
        )

        # 지역구 경계 스타일 설정
        style_function = lambda x: {
            'fillColor': '#00704A' if x['properties']['name'] == selected_district else 'transparent',
            'color': '#00704A' if x['properties']['name'] == selected_district else '#666666',
            'weight': 2 if x['properties']['name'] == selected_district else 1,
            'fillOpacity': 0.2 if x['properties']['name'] == selected_district else 0,
        }

        # GeoJSON 경계 추가
        folium.GeoJson(
            seoul_geo,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=['name'],
                aliases=['지역구:'],
                style=('background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;')
            )
        ).add_to(m)

        # TOP 9 매장 목록 획득
        top10_stores = []
        total_scores = get_store_theme_scores(selected_theme, selected_district)
        if not total_scores.empty:
            top10_stores = total_scores.head(10)['Store'].tolist()

        # 선택된 지역구만 또는 전체 표시
        if selected_district != '전체':
            display_stores = df_stores[df_stores['district'] == selected_district]
        else:
            display_stores = df_stores

        # 매장 마커 추가 (TOP 10은 특별 강조)
        for idx, row in display_stores.iterrows():
            is_top10 = row['매장명_원본'] in top10_stores

            # 팝업 내용
            popup_content = f"""
            <div style="font-family: 'Malgun Gothic', sans-serif;">
                <b>{row['매장명_원본']}</b><br>
                <b>주소:</b> {row['주소']}<br>
                <b>전화번호:</b> {row['전화번호']}
                {f'<br><b style="color: #036635;">✨ {selected_theme} TOP 10 매장</b>' if is_top10 else ''}
            </div>
            """

            # TOP 9 매장은 특별 마커로 표시
            store_icon_url = "https://img.icons8.com/fluency/48/starbucks.png"
            if is_top10:
                # 아이콘 설정
                icon = folium.CustomIcon(
                    icon_image=store_icon_url,
                    icon_size=(48, 48)  # 아이콘 크기 설정
                )

                # 매장 마커 추가 (이미지 아이콘 적용)
                folium.Marker(
                    location=[row['위도'], row['경도']],
                    icon=icon,
                    popup=folium.Popup(popup_content, max_width=300)
                ).add_to(m)

                # 매장명 라벨 추가
                folium.map.Marker(
                    [row['위도'], row['경도']],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 11px; color: #D92121; font-weight: bold; text-shadow: 2px 2px 2px white;">{row["매장명_원본"]}</div>',
                        icon_size=(150,20),
                        icon_anchor=(75,0)
                    )
                ).add_to(m)

            else:
                # 일반 매장 마커
                folium.CircleMarker(
                    location=[row['위도'], row['경도']],
                    radius=5,
                    popup=folium.Popup(popup_content, max_width=300),
                    color='#00704A',
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)

        st_folium(m, use_container_width=True, height=700)

    with col2:
        # 페이지가 새로 로드되면 선택된 매장 리스트 초기화
        if "selected_stores" not in st.session_state:
            st.session_state.selected_stores = []

        # {selected_theme} 추천 매장 TOP 9 출력
        st.markdown(
            f'##### <p class="custom-label">{selected_theme} 추천 매장 TOP 9</p>',
            unsafe_allow_html=True
        )

        total_scores = get_store_theme_scores(selected_theme, selected_district)

        if not total_scores.empty:
            top9 = total_scores.head(9)
            selected_stores = st.session_state.selected_stores.copy()  # 현재 선택된 매장 복사

            # 매장 목록을 3개씩 나누어 카드 형태로 표시
            for i in range(0, len(top9), 3):
                row_stores = top9.iloc[i:i+3]
                cols = st.columns(3)

                # 두 번째 행부터 간격 추가
                margin_top = "30px" if i >= 3 else "14px"

                for j in range(len(row_stores)):
                    with cols[j]:
                        store = row_stores.iloc[j]
                        store_name = store["Store"]
                        is_selected = store_name in selected_stores

                        # 선택된 매장인지에 따라 카드 배경색 변경
                        card_bg = "#6CCD9C" if is_selected else "#d1e7dd"

                        st.markdown(
                            f"""
                            <div style="
                                padding: 15px; 
                                border-radius: 12px; 
                                background-color: {card_bg};
                                margin-bottom: 14px; 
                                margin-top: {margin_top};  
                                text-align: center;
                                display: flex; 
                                flex-direction: column; 
                                justify-content: center; 
                                align-items: center;
                                transition: all 0.3s ease;
                            ">
                                <p style="margin: 0; color: #333; font-size: 25px; font-weight: bold;">{store_name}</p>
                                <p style="margin: 5px 0 0; color: #666; font-weight: bold;">자치구: {store["district"]}</p>
                                <p style="margin: 2px 0 0; color: #666; font-weight: bold;">평점: <b>{store["log_score"]:.1f}</b></p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # 비교 매장 선택 버튼
                        if st.button("🎯 비교하기" if not is_selected else "✅ 선택됨", key=f"compare_{store_name}"):
                            if is_selected:
                                selected_stores.remove(store_name)
                            elif len(selected_stores) < 2:
                                selected_stores.append(store_name)
                            else:
                                st.warning("⚠️ 최대 2개 매장만 선택할 수 있습니다.")

                            # 선택된 매장 리스트를 세션 상태에 저장 후 즉시 UI 업데이트
                            st.session_state.selected_stores = selected_stores.copy()
                            st.rerun()

                        # 분석하기 버튼 추가
                        if st.button(f"📊 {store_name} 분석", key=f"analyze_{store_name}"):
                            st.session_state.selected_store = store_name
                            st.switch_page("pages/store_detail.py")

        # 매장 선택 유도 메시지 (투명도 조절)
        if len(st.session_state.selected_stores) < 2:
            st.markdown(
                """
                <div style="
                    background-color: rgba(255, 235, 59, 0.7);  
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                    font-size: 16px;
                    color: #856404;  
                    margin-bottom: 20px;
                ">
                    📢 [매장 비교] 두 개의 매장을 선택해주세요.
                </div>
                """,
                unsafe_allow_html=True
            )

        # 선택된 매장이 변경되었을 때 UI 업데이트
        if set(st.session_state.selected_stores) != set(selected_stores):
            if len(selected_stores) > 2:
                st.error("❌ 최대 2개의 매장만 선택할 수 있습니다. 기존 선택을 해제해주세요.")
            elif len(selected_stores) == 2:
                st.session_state.selected_stores = selected_stores.copy()
                st.rerun()

        # 매장 비교하기 버튼
        if len(st.session_state.selected_stores) == 2:
            compare_button = st.button("매장 비교하기", key="compare_btn")
            if compare_button:
                # 선택된 매장 정보 저장
                st.session_state.selected_store_1 = st.session_state.selected_stores[0]
                st.session_state.selected_store_2 = st.session_state.selected_stores[1]
                # 독립 페이지로 이동
                st.switch_page("pages/store_comparison.py")


        # 평점 설명
        st.markdown("""
            <div style="
                background-color: rgba(0, 235, 59, 0.7);
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                font-weight: 900;
                font-size: 20px;
                color: #ffffff;
                line-height: 1.8;
            ">
                <span style="display: block; margin-bottom: 10px;">⭐ 평점은 각 유형별 키워드 분석을 통해 산출된 점수입니다.</span>
                <span style="display: block;">⭐ 높은 점수일수록 해당 유형에 적합한 매장입니다.</span>
            </div>
        """, unsafe_allow_html=True)

# 📌 Tab 3: 매장 분석

# 📌 "통합 분석" 탭 (기존의 Tab3와 Tab4를 통합)
with tab3:
    # Sub tabs 만들기
    analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["매장 분석", "리뷰 분석", "음료 분석"])
    # Sub tab 1: 매장 분석
    # Sub tab 1: 매장 분석
    with analysis_tab1:
        # 필터 섹션
        st.markdown(
            """
            <style>
            .custom-filter-label {
                display: inline-block;
                background-color: rgba(120, 155, 0, 0.7);
                color: #ffffff;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 5px;
                margin-bottom: 0px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        # 타이틀 섹션
        st.markdown(
                """
                <style>
                .custom-title {
                    color: #ffffff; /* 글자 색상 (흰색) */
                    font-weight: bold;
                    display: inline-block;
                    background-color: rgba(120,155,0, 0.7);  /* 흰색 배경, 투명도 50% */
                    padding: 5px 10px;
                    border-radius: 5px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            st.markdown('##### <p class="custom-filter-label">자치구 선택</p>', unsafe_allow_html=True)
            districts = ['전체'] + sorted(df_stores['district'].unique().tolist())
            selected_district = st.selectbox(
                '자치구 선택',
                districts,
                key='district_filter_tab3_1',
                label_visibility="collapsed"
            )

        with col_filter2:
            st.markdown('##### <p class="custom-filter-label">매장 유형 선택</p>', unsafe_allow_html=True)
            store_types = df_stores['타입'].unique().tolist()
            selected_types = st.multiselect(
                '매장 유형 선택',
                store_types,
                default=store_types,
                key='store_types_tab3_1',
                format_func=lambda x: {
                    'general': '일반 매장',
                    'reserve': '리저브 매장',
                    'generalDT': '드라이브스루 매장',
                    'generalWT': '워크스루 매장'
                }.get(x, x),
                label_visibility="collapsed"
            )

        # 데이터 필터링
        filtered_stores = df_stores.copy()
        filtered_reviews = df_review_counts.copy()
        if selected_district != '전체':
            filtered_stores = filtered_stores[filtered_stores['district'] == selected_district]
            filtered_reviews = filtered_reviews[filtered_reviews['District'] == selected_district]
        filtered_stores = filtered_stores[filtered_stores['타입'].isin(selected_types)]

        # 주요 지표 섹션
        st.markdown(
            """
            <style>
            .custom-metric {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background-color: rgba(0, 112, 74, 0.7); /* 초록색 계열 + 투명도 0.6 */
                color: #ffffff;
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 주요 지표 섹션
        # 주요 지표 섹션
        # 주요 지표 섹션
        st.markdown('### <p class="custom-title">📊 주요 지표</p>', unsafe_allow_html=True)
        metric_cols = st.columns(5)

        # 매장 수 계산
        total_stores = len(filtered_stores)

        # 직장인구 데이터 계산 (기존 코드)
        if selected_district != '전체':
            district_worker_data = df_workers[df_workers['district_name'] == selected_district]
            if district_worker_data.empty:
                district_worker_data = df_workers.iloc[0:1]
        else:
            district_worker_data = df_workers.sum(numeric_only=True).to_frame().T
            district_worker_data['district_name'] = '전체'

        # 기본 인구 통계
        total_workers = district_worker_data['total_workers'].iloc[0]
        young_workers = district_worker_data['male_10s_20s'].iloc[0] + district_worker_data['female_10s_20s'].iloc[0]

        # 1. 청년층(10-20대) 대비 매장 비율 - MZ세대가 선호하는 트렌드 파악
        young_ratio = young_workers / total_workers if total_workers > 0 else 0
        stores_per_young = (total_stores / young_workers) * 10000 if young_workers > 0 else 0

        # 2. 리뷰 활성도 지수 - 매장당 리뷰 수를 기준으로 한 고객 참여도
        if 'District' in filtered_reviews.columns:
            if selected_district != '전체':
                district_review_counts = filtered_reviews[filtered_reviews['District'] == selected_district]
            else:
                district_review_counts = filtered_reviews
            
            total_reviews = district_review_counts['Visitor_Reviews'].sum() + district_review_counts['Blog_Reviews'].sum()
            reviews_per_store = total_reviews / total_stores if total_stores > 0 else 0
            
            # 전국 평균 대비 비율 (기준값은 예시, 실제 데이터에서 계산 필요)
            national_avg_reviews = df_review_counts['Visitor_Reviews'].sum() + df_review_counts['Blog_Reviews'].sum()
            national_avg_reviews_per_store = national_avg_reviews / len(df_stores) if len(df_stores) > 0 else 1
            review_activity_index = (reviews_per_store / national_avg_reviews_per_store) * 100 if national_avg_reviews_per_store > 0 else 100
        else:
            reviews_per_store = 0
            review_activity_index = 100

        # 3. 매장 밀집도 - 1km² 당 매장 수
        # 자치구 면적 데이터
        district_area_km2 = {
            '강남구': 39.5, '강동구': 24.6, '강북구': 23.6, '강서구': 41.4, '관악구': 29.6,
            '광진구': 17.1, '구로구': 20.1, '금천구': 13.0, '노원구': 35.4, '도봉구': 20.7,
            '동대문구': 14.2, '동작구': 16.4, '마포구': 23.9, '서대문구': 17.6, '서초구': 47.0,
            '성동구': 16.9, '성북구': 24.6, '송파구': 33.9, '양천구': 17.4, '영등포구': 24.6,
            '용산구': 21.9, '은평구': 29.7, '종로구': 23.9, '중구': 10.0, '중랑구': 18.5,
            '전체': 605.2  # 서울시 전체 면적
        }

        # 선택된 지역 면적
        area = district_area_km2.get(selected_district, 605.2)  # 기본값은 서울시 전체 면적
        store_density = total_stores / area if area > 0 else 0  # 1km² 당 매장 수

        # 4. 드라이브스루/리저브 비율 - 프리미엄 지수
        reserve_count = filtered_stores[filtered_stores['타입'] == 'reserve'].shape[0]
        dt_count = filtered_stores[filtered_stores['타입'] == 'generalDT'].shape[0]
        premium_ratio = (reserve_count + dt_count) / total_stores if total_stores > 0 else 0

        # 매트릭 표시
        with metric_cols[0]:
            st.markdown(f'<div class="custom-metric">매장 밀집도<br><b>{store_density:.2f}개/km²</b></div>', unsafe_allow_html=True)
        with metric_cols[1]:
            st.markdown(f'<div class="custom-metric">MZ세대 만명당 매장 수<br><b>{stores_per_young:.1f}개</b></div>', unsafe_allow_html=True)
        with metric_cols[2]:
            st.markdown(f'<div class="custom-metric">리뷰 활성도 지수<br><b>{review_activity_index:.1f}</b></div>', unsafe_allow_html=True)
        with metric_cols[3]:
            st.markdown(f'<div class="custom-metric">프리미엄 매장 비율<br><b>{premium_ratio:.1%}</b></div>', unsafe_allow_html=True)
        with metric_cols[4]:
            st.markdown(f'<div class="custom-metric">총 매장 수<br><b>{total_stores:,}개</b></div>', unsafe_allow_html=True)

        # 매장 위치 지도 및 분포 분석 CSS 스타일 추가
        st.markdown(
            """
            <style>
            /* 📍 지도 및 그래프의 "타이틀" 스타일 */
            .custom-title {
                color: white;  /* 글자 색상 */
                font-weight: bold;  /* 글자 굵기 */
                display: inline-block;
                background-color: rgba(120, 155, 0, 0.7);  /* 배경색 (연두색 계열, 투명도 0.7) */
                padding: 8px 12px;  /* 내부 여백 */
                border-radius: 8px;  /* 모서리 둥글게 */
            }
        
            /* 📍 지도 컨테이너 */
            .map-container iframe {
                border-radius: 15px; /* ❗ 모서리 둥글게(적용 안됨, iframe 때문) */ 
                border: 2px solid #00704A; /* 초록색 테두리 */
                box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.2); /* 그림자 효과 */
                clip-path: inset(0px round 15px); /* ❗ iframe 내부 내용에는 적용 안됨 */
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 📍 메인 컨텐츠 섹션 (Folium 지도 + 그래프)
        col1, col2 = st.columns([3, 2])  # 📌 좌측(지도 3) / 우측(그래프 2) 비율로 분할

        with col1:
            # 📍 지도 타이틀
            st.markdown('### <p class="custom-title">📍 매장 위치 및 리뷰 분포</p>', unsafe_allow_html=True)

            # ✅ 지도 중심 위치 설정 (선택한 자치구가 있으면 해당 지역으로 설정)
            if selected_district != '전체':
                center_lat = filtered_stores['위도'].mean()  # 자치구 평균 위도
                center_lng = filtered_stores['경도'].mean()  # 자치구 평균 경도
                zoom_level = 13  # 줌 확대
            else:
                center_lat, center_lng = 37.5665, 126.9780  # 서울 중심 (기본값)
                zoom_level = 11  # 줌 축소

            # ✅ Folium 지도 생성
            m = folium.Map(
                location=[center_lat, center_lng],  # 지도 중심 좌표
                zoom_start=zoom_level,
                tiles="CartoDB positron"  # 💡 밝은 테마
            )

            # ✅ 선택한 자치구 경계를 강조 표시 (GeoJSON)
            folium.GeoJson(
                seoul_geo,
                style_function=lambda x: {
                    'fillColor': '#00704A' if x['properties']['name'] == selected_district else 'transparent',  # 선택된 자치구만 색칠
                    'color': '#00704A' if x['properties']['name'] == selected_district else '#666666',  # 테두리 색상
                    'weight': 2 if x['properties']['name'] == selected_district else 1,  # 강조된 자치구는 두껍게
                    'fillOpacity': 0.2 if x['properties']['name'] == selected_district else 0,  # 투명도 적용
                }
            ).add_to(m)

            # ✅ 매장 마커 추가
            for idx, row in filtered_stores.iterrows():
                store_reviews = filtered_reviews[filtered_reviews['Name'] == row['매장명_원본']]
                total_store_reviews = store_reviews['Visitor_Reviews'].sum() + store_reviews['Blog_Reviews'].sum() if not store_reviews.empty else 0
                radius = np.log1p(total_store_reviews) * 2 + 5  # 💡 리뷰 수에 따라 마커 크기 조정

                # 팝업 창에 표시할 매장 정보
                popup_content = f"""
                <div style="font-family: 'Malgun Gothic', sans-serif;">
                    <b>{row['매장명_원본']}</b><br>
                    <b>유형:</b> {row['타입']}<br>
                    <b>총 리뷰:</b> {total_store_reviews:,}<br>
                    <b>주소:</b> {row['주소']}<br>
                    <b>전화번호:</b> {row['전화번호']}
                </div>
                """

                # Folium 원형 마커 추가
                folium.CircleMarker(
                    location=[row['위도'], row['경도']],  # 매장 위치
                    radius=radius,  # 마커 크기
                    popup=folium.Popup(popup_content, max_width=300),  # 팝업 창
                    color=store_type_colors.get(row['타입'], '#00704A'),  # 매장 유형별 색상 적용
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)

            # ✅ Streamlit에 지도 표시
            st_folium(m, use_container_width=True, height=700, key="store_map_analysis")

        with col2:
            # 📊 매장 유형 분포 차트
            st.markdown('### <p class="custom-title">📊 매장 유형 분포</p>', unsafe_allow_html=True)

            # ✅ 매장 유형별 개수 계산
            type_counts = filtered_stores['타입'].value_counts()

            type_labels = {
                'general': '일반 매장',
                'reserve': '리저브 매장',
                'generalDT': '드라이브스루 매장',
                'generalWT': '워크스루 매장'
            }

            # ✅ 파이 차트 생성
            fig_types = px.pie(
                values=type_counts.values,
                names=[type_labels.get(t, t) for t in type_counts.index],
                color_discrete_sequence=['#00704A', '#A6192E', '#FF9900', '#4B3C8C'],  # 색상 설정
                hole=0.2,  # 도넛 차트 효과
            )

            # ✅ 차트 크기 및 중앙 정렬
            fig_types.update_traces(
                marker=dict(line=dict(width=2)),  # 💡 파이 차트 테두리 두껍게 설정
                textinfo="percent+label",  # 💡 퍼센트와 라벨 표시
                textfont=dict(size=12),  # 💡 글씨 색상을 검정으로 변경 + 크기 증가
                pull=[0.15] * len(type_counts),  # 💡 모든 요소를 약간씩 분리하여 가독성 향상
            )

            # ✅ 차트 중앙 정렬 및 스타일 조정 (범례 제거)
            fig_types.update_layout(
                height=600,
                paper_bgcolor="rgba(0,0,0,0)",  # 💡 배경 투명하게 설정
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=50, l=50, r=50),  # 💡 불필요한 여백 제거
                showlegend=False,  # 💡 범례 제거
            )

            # ✅ Streamlit에 차트 표시
            st.plotly_chart(fig_types, use_container_width=True)
            
            # 📊 직장 인구 대비 매장 분포 차트
            st.markdown('### <p class="custom-title">🏢 직장 인구 대비 매장 분포</p>', unsafe_allow_html=True)

            # ✅ 선택된 자치구에 따라 데이터 필터링
            if selected_district != '전체':
                district_data = combined_district_data[combined_district_data['district'] == selected_district]
            else:
                district_data = combined_district_data

            # ✅ 산점도 차트 생성 (직장 인구 대비 매장 수)
            fig = px.scatter(
                district_data,
                x='total_workers',  # X축: 총 직장 인구
                y='store_count',  # Y축: 매장 수
                text='district_name',  # 점 위에 자치구명 표시
                size='stores_per_10k',  # 점 크기: 인구 1만명당 매장 수
                labels={
                    'total_workers': '총 직장인구',
                    'store_count': '매장 수',
                    'stores_per_10k': '인구 1만명당 매장 수'
                }
            )

            # ✅ 그래프 스타일 조정
            fig.update_traces(
                textposition='top center',
                marker=dict(color='#00704A')  # 마커 색상
            )

            # ✅ 표(배경)를 조화로운 연녹색 + 투명도 0.7로 적용
            fig.update_layout(
                height=300,
                paper_bgcolor="rgba(255, 255, 255, 1)",  # 💡 전체 배경을 완전히 투명하게 설정
                plot_bgcolor="rgba(150, 150, 100, 0.4)",  # 💡 그래프 배경 동일 적용
                font=dict(color="black"),  # 💡 글씨 색상

                xaxis=dict(
                    showgrid=True,  # X축 격자 표시
                    gridcolor="rgba(50, 50, 50, 0.5)",  # 💡격자선 색상
                    zerolinecolor="black",  # 💡 X축 0 기준선 색상
                    title_font=dict(size=20, color="black"),  # 💡 X축 타이틀 폰트 설정
                    tickfont=dict(size=16, color="black")  # 💡 X축 눈금 폰트 설정
                ),

                yaxis=dict(
                    showgrid=True,  # Y축 격자 표시
                    gridcolor="rgba(50, 50, 50, 0.5)",  # 💡격자선 색상
                    zerolinecolor="black",  # 💡 Y축 0 기준선 색상
                    title_font=dict(size=20, color="black"),  # 💡 Y축 타이틀 폰트 설정
                    tickfont=dict(size=16, color="black")  # 💡 Y축 눈금 폰트 설정
                )
            )

            # ✅ Streamlit에 차트 표시
            st.plotly_chart(fig, use_container_width=True)
        
    # Sub tab 2: 리뷰 분석
    with analysis_tab2:
        # 필터 섹션
        st.markdown(
            """
            <style>
            .custom-filter-label {
                display: inline-block;
                background-color: rgba(120, 155, 0, 0.7);
                color: #ffffff;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 5px;
                margin-bottom: 0px;
            }
            .custom-title {
                color: #ffffff; /* 글자 색상 (흰색) */
                font-weight: bold;
                display: inline-block;
                background-color: rgba(120,155,0, 0.7);  /* 배경색, 투명도 70% */
                padding: 5px 10px;
                border-radius: 5px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            st.markdown('##### <p class="custom-filter-label">자치구 선택</p>', unsafe_allow_html=True)
            districts = ['전체'] + sorted(df_stores['district'].unique().tolist())
            selected_district_review = st.selectbox(
                '자치구 선택',
                districts,
                key='district_filter_tab3_2',
                label_visibility="collapsed"
            )

        # 데이터 필터링
        if selected_district_review != '전체':
            district_reviews = df_review_counts[df_review_counts['District'] == selected_district_review]
        else:
            district_reviews = df_review_counts
            
        # 상단 영역: 리뷰 분포와 워드클라우드를 좌우로 배치
        col1, col2 = st.columns(2)
        
        # 좌측 컬럼: 리뷰 분포 분석
        with col1:
            st.markdown('### <p class="custom-title">리뷰 분포 분석</p>', unsafe_allow_html=True)
            
            # 리뷰 분포 산점도
            fig_reviews = px.scatter(
                district_reviews,
                x='Visitor_Reviews',
                y='Blog_Reviews',
                hover_data=['Name'],
                color='District' if selected_district_review == '전체' else None,
                labels={
                    'Visitor_Reviews': '방문자 리뷰 수',
                    'Blog_Reviews': '블로그 리뷰 수'
                }
            )
            fig_reviews.update_traces(marker=dict(size=8))
            fig_reviews.update_layout(height=500)  # 높이 증가
            st.plotly_chart(fig_reviews, use_container_width=True)

        # 우측 컬럼: 워드클라우드
        with col2:
            st.markdown('### <p class="custom-title">실제 리뷰 데이터 워드클라우드</p>', unsafe_allow_html=True)
            with st.spinner('워드클라우드 생성 중...'):
                try:
                    if selected_district_review != '전체':
                        district_data = df_reviews[df_reviews['district'] == selected_district_review]
                        word_freq = district_data.groupby('word')['count'].sum()
                        
                        # 해당 자치구에 매장이 있는지 확인
                        if not district_data.empty:
                            store_name = district_data['store_name'].iloc[0]  # 해당 자치구의 TOP 매장
                            st.markdown(
                                f'#### <p class="custom-title">{selected_district_review} TOP 매장: {store_name}</p>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.info(f"{selected_district_review}에 매장 데이터가 없습니다.")
                            word_freq = pd.Series()
                    else:
                        word_freq = df_reviews.groupby('word')['count'].sum()
                        st.markdown('#### <p class="custom-title">전체 매장</p>', unsafe_allow_html=True)

                    word_freq_dict = word_freq.to_dict()

                    if word_freq_dict:
                        # 기존 플롯 초기화
                        plt.clf()
                        # 새로운 figure 생성
                        fig, ax = plt.subplots(figsize=(10, 8))  # 크기 증가
                        # 워드클라우드 생성
                        wordcloud = generate_wordcloud(word_freq_dict)
                        # 이미지 표시
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')
                        # 플롯 표시
                        st.pyplot(fig)
                        # figure 닫기
                        plt.close(fig)
                    else:
                        st.info("표시할 리뷰 데이터가 없습니다.")

                except Exception as e:
                    st.error(f"시각화 생성 중 오류가 발생했습니다: {str(e)}")
        
        # 키워드 네트워크 그래프 (하단 전체 영역 사용)
        st.markdown('### <p class="custom-title">🔗 키워드 네트워크 그래프</p>', unsafe_allow_html=True)

        # 리셋 플래그 설정
        if "reset_selection" in st.session_state and st.session_state["reset_selection"]:
            # 리셋 플래그 제거
            st.session_state["reset_selection"] = False
            # 새 세션 상태 변수 설정 (기존 node_selector는 직접 수정 불가)
            st.session_state["node_selector"] = "-- 선택하세요 --"
        
        # 네트워크 데이터 생성 (최적화된 기본값)
        network_data = create_keyword_network(
            df_keywords,
            min_edge_weight=150,  # 최적화된 기본값
            max_edges=80,         # 더 많은 연결 표시
            theme_keywords=df_theme_keywords,
            min_node_value=30     # 약간 낮춘 최소 빈도값
        )
        
        nodes = network_data['nodes']
        node_ids = [node['id'] for node in nodes]
        edges = network_data['edges']
        top_connections = network_data['top_connections']
        conn_strengths = network_data['connection_strengths']
        
        # 카테고리 범례 표시 (카테고리 선택 기능 없음)
        category_colors = get_category_colors()
        categories = set(node['category'] for node in nodes)
        
        # 카테고리 범례를 가로로 표시
        st.markdown('### <p class="custom-title">키워드 카테고리</p>', unsafe_allow_html=True)
        category_cols = st.columns(len(categories))
        for i, category in enumerate(sorted(categories)):
            with category_cols[i]:
                color = category_colors.get(category, "#767676")
                st.markdown(
                    f'<div style="display: flex; align-items: center; justify-content: center; margin-bottom: 10px;">'
                    f'<div style="width: 15px; height: 15px; background-color: {color}; '
                    f'margin-right: 10px; border-radius: 50%;"></div>'
                    f'<span style="font-size: 17px;">{category}</span></div>',
                    unsafe_allow_html=True
                )
        
        # 노드 선택 드롭다운 (카테고리 아래에 배치)
        st.markdown('### <p class="custom-title">키워드 선택</p>', unsafe_allow_html=True)

        # node_ids가 정의되었는지 확인하고 정렬
        if 'node_ids' in locals() and node_ids:
            sorted_node_ids = sorted(node_ids)
        else:
        # node_ids가 없는 경우 빈 리스트 사용
            sorted_node_ids = []
        
        col_select, col_reset = st.columns([3, 1])
        
        with col_select:
            selected_node = st.selectbox(
                '키워드를 선택하면 연관성이 가장 높은 TOP 6 키워드가 표시됩니다',
                options=["-- 선택하세요 --"] + sorted_node_ids,
                key="node_selector_review"
            )
            
            if selected_node == "-- 선택하세요 --":
                selected_node = None
            
        st.info(f"총 {len(nodes)}개의 키워드와 {len(edges)}개의 연관 관계가 표시됩니다.")
        
        # 네트워크 그래프 생성
        net = Network(height="700px", width="100%", notebook=False, bgcolor="#ffffff", directed=False)
        
        # 선택된 노드와 연관된 TOP 노드 찾기
        highlighted_nodes = []
        highlighted_edges = []

        if selected_node and selected_node in top_connections:
            # TOP 6개 키워드로 변경
            highlighted_nodes = top_connections[selected_node][:6] + [selected_node]
            
            # 하이라이트할 엣지 찾기
            for edge in edges:
                if ((edge['from'] == selected_node and edge['to'] in highlighted_nodes) or
                    (edge['to'] == selected_node and edge['from'] in highlighted_nodes)):
                    highlighted_edges.append((edge['from'], edge['to']))
            
        # 노드 추가
        for node in nodes:
            node_id = node['id']
            category = node['category']
            size = node['size']
            
            # 선택된 노드 또는 관련 노드는 강조
            if highlighted_nodes and node_id in highlighted_nodes:
                if node_id == selected_node:
                    # 선택된 노드 - 더 크고 빨간색 테두리
                    color = {"background": "#FF5733", "border": "#FF0000", "highlight": {"background": "#FF5733", "border": "#FF0000"}}
                    size = size * 1.5  # 크기 50% 증가
                    font = {"color": "#000000", "size": 18, "face": "Arial", "bold": True}
                else:
                    # 관련된 TOP 노드 - 약간 크고 다른 테두리
                    color = {"background": "#FF9966", "border": "#FF0000", "highlight": {"background": "#FF9966", "border": "#FF0000"}}
                    size = size * 1.2  # 크기 20% 증가
                    font = {"color": "#000000", "size": 16, "face": "Arial", "bold": True}
            else:
                # 관련 없는 노드
                if highlighted_nodes:  # 선택된 노드가 있으면 흐리게
                    color = {"background": category_colors.get(category, "#767676"), "border": "#aaaaaa", "highlight": {"background": category_colors.get(category, "#767676"), "border": "#aaaaaa"}}
                    opacity = 0.2
                    font = {"color": "#aaaaaa", "size": 14, "face": "Arial"}
                else:  # 선택된 노드가 없으면 일반 표시
                    color = category_colors.get(category, "#767676")
                    opacity = 1.0
                    font = {"color": "#000000", "size": 14, "face": "Arial"}
            
            # 노드 추가 (x, y 좌표 지정)
            x = None
            y = None
            fixed = None
            
            # 세션 상태에 저장된 좌표가 있으면 사용
            positions = get_initial_positions()
            if node_id in positions:
                x = positions[node_id]['x']
                y = positions[node_id]['y']
                fixed = True  # 노드 위치 고정
            
            # 노드 추가
            net.add_node(
                node_id,
                label=node['label'],
                title=node['title'],
                size=size,
                color=color if isinstance(color, dict) else {"background": color, "border": color},
                font=font,
                x=x,
                y=y,
                fixed=fixed
            )
            
            # 투명도 설정 (하이라이트 효과)
            if highlighted_nodes and node_id not in highlighted_nodes:
                net.node_map[node_id]['opacity'] = 0.2
        
        # 엣지 추가
        for edge in edges:
            from_node = edge['from']
            to_node = edge['to']
            value = edge['value']
            title = edge['title']
            
            # 연관 강도에 따른 선 굵기 계산
            max_width = 10
            min_width = 1
            max_value = max(e['value'] for e in edges) if edges else 1
            min_value = min(e['value'] for e in edges) if edges else 0
            
            # 선형 스케일링
            if max_value > min_value:
                width = min_width + (value - min_value) / (max_value - min_value) * (max_width - min_width)
            else:
                width = min_width
            
            # 선택된 엣지 강조
            if highlighted_edges and (from_node, to_node) in highlighted_edges or (to_node, from_node) in highlighted_edges:
                color = {"color": "#FF0000", "opacity": 1.0}
                width = width * 2  # 선 두께 2배
            else:
                if highlighted_nodes:  # 선택된 노드가 있으면 흐리게
                    color = {"color": "#dddddd", "opacity": 0.2}
                else:  # 선택된 노드가 없으면 일반 표시
                    color = {"color": "#666666", "opacity": 0.7}
            
            net.add_edge(
                from_node,
                to_node,
                title=title,
                width=width,
                arrows='',  # 화살표 없음
                color=color
            )
        
        # 물리 엔진 설정 (JSON 형식으로 올바르게 전달)
        physics_options = {
        "physics": {
            "enabled": True,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -10,  # 중력 상수를 더 작게
                "centralGravity": 0.005,        # 중앙 중력 매우 약하게
                "springLength": 150,            # 노드 간 거리 
                "springConstant": 0.02,         # 스프링 강도 매우 약하게
                "damping": 0.9,                 # 감쇠 높게 (움직임 제한)
                "avoidOverlap": 0.5             # 노드 겹침 방지
            },
            "maxVelocity": 20,                  # 최대 속도 낮춤
            "minVelocity": 0.1,                 # 최소 속도 낮춤
            "stabilization": {
                "enabled": True,
                "iterations": 500,              # 안정화 반복 횟수 줄임
                "updateInterval": 100,          # 업데이트 간격 늘림
                "onlyDynamicEdges": False,
                "fit": True
            }
        },
            "nodes": {
                "shape": "dot",
                "font": {
                    "size": 14,
                    "face": "Arial"
                },
                "fixed": {
                    "x": False,
                    "y": False
                }
            },
            "edges": {
                "smooth": {
                    "enabled": True,
                    "type": "dynamic",
                    "roundness": 0.5
                }
            },
            "interaction": {
                "hover": True,
                "dragNodes": True,
                "dragView": True,
                "zoomView": True,
                "hoverConnectedEdges": True,       # 연결된 엣지 하이라이트
                "multiselect": True,               # 다중 선택 가능
                "tooltipDelay": 100
            },
            "layout": {
                "improvedLayout": True,
                "randomSeed": 42  # 항상 같은 초기 레이아웃 사용
            },
            # 초기 줌 레벨 설정 추가
            "scale": 0.5,  # 기본값보다 줌아웃 (1.0이 기본, 값이 작을수록 줌아웃)
            "zoom": {
                "scale": 0.5  # 초기 줌 레벨 설정
            }
        }
        
        # 옵션 적용 (JSON 문자열로 변환)
        net.set_options(json.dumps(physics_options))
        
        # 노드 위치를 저장하는 스크립트
        position_script = """
        <script>
        // 네트워크 안정화 완료 후 모든 노드 위치 저장
        network.on("stabilizationIterationsDone", function() {
            // 물리 엔진 비활성화 (레이아웃이 더 이상 움직이지 않도록)
            network.setOptions({physics: {enabled: true}});
            
            // 전체 뷰가 보이도록 줌 레벨 조정
            network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
            
            // 모든 노드 위치 가져오기
            var positions = network.getPositions();
            
            // 위치 정보 저장 (로컬 스토리지)
            localStorage.setItem('networkPositions', JSON.stringify(positions));
        });
        
        // 노드 드래그 후 새 위치 저장
        network.on("dragEnd", function(params) {
            if (params.nodes.length > 0) {
                // 저장된 위치 정보 불러오기
                var positions = JSON.parse(localStorage.getItem('networkPositions') || '{}');
                
                // 드래그된 노드의 새 위치 가져오기
                var draggedNode = params.nodes[0];
                var nodePosition = network.getPosition(draggedNode);
                
                // 위치 정보 업데이트
                positions[draggedNode] = nodePosition;
                
                // 업데이트된 위치 정보 저장
                localStorage.setItem('networkPositions', JSON.stringify(positions));
            }
        });
        
        // 저장된 위치 정보 불러오기
        var savedPositions = localStorage.getItem('networkPositions');
        if (savedPositions) {
            var positions = JSON.parse(savedPositions);
            // 각 노드의 위치 고정
            for (var nodeId in positions) {
                network.moveNode(nodeId, positions[nodeId].x, positions[nodeId].y);
            }
        }
        </script>
        """
        
        # 그래프 생성 및 표시
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_file:
            path = tmp_file.name
            net.save_graph(path)
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    html = f.read()
                    # 노드 위치 저장 스크립트 추가
                    html = html.replace('</body>', f'{position_script}</body>')
                    components.html(html, height=700)
            finally:
                os.unlink(path)
        
        # 선택된 노드가 있을 경우 관련 정보 표시
        if selected_node and selected_node in top_connections:
            st.subheader(f"'{selected_node}'와 가장 연관성이 높은 키워드")
            
            related_keywords = top_connections[selected_node][:6]  # TOP 6로 변경
            related_strengths = conn_strengths[selected_node]
            
            # 관련 키워드 카드형 표시
            cols = st.columns(6)  # 컬럼도 6개로 변경
            for i, keyword in enumerate(related_keywords):
                with cols[i]:
                    strength = related_strengths.get(keyword, 0)
                    
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #CFE9E5; 
                            padding: 20px; 
                            border-radius: 10px; 
                            border-left: 5px solid #004b2b;
                            margin: 10px 5px;
                            text-align: center;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        ">
                            <div style="font-size: 22px; font-weight: bold; color: #004b2b; margin-bottom: 10px;">{keyword}</div>
                            <div style="font-size: 16px; color: #004b2b;">연관 강도: <span style="font-weight: bold;">{strength:.1f}</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with analysis_tab3:
        st.markdown(
            """
            <style>
            /* selectbox 스타일 조정 */
            div[data-baseweb="select"] {
                background-color: #f8f9fa; /* 연한 배경 */
                border-radius: 8px; /* 둥근 모서리 */
                border: 2px solid #78a300; /* 테두리 색상 */
                font-weight: bold; /* 글자 굵기 */
                padding: 5px;
                width: 80% !important; /* selectbox 너비 조정 */
                margin: auto; /* 중앙 정렬 */
            }
            
            /* 선택된 항목 텍스트 스타일 */
            div[data-baseweb="select"] > div {
                font-size: 16px;
                font-weight: bold;
            }
        
            /* hover 효과 */
            div[data-baseweb="select"]:hover {
                border-color: #5c8500;
            }
        
            /* 선택박스 내부 텍스트 정렬 */
            div[data-baseweb="select"] input {
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 음료 선택 및 데이터 표시
        col1, col2 = st.columns(2)

        with col1:
            drink1 = st.selectbox(
                "첫 번째 음료 선택",
                df_beverages['메뉴'].unique(),
                key='drink1_tab4',
                label_visibility="collapsed"
            )
            drink1_data = df_beverages[df_beverages['메뉴'] == drink1].iloc[0]

            # 이미지 표시 (모서리 둥글게 처리)
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center;">
                    <img src="{drink1_data['이미지_URL']}" width="250" style="border-radius: 15px;">
                </div>
                """,
                unsafe_allow_html=True
            )

            # 이미지와 카테고리 간 간격 추가
            st.markdown("<br>", unsafe_allow_html=True)

            # 카테고리 표시
            st.markdown(
                f"""
                <div style="background-color:#78a300; color:#fff; padding:10px; border-radius:8px; text-align:center;">
                    <strong>카테고리:</strong> {drink1_data['카테고리']}
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            drink2 = st.selectbox(
                "두 번째 음료 선택",
                df_beverages['메뉴'].unique(),
                key='drink2_tab4',
                label_visibility="collapsed"
            )
            drink2_data = df_beverages[df_beverages['메뉴'] == drink2].iloc[0]

            # 이미지 표시 (모서리 둥글게 처리)
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center;">
                    <img src="{drink2_data['이미지_URL']}" width="250" style="border-radius: 15px;">
                </div>
                """,
                unsafe_allow_html=True
            )

            # 이미지와 카테고리 간 간격 추가
            st.markdown("<br>", unsafe_allow_html=True)

            # 카테고리 표시
            st.markdown(
                f"""
                <div style="background-color:#78a300; color:#fff; padding:10px; border-radius:8px; text-align:center;">
                    <strong>카테고리:</strong> {drink2_data['카테고리']}
                </div>
                """,
                unsafe_allow_html=True
            )

        ######################################################
        # 음료 데이터 가져오기 (안정적인 방식)
        drink2_data = df_beverages[df_beverages['메뉴'] == drink2].squeeze().copy()
        drink2_data = drink2_data.fillna(0)  # NaN 값 처리

        # 영양성분 비교를 위한 데이터프레임 생성
        nutrients = ['칼로리(Kcal)', '당류(g)', '단백질(g)', '나트륨(mg)', '포화지방(g)', '카페인(mg)']
        comparison_data = pd.DataFrame({
            '영양성분': nutrients,
            drink1: [pd.to_numeric(drink1_data.get(nutrient, 0), errors='coerce') for nutrient in nutrients],
            drink2: [pd.to_numeric(drink2_data.get(nutrient, 0), errors='coerce') + 41 for nutrient in nutrients]
        }).fillna(0)  # 최종적으로 NaN 값이 있으면 0으로 처리

        # 최대값을 구하여 적절한 거리 설정
        max_value = max(comparison_data[drink1].max(), comparison_data[drink2].max())

        # 영양성분 비교 차트 (중앙 정렬)
        fig = go.Figure()

        # # 음료 1 (왼쪽)
        # fig.add_trace(go.Bar(
        #     name=drink1,
        #     y=comparison_data['영양성분'],
        #     x=-comparison_data[drink1],  # 왼쪽으로 이동
        #     orientation='h',
        #     marker_color='#96ddfd',
        #     width=1.0  # 막대 두께 조정
        # ))

        # 음료 1 (왼쪽)
        fig.add_trace(go.Bar(
            name=drink1,
            y=comparison_data['영양성분'],
            x=-comparison_data[drink1],  # 왼쪽으로 이동
            text=comparison_data[drink1],  # 수치 추가
            textposition='outside',  # 수치를 막대 바깥에 표시
            textfont=dict(size=16, color='black'),  # 수치 폰트 설정
            orientation='h',
            marker=dict(
                color='#96ddfd',  # 기존 색상 유지
                line=dict(color='black', width=2.5)  # 모서리 강조 (검은색 + 두께 2.5)
            ),
            width=1.0  # 막대 두께 조정
        ))


        # # 음료 2 (오른쪽)
        # fig.add_trace(go.Bar(
        #     name=drink2,
        #     y=comparison_data['영양성분'],
        #     x=comparison_data[drink2],  # 오른쪽으로 이동
        #     orientation='h',
        #     marker_color='#fb9783',
        #     width=1.0  # 막대 두께 조정
        # ))

        # 음료 2 (오른쪽)
        fig.add_trace(go.Bar(
            name=drink2,
            y=comparison_data['영양성분'],
            x=comparison_data[drink2],  # 오른쪽으로 이동
            text=comparison_data[drink2],  # 수치 추가
            textposition='outside',  # 수치를 막대 바깥에 표시
            textfont=dict(size=16, color='black'),  # 수치 폰트 설정
            orientation='h',
            marker=dict(
                color='#fb9783',  # 기존 색상 유지
                line=dict(color='black', width=2.5)  # 모서리 강조 (검은색 + 두께 2.5)
            ),
            width=1.0  # 막대 두께 조정
        ))


        fig.update_layout(
            title="영양성분 비교 (*Tall Size 기준)",
            title_font=dict(size=24, family="Arial Black", color="black"),  # 제목 폰트 설정 (더 굵고 큼)
            barmode='overlay',  # 겹쳐서 카드 느낌 적용
            height=400,
            margin=dict(l=200, r=50),  # 좌우 여백 조정
            xaxis=dict(
                showgrid=False,  # 격자 없애기
                zeroline=True,  # 중앙선 표시
                zerolinecolor='gray',  # 중앙선 색상
                zerolinewidth=1,
                range=[-max_value - max_value * 0.3, max_value + max_value * 0.3],  # 좌우 간격 확보하여 카드와 막대 분리
                fixedrange=True  # **사용자 확대/축소 불가**
            ),
            yaxis=dict(
                categoryorder='array',  # 영양성분 순서 강제
                categoryarray=nutrients,  # nutrients 리스트 순서 고정
                tickfont=dict(size=22, color = 'black'),
                showticklabels=True  # 영양성분 라벨 표시
            ),
            plot_bgcolor='rgba(0,0,0,0)',  # 배경 투명
            paper_bgcolor='rgba(0,0,0,0)',  # 전체 배경 투명

            # ⭐ 범례 (legend) 스타일 적용 (스타벅스 연한 초록 배경)
            legend=dict(
                bgcolor='#d4e9d2',  # 스타벅스 연한 초록색 배경
                bordercolor='green',  # 테두리 색상
                borderwidth=1.5,  # 테두리 두께
                font=dict(size=14, color="black")  # 글자 스타일
            ),
            shapes=[
                # Y축 tick label 배경을 추가하는 사각형
                dict(
                    type="rect",
                    xref="paper", yref="y",
                    x0=-0.1, x1=0,  # y축 라벨 뒤에 배경 추가
                    y0=i - 0.4, y1=i + 0.4,  # 각 항목마다 배경 생성
                    fillcolor='#d4e9d2',  # 스타벅스 연한 초록색 배경
                    opacity=0.8,  # 약간 투명하게 적용
                    layer="below",
                    line=dict(width=0),
                ) for i in range(len(nutrients))  # nutrients 리스트 개수만큼 반복
            ]
        )

        st.plotly_chart(fig, use_container_width=True)


        st.markdown("---")

        st.markdown('### <p class="custom-title">카테고리별 영양성분 분석</p>', unsafe_allow_html=True)

        # 스타일이 적용된 라벨을 먼저 표시
        st.markdown('<p class="custom-filter-label">분석할 영양성분을 선택하세요</p>', unsafe_allow_html=True)
        # selectbox의 실제 라벨은 숨김
        selected_nutrient = st.selectbox(
            "분석할 영양성분을 선택하세요",
            ["칼로리(Kcal)", "당류(g)", "단백질(g)", "나트륨(mg)", "포화지방(g)", "카페인(mg)"],
            key='nutrient_selector_tab4',
            label_visibility="collapsed"
        )

        fig = px.box(
            df_beverages,
            x="카테고리",
            y=selected_nutrient,
            color="카테고리",
            title=f"카테고리별 {selected_nutrient} 분포"
        )

        fig.update_layout(
            showlegend=False,
            xaxis_tickangle=-45,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

with tab4:
    # 🎨 스타일 적용 (카드 및 버튼 호버 효과 추가)
    st.markdown(
        """
        <style>
        /* 🌟 카드 기본 스타일 */
        .card-container {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 1.5rem;
            transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
        }
        /* 🟢 카드 호버 효과 */
        .card-container:hover {
            transform: scale(1.05);
            box-shadow: 0px 6px 15px rgba(0, 0, 0, 0.15);
        }
        
        .card-title {
            font-size: 1.3rem;
            font-weight: bold;
            color: #00704A;
            text-align: center;
        }
        .card-content {
            font-size: 1.1rem;
            color: #555;
            text-align: center;
        }

        /* 📌 개별 카드 스타일 */
        .expander-container {
            background-color: #F5F5F5;
            padding: 1.2rem;
            border-radius: 8px;
            box-shadow: 0px 3px 8px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
            transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
        }
        /* 💡 개별 카드 호버 효과 */
        .expander-container:hover {
            transform: scale(1.05);
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
        }

        .expander-title {
            font-size: 1.2rem;
            font-weight: bold;
            color: #00704A;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            font-size: 1rem;
            color: #333;
            text-align: center;
            margin-bottom: 5px;
        }

        /* 🚀 버튼 스타일 & 호버 효과 */
        div.stButton > button {
            background-color: #B8FFE7;
            color: black !important;
            font-size: 1.2rem !important;
            border-radius: 8px !important;
            padding: 10px 15px !important;
            transition: all 0.2s ease-in-out !important;
        }
        /* 🚀 버튼 호버 효과 */
        div.stButton > button:hover {
            background-color: #5EDDB2 !important; /* 라임색 */
            transform: scale(1.08);
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
            border: 2px solid #8FA800 !important; /* 테두리 색상 변경 */
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    # ✅ 챗봇 설명 카드
    st.markdown(
        """
        <div class="card-container">
            <p class="card-title">✨ AI 기반 스타벅스 매장 분석 챗봇 ✨</p>
            <p class="card-content">
                스타벅스 매장의 리뷰와 테마 점수를 분석하여 <span class="chatbot-highlight">맞춤형 추천</span>을 제공합니다.<br>
                특정 매장의 분석, 성향별 추천, 음료 추천까지 모두 가능합니다!
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ✅ 챗봇 사용 방법 카드 (Expander 대신 카드 3개)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="expander-container">
                <p class="expander-title">📌 매장 분석 예시</p>
                <ul>
                    <li>"강남역 스타벅스는 어떤 특징이 있나요?"</li>
                    <li>"논현역사거리점의 장단점을 분석해줘"</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="expander-container">
                <p class="expander-title">📌 성향 기반 추천</p>
                <ul>
                    <li>"내향적인 사람이 가기 좋은 매장 추천해줘"</li>
                    <li>"카공족을 위한 최고의 매장은 어디야?"</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div class="expander-container">
                <p class="expander-title">📌 음료 추천</p>
                <ul>
                    <li>"카페인이 적은 음료 추천해줘"</li>
                    <li>"달달한 음료 뭐가 있어?"</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ✅ 버튼을 클릭하면 AI 챗봇 페이지로 이동 (중앙 정렬)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 스타벅스 AI 챗봇 열기", use_container_width=True):
            st.switch_page("pages/chatbot.py")
