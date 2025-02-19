import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from store_data import chart_info
from modules.score_utils import get_scores_from_all_csv  # 모듈 불러오기
import base64

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

# 탭 레이아웃
tab1, tab2 = st.tabs(["매장 목록", "매장 별 비교"])

st.markdown(
    """
    <style>
    /* 🟢 탭 컨테이너 스타일 */
    div.stTabs {
        font-weight: bold;         /* 기본 글씨 두껍게 */
        font-size: 2vw;            /* 기본 글씨 크기 (뷰포트 너비 기준) */
        padding: 2vh 3vw;          /* 내부 여백 (뷰포트 기준) */
    }
    
    /* 🟡 활성 탭 스타일링 (선택된 탭) */
    div.stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #004b2b; /* 선택된 탭 배경색 (더 진한 스타벅스 그린) */
        color: #FFFFFF !important; /* 선택된 탭 글씨색 (흰색) */
        font-size: 2.5vw;          /* 선택된 탭 글씨 크기 (뷰포트 너비 기준) */
        font-family: 'Noto Sans KR', sans-serif; /* 원하는 폰트 적용 */
        font-weight: 900;           /* 글씨 매우 두껍게 */
        padding: 1.8vh 3vw;         /* 탭 크기 확대 (뷰포트 기준) */   
        transition: all 0.3s ease-in-out;
        border-radius: 1vw;         /* 모서리 둥글게 (뷰포트 기준) */
    }
    
    /* 🟠 비활성 탭 스타일링 */
    div.stTabs [data-baseweb="tab"] {
        background-color: #C3D7BA; 
        transition: background-color 0.3s ease, color 0.3s ease;
        padding: 1.2vh 2vw;          /* 탭 내부 여백 (뷰포트 기준) */
        font-weight: 600;          /* 기본 글씨 두께 */
        font-size: 2vw;            /* 기본 글씨 크기 (뷰포트 너비 기준) */
        color: #1E3932;            /* 글씨색 (짙은 스타벅스 그린) */
        font-family: 'Noto Sans KR', sans-serif; /* 원하는 폰트 적용 */
        border-radius: 1vw;        /* 모서리 둥글게 (뷰포트 기준) */
    }
    
    /* 🟢 탭 호버 시 스타일 */
    div.stTabs [data-baseweb="tab"]:hover {
        background-color: #C4D600; /* 라임색 */
        color: #FFFFFF; /* 흰색 글씨 */
        transform: scale(1.05); /* 약간 확대 효과 */
        transition: all 0.2s ease-in-out;
        border-radius: 1vw;        /* 모서리 둥글게 (뷰포트 기준) */
    }
    </style>
    """,
    unsafe_allow_html=True
)
# =========================================
# "매장 목록 보기" 탭
# =========================================
with tab1:
    st.markdown(
        """
        <style>
        /* 🟢 기본 검색창 스타일링 */
        div[data-baseweb="input"] {
            border-radius: 25px; /* 모서리를 둥글게 (구글 검색창 스타일) */
            border: 2px solid #006241; /* 테두리 색상 (스타벅스 그린) */
            padding: 5px; /* 내부 여백 (입력창 안의 여백) */
            font-size: 25px; /* 입력 글자 크기 */
            transition: box-shadow 0.3s ease; /* 호버 시 박스 그림자 부드럽게 전환 */
            box-shadow: 0 2px 5px rgba(0,0,0,0.15); /* 기본 그림자 (은은한 느낌) */
            width: 60%; /* 검색창 너비 (화면의 80% 차지) */
            height: 2.5em; /* 폰트 크기의 2.5배 */
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
    # 🔍 검색 기능
    # search_query = st.text_input("🔍 매장 검색", value="")
    # 📌 검색창 표시 (구글 스타일)
    search_query = st.text_input(
        "",         # 검색창 위에 문구 추가
        value="",
        placeholder="매장명을 검색해 보세요...",
    )


    # ----------------------------------
    # [변경] 매장 유형 선택 -> 네모칸 전체가 클릭 가능한 커스텀 체크박스 UI
    # ----------------------------------
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
            height: 10vh;              /* 네모칸 높이 (뷰포트 높이의 10%) */
            border: 3px solid #006241;  /* 테두리 (스타벅스 그린) */
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
        st.warning("🚫 해당 검색어에 맞는 매장이 없습니다.")
    else:
        st.markdown("#### 서울 지역 분석 결과 바로보기")
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
                    with st.expander(label=f"**{i+j+1}. {store_name}**", expanded=True):
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

# =========================================
# "매장 별 비교하기" 탭
# =========================================
with tab2:
    st.title("🏪 매장 비교하기")
    col1, col2 = st.columns(2)
    with col1:
        selected_store_1 = st.selectbox(
            "첫 번째 매장 선택",
            [""] + [store['name'] for store in st.session_state.stores],
            index=0
        )
    with col2:
        selected_store_2 = st.selectbox(
            "두 번째 매장 선택",
            [""] + [store['name'] for store in st.session_state.stores],
            index=0
        )
    if selected_store_1 and selected_store_2:
        st.subheader(f"📊 {selected_store_1} vs {selected_store_2}")
        cols = st.columns(2)
        for i, (title, labels) in enumerate(chart_info):
            with cols[i % 2]:
                st.markdown(f"<h3 style='text-align: center; color:#006241;'>{title}</h3>", unsafe_allow_html=True)
                file_name_keyword = title
                all_scores_1 = get_scores_from_all_csv(selected_store_1, labels, file_name_keyword)
                all_scores_2 = get_scores_from_all_csv(selected_store_2, labels, file_name_keyword)
                angles = np.linspace(0, 2 * np.pi, len(all_scores_1)+1)
                fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
                scores_1 = np.append(all_scores_1, all_scores_1[0])
                ax.plot(angles, scores_1, 'o-', linewidth=2, label=selected_store_1, color="#006241")
                ax.fill(angles, scores_1, alpha=0.3, color="#006241")
                scores_2 = np.append(all_scores_2, all_scores_2[0])
                ax.plot(angles, scores_2, 'o-', linewidth=2, label=selected_store_2, color="#C4D600")
                ax.fill(angles, scores_2, alpha=0.3, color="#C4D600")
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(labels)
                ax.legend(loc="upper right")
                st.pyplot(fig)
    else:
        st.warning("📢️ 두 개의 매장을 선택해주세요!")

# =========================================
# 푸터
# =========================================
st.markdown(
    """
    <div class="footer">
        &copy; 2025 SIREN VALUE. All rights reserved.
    </div>
    """,
    unsafe_allow_html=True
)