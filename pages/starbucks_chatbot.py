import streamlit as st
import google.generativeai as genai
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import io
import base64
import markdown
from functools import lru_cache
from store_data import chart_info

class StarbucksGeminiChatbot:
    def __init__(self):
        GOOGLE_API_KEY = "AIzaSyC_5PGdU8hfRu1XDLb-4WUhwnorqf329jA"
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.data = self.load_all_data()
        self.theme_info = dict(chart_info)
        self.system_prompt = self.create_system_prompt()
        self.chat = self.model.start_chat(history=[])

    @lru_cache(maxsize=32)
    def load_all_data(self):
        """데이터 로드 및 전처리"""
        data = {
            'stores': pd.read_csv('data/starbucks_seoul_all_store_info.csv'),
            'reviews': pd.read_csv('data/cleaned_starbucks_reviews_with_counts.csv'),
            'store_reviews': pd.read_csv('data/스타벅스_리뷰_500개.csv'),
            'beverages': pd.read_csv('data/starbucks_nutrition_with_images.csv'),  # 키 이름 수정
            '내향형': pd.read_csv('hexa_point_data/내향형_테마_키워드_매장별_Theme_score.csv'),
            '외향형': pd.read_csv('hexa_point_data/외향형_테마_키워드_매장별_Theme_score.csv'),
            '수다형': pd.read_csv('hexa_point_data/수다형_테마_키워드_매장별_Theme_score.csv'),
            '카공형': pd.read_csv('hexa_point_data/카공형_테마_키워드_매장별_Theme_score.csv')
        }

        # 매장 데이터 전처리
        data['stores']['district'] = data['stores']['주소'].str.extract(r'서울특별시\s+(\S+구)')

        # 키워드 데이터 로드
        with open('keyword_data/store_keywords.json', 'r', encoding='utf-8') as f:
            data['store_keywords'] = json.load(f)

        return data

    def plot_radar_chart(self, store_name, personality_type):
        """레이더 차트 그리기"""
        angles = np.linspace(0, 2 * np.pi, len(self.theme_info[personality_type]) + 1)

        fig, ax = plt.subplots(figsize=(4, 4), subplot_kw={'projection': 'polar'})
        ax.spines['polar'].set_visible(False)
        ax.grid(False)

        # 데이터 준비
        df = self.data[personality_type]
        store_data = df[df['Store'] == store_name]
        scores = []
        labels = self.theme_info[personality_type]

        for theme in labels:
            score = store_data[store_data['Theme'] == theme]['final_theme_score'].values
            scores.append(score[0] if len(score) > 0 else 0)

        scores = np.append(scores, scores[0])  # 닫힌 다각형 형성

        # 색상 매핑
        color_mapping = {
            "외향형": "#fb9783",
            "내향형": "#73FFD0",
            "수다형": "#fdde8d",
            "카공형": "#96ddfd"
        }
        chart_color = color_mapping.get(personality_type, "blue")

        # 외곽 배경 채우기
        outer_radius = max(scores) * 1.1
        ax.fill(angles, [outer_radius] * len(angles), color='#f0f0f0', alpha=1)

        # 레이더 차트 그리기
        ax.plot(angles, scores, 'o-', linewidth=2, label=store_name, color=chart_color)
        ax.fill(angles, scores, alpha=0.3, color=chart_color)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=12)

        # 방사형 격자선 추가
        num_grid_lines = 5
        grid_step = outer_radius / num_grid_lines

        for i in range(1, num_grid_lines + 1):
            r = grid_step * i
            ax.plot(angles, [r] * len(angles), color='grey', linestyle='-', linewidth=0.5)

        # 방사형 축 추가
        for angle in angles[:-1]:
            ax.plot([angle, angle], [0, outer_radius], color='grey', linestyle='-', linewidth=0.5)

        # 점수 표시
        for angle, score, label in zip(angles[:-1], scores[:-1], labels):
            ax.text(angle, score, f'{score:.2f}', ha='center', fontsize=10,
                    fontweight='bold', color=chart_color)

        # y축 눈금 제거
        ax.set_yticklabels([])

        return fig

    def plot_radar_chart_to_base64(self, store_name, personality_type):
        """레이더 차트를 그리고 base64 인코딩된 이미지로 반환"""
        fig = self.plot_radar_chart(store_name, personality_type)

        # 이미지를 바이트 스트림으로 저장
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', transparent=True, dpi=100)
        plt.close(fig)  # 메모리 누수 방지

        # 바이트 스트림을 base64로 인코딩
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')

        return f"data:image/png;base64,{img_str}"

    def get_store_analysis(self, store_name):
        """매장 종합 분석"""
        analysis = {
            'personality_scores': {},
            'theme_scores': {},
            'keywords': self.data['store_keywords'].get(store_name, {}),
            'reviews': self.data['store_reviews'][
                self.data['store_reviews']['store_name'] == store_name
                ]['review_text'].tolist()
        }

        # 성향별 점수 계산
        for p_type in ['내향형', '외향형', '수다형', '카공형']:
            df = self.data[p_type]
            store_data = df[df['Store'] == store_name]
            analysis['personality_scores'][p_type] = store_data['final_theme_score'].sum()
            analysis['theme_scores'][p_type] = store_data.set_index('Theme')['final_theme_score'].to_dict()

        return analysis

    @lru_cache(maxsize=32)
    def get_personality_recommendation(self, personality_type, district=None):
        """개인 특성별 매장 추천"""
        if personality_type not in ['내향형', '외향형', '수다형', '카공형']:
            return None

        df = self.data[personality_type]
        stores_df = self.data['stores']

        if district:
            district = district.replace("구", "") + "구"
            stores_in_district = stores_df[stores_df['district'] == district]['매장명'].tolist()
            df = df[df['Store'].isin(stores_in_district)]

        store_scores = df.groupby('Store')['final_theme_score'].sum().sort_values(ascending=False)

        recommendations = []
        for store in store_scores.head().index:
            store_data = df[df['Store'] == store]
            store_info = stores_df[stores_df['매장명'] == store].iloc[0]

            recommendations.append({
                'store': store,
                'total_score': store_scores[store],
                'top_themes': [f"{row['Theme']}({row['final_theme_score']:.1f}점)"
                               for _, row in store_data.nlargest(3, 'final_theme_score').iterrows()],
                'keywords': [f"{k}({v}회)" for k, v in sorted(
                    self.data['store_keywords'].get(store, {}).items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]],
                'address': store_info['주소']
            })

        return recommendations

    def create_system_prompt(self):
        """시스템 프롬프트 생성"""
        personality_info = [
            f"{p_type}:\n" + \
            f"- 평가 테마: {', '.join(themes)}\n" + \
            f"- 특징: {self._get_personality_description(p_type)}"
            for p_type, themes in self.theme_info.items()
        ]

        return f"""당신은 스타벅스 매장 분석 전문가입니다. 각 매장의 특성과 데이터를 바탕으로 맞춤형 추천과 분석을 제공합니다.

보유 데이터:
1. 매장 정보: 서울시 633개 매장의 위치, 유형, 특성 데이터
2. 리뷰 데이터: 실제 방문자들의 리뷰와 평가
3. 성향별 테마 점수: 각 매장의 테마별 상세 평가 점수
4. 키워드 분석: 매장별 주요 키워드와 언급 빈도
5. 음료 데이터: 각 음료별 영양성분과 이미지 URL 데이터

성향별 특성:
{chr(10).join(personality_info)}

답변 작성 가이드:
기본 스타일: 친근한 20대 여성 안내원 말투
1. 매장 추천 시:
   - 추천 이유를 테마 점수와 함께 설명
   - 실제 리뷰나 키워드를 인용하여 설명
   - 해당 성향에 특히 적합한 이유 설명

2. 매장 분석 시:
   - 강점과 특징을 수치로 제시
   - 가장 높은 점수의 테마 강조
   - 실제 방문자 리뷰 인용

응답 형식:
- 마크다운 형식을 사용하여 응답합니다.
- 볼드체(**), 이탤릭체(*), 제목(#) 등을 적절히 사용합니다.
- 중요한 키워드와 수치는 **볼드체**로 강조합니다.
- 리스트 항목은 * 또는 -으로 표시합니다.

시각화 참고:
각 답변에는 관련 테마 점수 차트가 함께 제공됩니다."""

    def _get_personality_description(self, personality_type):
        """성향별 특성 설명"""
        descriptions = {
            "내향형": "조용하고 프라이빗한 공간을 선호하며, 개인의 집중과 편안함을 중시하는 특성",
            "외향형": "활기찬 분위기와 사교적 활동이 가능한 공간을 선호하며, 다양한 경험을 추구하는 특성",
            "수다형": "대화하기 좋은 환경과 편안한 분위기를 중시하며, 그룹 활동에 적합한 공간을 선호하는 특성",
            "카공형": "학습과 업무에 집중할 수 있는 환경을 선호하며, 장시간 머무르기 좋은 공간을 찾는 특성"
        }
        return descriptions.get(personality_type, "")

    def get_beverage_recommendations(self, query):
        """음료 추천 및 분석"""
        beverages_df = self.data['beverages']  # 키 이름 수정

        # 쿼리 키워드 분석
        is_low_caffeine = any(word in query.lower() for word in ['저카페인', '카페인 적은', '카페인이 적은'])
        is_sweet = any(word in query.lower() for word in ['달달한', '단', '달콤한', '달달'])
        is_cold = any(word in query.lower() for word in ['차가운', '시원한', '아이스', '시원'])
        is_hot = any(word in query.lower() for word in ['따뜻한', '뜨거운', '핫', '따듯'])

        # 필터링 조건 설정
        filtered_df = beverages_df.copy()

        if is_low_caffeine:
            # 카페인 75mg 이하를 저카페인으로 간주
            filtered_df = filtered_df[filtered_df['카페인(mg)'] <= 75]

        if is_sweet:
            # 당류가 높은 음료 (상위 50%)
            median_sugar = beverages_df['당류(g)'].median()
            filtered_df = filtered_df[filtered_df['당류(g)'] >= median_sugar]

        # 카테고리별 필터링 (쿼리에 특정 카테고리가 언급된 경우)
        categories = ['에스프레소', '프라푸치노', '티', '콜드브루', '리프레셔', '블렌디드']
        for category in categories:
            if category in query:
                filtered_df = filtered_df[filtered_df['카테고리'] == category]

        # 결과가 없으면 원래 데이터프레임 사용
        if filtered_df.empty:
            filtered_df = beverages_df

        # 랜덤하게 3개 추천 (또는 있는 만큼)
        recommended_drinks = filtered_df.sample(min(3, len(filtered_df)))

        return recommended_drinks.to_dict('records')

    def get_answer(self, query):
        """사용자 질문에 대한 답변 생성"""
        try:
            # 매장명 확인
            store_name = None
            for store in self.data['store_keywords'].keys():
                if store in query:
                    store_name = store
                    break

            # 성향 확인
            personality_type = None
            for p_type in ['내향형', '외향형', '수다형', '카공형']:
                if p_type in query:
                    personality_type = p_type
                    break

            # 카공 키워드가 있을 경우 카공형으로 설정
            if '카공' in query and not personality_type:
                personality_type = '카공형'

            # 지역구 확인
            district = None
            for d in self.data['stores']['district'].unique():
                if d in query:
                    district = d
                    break

            # 음료 추천 여부 확인
            is_beverage_query = any(word in query for word in ['음료', '마실', '추천', '카페인', '달달', '차가운', '따뜻한'])

            # 이미지 및 컨텍스트 준비
            charts = []
            context = []
            beverage_images = []

            if is_beverage_query:
                # 음료 추천
                try:
                    recommended_beverages = self.get_beverage_recommendations(query)

                    if recommended_beverages:
                        context.append("\n추천 음료:")
                        for i, beverage in enumerate(recommended_beverages, 1):
                            context.append(f"{i}. {beverage['메뉴']} - {beverage['카테고리']}")
                            context.append(f"   칼로리: {beverage['칼로리(Kcal)']}kcal, 카페인: {beverage['카페인(mg)']}mg, 당류: {beverage['당류(g)']}g")

                            # 음료 이미지 URL 추가
                            if beverage['이미지_URL']:
                                beverage_images.append({
                                    'name': beverage['메뉴'],
                                    'url': beverage['이미지_URL']
                                })
                except Exception as e:
                    context.append(f"\n음료 추천 중 오류 발생: {str(e)}")

            if store_name:
                # 매장 분석용 차트 생성
                for p_type in ['내향형', '외향형', '수다형', '카공형']:
                    img_data = self.plot_radar_chart_to_base64(store_name, p_type)
                    if img_data:
                        charts.append({
                            'title': f'{p_type} 테마 분석',
                            'image': img_data
                        })

                # 매장 정보 컨텍스트 추가
                analysis = self.get_store_analysis(store_name)
                context.append(f"\n{store_name} 매장 분석:")
                for p_type, score in analysis['personality_scores'].items():
                    context.append(f"- {p_type}: {score:.1f}점")

                # 키워드 정보 추가
                top_keywords = sorted(analysis['keywords'].items(), key=lambda x: x[1], reverse=True)[:5]
                context.append("\n주요 키워드:")
                context.append(", ".join(f"{k}({v}회)" for k, v in top_keywords))

                # 리뷰 예시 추가
                store_district = self.data['stores'][self.data['stores']['매장명'] == store_name]['district'].values
                district_for_review = store_district[0] if len(store_district) > 0 else None

                reviews = []
                if analysis['reviews']:
                    reviews = analysis['reviews'][:3]
                # 해당 매장 리뷰가 없는 경우, 동일 구의 다른 인기 매장 리뷰 가져오기
                elif district_for_review:
                    # 동일 구의 TOP 리뷰 매장 찾기 (리뷰 수 기준)
                    district_top_stores = self.data['store_reviews'][
                        self.data['store_reviews']['district'] == district_for_review
                        ]['store_name'].value_counts().head(3).index.tolist()

                    # TOP 매장들의 리뷰 가져오기
                    for top_store in district_top_stores:
                        district_reviews = self.data['store_reviews'][
                            self.data['store_reviews']['store_name'] == top_store
                            ]['review_text'].tolist()

                        if district_reviews:
                            context.append(f"\n{district_for_review} 인기 매장 {top_store}의 리뷰 예시:")
                            for i, review in enumerate(district_reviews[:2]):  # 각 매장당 최대 2개 리뷰
                                context.append(f"- {review}")
                            break

                if reviews:  # 원래 매장의 리뷰가 있는 경우
                    context.append("\n리뷰 예시:")
                    context.extend([f"- {review}" for review in reviews])

            elif personality_type and district:
                # 지역 기반 추천
                try:
                    recommendations = self.get_personality_recommendation(personality_type, district)
                    if recommendations:
                        context.append(f"\n{personality_type}을 위한 {district} 추천 매장:")
                        for i, rec in enumerate(recommendations[:3], 1):
                            # 추천 매장의 레이더 차트 생성
                            img_data = self.plot_radar_chart_to_base64(rec['store'], personality_type)
                            if img_data:
                                charts.append({
                                    'title': f"{rec['store']} 분석",
                                    'image': img_data
                                })

                            context.append(
                                f"{i}. {rec['store']} (총점: {rec['total_score']:.1f})\n"
                                f"   주요 테마: {', '.join(rec['top_themes'])}\n"
                                f"   대표 키워드: {', '.join(rec['keywords'])}\n"
                                f"   위치: {rec['address']}"
                            )

                            # 추천 매장의 리뷰 추가
                            store_reviews = self.data['store_reviews'][
                                self.data['store_reviews']['store_name'] == rec['store']
                                ]['review_text'].tolist()

                            if store_reviews:
                                context.append(f"\n{rec['store']} 리뷰 예시:")
                                context.extend([f"- {review}" for review in store_reviews[:2]])
                            # 리뷰가 없는 경우, 동일 구의 인기 매장 리뷰를 대신 제공
                            else:
                                # 동일 구의 TOP 리뷰 매장 찾기
                                district_top_stores = self.data['store_reviews'][
                                    self.data['store_reviews']['district'] == district
                                    ]['store_name'].value_counts().head(3).index.tolist()

                                if district_top_stores:
                                    top_district_store = district_top_stores[0]
                                    district_reviews = self.data['store_reviews'][
                                        self.data['store_reviews']['store_name'] == top_district_store
                                        ]['review_text'].tolist()

                                    if district_reviews:
                                        context.append(f"\n{district} 인기 매장 {top_district_store}의 리뷰 예시:")
                                        context.extend([f"- {review}" for review in district_reviews[:2]])

                except Exception as e:
                    context.append(f"\n매장 추천 중 오류 발생: {str(e)}")

            # Gemini로 응답 생성
            prompt = f"{self.system_prompt}\n\n추가 정보:\n{''.join(context)}\n\n질문: {query}"
            response = self.chat.send_message(prompt)

            return {
                'text': response.text,
                'store_name': store_name,
                'personality_type': personality_type,
                'district': district,
                'charts': charts,
                'beverage_images': beverage_images
            }

        except Exception as e:
            st.error(f"오류 발생: {str(e)}")
            return {
                'text': f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}",
                'charts': [],
                'beverage_images': []
            }

