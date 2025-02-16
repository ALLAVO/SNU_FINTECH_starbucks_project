import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import math

# CSV 파일 읽기
df = pd.read_csv('/Users/hyungjuncho/Documents/SNU_BFA/visual/streamlit_starbucks.2/hexa_point_data/수다형_테마_키워드_매장별_Theme_score.csv')

# 모든 unique한 theme 추출
themes = df['Theme'].unique()

# 테마별 전처리(로그 변환 함수) 정의
def log_transform(x, b):
    return np.log(x + b)

# b값을 저장할 딕셔너리 생성
b_values = {}

# 테마별 데이터 전처리 및 로그 변환
for theme in themes:
    theme_data = df[df['Theme'] == theme]['final_theme_score']
    min_value = math.floor(theme_data.min())

    if min_value < 0:
        b = abs(min_value) + 1
    elif min_value == 0:
        b = 1
    else:
        b = 0

    b_values[theme] = b  # b값 저장
    df.loc[df['Theme'] == theme, 'log_score'] = log_transform(theme_data, b)
    print(f"📝 로그 변환 샘플 (5개): { log_transform(theme_data, b).head().values}")

# 2행 3열의 서브플롯 설정
fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle('Distribution of Log-Transformed Theme Scores', fontsize=16)

# axes를 1차원 배열로 변환
axes = axes.flatten()

for i, theme in enumerate(themes):
    theme_data = df[df['Theme'] == theme]['log_score']
    #
    # # 히스토그램 그리기
    # sns.histplot(data=theme_data, kde=True, ax=axes[i])
    # axes[i].set_title(f'{theme} Distribution')
    # axes[i].set_xlabel(f'Log(Score + {b_values[theme]})')  # b값 포함
    # axes[i].set_ylabel('Count')

    # 통계량 계산
    mean = theme_data.mean()
    std = theme_data.std()
    q1, q2, q3 = theme_data.quantile([0.25, 0.5, 0.75])
    max_val = theme_data.max()

    # 통계량 텍스트로 추가
    stats_text = (f'Mean: {mean:.2f}\n'
                  f'Std: {std:.2f}\n'
                  f'Q1: {q1:.2f}\n'
                  f'Q2 (Median): {q2:.2f}\n'
                  f'Q3: {q3:.2f}\n'
                  f'Max: {max_val:.2f}\n'
                  f'b: {b_values[theme]}')  # b값 추가
    # axes[i].text(0.95, 0.95, stats_text,
    #              transform=axes[i].transAxes,
    #              fontsize=10,
    #              verticalalignment='top',
    #              horizontalalignment='right',
    #              bbox=dict(facecolor='white', alpha=0.8))

# 남은 서브플롯 제거 (테마가 6개 미만인 경우)
for j in range(i+1, 6):
    fig.delaxes(axes[j])

plt.tight_layout()
plt.show()