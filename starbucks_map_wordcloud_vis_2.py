import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
import json
import requests
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Set page configuration
st.set_page_config(page_title="Seoul Starbucks Analysis", layout="wide")

# 서울시 각 구의 중심 좌표와 줌 레벨 정의
district_coordinates = {
    '강남구': {'lat': 37.4959854, 'lng': 127.0664091, 'zoom': 13},
    '강동구': {'lat': 37.5492077, 'lng': 127.1464824, 'zoom': 13},
    '강북구': {'lat': 37.6396773, 'lng': 127.0255167, 'zoom': 13},
    '강서구': {'lat': 37.5657617, 'lng': 126.8226561, 'zoom': 13},
    '관악구': {'lat': 37.4782929, 'lng': 126.9517171, 'zoom': 13},
    '광진구': {'lat': 37.5384843, 'lng': 127.0822432, 'zoom': 13},
    '구로구': {'lat': 37.4952755, 'lng': 126.8506269, 'zoom': 13},
    '금천구': {'lat': 37.4600969, 'lng': 126.9001546, 'zoom': 13},
    '노원구': {'lat': 37.6541917, 'lng': 127.0564832, 'zoom': 13},
    '도봉구': {'lat': 37.6687738, 'lng': 127.0470397, 'zoom': 13},
    '동대문구': {'lat': 37.5744304, 'lng': 127.0398643, 'zoom': 13},
    '동작구': {'lat': 37.4965037, 'lng': 126.9443073, 'zoom': 13},
    '마포구': {'lat': 37.5622906, 'lng': 126.9087803, 'zoom': 13},
    '서대문구': {'lat': 37.5820369, 'lng': 126.9356665, 'zoom': 13},
    '서초구': {'lat': 37.4837121, 'lng': 127.0324112, 'zoom': 13},
    '성동구': {'lat': 37.5506753, 'lng': 127.0409622, 'zoom': 13},
    '성북구': {'lat': 37.5894843, 'lng': 127.0167088, 'zoom': 13},
    '송파구': {'lat': 37.5048534, 'lng': 127.1144822, 'zoom': 13},
    '양천구': {'lat': 37.5270616, 'lng': 126.8561534, 'zoom': 13},
    '영등포구': {'lat': 37.5263674, 'lng': 126.8962771, 'zoom': 13},
    '용산구': {'lat': 37.5320147, 'lng': 126.9904769, 'zoom': 13},
    '은평구': {'lat': 37.6176125, 'lng': 126.9227004, 'zoom': 13},
    '종로구': {'lat': 37.5728933, 'lng': 126.9793881, 'zoom': 13},
    '중구': {'lat': 37.5579452, 'lng': 126.9941904, 'zoom': 13},
    '중랑구': {'lat': 37.5953795, 'lng': 127.0939669, 'zoom': 13}
}

# Define color scheme for different store types
store_type_colors = {
    'general': '#00704A',     # Regular Starbucks green
    'reserve': '#A6192E',     # Reserve stores in dark red
    'generalDT': '#FF9900',   # Drive-thru in orange
    'generalWT': '#4B3C8C'    # Walk-thru in purple
}

@st.cache_data
def load_seoul_geojson():
    response = requests.get('https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json')
    return response.json()

@st.cache_data
def load_data():
    df = pd.read_csv('data/starbucks_seoul_all_store_info.csv')
    df['district'] = df['주소'].str.extract(r'서울특별시\s+(\S+구)')
    df['매장명'] = df['매장명'].str.replace('\n', '') + df['매장명'].apply(lambda x: '점' if not x.endswith('점') else '')
    return df

@st.cache_data
def load_review_data():
    df = pd.read_csv('data/cleaned_starbucks_reviews_with_counts.csv')
    return df

@st.cache_data
def load_worker_data():
    df = pd.read_csv('data/seoul_district_age_group_workers.csv')
    return df

@st.cache_data
def generate_wordcloud(text_data, width=400, height=200):
    wordcloud = WordCloud(
        font_path='NanumSquareRoundB.ttf',
        width=width,
        height=height,
        background_color='white',
        colormap='Greens',
        max_words=100
    ).generate_from_frequencies(text_data)
    return wordcloud

@st.cache_data
def load_review_counts():
    df = pd.read_csv('data/starbucks_review_num_with_district.csv')
    return df

