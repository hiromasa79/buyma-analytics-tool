# scraper.py (日付指定成功時のコード)

import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options

def scrape_product_details(driver, product_url):
    details = {
        'brand_name': '取得失敗', 'category_1': '', 'category_2': '', 'category_3': '',
        'access_count': '取得失敗', 'wish_count': '取得失敗', 'inquiry_count': '取得失敗',
        'price': '取得失敗', 'origin_place': '取得失敗', 'shipping_place': '取得失敗'
    }
    try:
        driver.get(product_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 's_brand')))
        detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        brand_tag = detail_soup.find('a', class_='brand-link')
        if brand_tag: details['brand_name'] = brand_tag.text.strip()
        
        all_ulikelinks = detail_soup.find_all('a', class_='ulinelink')
        temp_categories = []
        found_main_cat = False
        for link in all_ulikelinks:
            text = link.text.strip()
            if '×' in text:
                if not found_main_cat:
                    all_matches = re.findall(r'（(.*?)）', text)
                    if all_matches:
                        details['category_1'] = all_matches[-1]
                        found_main_cat = True
                sub_cat_match = re.search(r'×\s*(.*?)(?=\s*（|$)', text)
                if sub_cat_match: temp_categories.append(sub_cat_match.group(1))
        details['category_2'] = temp_categories[0] if len(temp_categories) > 0 else ''
        details['category_3'] = temp_categories[1] if len(temp_categories) > 1 else ''
        details['access_count'] = detail_soup.find('span', class_='ac_count').text.strip() if detail_soup.find('span', class_='ac_count') else '取得失敗'
        wish_tag = detail_soup.find('span', class_='fav_count')
        details['wish_count'] = wish_tag.text.strip().replace('人', '') if wish_tag else '取得失敗'
        details['inquiry_count'] = detail_soup.find('p', id='tabmenu_inqcnt').text.strip() if detail_soup.find('p', id='tabmenu_inqcnt') else '取得失敗'
        details['price'] = detail_soup.find('span', class_='price_txt').text.strip() if detail_soup.find('span', class_='price_txt') else '取得失敗'
        buying_area = detail_soup.find('dl', id='s_buying_area')
        details['origin_place'] = buying_area.find('a').text.strip() if buying_area and buying_area.find('a') else '取得失敗'
        shipment_area = detail_soup.find('dl', id='s_shipment_area')
        details['shipping_place'] = shipment_area.find('dd').text.strip() if shipment_area and shipment_area.find('dd') else '取得失敗'
    except Exception as e:
        print(f"詳細取得エラー: {e}")
    return details

def analyze_buyma(base_url, start_date_str, end_date_str):
    if not base_url or not base_url.startswith('https://www.buyma.com'):
        print("不正なURLのため処理を中断します。")
        return []
        
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        BASE_URL_DOMAIN = 'https://www.buyma.com'
        all_product_base_info = []
        
        driver.get(base_url)
        
        page_count = 1
        stop_scraping = False
        while not stop_scraping:
            print(f"リストページ収集中: {page_count} ページ目")
            time.sleep(1)
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.buyeritemtable_body')))
            except TimeoutException:
                print("ページの読み込みがタイムアウトしました。")
                break

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_boxes = soup.find_all('div', class_='buyeritemtable_body')
            if not product_boxes:
                print("商品リストが見つかりません。")
                break

            for box in product_boxes:
                contract_date_text = '取得失敗'
                p_tags = box.find_all('p')
                for p in p_tags:
                    if '成約日' in p.text:
                        contract_date_text = p.text
                        break
                
                if contract_date_text == '取得失敗': continue
                
                date_match = re.search(r'(\d{4}/\d{2}/\d{2})', contract_date_text)
                if not date_match: continue
                
                item_date = datetime.strptime(date_match.group(1), '%Y/%m/%d')

                if item_date < start_date:
                    print("指定された開始日より古いデータに到達したため、リスト収集を終了します。")
                    stop_scraping = True
                    break
                
                if start_date <= item_date <= end_date:
                    name_tag = box.find('p', class_='buyeritem_name')
                    name = name_tag.text.strip() if name_tag else '名前取得失敗'
                    product_link_tag = name_tag.find('a') if name_tag else None
                    partial_url = product_link_tag['href'] if product_link_tag else ''
                    full_url = BASE_URL_DOMAIN + partial_url if partial_url else 'URL取得失敗'
                    
                    image_tag_in_list = box.find('img')
                    image_url_in_list = image_tag_in_list.get('src', '') if image_tag_in_list else ''
                    listing_match = re.search(r'/item/(\d{6})/', image_url_in_list)
                    listing_date = f"20{listing_match.group(1)[:2]}-{listing_match.group(1)[2:4]}-{listing_match.group(1)[4:]}" if listing_match else '取得失敗'
                    
                    order_count = '不明'
                    for p in p_tags:
                        if '注文数' in p.text:
                            order_count = p.text.strip().replace('注文数', '').replace(':', '').replace('：', '').strip()
                            break

                    all_product_base_info.append({
                        '商品名': name, '商品ページURL': full_url, 
                        '注文情報': order_count, '成約日': item_date.strftime('%Y-%m-%d'), 
                        '出品日': listing_date
                    })
            
            if stop_scraping: break

            try:
                next_button = driver.find_element(By.LINK_TEXT, '次へ')
                driver.execute_script("arguments[0].click();", next_button)
                page_count += 1
            except (NoSuchElementException, TimeoutException):
                print("「次へ」ボタンが見つかりません。最後のページです。")
                break

        final_results = []
        if all_product_base_info:
            main_window = driver.current_window_handle
            for i, base_info in enumerate(all_product_base_info):
                print(f"詳細情報取得中 ({i+1}/{len(all_product_base_info)})")
                details = {}
                if base_info['商品ページURL'] != 'URL取得失敗':
                    try:
                        driver.switch_to.new_window('tab')
                        details = scrape_product_details(driver, base_info['商品ページURL'])
                        driver.close()
                        driver.switch_to.window(main_window)
                    except Exception as e:
                        print(f"詳細ページアクセスエラー: {e}")
                        if len(driver.window_handles) > 1: driver.close()
                        driver.switch_to.window(main_window)
                
                product_info = {
                    '商品名': base_info.get('商品名'), 'ブランド名': details.get('brand_name'),
                    '大カテゴリ': details.get('category_1'), '中カテゴリ': details.get('category_2'), '小カテゴリ': details.get('category_3'),
                    '価格': details.get('price'), 'アクセス数': details.get('access_count'),
                    'お気に入り登録数': details.get('wish_count'), 'お問い合わせ数': details.get('inquiry_count'),
                    '注文情報': base_info.get('注文情報'), '成約日': base_info.get('成約日'), '出品日': base_info.get('出品日'),
                    '買付地': details.get('origin_place'), '発送地': details.get('shipping_place'),
                    '商品ページURL': base_info.get('商品ページURL')
                }
                final_results.append(product_info)
        
        return final_results

    except WebDriverException as e:
        print(f"WebDriverでエラーが発生しました: {e}")
        return []
    finally:
        if driver:
            driver.quit()