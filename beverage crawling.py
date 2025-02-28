import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re

def clean_menu_name(name):
    # (Trenta) 또는 다른 사이즈 정보를 제거
    return re.sub(r'\([^)]*\)', '', name).strip()

def get_menu_images(soup):
    menu_images = {}
    products = soup.select('li.menuDataSet')
    
    for product in products:
        img_element = product.select_one('dl dt a img')
        name_element = product.select_one('dl dd')
        
        if name_element and img_element:
            # 원본 메뉴 이름과 정제된 메뉴 이름 모두 저장
            original_name = name_element.text.strip()
            cleaned_name = clean_menu_name(original_name)
            img_url = img_element.get('src', '')
            
            # 원본 이름과 정제된 이름 모두에 대해 이미지 URL 매핑
            menu_images[original_name] = img_url
            menu_images[cleaned_name] = img_url
            
    print(f"Found {len(menu_images)} menu items with images")
    return menu_images

def crawl_starbucks_nutrition():
    driver = webdriver.Chrome()
    driver.get('https://www.starbucks.co.kr/menu/drink_list.do')
    
    try:
        time.sleep(3)
        
        # 초기 페이지에서 메뉴 이미지 정보 수집
        initial_soup = BeautifulSoup(driver.page_source, 'html.parser')
        menu_images = get_menu_images(initial_soup)
        
        # 영양정보로 보기 버튼 클릭
        nutrition_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="container"]/div[2]/div[2]/div/dl/dt[2]/a'))
        )
        nutrition_btn.click()
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        all_drinks = []
        categories = soup.find_all('h3')
        
        for category in categories:
            category_name = category.text.strip()
            table = category.find_next('table')
            if not table:
                continue
                
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 7:
                    menu_name = cols[0].text.strip()
                    cleaned_menu_name = clean_menu_name(menu_name)
                    
                    # 원본 이름과 정제된 이름으로 이미지 URL 찾기 시도
                    img_url = menu_images.get(menu_name, menu_images.get(cleaned_menu_name, ''))
                    
                    drink_info = {
                        '카테고리': category_name,
                        '메뉴': menu_name,
                        '이미지_URL': img_url,
                        '칼로리(Kcal)': cols[1].text.strip(),
                        '당류(g)': cols[2].text.strip(),
                        '단백질(g)': cols[3].text.strip(),
                        '나트륨(mg)': cols[4].text.strip(),
                        '포화지방(g)': cols[5].text.strip(),
                        '카페인(mg)': cols[6].text.strip()
                    }
                    all_drinks.append(drink_info)
        
        df = pd.DataFrame(all_drinks)
        
        # 숫자형 데이터 변환
        numeric_columns = ['칼로리(Kcal)', '당류(g)', '단백질(g)', '나트륨(mg)', '포화지방(g)', '카페인(mg)']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # CSV 파일로 저장
        df.to_csv('starbucks_nutrition_with_images.csv', index=False, encoding='utf-8-sig')
        
        # 결과 출력
        print("\n=== 크롤링 결과 ===")
        print(f"총 메뉴 수: {len(df)}")
        print("\n카테고리별 메뉴 수:")
        print(df['카테고리'].value_counts())
        print("\n이미지 URL 수집 현황:")
        print(f"이미지 URL이 있는 메뉴 수: {df['이미지_URL'].str.len().gt(0).sum()}")
        print(f"이미지 URL이 없는 메뉴 수: {df['이미지_URL'].str.len().eq(0).sum()}")
        
        if df['이미지_URL'].str.len().eq(0).sum() > 0:
            print("\n이미지 URL이 없는 메뉴:")
            print(df[df['이미지_URL'] == '']['메뉴'].tolist())
        
        return df
        
    finally:
        driver.quit()

if __name__ == "__main__":
    df = crawl_starbucks_nutrition()
    print("\n크롤링이 완료되었습니다.")