@st.cache_data
def load_beverage_data():
    df = pd.read_csv('data/starbucks_nutrition_with_images.csv')
    return df

# Load all data
df = load_data()
df_reviews = load_review_data()
seoul_geo = load_seoul_geojson()
df_workers = load_worker_data()
df_review_counts = load_review_counts()
df_beverages = load_beverage_data()

# Calculate total workers and stores per district
df_workers['total_workers'] = (
    df_workers['male_10s_20s'] + df_workers['male_30s_40s'] + df_workers['male_50s_60s_above'] +
    df_workers['female_10s_20s'] + df_workers['female_30s_40s'] + df_workers['female_50s_60s_above']
)
stores_per_district = df.groupby('district').size().reset_index(name='store_count')
combined_district_data = pd.merge(
    df_workers,
    stores_per_district,
    left_on='district_name',
    right_on='district',
    how='left'
)
combined_district_data['store_count'] = combined_district_data['store_count'].fillna(0)
combined_district_data['stores_per_10k'] = (combined_district_data['store_count'] / combined_district_data['total_workers']) * 10000

# Create sidebar filters
st.sidebar.title("필터")

# District filter
districts = ['전체'] + sorted(df['district'].unique().tolist())
selected_district = st.sidebar.selectbox('지역구 선택', districts)

