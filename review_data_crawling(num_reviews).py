from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import pandas as pd
from datetime import datetime

def get_starbucks_reviews():
    # 현재 시간을 파일명에 포함
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("데이터 파일 읽는 중...")
    df = pd.read_csv('starbucks_seoul_all_store_info.csv')
    print(f"총 {len(df)}개의 매장 데이터를 읽었습니다.\n")
    
    # Initialize webdriver
    print("브라우저 설정 중...")
    driver = webdriver.Chrome()
    driver.maximize_window()
    print("브라우저 설정 완료\n")
    
    # 결과를 저장할 리스트
    all_stores = []
    success_count = 0
    error_count = 0
    
    # 로그 파일 생성
    log_filename = f'crawling_log_{current_time}.txt'
    with open(log_filename, 'w', encoding='utf-8') as log_file:
        log_file.write(f"크롤링 시작 시간: {current_time}\n")
    
    print("크롤링 시작...\n")
    
    for idx, row in df.iterrows():
        store_name = row['매장명']
        address = row['주소']
        
        try:
            print(f"\n[{idx+1}/{len(df)}] {store_name} 처리 중...")
            progress = (idx + 1) / len(df) * 100
            print(f"전체 진행률: {progress:.2f}%")
            
            # Navigate to the URL with search query
            search_query = f"서울 스타벅스 {store_name}"
            url = f"https://pcmap.place.naver.com/restaurant/list?query={search_query}"
            driver.get(url)
            time.sleep(2)
            
            # Get current page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find store entry
            stores = soup.find_all('li', class_='UEzoS')
            
            store_found = False
            for store in stores:
                try:
                    # Get store name and address
                    name = store.find('span', class_='TYaxT').text.strip()
                    store_address = store.find('span', class_='Pb4bU').text.strip()
                    
                    # Check if this is the correct store
                    if store_name in name and any(part in store_address for part in address.split()):
                        # Get reviews
                        review_spans = store.find_all('span', class_='h69bs')
                        visitor_reviews = '0'
                        blog_reviews = '0'
                        
                        for span in review_spans:
                            text = span.text.strip()
                            if '방문자 리뷰' in text:
                                visitor_reviews = text.replace('방문자 리뷰', '').strip()
                            elif '블로그 리뷰' in text:
                                blog_reviews = text.replace('블로그 리뷰', '').strip()
                        
                        store_info = {
                            'Name': name,
                            'Address': store_address,
                            'Visitor_Reviews': visitor_reviews,
                            'Blog_Reviews': blog_reviews
                        }
                        
                        all_stores.append(store_info)
                        success_count += 1
                        store_found = True
                        
                        print(f"매장 정보 찾음: {name}")
                        print(f"방문자 리뷰: {visitor_reviews}, 블로그 리뷰: {blog_reviews}")
                        
                        # 로그 파일에 기록
                        with open(log_filename, 'a', encoding='utf-8') as log_file:
                            log_file.write(f"{name}: 방문자 리뷰 {visitor_reviews}, 블로그 리뷰 {blog_reviews}\n")
                        
                        break
                        
                except Exception as e:
                    print(f"개별 매장 처리 중 에러: {str(e)}")
                    continue
            
            if not store_found:
                print(f"매장을 찾을 수 없음: {store_name}")
                error_count += 1
                all_stores.append({
                    'Name': store_name,
                    'Address': address,
                    'Visitor_Reviews': '0',
                    'Blog_Reviews': '0'
                })
            
            # 중간 저장 (50개 매장마다)
            if (idx + 1) % 50 == 0:
                temp_df = pd.DataFrame(all_stores)
                temp_df.to_csv(f'starbucks_reviews_temp_{current_time}.csv', 
                             index=False, encoding='utf-8-sig')
                print(f"\n중간 저장 완료 ({idx+1}개 매장 처리)\n")
            
        except Exception as e:
            print(f"에러 발생 - {store_name}: {str(e)}")
            error_count += 1
            all_stores.append({
                'Name': store_name,
                'Address': address,
                'Visitor_Reviews': '0',
                'Blog_Reviews': '0'
            })
            continue
        
        time.sleep(2)  # 너무 빠른 요청 방지
    
    # Save final results
    final_df = pd.DataFrame(all_stores)
    output_filename = f'starbucks_reviews_{current_time}.csv'
    final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    # 최종 통계 출력
    print("\n크롤링 완료!")
    print(f"총 처리 매장 수: {len(df)}")
    print(f"성공: {success_count}개")
    print(f"실패: {error_count}개")
    print(f"성공률: {(success_count/len(df))*100:.2f}%")
    print(f"\n결과 파일 저장 완료: {output_filename}")
    print(f"로그 파일 저장 완료: {log_filename}")
    
    # Close the browser
    driver.quit()
    
    return final_df

# Run the scraper
if __name__ == "__main__":
    print("스타벅스 리뷰 정보 수집을 시작합니다...")
    df = get_starbucks_reviews()
    print("\n수집 완료!")