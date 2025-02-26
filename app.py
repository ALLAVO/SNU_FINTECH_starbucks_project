import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import folium
from streamlit_folium import st_folium
from modules.score_utils import load_all_scores, get_scores_from_all_csv  # 모듈 불러오기
import base64
import requests
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
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

#지도, 매장, 음료 정보를 불러오기 위한 데이터 미리 호출
df_stores = load_store_data()
seoul_geo = load_seoul_geojson()
df_beverages = load_beverage_data()
df_review_counts = load_review_counts()
df_workers = load_worker_data()
df_reviews = load_review_data()

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
        background-color: rgba(255, 255, 255, 0.7) !important; /* 배경색 (흰색, 투명도 70%) */
        backdrop-filter: blur(6px); /* 블러 효과 */
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["매장 목록", "서울 스타벅스 개인 특성 별 매장 추천", "매장 분석", "음료 분석", "ChatBot"])

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
                background-color: rgba(120,155,0, 0.7);  /* 빨간색 배경, 투명도 20% */
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

            # TOP 10 매장은 특별 마커로 표시
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

    # 추천 매장 목록 표시
    with col2:
        # 페이지가 새로 로드되면 선택된 매장 리스트 초기화
        if "selected_stores" not in st.session_state or "selected_store" in st.session_state:
            st.session_state.selected_stores = []

        # {selected_theme} 추천 매장 TOP 9 출력
        st.markdown(
            f'##### <p class="custom-label">{selected_theme} 추천 매장 TOP 9</p>',
            unsafe_allow_html=True
        )

        total_scores = get_store_theme_scores(selected_theme, selected_district)

        if not total_scores.empty:
            top9 = total_scores.head(9)

            # 선택된 매장 리스트 초기화
            if "selected_stores" not in st.session_state:
                st.session_state.selected_stores = []

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
                        button_text = "🎯 비교 매장 선택 해제" if is_selected else "비교 매장으로 선택"

                        st.markdown(
                            f"""
                            <div style="
                                padding: 15px; 
                                border-radius: 12px; 
                                background-color: {card_bg};
                                margin-bottom: 14px; 
                                margin-top: {margin_top};  /* 두 번째 행부터 간격 추가 */
                                text-align: center;
                                display: flex; 
                                flex-direction: column; 
                                justify-content: center; 
                                align-items: center;
                                transition: all 0.3s ease;  /* 부드러운 전환 효과 */
                            ">
                                <p style="margin: 0; color: #333; font-size: 25px; font-weight: bold;">{store_name}</p>
                                <p style="margin: 5px 0 0; color: #666; font-weight: bold;">자치구: {store["district"]}</p>
                                <p style="margin: 2px 0 0; color: #666; font-weight: bold;">평점: <b>{store["log_score"]:.1f}</b></p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )


                        # 비교 매장 선택 버튼 (카드 위에 배치)
                        if st.button("🎯 비교하기" if not is_selected else "✅ 선택됨", key=f"compare_{store_name}"):
                            if is_selected:
                                selected_stores.remove(store_name)
                            elif len(selected_stores) < 2:
                                selected_stores.append(store_name)
                            else:
                                st.warning("최대 2개 매장만 선택할 수 있습니다.")

                            # 선택된 매장 리스트를 세션 상태에 저장
                            st.session_state.selected_stores = selected_stores

                            # UI 즉시 업데이트
                            st.rerun()

                        # 분석하기 버튼 추가
                        if st.button(f"📊 {store_name} 분석", key=f"analyze_{store_name}"):
                            st.session_state.selected_store = store_name
                            st.switch_page("pages/store_detail.py")


        # # 초기 메시지: 두 개의 매장을 선택하도록 유도
        # if len(selected_stores) < 2:
        #     st.warning("⚠️ 두 개의 매장을 선택해주세요.")
        # 초기 메시지: 두 개의 매장을 선택하도록 유도 (투명도 조절)
        if len(selected_stores) < 2:
            st.markdown(
                """
                <div style="
                    background-color: rgba(255, 235, 59, 0.7);  /* 연한 노란색 배경 */
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                    font-size: 16px;
                    color: #856404;  /* 경고색 */
                    margin-bottom: 20px;  /* 🔹 아래쪽 여백 추가 */
                ">
                    📢 [매장 비교] 두 개의 매장을 선택해주세요.
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write("")  # 🔹 빈 줄 추가 (자동 간격 확보)

        # 새로운 선택이 기존 선택과 다를 경우만 업데이트
        if set(selected_stores) != set(st.session_state.selected_stores):
            if len(selected_stores) > 2:
                st.error("❌ 최대 2개의 매장만 선택할 수 있습니다. 기존 선택을 해제해주세요.")
            elif len(selected_stores) == 2:
                st.session_state.selected_stores = selected_stores
                st.rerun()  # 두 개가 선택된 경우 UI를 즉시 업데이트

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
                background-color: rgba(0, 235, 59, 0.7);  /* 연한 초록색 배경 */
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                font-weight: 900;  /* 글씨 더 두껍게 */
                font-size: 20px;  /* 글씨 크기 증가 */
                color: #ffffff;  /* 흰색 텍스트 */
                line-height: 1.8;  /* 줄 간격 조정 */
            ">
                <span style="display: block; margin-bottom: 10px;">⭐ 평점은 각 유형별 키워드 분석을 통해 산출된 점수입니다.</span>
                <span style="display: block;">⭐ 높은 점수일수록 해당 유형에 적합한 매장입니다.</span>
            </div>
        """, unsafe_allow_html=True)


# 📌 Tab 3: 매장 분석
with tab3:
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
            key='district_filter_tab3',
            label_visibility="collapsed"
        )

    with col_filter2:
        st.markdown('##### <p class="custom-filter-label">매장 유형 선택</p>', unsafe_allow_html=True)
        store_types = df_stores['타입'].unique().tolist()
        selected_types = st.multiselect(
            '매장 유형 선택',
            store_types,
            default=store_types,
            key='store_types_tab3',
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

    st.markdown('### <p class="custom-title">📊 주요 지표</p>', unsafe_allow_html=True)
    metric_cols = st.columns(5)

    # 지표 계산
    total_stores = len(filtered_stores)
    total_reviews = filtered_reviews['Visitor_Reviews'].sum() + filtered_reviews['Blog_Reviews'].sum()
    avg_reviews = total_reviews / len(filtered_reviews) if len(filtered_reviews) > 0 else 0
    visitor_ratio = filtered_reviews['Visitor_Reviews'].sum() / total_reviews if total_reviews > 0 else 0
    blog_ratio = filtered_reviews['Blog_Reviews'].sum() / total_reviews if total_reviews > 0 else 0

    with metric_cols[0]:
        st.markdown(f'<div class="custom-metric">매장 수<br><b>{total_stores:,}</b></div>', unsafe_allow_html=True)
    with metric_cols[1]:
        st.markdown(f'<div class="custom-metric">총 리뷰 수<br><b>{total_reviews:,}</b></div>', unsafe_allow_html=True)
    with metric_cols[2]:
        st.markdown(f'<div class="custom-metric">매장당 평균 리뷰<br><b>{avg_reviews:.1f}</b></div>', unsafe_allow_html=True)
    with metric_cols[3]:
        st.markdown(f'<div class="custom-metric">방문자 리뷰 비율<br><b>{visitor_ratio:.1%}</b></div>', unsafe_allow_html=True)
    with metric_cols[4]:
        st.markdown(f'<div class="custom-metric">블로그 리뷰 비율<br><b>{blog_ratio:.1%}</b></div>', unsafe_allow_html=True)


    # 📌 매장 위치 지도 및 분포 분석 CSS 스타일 추가
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
        st_folium(m, use_container_width=True, height=700, key="store_map")

    # with col2:
    #     # 📊 매장 유형 분포 차트
    #     st.markdown('### <p class="custom-title">📊 매장 유형 분포</p>', unsafe_allow_html=True)
    #
    #     # ✅ 매장 유형별 개수 계산
    #     type_counts = filtered_stores['타입'].value_counts()
    #
    #     type_labels = {
    #         'general': '일반 매장',
    #         'reserve': '리저브 매장',
    #         'generalDT': '드라이브스루 매장',
    #         'generalWT': '워크스루 매장'
    #     }
    #
    #     # ✅ 파이 차트 생성
    #     fig_types = px.pie(
    #         values=type_counts.values,
    #         names=[type_labels.get(t, t) for t in type_counts.index],
    #         color_discrete_sequence=['#00704A', '#A6192E', '#FF9900', '#4B3C8C'],  # 색상 설정
    #         hole=0.3,  # 도넛 차트 효과
    #     )
    #
    #     # ✅ 차트 크기 조정 및 배경 투명화
    #     fig_types.update_layout(
    #         height=600,
    #         paper_bgcolor="rgba(0,0,0,0)",  # 💡 배경 투명하게 설정
    #         plot_bgcolor="rgba(0,0,0,0)",
    #         legend=dict(
    #             font=dict(size=30, color="white"),  # 💡 Legend(범례) 폰트 크기 증가 + 흰색
    #             bgcolor="rgba(120, 155, 100, 0.7)",  # 💡 연두색 계열 + 투명도 0.7
    #             bordercolor="white",  # 💡 테두리 색상 (선택 사항)
    #             borderwidth=2  # 💡 테두리 두께 (선택 사항)
    #         )
    #     )
    #
    #     # ✅ Streamlit에 차트 표시
    #     st.plotly_chart(fig_types, use_container_width=True)

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


    # 하단 분석 섹션
    st.markdown("---")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown('### <p class="custom-title">리뷰 분포 분석</p>', unsafe_allow_html=True)
        if selected_district != '전체':
            district_data = df_review_counts[df_review_counts['District'] == selected_district]
        else:
            district_data = df_review_counts

        # 리뷰 분포 산점도
        fig = px.scatter(
            district_data,
            x='Visitor_Reviews',
            y='Blog_Reviews',
            hover_data=['Name'],
            color='District' if selected_district == '전체' else None,
            labels={
                'Visitor_Reviews': '방문자 리뷰 수',
                'Blog_Reviews': '블로그 리뷰 수'
            }
        )
        fig.update_traces(marker=dict(size=8))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        with st.spinner('워드클라우드 생성 중...'):
            try:
                if selected_district != '전체':
                    district_data = df_reviews[df_reviews['district'] == selected_district]
                    word_freq = district_data.groupby('word')['count'].sum()
                    store_name = district_data['store_name'].iloc[0]  # 해당 자치구의 TOP 매장

                    st.markdown(
                        f'#### <p class="custom-title">{selected_district} TOP 매장: {store_name} 리뷰 키워드</p>',
                        unsafe_allow_html=True
                    )
                else:
                    word_freq = df_reviews.groupby('word')['count'].sum()
                    st.markdown('### <p class="custom-title">전체 매장 워드클라우드</p>', unsafe_allow_html=True)

                word_freq_dict = word_freq.to_dict()

                if word_freq_dict:
                    # 기존 플롯 초기화
                    plt.clf()
                    # 새로운 figure 생성
                    fig, ax = plt.subplots(figsize=(10, 5))
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

# 📌 Tab 4: 음료 분석
with tab4:
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
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('### <p class="custom-title">음료 비교하기</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # 스타일이 적용된 라벨을 먼저 표시
        st.markdown('<p class="custom-filter-label">첫 번째 음료 선택</p>', unsafe_allow_html=True)
        # selectbox의 실제 라벨은 숨김
        drink1 = st.selectbox(
            "첫 번째 음료 선택",  # 접근성을 위해 라벨은 유지
            df_beverages['메뉴'].unique(),
            key='drink1_tab4',
            label_visibility="collapsed"  # 라벨 숨김
        )
        drink1_data = df_beverages[df_beverages['메뉴'] == drink1].iloc[0]
        st.image(drink1_data['이미지_URL'], width=200)
        st.write(f"**카테고리:** {drink1_data['카테고리']}")

    with col2:
        # 스타일이 적용된 라벨을 먼저 표시
        st.markdown('<p class="custom-filter-label">두 번째 음료 선택</p>', unsafe_allow_html=True)
        # selectbox의 실제 라벨은 숨김
        drink2 = st.selectbox(
            "두 번째 음료 선택",  # 접근성을 위해 라벨은 유지
            df_beverages['메뉴'].unique(),
            key='drink2_tab4',
            label_visibility="collapsed"  # 라벨 숨김
        )
        drink2_data = df_beverages[df_beverages['메뉴'] == drink2].iloc[0]
        st.image(drink2_data['이미지_URL'], width=200)
        st.write(f"**카테고리:** {drink2_data['카테고리']}")

    nutrients = ['칼로리(Kcal)', '당류(g)', '단백질(g)', '나트륨(mg)', '포화지방(g)', '카페인(mg)']
    comparison_data = pd.DataFrame({
        '영양성분': nutrients,
        drink1: [drink1_data[nutrient] for nutrient in nutrients],
        drink2: [drink2_data[nutrient] for nutrient in nutrients]
    })

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=drink2,
        y=comparison_data['영양성분'],
        x=comparison_data[drink2],
        orientation='h',
        marker_color='#FF9900'
    ))

    fig.add_trace(go.Bar(
        name=drink1,
        y=comparison_data['영양성분'],
        x=comparison_data[drink1],
        orientation='h',
        marker_color='#00704A'
    ))

    fig.update_layout(
        title="영양성분 비교 (*Tall Size 기준)",
        barmode='group',
        height=400,
        margin=dict(l=200),
        yaxis={'categoryorder':'total ascending'}
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

with tab5:
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
            st.switch_page("pages/starbucks_chatbot.py")
    # with st.expander("💡 챗봇 사용 방법 예시 보기"):
    #     st.markdown(
    #         """
    #         <div class="expander-container">
    #             <p class="expander-title">📌 매장 분석 예시</p>
    #             <ul>
    #                 <li>"강남역 스타벅스는 어떤 특징이 있나요?"</li>
    #                 <li>"논현역사거리점의 장단점을 분석해줘"</li>
    #             </ul>
    #         </div>
    #
    #         <div class="expander-container">
    #             <p class="expander-title">📌 성향 기반 추천</p>
    #             <ul>
    #                 <li>"내향적인 사람이 가기 좋은 매장 추천해줘"</li>
    #                 <li>"카공족을 위한 최고의 매장은 어디야?"</li>
    #             </ul>
    #         </div>
    #
    #         <div class="expander-container">
    #             <p class="expander-title">📌 음료 추천</p>
    #             <ul>
    #                 <li>"카페인이 적은 음료 추천해줘"</li>
    #                 <li>"달달한 음료 뭐가 있어?"</li>
    #             </ul>
    #         </div>
    #         """,
    #         unsafe_allow_html=True
    #     )