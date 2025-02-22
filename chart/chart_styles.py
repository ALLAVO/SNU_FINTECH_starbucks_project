import matplotlib.pyplot as plt

# 한글 폰트 설정
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 폰트 깨짐 방지

# 차트 색상 매핑
color_mapping = {
    "외향형": "#fb9783",
    "내향형": "#73FFD0",
    "수다형": "#fdde8d",
    "카공형": "#96ddfd"
}

# CSS 스타일 설정
STYLES = """
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        .card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            text-align: center;
            font-family: 'AppleGothic', sans-serif;
            margin-bottom: 20px;
        }
        .card h4 {
            margin-top: 0;
            font-size: 22px;
            color: #333333;
        }
        .card p {
            font-size: 20px;
            color: #666666;
        }
        .card .score {
            font-size: 26px;
            font-weight: bold;
            color: #000000;
        }
    </style>
"""