# Streamlit UI
def main():
    st.set_page_config(
        page_title="SIREN VALUE",
        page_icon="https://img.icons8.com/fluency/48/starbucks.png",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown(
        """
        <style>
        .chat-message {
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
        }
        .user-message {
            background-color: #E5F6E8;
            margin-left: 2rem;
        }
        .assistant-message {
            background-color: #F4F4F4;
            margin-right: 2rem;
        }
        .chart-container {
            margin-top: 1rem;
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .chat-message h1 {
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .chat-message h2 {
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 0.4rem;
        }
        .chat-message h3 {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 0.3rem;
        }
        .chat-message ul {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .chat-message li {
            margin-left: 1.5rem;
            list-style-type: disc;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("스타벅스 AI 분석 챗봇 🤖")

    with st.expander("💡 이런 것들을 물어보세요!", expanded=True):
        st.markdown("""
        **개인 특성별 매장 추천:**
        - "내향형인데 강남구에 있는 매장 추천해주세요"
        - "카공하기 좋은 매장 알려주세요"
        - "수다떨기 좋은 조용한 매장 어디 있나요?"
        - "외향형에게 어울리는 매장 추천해주세요"
        
        **매장 상세 분석:**
        - "역삼아레나빌딩점은 어떤 특징이 있나요?"
        - "논현역사거리점의 장단점을 분석해주세요"
        
        **음료 추천:**
        - "카페인이 적은 음료 추천해주세요"
        - "달달한 음료 추천해주세요"
        """)

    # 세션 상태 초기화
    if 'gemini_chatbot' not in st.session_state:
        with st.spinner("챗봇을 초기화하고 있습니다..."):
            st.session_state.gemini_chatbot = StarbucksGeminiChatbot()

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # 채팅 이력 표시
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
                <div class="chat-message user-message">
                    <div>👤 사용자</div>
                    {message["content"]}
                </div>
            """, unsafe_allow_html=True)
        else:
            # AI 응답 마크다운을 HTML로 변환
            formatted_text = markdown.markdown(message["content"]["text"])

            # AI 응답 표시
            st.markdown(f"""
                <div class="chat-message assistant-message">
                    <div>☕️ 스타벅스 분석가</div>
                    {formatted_text}
                </div>
            """, unsafe_allow_html=True)

            # 차트 이미지 표시
            if message["content"].get("charts"):
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)

                col1, col2 = st.columns([1, 1])
                for i, chart in enumerate(message["content"]["charts"]):
                    with col1 if i % 2 == 0 else col2:
                        st.markdown(f"### {chart['title']}")
                        st.markdown(f'<img src="{chart["image"]}" width="100%">', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

    # 사용자 입력
    user_input = st.chat_input("질문을 입력하세요...")

    if user_input:
        # 사용자 메시지 저장
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 챗봇 응답 생성
        with st.spinner("AI가 답변을 분석하고 있습니다..."):
            response = st.session_state.gemini_chatbot.get_answer(user_input)

        # 챗봇 응답 저장
        st.session_state.messages.append({"role": "assistant", "content": response})

        # 페이지 리프레시
        st.rerun()

if __name__ == "__main__":
    # matplotlib 한글 폰트 설정
    plt.rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False
    main()

