# 📌 차트 정보 (테마별 평가 기준)
chart_info = [
    ("외향형", ["분위기", "사교 활동", "시각적 요소", "경험", "다양성", "특별함"]),
    ("내향형", ["분위기", "환경", "프라이버시", "집중도", "개인 시간", "편의성"]),
    ("수다형", ["분위기", "공간", "프라이버시", "서비스", "단체모임", "가성비"]),
    ("카공형", ["분위기", "공간", "서비스", "청결도", "집중도", "가성비"])
]



# 📌수다형
# 수다형 Theme Scores 초기화
수다형_theme_scores = {
    '분위기': 0,
    '공간': 0,
    '프라이버시': 0,
    '서비스': 0,
    '단체모임': 0,
    '가성비': 0
}

# 매장별 Theme별 리뷰 count 초기화
수다형_theme_review_counts = {
    '분위기': 0,
    '공간': 0,
    '프라이버시': 0,
    '서비스': 0,
    '단체모임': 0,
    '가성비': 0
}

# 📌카공형
# 카공형 Theme Scores 초기화
카공형_theme_scores = {
    '분위기': 0,
    '공간': 0,
    '서비스': 0,
    '청결도': 0,
    '집중도': 0,
    '가성비': 0
}

# 매장별 Theme별 리뷰 count 초기화
카공형_theme_review_counts = {
    '분위기': 0,
    '공간': 0,
    '서비스': 0,
    '청결도': 0,
    '집중도': 0,
    '가성비': 0
}

# 📌외향형
# 외향형 Theme Scores 초기화
외향형_theme_scores = {
    '분위기': 0,
    '사교 활동': 0,
    '시각적 요소': 0,
    '경험': 0,
    '다양성': 0,
    '특별함': 0
}

# 매장별 Theme별 리뷰 count 초기화
외향형_theme_review_counts = {
    '분위기': 0,
    '사교 활동': 0,
    '시각적 요소': 0,
    '경험': 0,
    '다양성': 0,
    '특별함': 0
}

# 📌내향형
# 내향형 Theme Scores 초기화
내향형_theme_scores = {
    '분위기': 0,
    '환경': 0,
    '프라이버시': 0,
    '집중도': 0,
    '개인 시간': 0,
    '편의성': 0
}

# 매장별 Theme별 리뷰 count 초기화
내향형_theme_review_counts = {
    '분위기': 0,
    '환경': 0,
    '프라이버시': 0,
    '집중도': 0,
    '개인 시간': 0,
    '편의성': 0
}