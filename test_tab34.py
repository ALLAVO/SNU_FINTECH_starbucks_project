import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import requests
from PIL import Image
import io
import base64

# 페이지 설정 
st.set_page_config(
    page_title="Seoul Starbucks Analysis",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

# 매장 유형별 색상 정의
store_type_colors = {
    'general': '#00704A',     # Regular Starbucks green
    'reserve': '#A6192E',     # Reserve stores in dark red
    'generalDT': '#FF9900',   # Drive-thru in orange
    'generalWT': '#4B3C8C'    # Walk-thru in purple
}

# 데이터 로드 함수들
@st.cache_data
def load_store_data():
    df = pd.read_csv('data/starbucks_seoul_all_store_info.csv')
    df['district'] = df['주소'].str.extract(r'서울특별시\s+(\S+구)')
    df['매장명'] = df['매장명'].str.strip()
    df['매장명_원본'] = df['매장명']
    df['매장명'] = df['매장명'].str.replace('점', '').str.strip()
    return df

@st.cache_data
def load_review_data():
    df = pd.read_csv('data/cleaned_starbucks_reviews_with_counts.csv')
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
def load_beverage_data():
    df = pd.read_csv('data/starbucks_nutrition_with_images.csv')
    return df

@st.cache_data
def load_seoul_geojson():
    response = requests.get('https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json')
    return response.json()

@st.cache_data
def generate_wordcloud(text_data, width=800, height=400):
    wordcloud = WordCloud(
        font_path='NanumSquareRoundB.ttf',
        width=width,
        height=height, 
        background_color='white',
        colormap='Greens',
        max_words=100
    ).generate_from_frequencies(text_data)
    return wordcloud

# 모든 데이터 로드
df_stores = load_store_data()
df_reviews = load_review_data()
df_review_counts = load_review_counts()
df_workers = load_worker_data()
df_beverages = load_beverage_data()
seoul_geo = load_seoul_geojson()

# Calculate total workers and stores per district
df_workers['total_workers'] = (
    df_workers['male_10s_20s'] + df_workers['male_30s_40s'] + df_workers['male_50s_60s_above'] +
    df_workers['female_10s_20s'] + df_workers['female_30s_40s'] + df_workers['female_50s_60s_above']
)
stores_per_district = df_stores.groupby('district').size().reset_index(name='store_count')
combined_district_data = pd.merge(
    df_workers,
    stores_per_district,
    left_on='district_name',
    right_on='district',
    how='left'
)
combined_district_data['store_count'] = combined_district_data['store_count'].fillna(0)
combined_district_data['stores_per_10k'] = (combined_district_data['store_count'] / combined_district_data['total_workers']) * 10000

# 타이틀
st.title("서울 스타벅스 통합 분석 대시보드")

# 탭 생성
tab1, tab2 = st.tabs(["매장 분석", "음료 분석"])

with tab1:
    # 필터 섹션
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        districts = ['전체'] + sorted(df_stores['district'].unique().tolist())
        selected_district = st.selectbox('자치구 선택', districts)

    with col_filter2:
        store_types = df_stores['타입'].unique().tolist()
        selected_types = st.multiselect(
            '매장 유형 선택',
            store_types,
            default=store_types,
            format_func=lambda x: {
                'general': '일반 매장',
                'reserve': '리저브 매장',
                'generalDT': '드라이브스루 매장',
                'generalWT': '워크스루 매장'
            }.get(x, x)
        )

    # 데이터 필터링
    filtered_stores = df_stores.copy()
    filtered_reviews = df_review_counts.copy()
    if selected_district != '전체':
        filtered_stores = filtered_stores[filtered_stores['district'] == selected_district]
        filtered_reviews = filtered_reviews[filtered_reviews['District'] == selected_district]
    filtered_stores = filtered_stores[filtered_stores['타입'].isin(selected_types)]

    # 주요 지표 섹션
    st.subheader("📊 주요 지표")
    metric_cols = st.columns(5)

    # 지표 계산
    total_stores = len(filtered_stores)
    total_reviews = filtered_reviews['Visitor_Reviews'].sum() + filtered_reviews['Blog_Reviews'].sum()
    avg_reviews = total_reviews / len(filtered_reviews) if len(filtered_reviews) > 0 else 0
    visitor_ratio = filtered_reviews['Visitor_Reviews'].sum() / total_reviews if total_reviews > 0 else 0
    blog_ratio = filtered_reviews['Blog_Reviews'].sum() / total_reviews if total_reviews > 0 else 0

    with metric_cols[0]:
        st.metric("매장 수", f"{total_stores:,}")
    with metric_cols[1]:
        st.metric("총 리뷰 수", f"{total_reviews:,}")
    with metric_cols[2]:
        st.metric("매장당 평균 리뷰", f"{avg_reviews:.1f}")
    with metric_cols[3]:
        st.metric("방문자 리뷰 비율", f"{visitor_ratio:.1%}")
    with metric_cols[4]:
        st.metric("블로그 리뷰 비율", f"{blog_ratio:.1%}")

    # 메인 컨텐츠 섹션 
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("매장 위치 및 리뷰 분포")
        
        # 지도 중심점 설정
        if selected_district != '전체':
            center_lat = filtered_stores['위도'].mean()
            center_lng = filtered_stores['경도'].mean()
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

        # 지역구 경계 추가
        folium.GeoJson(
            seoul_geo,
            style_function=lambda x: {
                'fillColor': '#00704A' if x['properties']['name'] == selected_district else 'transparent',
                'color': '#00704A' if x['properties']['name'] == selected_district else '#666666',
                'weight': 2 if x['properties']['name'] == selected_district else 1,
                'fillOpacity': 0.2 if x['properties']['name'] == selected_district else 0,
            }
        ).add_to(m)

        # 매장 마커 추가
        for idx, row in filtered_stores.iterrows():
            store_reviews = filtered_reviews[filtered_reviews['Name'] == row['매장명_원본']]
            total_store_reviews = store_reviews['Visitor_Reviews'].sum() + store_reviews['Blog_Reviews'].sum() if not store_reviews.empty else 0
            
            radius = np.log1p(total_store_reviews) * 2 + 5  # 리뷰 수에 따른 마커 크기
            
            popup_content = f"""
            <div style="font-family: 'Malgun Gothic', sans-serif;">
                <b>{row['매장명_원본']}</b><br>
                <b>유형:</b> {row['타입']}<br>
                <b>총 리뷰:</b> {total_store_reviews:,}<br>
                <b>주소:</b> {row['주소']}<br>
                <b>전화번호:</b> {row['전화번호']}
            </div>
            """
            
            folium.CircleMarker(
                location=[row['위도'], row['경도']],
                radius=radius,
                popup=folium.Popup(popup_content, max_width=300),
                color=store_type_colors.get(row['타입'], '#000000'),
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

        st_folium(m, height=500)

    with col2:
        # 매장 유형 분포
        st.subheader("매장 유형 분포")
        type_counts = filtered_stores['타입'].value_counts()
        fig_types = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            color_discrete_sequence=['#00704A', '#A6192E', '#FF9900', '#4B3C8C']
        )
        fig_types.update_layout(height=300)
        st.plotly_chart(fig_types, use_container_width=True)
        
        # 직장인구 대비 매장 분포
        st.subheader("직장인구 대비 매장 분포")
        if selected_district != '전체':
            district_data = combined_district_data[combined_district_data['district'] == selected_district]
        else:
            district_data = combined_district_data
            
        fig = px.scatter(
            district_data,
            x='total_workers',
            y='store_count',
            text='district_name',
            size='stores_per_10k',
            title='',
            labels={
                'total_workers': '총 직장인구',
                'store_count': '매장 수',
                'stores_per_10k': '인구 1만명당 매장 수'
            }
        )
        fig.update_traces(
            textposition='top center',
            marker=dict(color='#00704A')
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # 하단 분석 섹션
    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("리뷰 분포 분석")
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
        st.subheader("워드클라우드")
        if selected_district != '전체':
            word_freq = df_reviews[df_reviews['district'] == selected_district].groupby('word')['count'].sum()
        else:
            word_freq = df_reviews.groupby('word')['count'].sum()
        
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

with tab2:
    st.header("음료 영양성분 분석")
    
    # 음료 비교 섹션을 상단으로 이동
    st.subheader("음료 비교하기")
    
    col1, col2 = st.columns(2)
    
    with col1:
        drink1 = st.selectbox("첫 번째 음료 선택", df_beverages['메뉴'].unique(), key='drink1')
        drink1_data = df_beverages[df_beverages['메뉴'] == drink1].iloc[0]
        st.image(drink1_data['이미지_URL'], width=200)
        st.write(f"**카테고리:** {drink1_data['카테고리']}")
    
    with col2:
        drink2 = st.selectbox("두 번째 음료 선택", df_beverages['메뉴'].unique(), key='drink2')
        drink2_data = df_beverages[df_beverages['메뉴'] == drink2].iloc[0]
        st.image(drink2_data['이미지_URL'], width=200)
        st.write(f"**카테고리:** {drink2_data['카테고리']}")
    
    # 영양성분 비교 그래프
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
        marker_color='#FF9900',
        legendrank=2
    ))
    
    fig.add_trace(go.Bar(
        name=drink1,
        y=comparison_data['영양성분'],
        x=comparison_data[drink1],
        orientation='h',
        marker_color='#00704A',
        legendrank=1
    ))
    
    fig.update_layout(
        title="영양성분 비교 (*Tall Size 기준)",
        barmode='group',
        height=400,
        margin=dict(l=200),
        yaxis={'categoryorder':'total ascending'}
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 구분선 추가
    st.markdown("---")

    # 카테고리별 영양성분 분석을 하단으로 이동
    st.subheader("카테고리별 영양성분 분석")
    
    # 영양성분 선택 필터
    selected_nutrient = st.selectbox(
        "분석할 영양성분을 선택하세요",
        ["칼로리(Kcal)", "당류(g)", "단백질(g)", "나트륨(mg)", "포화지방(g)", "카페인(mg)"]
    )

    # Box plot
    fig = px.box(df_beverages, x="카테고리", y=selected_nutrient,
                 color="카테고리",
                 title=f"카테고리별 {selected_nutrient} 분포")
    
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)