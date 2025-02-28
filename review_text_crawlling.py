from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

def get_store_reviews(store_info):
    reviews = []
    
    # Configure Chrome options for better performance
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-images')  # Disable image loading
    driver = webdriver.Chrome(options=chrome_options)
    
    # Set page load timeout
    driver.set_page_load_timeout(30)
    
    try:
        print(f"\n{store_info['Name']} ({store_info['District']}) 리뷰 수집 시작...")
        
        # Reduce initial wait time
        driver.get(store_info['url'])
        time.sleep(2)  # Reduced from 5 to 2
        
        # Use WebDriverWait instead of fixed sleep
        wait = WebDriverWait(driver, 10)
        
        # Switch to iframe using wait
        try:
            entry_iframe = wait.until(EC.presence_of_element_located((By.ID, "entryIframe")))
            driver.switch_to.frame(entry_iframe)
        except Exception as e:
            print(f"entryIframe 전환 실패: {e}")
            return reviews
            
        # Click review button using wait
        try:
            review_button = wait.until(EC.presence_of_element_located((
                By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div/a[3]/span')))
            driver.execute_script("arguments[0].click();", review_button)
            time.sleep(1)  # Reduced from 3 to 1
        except Exception as e:
            print(f"리뷰 버튼 클릭 실패: {e}")
            return reviews
        
        # 리뷰 수집
        last_review_count = 0
        page_count = 0
        max_pages = 100  # 최대 더보기 클릭 횟수
        
        while len(reviews) < 500 and page_count < max_pages:
            # End 키를 눌러 페이지 맨 아래로 이동
            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.END)
            time.sleep(1)  # Reduced from 2 to 1
            
            # 현재 페이지의 리뷰 파싱
            review_elements = driver.find_elements(By.CSS_SELECTOR, 
                'a[role="button"][data-pui-click-code="rvshowmore"]')
            
            current_page_reviews = set()  # 현재 페이지에서 수집된 리뷰 텍스트
            
            for review in review_elements:
                if len(reviews) >= 500:
                    break
                    
                try:
                    review_text = review.get_attribute('innerText').strip()
                    
                    # Find the parent element that contains both review text and date
                    review_container = review.find_element(By.XPATH, '..')
                    
                    # Find the date element and visit count
                    try:
                        # Find parent elements until we find the one containing the info
                        parent = review_container
                        for _ in range(3):  # Try up to 3 levels up
                            try:
                                info_spans = parent.find_elements(By.CSS_SELECTOR, 'span.pui__gfuUIT')
                                if info_spans:
                                    break
                                parent = parent.find_element(By.XPATH, '..')
                            except:
                                parent = parent.find_element(By.XPATH, '..')
                        
                        if not info_spans:
                            raise Exception("Could not find info spans")
                        
                        # First span contains date information
                        date_span = info_spans[0]
                        visit_date_short = date_span.find_element(By.CSS_SELECTOR, 'time').get_attribute('innerText').strip()
                        full_date_element = date_span.find_elements(By.CSS_SELECTOR, 'span.pui__blind')[-1]
                        visit_date = full_date_element.get_attribute('innerText').strip()
                        
                        # Second span contains visit count
                        visit_count_text = info_spans[1].get_attribute('innerText').strip()
                        if '번째 방문' in visit_count_text:
                            visit_count = visit_count_text.replace('번째 방문', '').strip()
                        else:
                            visit_count = None
                        
                    except Exception as e:
                        print(f"날짜/방문횟수 파싱 에러: {str(e)}")
                        visit_date = None
                        visit_date_short = None
                        visit_count = None
                    
                    # 이미 수집된 리뷰인지 확인
                    if review_text not in current_page_reviews:
                        current_page_reviews.add(review_text)
                        
                        review_data = {
                            'store_name': store_info['Name'],
                            'district': store_info['District'],
                            'review_text': review_text,
                            'visit_date': visit_date,
                            'visit_date_short': visit_date_short,
                            'visit_count': visit_count,
                            'crawl_time': datetime.now().strftime("%Y-%m-%d")
                        }
                        
                        if not any(r['review_text'] == review_text for r in reviews):
                            reviews.append(review_data)
                        
                except Exception as e:
                    print(f"리뷰 파싱 에러: {str(e)}")
                    continue
            
            # 진행상황 출력
            if len(reviews) > last_review_count:
                print(f"수집된 리뷰 수: {len(reviews)}")
                last_review_count = len(reviews)
            
            # 더보기 버튼 클릭
            try:
                more_button = wait.until(EC.presence_of_element_located((
                    By.XPATH, '//*[@id="app-root"]/div/div/div/div[6]/div[3]/div[3]/div[2]/div/a/span')))
                driver.execute_script("arguments[0].click();", more_button)
                time.sleep(1)  # Reduced from 2 to 1
                page_count += 1
            except:
                print("더 이상 리뷰를 불러올 수 없습니다.")
                break
                
    except Exception as e:
        print(f"매장 처리 중 에러 발생: {str(e)}")
        
    finally:
        driver.quit()
        
    return reviews

def main():
    # 구별 최다 리뷰 매장 데이터 읽기
    top_stores = pd.read_csv('top_stores_by_district.csv')
    print(f"총 {len(top_stores)}개 매장 리뷰 수집 예정")
    
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_reviews = []
    
    # Add parallel processing for multiple stores
    from concurrent.futures import ThreadPoolExecutor
    import concurrent.futures
    
    with ThreadPoolExecutor(max_workers=3) as executor:  # Process 3 stores simultaneously
        future_to_store = {executor.submit(get_store_reviews, store): store 
                         for _, store in top_stores.iterrows()}
        
        for future in concurrent.futures.as_completed(future_to_store):
            store = future_to_store[future]
            try:
                store_reviews = future.result()
                all_reviews.extend(store_reviews)
                
                # Save intermediate results
                temp_df = pd.DataFrame(all_reviews)
                temp_df.to_csv(f'starbucks_top_reviews_temp_{current_time}.csv', 
                             index=False, encoding='utf-8-sig')
                
                print(f"\n{store['Name']} 완료: {len(store_reviews)}개 리뷰 수집")
                print(f"현재까지 총 {len(all_reviews)}개 리뷰 수집")
                
            except Exception as exc:
                print(f'{store["Name"]} generated an exception: {exc}')

    # 최종 결과 저장
    final_df = pd.DataFrame(all_reviews)
    output_filename = f'starbucks_top_reviews_{current_time}.csv'
    final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    print("\n크롤링 완료!")
    print(f"총 {len(all_reviews)}개의 리뷰가 수집되었습니다.")
    print(f"결과가 '{output_filename}'에 저장되었습니다.")

if __name__ == "__main__":
    main()