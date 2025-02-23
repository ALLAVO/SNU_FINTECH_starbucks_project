import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import folium
from streamlit_folium import st_folium
from modules.score_utils import load_all_scores, get_scores_from_all_csv  # 모듈 불러오기
import base64
import requests

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
)
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

#지도 정보를 불러오기 위한 데이터 미리 호출
df_stores = load_store_data()
seoul_geo = load_seoul_geojson()

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

    /* ✅ 8. 버튼 커스터마이징 */
    div.stButton > button {
        background-color: #006241;   /* 배경색 (스타벅스 그린) */
        color: #ffffff;              /* 글씨색 (흰색) */
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
tab1, tab2 = st.tabs(["매장 목록", "서울 스타벅스 개인 특성 별 매장 추천"])

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
# =========================================
# "매장 목록 보기" 탭
# =========================================
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


# "개인 특성별 매장 추천" 탭 - 새로운 내용으로 대체
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
            tiles="OpenStreetMap"
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

        # TOP 10 매장 목록 획득
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

        # # 지도 표시
        # st_folium(m, width=800, height=600)
        # Folium 지도 출력 (Streamlit에서 여백 없이 표시)
        st_folium(m, use_container_width=True, height=700)


    # 추천 매장 목록 표시
    with col2:
        # {selected_theme} 추천 매장 TOP 10 출력 (배경색 적용)
        st.markdown(
            f'##### <p class="custom-label">{selected_theme} 추천 매장 TOP 10</p>',
            unsafe_allow_html=True
        )

        total_scores = get_store_theme_scores(selected_theme, selected_district)

        if not total_scores.empty:
            top10 = total_scores.head(10)

            # 선택된 매장 리스트 초기화
            if 'selected_stores' not in st.session_state:
                st.session_state.selected_stores = []

            # 데이터프레임 생성 (체크박스 포함)
            df = pd.DataFrame({
                '두 매장 비교': [store in st.session_state.selected_stores for store in top10['Store']],
                '매장명': top10['Store'],
                '자치구': top10['district'],
                '평점': top10['log_score'].round(1)
            }).reset_index(drop=True)

            # Streamlit의 data_editor로 표 렌더링 (체크박스 포함)
            edited_df = st.data_editor(
                df,
                column_config={
                    "두 매장 비교": st.column_config.CheckboxColumn("두 매장 비교"),
                    "매장명": st.column_config.TextColumn("매장명", width="medium"),
                    "자치구": st.column_config.TextColumn("자치구", width="small"),
                    "평점": st.column_config.NumberColumn("평점", width="small", format="%.1f"),
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )

        # 선택된 매장 업데이트 (최대 2개까지만 허용)
        selected_stores = edited_df[edited_df["두 매장 비교"]]["매장명"].tolist()

        # 현재 상태를 유지한 채 업데이트 반영
        if "selected_stores" not in st.session_state:
            st.session_state.selected_stores = []

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