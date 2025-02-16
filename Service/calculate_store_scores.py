'''
📌 CSV 파일별 매장 Theme 점수 계산 및 저장 프로그램
    - JSON 파일(`store_keywords.json`): 매장별 키워드 및 리뷰 수
    - CSV 파일(`*_테마_키워드.csv`): 키워드별 Theme 및 점수 정보
    - `store_data.py`: 유형별(수다형, 카공형 등) 초기 Theme 정보
    - 결과: `_매장별_Theme_score.csv` 파일 생성 (매장별 Theme 점수 포함)
'''
import pandas as pd
import json
import os
import glob
import store_data as st

# 📌파일 불러오기
# json 파일 경로 설정
json_path = os.path.join('..', 'keyword_data', 'store_keywords.json')
# CSV 파일 경로 설정
csv_folder = os.path.join('..', 'keyword_data')
# keyword_data 폴더에서 *_테마_키워드.csv 패턴에 해당하는 모든 CSV 파일을 찾는다.
csv_files = glob.glob(os.path.join(csv_folder, '*_테마_키워드.csv'))

# JSON 파일 불러오기
with open(json_path, 'r', encoding='utf-8') as f:
    store_data = json.load(f)

# 📌 각 유형(외향형..등)에 대한 CSV 파일을 불러온 후,
    # 파일별 테마 점수를 계산 및 개별 CSV 파일 저장
for csv_file in csv_files:
    # CSV 파일명 추출
    file_name = os.path.basename(csv_file).replace('.csv', '')
    print(f"\n📂 파일명: {file_name}")

    # CSV 파일 불러오기
    df = pd.read_csv(csv_file)

    # 📌 수다형 또는 카공형 등에 따라 초기 Theme 스코어 및 카운트 불러오기
    if "수다형" in file_name:
        theme_scores = st.수다형_theme_scores.copy()
        theme_review_counts = st.수다형_theme_review_counts.copy()
    elif "카공형" in file_name:
        theme_scores = st.카공형_theme_scores.copy()
        theme_review_counts = st.카공형_theme_review_counts.copy()
    elif "외향형" in file_name:
        theme_scores = st.외향형_theme_scores.copy()
        theme_review_counts = st.외향형_theme_review_counts.copy()
    elif "내향형" in file_name:
        theme_scores = st.내향형_theme_scores.copy()
        theme_review_counts = st.내향형_theme_review_counts.copy()
    else:
        print(f"❌ 알 수 없는 파일 유형: {file_name}")
        continue

    # 📌 CSV 데이터를 Dictionary로 변환 (Keyword를 키로 Theme, Score, Mood 목록 저장)
    keyword_info = {}
    for _, row in df.iterrows():
        keyword = row['Keyword']
        theme = row['Theme']
        score = row['Score']
        mood = row['Mood']

        if keyword not in keyword_info:
            keyword_info[keyword] = []
        keyword_info[keyword].append({'Theme': theme, 'Score': score, 'Mood': mood})

    # 📌 각 매장의 키워드를 순회하며 Theme별 리뷰 수 합산
    theme_keyword_counts = {}
    for store_name, keywords in store_data.items():
        for keyword, count in keywords.items():
            if keyword in keyword_info:
                for info in keyword_info[keyword]:
                    theme = info['Theme']
                    if theme not in theme_keyword_counts:
                        theme_keyword_counts[theme] = []
                    theme_keyword_counts[theme].append(count)

    # Theme별 평균 리뷰 수 계산
    theme_keyword_averages = {}
    for theme, counts in theme_keyword_counts.items():
        theme_keyword_averages[theme] = sum(counts) / len(counts) if counts else 0

    # 📌️각 매장에서 키워드를 확인하며 Theme(꼭짓점)별 점수 및 리뷰 합산
    store_theme_scores = {}
    store_theme_review_counts = {}
    store_theme_averages = {}   # theme별 점수/리뷰 수 평균

    for store_name, keywords in store_data.items():
        theme_scores_copy = theme_scores.copy()
        theme_review_counts_copy = theme_review_counts.copy()

        for keyword, count in keywords.items():
            if keyword in keyword_info:
                for info in keyword_info[keyword]:
                    theme = info['Theme']
                    score = info['Score']
                    mood = info['Mood']

                    # Mood에 따라 점수 계산 (Plus는 더하고, Minus는 뺌)
                    if mood == 'Plus':
                        theme_scores_copy[theme] += count * score
                    elif mood == 'Minus':
                        theme_scores_copy[theme] -= count * score

                    # 리뷰 수 누적
                    theme_review_counts_copy[theme] += count

        # 📌 동일한 'theme'(꼭짓점)끼리 score_avg = (점수)/(리뷰 수) 계산
        theme_averages = {}
        for theme in theme_scores_copy.keys():
            score = theme_scores_copy[theme]                    # 해당 테마에 대한 총 점수 (키워드 기반 가중합)
            count = theme_review_counts_copy[theme]             # 해당 테마에 대한 총 리뷰 수
            theme_avg = theme_keyword_averages.get(theme, 0)    # 해당 테마에 대한 전체 평균 리뷰 수 (모든 매장 기반)

            # 📌 Theme별 점수와 전체 평균 리뷰 수를 함께 반영한 평균 계산
            #    - 전체 평균 리뷰 수(avg)를 추가해 편향을 완화 (스무딩 효과)
            score_average = (score + theme_avg) / (count + 1)

            # 📌️ 'score_average'에 10을 곱한 후, 소수점 둘째 자리까지 반올림
            theme_averages[theme] = round(score_average * 10, 2)  # 10배, 소수 둘째 자리

        # 📌 매장별 계산된 결과 저장
        store_theme_scores[store_name] = theme_scores_copy
        store_theme_review_counts[store_name] = theme_review_counts_copy
        store_theme_averages[store_name] = theme_averages

    # 📌📌️ CSV 파일로 저장
    output_folder = os.path.join('..', 'hexa_point_data')
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, f'{file_name}_매장별_Theme_score.csv')

    results_list = []
    for store, themes in store_theme_averages.items():
        for theme, average in themes.items():
            score = store_theme_scores[store][theme]
            review_count = store_theme_review_counts[store][theme]
            results_list.append({
                'Store': store,
                'Theme': theme,
                # 'TotalScore': score,
                # 'ReviewCount': review_count,
                'final_theme_score': average
            })

    results_df = pd.DataFrame(results_list)
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"✅ '{file_name}' 결과 파일 저장 완료: {output_path}")