'''
점수계산 & 로그 적용 코드
'''
import glob
import os
import math
import pandas as pd
import numpy as np

# 📌 CSV 파일 폴더 경로
CSV_FOLDER_PATH = './hexa_point_data/'

def load_all_scores():
    """
    hexa_point_data 폴더의 모든 CSV 파일을 불러와
    파일별(b값 다름) 및 Theme별 log_score 컬럼 추가 후 반환
    """
    csv_files = glob.glob(os.path.join(CSV_FOLDER_PATH, "*_매장별_Theme_score.csv"))
    if not csv_files:

        return pd.DataFrame()

    # 모든 CSV 파일을 하나의 리스트로 읽음
    all_dfs = []
    b_values_dict = {}  # CSV 파일별 b 값 저장

    for file in csv_files:
        df = pd.read_csv(file)
        file_name = os.path.basename(file)
        df['FileName'] = file_name  # CSV 파일명 추가
        all_dfs.append(df)

        # 유형별 b 값 계산
        themes = df['Theme'].unique()
        file_b_values = {}

        for theme in themes:
            theme_data = df[df['Theme'] == theme]['final_theme_score']
            min_value = math.floor(theme_data.min())

            if min_value < 0:
                b = abs(min_value) + 1
            elif min_value == 0:
                b = 1
            else:
                b = 0

            file_b_values[theme] = b

        b_values_dict[file_name] = file_b_values
        print(f"📊 [파일명: {file_name}] 유형별 b 값:", file_b_values)

    # 모든 CSV를 하나로 합침
    merged_df = pd.concat(all_dfs, ignore_index=True)

    # 로그 변환 함수
    def log_transform(x, b):
        return np.log(x + b)

    # merged_df에 log_score 컬럼 추가 (파일별 b값 적용)
    def apply_log_transform(row):
        file_name = row['FileName']
        theme = row['Theme']
        b = b_values_dict[file_name].get(theme, 0)
        return log_transform(row['final_theme_score'], b)

    merged_df['log_score'] = merged_df.apply(apply_log_transform, axis=1)

    print("\n📊 merged_df (로그 점수 포함):")
    print(merged_df.head())

    return merged_df, b_values_dict

def get_scores_from_all_csv(store_name, labels, file_name_keyword):
    """
    주어진 매장명(store_name)과 유형(file_name_keyword),
    chart_info의 labels(Theme 목록)에 맞는 'log_score'를 가져옴.
    """
    df, _ = load_all_scores()

    # 파일명 기반 필터링
    type_df = df[df['FileName'].str.contains(file_name_keyword)]

    # 매장명 필터링
    store_df = type_df[type_df['Store'] == store_name]

    scores = []
    for theme in labels:
        theme_score = store_df.loc[store_df['Theme'] == theme, 'log_score']
        scores.append(theme_score.values[0] if not theme_score.empty else 0)

    return np.array(scores)
def get_scores_from_all_csv(store_name, labels, file_name_keyword):
    """
    주어진 데이터프레임(df)에서 특정 매장(store_name)의 유형(file_name_keyword)
    및 Theme(labels)에 맞는 'log_score'를 반환.

    Args:
        df (pd.DataFrame): CSV 파일을 합친 전체 데이터프레임
        store_name (str): 선택된 매장명
        labels (list): Theme 목록
        file_name_keyword (str): 유형 키워드 (예: '수다형', '카공형' 등)

    Returns:
        np.array: Theme 순서에 맞는 로그 점수 리스트
    """
    df, _ = load_all_scores()

    # 파일명 기반 필터링
    type_df = df[df['FileName'].str.contains(file_name_keyword)]

    # 매장명 필터링
    store_df = type_df[type_df['Store'] == store_name]

    scores = []
    for theme in labels:
        theme_score = store_df.loc[store_df['Theme'] == theme, 'log_score']
        scores.append(theme_score.values[0] if not theme_score.empty else 0)

    return np.array(scores)