# Store type filter
store_types = df['타입'].unique().tolist()
selected_types = st.sidebar.multiselect(
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

# 음료 분석용 필터
st.sidebar.markdown("---")
st.sidebar.header("음료 분석 설정")
selected_nutrient = st.sidebar.selectbox(
    "분석할 영양성분을 선택하세요",
    ["칼로리(Kcal)", "당류(g)", "단백질(g)", "나트륨(mg)", "포화지방(g)", "카페인(mg)"]
)

# Filter data
filtered_df = df.copy()
if selected_district != '전체':
    filtered_df = filtered_df[filtered_df['district'] == selected_district]
filtered_df = filtered_df[filtered_df['타입'].isin(selected_types)]

# Create main layout
st.title("서울 스타벅스 종합 분석 대시보드")

tab1, tab2, tab3 = st.tabs(["📍 매장 분석", "📝 리뷰 분석", "☕ 음료 분석"])

with tab1:
    # 상단 통계 지표
    st.subheader("📊 주요 지표")
    stats_cols = st.columns(4)
    
    with stats_cols[0]:
        total_stores = len(filtered_df)
        st.metric("매장 수", f"{total_stores:,}")
    
    with stats_cols[1]:
        if selected_district != '전체':
            worker_stats = df_workers[df_workers['district_name'] == selected_district]
            total_workers = worker_stats['total_workers'].iloc[0]
        else:
            total_workers = df_workers['total_workers'].sum()
        st.metric("직장인구", f"{total_workers:,}")
    
    with stats_cols[2]:
        stores_per_10k = (total_stores / total_workers) * 10000
        st.metric("인구 1만명당 매장 수", f"{stores_per_10k:.1f}")
    
    with stats_cols[3]:
        avg_age = (
            (df_workers['male_30s_40s'].sum() + df_workers['female_30s_40s'].sum()) / 
            df_workers['total_workers'].sum() * 100
        )
        st.metric("30-40대 직장인 비율", f"{avg_age:.1f}%")

    # 지도와 분석 차트
    col1, col2 = st.columns([7,3])
    
    with col1:
        st.subheader("매장 위치 및 분포")
        
        # Set map center and zoom
        if selected_district != '전체' and selected_district in district_coordinates:
            center_lat = district_coordinates[selected_district]['lat']
            center_lng = district_coordinates[selected_district]['lng']
            zoom_level = district_coordinates[selected_district]['zoom']
        else:
            center_lat, center_lng = 37.5665, 126.9780
            zoom_level = 11

        # Create map
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=zoom_level,
            tiles="OpenStreetMap"
        )

        # Add GeoJSON layer with tooltips
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

        # Add markers
        for idx, row in filtered_df.iterrows():
            store_type = row['타입']
            
            popup_content = f"""
            <div style="font-family: 'Malgun Gothic', sans-serif;">
                <b>{row['매장명']}</b><br>
                <b>유형:</b> {row['타입']}<br>
                <b>주소:</b> {row['주소']}<br>
                <b>전화번호:</b> {row['전화번호']}
            </div>
            """
            
            folium.CircleMarker(
                location=[row['위도'], row['경도']],
                radius=5,
                popup=folium.Popup(popup_content, max_width=300),
                color=store_type_colors.get(store_type, '#000000'),
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

        # Display map
        st_folium(m, width=800, height=600)
    
    with col2:
        # 매장 유형 분포
        st.subheader("매장 유형")
        type_counts = filtered_df['타입'].value_counts()
        
        type_labels = {
            'general': '일반 매장',
            'reserve': '리저브 매장',
            'generalDT': '드라이브스루 매장',
            'generalWT': '워크스루 매장'
        }
        
        fig = px.pie(
            values=type_counts.values,
            names=[type_labels.get(t, t) for t in type_counts.index],
            color_discrete_sequence=['#00704A', '#A6192E', '#FF9900', '#4B3C8C']
        )
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
        
        # 직장인구 vs 매장 수 상관관계
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
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    # 하단 분석 차트
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("자치구별 매장 현황")
        district_counts = filtered_df.groupby('district').size().reset_index()
        district_counts.columns = ['district', 'count']
        
        fig = px.bar(
            district_counts, 
            x='district', 
            y='count',
            color='count',
            color_continuous_scale='Greens',
            labels={'district': '자치구', 'count': '매장 수'}
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        st.subheader("연령대별 직장인구 분포")
        if selected_district != '전체':
            district_workers = df_workers[df_workers['district_name'] == selected_district]
        else:
            district_workers = df_workers
            
        age_data = pd.DataFrame({
            '연령대': ['10-20대', '30-40대', '50-60대 이상'],
            '남성': [
                district_workers['male_10s_20s'].sum(),
                district_workers['male_30s_40s'].sum(),
                district_workers['male_50s_60s_above'].sum()
            ],
            '여성': [
                district_workers['female_10s_20s'].sum(),
                district_workers['female_30s_40s'].sum(),
                district_workers['female_50s_60s_above'].sum()
            ]
        })
        
        age_data_melted = pd.melt(
            age_data, 
            id_vars=['연령대'], 
            var_name='성별', 
            value_name='인구수'
        )
        
        fig = px.bar(
            age_data_melted,
            x='연령대',
            y='인구수',
            color='성별',
            barmode='group',
            color_discrete_map={'남성': '#1f77b4', '여성': '#ff7f0e'},
            labels={'인구수': '직장인구'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📊 리뷰 통계 분석")
    
    # 상단에 리뷰 유형 선택 라디오 버튼 배치
    review_type = st.radio(
        "리뷰 유형",
        ["전체 리뷰", "방문자 리뷰", "블로그 리뷰"],
        horizontal=True,
        key="review_type_selector"
    )
    
    # 첫 번째 행: 리뷰 수 분석
    if selected_district != '전체':
        district_data = df_review_counts[df_review_counts['District'] == selected_district]
    else:
        district_data = df_review_counts
        
    col1, col2 = st.columns(2)
    
    with col1:
        if review_type == "전체 리뷰":
            district_data['Total_Reviews'] = district_data['Visitor_Reviews'] + district_data['Blog_Reviews']
            
            # Top 10 매장 막대 차트
            top_stores = district_data.nlargest(10, 'Total_Reviews')
            fig = px.bar(
                top_stores,
                x='Name',
                y=['Visitor_Reviews', 'Blog_Reviews'],
                title='리뷰 수 TOP 10 매장',
                labels={'value': '리뷰 수', 'Name': '매장명', 'variable': '리뷰 유형'},
                color_discrete_map={
                    'Visitor_Reviews': '#00704A',
                    'Blog_Reviews': '#4B3C8C'
                },
                barmode='stack'
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=400,
                legend_title="리뷰 유형",
                showlegend=True,
                legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'xanchor': 'right', 'x': 1}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        elif review_type == "방문자 리뷰":
            st.subheader("방문자 리뷰 TOP 10 매장")
            top_visitor = district_data.nlargest(10, 'Visitor_Reviews')[['Name', 'Visitor_Reviews', 'District']]
            fig = px.bar(
                top_visitor,
                x='Name',
                y='Visitor_Reviews',
                text='Visitor_Reviews',
                color_discrete_sequence=['#00704A']
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:  # 블로그 리뷰
            st.subheader("블로그 리뷰 TOP 10 매장")
            top_blog = district_data.nlargest(10, 'Blog_Reviews')[['Name', 'Blog_Reviews', 'District']]
            fig = px.bar(
                top_blog,
                x='Name',
                y='Blog_Reviews',
                text='Blog_Reviews',
                color_discrete_sequence=['#4B3C8C']
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if review_type == "전체 리뷰":
            st.subheader("리뷰 분포 현황")
            fig = px.scatter(
                district_data,
                x='Visitor_Reviews',
                y='Blog_Reviews',
                color='District' if selected_district == '전체' else None,
                hover_data=['Name'],
                labels={
                    'Visitor_Reviews': '방문자 리뷰 수',
                    'Blog_Reviews': '블로그 리뷰 수'
                }
            )
            fig.update_traces(marker=dict(size=8))
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
        elif review_type == "방문자 리뷰":
            st.subheader("방문자 리뷰 분포")
            fig = px.box(
                district_data,
                y='Visitor_Reviews',
                points='all',
                labels={'Visitor_Reviews': '방문자 리뷰 수'},
                color_discrete_sequence=['#00704A']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
        else:  # 블로그 리뷰
            st.subheader("블로그 리뷰 분포")
            fig = px.box(
                district_data,
                y='Blog_Reviews',
                points='all',
                labels={'Blog_Reviews': '블로그 리뷰 수'},
                color_discrete_sequence=['#4B3C8C']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # 구분선 추가
    st.markdown("---")
    st.subheader("💬 키워드 분석")
    
    # 두 번째 행: 키워드 분석
    col3, col4 = st.columns([6,4])
    
    with col3:
        # 자치구별 총 리뷰 키워드 수
        district_reviews = df_reviews.groupby('district')['count'].sum().reset_index()
        fig = px.bar(
            district_reviews,
            x='district',
            y='count',
            color='count',
            color_continuous_scale='Greens',
            labels={'district': '자치구', 'count': '키워드 출현 횟수'},
            title="자치구별 키워드 출현 빈도"
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        if selected_district != '전체':
            district_words = df_reviews[df_reviews['district'] == selected_district]
            word_counts = district_words.groupby('word')['district_count'].sum().sort_values(ascending=True).tail(10)
            
            fig = px.bar(
                x=word_counts.values,
                y=word_counts.index,
                orientation='h',
                color=word_counts.values,
                color_continuous_scale='Greens',
                title=f"{selected_district} 주요 키워드 TOP 10"
            )
            fig.update_layout(
                yaxis_title="키워드",
                xaxis_title="출현 빈도",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        st.subheader("워드클라우드")
        view_option = st.radio(
            "분석 범위",
            ["전체 리뷰", "자치구별 리뷰"],
            horizontal=True,
            key="wordcloud_option"
        )
        
        with st.spinner('워드클라우드 생성 중...'):
            try:
                if view_option == "전체 리뷰":
                    word_freq = df_reviews.groupby('word')['count'].sum().to_dict()
                    if word_freq:
                        wordcloud = generate_wordcloud(word_freq)
                        plt.clf()
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')
                        st.pyplot(fig)
                        plt.close(fig)
                else:
                    if selected_district != '전체':
                        district_words = df_reviews[df_reviews['district'] == selected_district]
                        word_freq = district_words.groupby('word')['district_count'].sum().to_dict()
                        
                        if word_freq:
                            wordcloud = generate_wordcloud(word_freq)
                            plt.clf()
                            fig, ax = plt.subplots(figsize=(10, 5))
                            ax.imshow(wordcloud, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                            plt.close(fig)
                        else:
                            st.warning(f"{selected_district}의 리뷰 데이터가 없습니다.")
                    else:
                        st.info("자치구를 선택해주세요.")
            except Exception as e:
                st.error(f"시각화 생성 중 오류가 발생했습니다: {str(e)}")
with tab3:
    st.header("음료 영양성분 분석")
    
    # 첫 번째 행: 카테고리별 분석
    st.subheader("카테고리별 영양성분 분포")
    
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
    
    # 두 번째 행: 음료 비교
    st.markdown("---")
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