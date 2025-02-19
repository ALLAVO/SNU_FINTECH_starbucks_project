import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
import requests
from modules.score_utils import load_all_scores, get_scores_from_all_csv
from store_data import chart_info

# 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 폰트 깨짐 방지

# 페이지 설정
st.set_page_config(
    page_title="스타벅스 매장 비교",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터 로드 함수들
@st.cache_data
def load_store_data():
    df = pd.read_csv('data/starbucks_seoul_all_store_info.csv')
    df['district'] = df['주소'].str.extract(r'서울특별시\s+(\S+구)')
    df['매장명'] = df['매장명'].str.strip()
    return df

@st.cache_data
def load_theme_scores():
    merged_df, b_values = load_all_scores()
    return merged_df, b_values

# 매장명 정규화 함수
def normalize_store_name(name):
    return name.strip().replace('점', '').strip()

def main():
    st.title("🏪 스타벅스 매장 비교하기")
    
    # 세션에서 선택된 매장 정보 가져오기
    selected_store_1 = st.session_state.get('selected_store_1', '')
    selected_store_2 = st.session_state.get('selected_store_2', '')
    
    # 데이터 로드
    df_stores = load_store_data()
    store_list = [""] + list(df_stores['매장명'].unique())
    
    # 선택된 매장이 있는지 확인
    has_selected_stores = selected_store_1 != '' and selected_store_2 != ''
    
    # 인덱스 찾기
    default_store1_index = store_list.index(selected_store_1) if selected_store_1 in store_list else 0
    
    # 매장 선택 UI
    col1, col2 = st.columns(2)
    with col1:
        selected_store_1 = st.selectbox(
            "첫 번째 매장 선택", 
            store_list,
            index=default_store1_index
        )
    
    with col2:
        # 첫 번째 매장과 다른 매장만 표시
        available_stores = [""] + [s for s in store_list[1:] if s != selected_store_1]
        
        # 두 번째 매장의 인덱스 찾기
        if selected_store_2 in available_stores:
            default_store2_index = available_stores.index(selected_store_2)
        else:
            default_store2_index = 0
            
        selected_store_2 = st.selectbox(
            "두 번째 매장 선택", 
            available_stores,
            index=default_store2_index
        )
    
    # 두 개의 매장이 선택된 경우 비교 차트 생성
    if selected_store_1 and selected_store_2:
        st.subheader(f"📊 {selected_store_1} vs {selected_store_2}")
        
        # 매장명 정규화
        store1_normalized = normalize_store_name(selected_store_1)
        store2_normalized = normalize_store_name(selected_store_2)
        
        # 2x2 차트 레이아웃 생성
        cols = st.columns(2)

        # 각 유형별 차트 생성
        for i, (title, labels) in enumerate(chart_info):
            with cols[i % 2]:
                st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

                file_name_keyword = title
                
                try:
                    # 정규화된 매장명으로 점수 가져오기 - 실패 시 원본 이름으로 시도
                    try:
                        all_scores_1 = get_scores_from_all_csv(store1_normalized, labels, file_name_keyword)
                    except Exception:
                        st.warning(f"정규화된 이름으로 '{store1_normalized}' 매장을 찾을 수 없어 원본 이름으로 시도합니다.")
                        all_scores_1 = get_scores_from_all_csv(selected_store_1, labels, file_name_keyword)
                        
                    try:
                        all_scores_2 = get_scores_from_all_csv(store2_normalized, labels, file_name_keyword)
                    except Exception:
                        st.warning(f"정규화된 이름으로 '{store2_normalized}' 매장을 찾을 수 없어 원본 이름으로 시도합니다.")
                        all_scores_2 = get_scores_from_all_csv(selected_store_2, labels, file_name_keyword)
                    
                    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)

                    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})

                    scores_1 = np.append(all_scores_1, all_scores_1[0])
                    ax.plot(angles, scores_1, 'o-', linewidth=2, label=selected_store_1, color="#00704A")
                    ax.fill(angles, scores_1, alpha=0.3, color="#00704A")

                    scores_2 = np.append(all_scores_2, all_scores_2[0])
                    ax.plot(angles, scores_2, 'o-', linewidth=2, label=selected_store_2, color="#D92121")
                    ax.fill(angles, scores_2, alpha=0.3, color="#D92121")

                    ax.set_xticks(angles[:-1])
                    ax.set_xticklabels(labels)
                    ax.legend(loc="upper right")

                    st.pyplot(fig)
                    plt.close()
                    
                except Exception as e:
                    st.error(f"차트 생성 중 오류가 발생했습니다: {str(e)}")
                    
                    # 예외 발생 시, 간단한 메시지와 빈 차트 표시
                    fig, ax = plt.subplots(figsize=(5, 5))
                    ax.text(0.5, 0.5, f"데이터를 불러올 수 없습니다\n({title})", 
                            ha='center', va='center', fontsize=12)
                    ax.axis('off')
                    st.pyplot(fig)
                    plt.close()
    else:
        if has_selected_stores:
            st.info(f"선택된 매장: {selected_store_1}, {selected_store_2}")
        
        st.warning("📢️ 두 개의 매장을 선택해주세요!")
    
    # 매장 분석 페이지로 돌아가기 버튼
    if st.button("← 매장 분석으로 돌아가기"):
        # 세션 상태 초기화
        if 'selected_store_1' in st.session_state:
            del st.session_state['selected_store_1']
        if 'selected_store_2' in st.session_state:
            del st.session_state['selected_store_2']
        if 'selected_stores' in st.session_state:
            st.session_state['selected_stores'] = []
        
        # 메인 페이지로 이동
        st.switch_page("app.py")

if __name__ == "__main__":
    main()