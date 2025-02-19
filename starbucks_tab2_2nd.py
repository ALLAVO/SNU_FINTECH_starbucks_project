import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
import plotly.express as px
import requests
from modules.score_utils import load_all_scores, get_scores_from_all_csv
import os
from store_data import chart_info

# 📌메인 페이지 설정
st.set_page_config(
    page_title="Seoul Starbucks Analysis",
    layout="wide",
    initial_sidebar_state="collapsed"  # 사이드 바 숨기기
)
 
# 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 폰트 깨짐 방지

# 📌각 필요 데이터 로드
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

# 매장명 정규화 함수 (점 제거)
def normalize_store_name(name):
    return name.strip().replace('점', '').strip()

# Load data
df_stores = load_store_data()
seoul_geo = load_seoul_geojson()

# Main content
st.title("서울 스타벅스 개인 특성 별 매장 추천")
st.markdown("<br>", unsafe_allow_html=True)

# 필터 컬럼 생성
filter_col1, filter_col2 = st.columns(2)
    
with filter_col1:
    districts = ['전체'] + sorted(df_stores['district'].unique().tolist())
    selected_district = st.selectbox(
        '자치구 선택',
        districts,
        key='district_filter'
    )

with filter_col2:
    selected_theme = st.selectbox(
        "매장 유형 선택",
        ["내향형", "수다형", "외향형", "카공형"],
        key='theme_filter'
    )

st.markdown("<br>", unsafe_allow_html=True)

# Main content columns
col1, col2 = st.columns([5, 5])

with col1:
    st.subheader("매장 위치 및 분포")
    
    if selected_district != '전체':
        district_data = df_stores[df_stores['district'] == selected_district]
        center_lat = district_data['위도'].mean()
        center_lng = district_data['경도'].mean()
        zoom_level = 13
    else:
        center_lat, center_lng = 37.5665, 126.9780
        zoom_level = 11

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom_level,
        tiles="OpenStreetMap"
    )

    style_function = lambda x: {
        'fillColor': '#00704A' if x['properties']['name'] == selected_district else 'transparent',
        'color': '#00704A' if x['properties']['name'] == selected_district else '#666666',
        'weight': 2 if x['properties']['name'] == selected_district else 1,
        'fillOpacity': 0.2 if x['properties']['name'] == selected_district else 0,
    }

    folium.GeoJson(
        seoul_geo,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['name'],
            aliases=['지역구:'],
            style=('background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;')
        )
    ).add_to(m)

    # Get top 10 stores
    top10_stores = []
    total_scores = get_store_theme_scores(selected_theme, selected_district)
    if not total_scores.empty:
        top10_stores = total_scores.head(10)['Store'].tolist()

    if selected_district != '전체':
        display_stores = df_stores[df_stores['district'] == selected_district]
    else:
        display_stores = df_stores

    # Add markers for stores
    for idx, row in display_stores.iterrows():
        is_top10 = row['매장명_원본'] in top10_stores
        
        popup_content = f"""
        <div style="font-family: 'Malgun Gothic', sans-serif;">
            <b>{row['매장명_원본']}</b><br>
            <b>주소:</b> {row['주소']}<br>
            <b>전화번호:</b> {row['전화번호']}
            {f'<br><b style="color: #036635;">✨ {selected_theme} TOP 10 매장</b>' if is_top10 else ''}
        </div>
        """
        
        if is_top10:
            folium.CircleMarker(
                location=[row['위도'], row['경도']],
                radius=8,
                popup=folium.Popup(popup_content, max_width=300),
                color='#D92121',
                fill=True,
                fill_opacity=0.9,
                weight=2
            ).add_to(m)
            
            folium.map.Marker(
                [row['위도'], row['경도']],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 11px; color: #D92121; font-weight: bold; text-shadow: 2px 2px 2px white;">{row["매장명_원본"]}</div>',
                    icon_size=(150,20),
                    icon_anchor=(75,0)
                )
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[row['위도'], row['경도']],
                radius=5,
                popup=folium.Popup(popup_content, max_width=300),
                color='#00704A',
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

    st_folium(m, width=800, height=600)

# col2의 dataframe과 체크박스 부분 수정
with col2:
    st.markdown(f"### {selected_theme} 추천 매장 TOP 10")
    if selected_district != '전체':
        st.markdown(f"*{selected_district} 지역*")
    
    total_scores = get_store_theme_scores(selected_theme, selected_district)
    
    if not total_scores.empty:
        top10 = total_scores.head(10)
        
        # 표와 체크박스를 위한 컬럼 생성
        table_col, checkbox_col = st.columns([3, 1])
        
        with table_col:
            # 기존 데이터프레임 표시
            styled_df = pd.DataFrame({
                '매장명': top10['Store'],
                '자치구': top10['district'],
                '평점': top10['log_score'].round(1)
            }).reset_index(drop=True)
            
            st.dataframe(
                styled_df,
                column_config={
                    "매장명": st.column_config.TextColumn(
                        "매장명",
                        width="medium",
                    ),
                    "자치구": st.column_config.TextColumn(
                        "자치구",
                        width="small",
                    ),
                    "평점": st.column_config.NumberColumn(
                        "평점",
                        width="small",
                        format="%.1f",
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
        
        with checkbox_col:
            st.write("매장 선택")
            
            # 선택된 매장 리스트 초기화
            if 'selected_stores' not in st.session_state:
                st.session_state.selected_stores = []
            
            # 각 매장에 대한 체크박스 생성
            for idx, row in top10.iterrows():
                store_name = row['Store']
                is_checked = store_name in st.session_state.selected_stores
                
                # 체크박스 UI 표시
                if st.checkbox(
                    '',
                    value=is_checked,
                    key=f"check_{store_name}_{idx}",
                    disabled=len(st.session_state.selected_stores) >= 2 and store_name not in st.session_state.selected_stores
                ):
                    if store_name not in st.session_state.selected_stores and len(st.session_state.selected_stores) < 2:
                        st.session_state.selected_stores.append(store_name)
                    # 이미 2개 선택된 상태에서 또 다른 항목 선택 시 가장 오래된 선택 해제
                    elif store_name not in st.session_state.selected_stores:
                        st.session_state.selected_stores.pop(0)
                        st.session_state.selected_stores.append(store_name)
                elif store_name in st.session_state.selected_stores:
                    st.session_state.selected_stores.remove(store_name)
            
            # 매장 비교하기 버튼 - 세션 상태 수정 후 독립 페이지로 이동
            if len(st.session_state.selected_stores) == 2:
                compare_button = st.button("매장 비교하기", key="compare_btn")
                if compare_button:
                    # 선택된 매장 정보 저장
                    st.session_state.selected_store_1 = st.session_state.selected_stores[0]
                    st.session_state.selected_store_2 = st.session_state.selected_stores[1]
                    # 독립 페이지로 이동
                    st.switch_page("pages/store_comparison.py")
            elif len(st.session_state.selected_stores) == 1:
                st.info("⚠️ 비교할 매장을 하나 더 선택해주세요.")

    else:
        st.info("해당 조건에 맞는 매장이 없습니다.")
        
    # Add a note about the scoring
    st.markdown("""
    ---
    * 평점은 각 유형별 키워드 분석을 통해 산출된 점수입니다.
    * 높은 점수일수록 해당 유형에 적합한 매장입니다.
    """)