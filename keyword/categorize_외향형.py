import json
import pandas as pd
from collections import defaultdict

# store_keywords.json 파일 로드
with open("store_keywords.json", "r", encoding="utf-8") as file:
    store_keywords = json.load(file)

# 테마별 키워드 매핑
theme_mapping = {
    "활기찬 분위기": ["컨셉이 독특해요", "야외공간이 멋져요", "음악이 좋아요", "매장이 넓어요"],
    "사교적 활동": ["대화하기 좋아요", "단체모임 하기 좋아요"],
    "시각적이고 경험적 요소": ["사진이 잘 나와요", "인테리어가 멋져요", "뷰가 좋아요"],
    "활동적인 경험 제공": ["음료가 맛있어요", "디저트가 맛있어요", "주문제작을 잘해줘요"],
    "다양한 사람들과 어울릴 수 있는 요소": ["친절해요", "차분한 분위기에요", "매장이 청결해요"],
    "특별함": ["특별한 날 가기 좋아요", "특별한 메뉴가 있어요"]
}

# 테마별 매장 키워드 데이터 저장
categorized_data = defaultdict(lambda: defaultdict(int))

# 매장 데이터를 테마별로 분류
for store, keywords in store_keywords.items():
    for keyword, count in keywords.items():
        for theme, theme_keywords in theme_mapping.items():
            if keyword in theme_keywords:
                categorized_data[theme][store] += count

# 결과 출력
categorized_df = pd.DataFrame(categorized_data).fillna(0).astype(int)

print('categorized_df', categorized_df)

