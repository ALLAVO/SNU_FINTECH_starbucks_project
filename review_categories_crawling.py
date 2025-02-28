from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
from datetime import datetime

def get_store_keywords(store_info):
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 10)
    displayed_name = None
    
    try:
        store_name = store_info['매장명']
        address = store_info['주소'].split('(')[0].split(',')[0].strip()
        print(f"\n{store_name} 키워드 수집 시작...")
        driver.get(f"https://map.naver.com/p/search/{address} 스타벅스 {store_name}점")
        time.sleep(2)
        
        search_frame = wait.until(EC.presence_of_element_located((By.ID, "searchIframe")))
        driver.switch_to.frame(search_frame)
        
        try:
            first_result = driver.find_element(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]/ul/li/div[1]/a/div/div')
            driver.execute_script("arguments[0].click();", first_result)
        except:
            time.sleep(0)
        
        driver.switch_to.default_content()
        time.sleep(1)
        
        entry_frame = wait.until(EC.presence_of_element_located((By.ID, "entryIframe")))
        driver.switch_to.frame(entry_frame)
        
        try:
            displayed_name = driver.find_element(By.CSS_SELECTOR, "span.GHAhO").text
        except:
            displayed_name = store_name
        
        review_button = wait.until(EC.presence_of_element_located((
            By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div/a[3]/span')))
        driver.execute_script("arguments[0].click();", review_button)
        time.sleep(3)
        
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)

        while True:
            try:
                more_button = driver.find_element(By.XPATH, '//*[@id="app-root"]/div/div/div/div[6]/div[3]/div[1]/div/div/div[2]/div/a/span[1]')
                driver.execute_script("arguments[0].click();", more_button)
                time.sleep(1)
            except:
                break
        
        time.sleep(2)
        keywords = {}
        keyword_elements = driver.find_elements(By.CSS_SELECTOR, "li.MHaAm")
        
        for element in keyword_elements:
            try:
                text_element = element.find_element(By.CSS_SELECTOR, "span.t3JSf")
                count_text = element.find_element(By.CSS_SELECTOR, "span.CUoLy").text
                count = int(count_text.split('\n')[-1])
                
                keyword = text_element.text.strip('"')
                keywords[keyword] = count
            except Exception as e:
                print(f"키워드 파싱 오류: {str(e)}")
                continue
                
        return keywords, displayed_name
        
    except Exception as e:
        print(f"에러 발생: {str(e)}")
        return None, None
        
    finally:
        driver.quit()

def main():
    df = pd.read_csv('starbucks_seoul_all_store_info.csv', encoding='utf-8')
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []
    failed_stores = []
    
    for idx, row in df.iterrows():
        store_info = row
        keywords, displayed_name = get_store_keywords(store_info)
        
        if keywords:
            for keyword, count in keywords.items():
                result = {
                    'store_name': store_info['매장명'],
                    'displayed_name': displayed_name,
                    'keyword': keyword,
                    'count': count
                }
                results.append(result)
                print(f"{store_info['매장명']} ({displayed_name}) - {keyword}: {count}")
        else:
            failed_stores.append(store_info['매장명'])
            
        if idx % 5 == 0:
            if results:
                pd.DataFrame(results).to_csv(f'keywords_result_temp_{current_time}.csv', 
                                           index=False, encoding='utf-8-sig')
            if failed_stores:
                pd.DataFrame({'store_name': failed_stores}).to_csv(
                    f'failed_stores_{current_time}.csv', index=False, encoding='utf-8-sig')
                
        print(f"\n진행률: {idx + 1}/{len(df)} ({((idx + 1)/len(df))*100:.1f}%)\n")
    
    if results:
        pd.DataFrame(results).to_csv(f'keywords_result_final_{current_time}.csv', 
                                    index=False, encoding='utf-8-sig')
    if failed_stores:
        pd.DataFrame({'store_name': failed_stores}).to_csv(
            f'failed_stores_final_{current_time}.csv', index=False, encoding='utf-8-sig')
        print(f"\n크롤링 실패한 매장 수: {len(failed_stores)}")
    
    print(f"\n크롤링 완료! 총 {len(df)}개의 매장 중 {len(df)-len(failed_stores)}개 성공")

if __name__ == "__main__":
    main()