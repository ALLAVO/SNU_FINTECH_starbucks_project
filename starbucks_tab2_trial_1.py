import streamlit as st
import folium
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
from store_data import chart_info
from modules.score_utils import get_scores_from_all_csv, load_all_scores

# 페이지 설정
st.set_page_config(page_title="Starbucks Store Viewer", layout="wide")
st.title("스타벅스 매장 지도 뷰어")

# 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

# 데이터 로드
@st.cache_data
def load_data():
    df = pd.read_csv('data/starbucks_seoul_all_store_info.csv')
    # 매장명의 '점' 제거하여 CSV 파일의 매장명과 매칭되도록 함
    df['매장명'] = df['매장명'].str.replace('\n', '').str.replace('점', '')
    return df

# 매장 타입별 색상 정의
store_type_colors = {
    'general': '#00704A',     # 일반 매장
    'reserve': '#A6192E',     # 리저브 매장
    'generalDT': '#FF9900',   # 드라이브스루
    'generalWT': '#4B3C8C'    # 워크스루
}
# 매장 타입별 이름 정의
store_type_labels = {
    'general': '스타벅스 일반',
    'reserve': '스타벅스 리저브',
    'generalDT': '스타벅스 드라이브스루',
    'generalWT': '스타벅스 워크스루'
}

# 데이터 로드
df = load_data()

# 레이더 차트 그리기 함수
def plot_radar_chart(title, labels, scores, store_name):
    angles = np.linspace(0, 2 * np.pi, 7)  # 6개 항목 + 1(처음으로 돌아오기)
    scores = np.append(scores, scores[0])  # 닫힌 육각형 만들기
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'})
    ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color='#00704A')
    ax.fill(angles, scores, alpha=0.3, color='#00704A')
    
    # 축 설정
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    
    # 격자 설정
    ax.grid(True)
    ax.set_yticklabels([])
    
    # 점수 표시
    for angle, score in zip(angles[:-1], scores[:-1]):
        ax.text(angle, score, f'{score:.2f}', ha='center', va='center')
    
    # 범례 추가
    ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    
    plt.title(title, pad=15, fontsize=12)
    return fig

# 레이아웃 설정
col1, col2 = st.columns([7, 3])

with col1:
    # 매장 선택 드롭다운을 상단에 배치
    selected_store = st.selectbox(
        "매장을 선택하세요",
        df['매장명'].sort_values(),
        index=None,
        placeholder="매장을 선택해주세요..."
    )

# 지도 생성 함수
def create_map(store_data=None):
    center_lat, center_lng = 37.5665, 126.9780
    zoom_level = 11
    
    if store_data is not None:
        center_lat = store_data['위도']
        center_lng = store_data['경도']
        zoom_level = 15

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom_level,
        tiles="OpenStreetMap"
    )
    
    for idx, row in df.iterrows():
        store_type = row['타입']
        
        popup_content = f"""
        <div style="font-family: 'Malgun Gothic', sans-serif;">
            <b>{row['매장명']}</b><br>
            <b>유형:</b> {row['타입']}<br>
            <b>주소:</b> {row['주소']}<br>
            <b>전화번호:</b> {row['전화번호']}
        </div>
        """
        
        radius = 8 if row['매장명'] == selected_store else 5
        
        folium.CircleMarker(
            location=[row['위도'], row['경도']],
            radius=radius,
            popup=folium.Popup(popup_content, max_width=300),
            color=store_type_colors.get(store_type, '#000000'),
            fill=True,
            fill_opacity=0.7,
            weight=2 if row['매장명'] == selected_store else 1
        ).add_to(m)
        
        if row['매장명'] == selected_store:
            # 하이라이트 원
            folium.CircleMarker(
                location=[row['위도'], row['경도']],
                radius=15,
                color='red',
                fill=False,
                weight=5
            ).add_to(m)

    return m

# 매장이 선택된 경우
if selected_store:
    store_data = df[df['매장명'] == selected_store].iloc[0]
    
    # 선택된 매장 정보로 지도 생성
    with col1:
        m = create_map(store_data)
        st_folium(m, width=1000, height=600)
        # 지도 밑에 Legends 표시
        legend_html = '<div style="display: flex; flex-direction: row; align-items: center; gap: 30px;">'
        for store_type, color in store_type_colors.items():
            legend_html += (
                f'<div style="display: flex; align-items: center;">'
                f'<div style="width: 20px; height: 20px; border-radius: 50%; '
                f'background-color: {color}; margin-right: 10px;"></div>'
                f'<div>{store_type_labels[store_type]}</div></div>'
            )
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)
    
    # 오른쪽 열에 매장 정보와 레이더 차트 표시
    with col2:
        st.markdown("### 📍 선택된 매장 정보")
        st.markdown(
            f"""
            **매장명:** {store_data['매장명']}  
            **유형:** {store_data['타입']}  
            **주소:** {store_data['주소']}  
            **전화번호:** {store_data['전화번호']}
            """
        )
        
        # 유형 선택
        st.markdown("### 📊 유형별 분석")
        selected_type = st.selectbox(
            "분석할 유형을 선택하세요",
            ["내향형", "수다형", "외향형", "카공형"]
        )
        
        # 선택된 유형의 레이더 차트 표시
        if selected_type:
            for title, labels in chart_info:
                if title == selected_type:
                    # 유형별 키워드를 파일명에서 찾음
                    file_name_keyword = title
                    
                    # CSV 데이터 확인
                    merged_df, _ = load_all_scores()
                    
                    # 선택된 매장의 점수 가져오기
                    scores = get_scores_from_all_csv(store_data['매장명'], labels, file_name_keyword)
                    
                    # 레이더 차트 생성
                    fig = plot_radar_chart(title, labels, scores, store_data['매장명'])
                    st.pyplot(fig)
else:
    # 전체 지도 보기
    with col1:
        m = create_map()
        st_folium(m, width=800, height=600)
    
    # 오른쪽 열에 안내 메시지 표시
    with col2:
        st.info("매장을 선택하면 상세 정보가 이곳에 표시됩니다.")